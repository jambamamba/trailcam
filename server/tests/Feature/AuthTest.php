<?php

/*
|--------------------------------------------------------------------------
| AUTH-01..18 (WI-101 — Laravel + WebAuthn scaffold)
|--------------------------------------------------------------------------
|
| In-process mirror of the HTTP suite in tests/test.py (the catalog
| authority). Ceremonies are driven by the PHP FakeAuthenticator so the
| server-side web-auth/webauthn-lib verification runs exactly as in
| production.
|
*/

use Illuminate\Testing\TestResponse;
use Tests\Support\FakeAuthenticator;

function auth_unique_handle(): string
{
    return 'p'.bin2hex(random_bytes(6));
}

/**
 * Full registration ceremony.
 *
 * @return array{0: string, 1: FakeAuthenticator, 2: TestResponse}
 */
function auth_register(object $t, ?FakeAuthenticator $authenticator = null): array
{
    $handle = auth_unique_handle();
    $authenticator ??= new FakeAuthenticator();

    $begin = $t->postJson('/auth/register/begin', [
        'handle' => $handle,
        'email' => $handle.'@example.com',
    ]);
    $begin->assertOk();

    $credential = $authenticator->create($begin->json('publicKey'), config('webauthn.origin'));
    $complete = $t->postJson('/auth/register/complete', ['response' => $credential]);
    $complete->assertStatus(201);

    return [$handle, $authenticator, $complete];
}

/** Session cookie line from a response (everything except the XSRF token). */
function auth_session_cookie_line(TestResponse $response): string
{
    $lines = array_map(
        static fn ($cookie): string => (string) $cookie,
        $response->headers->getCookies(),
    );
    foreach ($lines as $line) {
        if (! str_starts_with($line, 'XSRF-TOKEN=')) {
            return $line;
        }
    }

    return '';
}

/**
 * @return list<string>
 */
function auth_cookie_attributes(string $setCookieLine): array
{
    $parts = explode(';', $setCookieLine);
    array_shift($parts);

    return array_map(static fn (string $part): string => trim($part), $parts);
}

test('AUTH-01: register begin returns creation options', function () {
    $response = $this->postJson('/auth/register/begin', [
        'handle' => auth_unique_handle(),
        'email' => auth_unique_handle().'@example.com',
    ]);

    $response->assertOk();
    $response->assertJsonStructure(['publicKey' => ['challenge', 'rp', 'user', 'pubKeyCredParams']]);
    $challenge = $response->json('publicKey.challenge');
    expect($challenge)->toBeString()->not->toBe('');
    expect($challenge)->toMatch('/^[A-Za-z0-9_-]+$/');
});

test('AUTH-02: register complete creates user + credential and opens session', function () {
    [$handle, , $complete] = auth_register($this);

    $complete->assertStatus(201);
    $complete->assertJsonPath('user.handle', $handle);
    expect(auth_session_cookie_line($complete))->not->toBe('');

    $this->getJson('/auth/status')
        ->assertOk()
        ->assertJsonPath('handle', $handle);
});

test('AUTH-03: register begin rejects duplicate handle', function () {
    [$handle] = auth_register($this);

    $this->postJson('/auth/register/begin', [
        'handle' => $handle,
        'email' => auth_unique_handle().'@example.com',
    ])->assertStatus(409);
});

test('AUTH-04: register begin rejects duplicate email', function () {
    $handle = auth_unique_handle();
    $email = $handle.'@example.com';

    $begin = $this->postJson('/auth/register/begin', ['handle' => $handle, 'email' => $email]);
    $begin->assertOk();
    $this->postJson('/auth/register/complete', [
        'response' => (new FakeAuthenticator())->create($begin->json('publicKey'), config('webauthn.origin')),
    ])->assertStatus(201);

    $this->postJson('/auth/register/begin', [
        'handle' => auth_unique_handle(),
        'email' => $email,
    ])->assertStatus(409);
});

test('AUTH-05: register begin rejects short handle', function () {
    $this->postJson('/auth/register/begin', [
        'handle' => 'ab',
        'email' => 'short@example.com',
    ])->assertStatus(422);
});

test('AUTH-06: register begin rejects invalid email', function () {
    $this->postJson('/auth/register/begin', [
        'handle' => auth_unique_handle(),
        'email' => 'not-an-email',
    ])->assertStatus(422);
});

test('AUTH-07: login begin returns request options', function () {
    [$handle] = auth_register($this);

    $response = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    $response->assertOk();
    $response->assertJsonStructure(['publicKey' => ['allowCredentials']]);
    expect($response->json('publicKey.allowCredentials'))->toBeArray()->not->toBeEmpty();
});

test('AUTH-08: login begin rejects unknown handle', function () {
    $this->postJson('/auth/login/begin', ['handle' => 'ghost-'.auth_unique_handle()])
        ->assertStatus(404);
});

test('AUTH-09: login complete verifies assertion and opens session', function () {
    [$handle, $authenticator] = auth_register($this);

    // start from a signed-out browser
    $this->postJson('/auth/logout')->assertOk();
    $this->getJson('/auth/status')->assertUnauthorized();

    $begin = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    $begin->assertOk();

    $credential = $authenticator->get($begin->json('publicKey'), config('webauthn.origin'));
    $this->postJson('/auth/login/complete', ['response' => $credential])
        ->assertOk()
        ->assertJsonPath('user.handle', $handle);

    $this->getJson('/auth/status')
        ->assertOk()
        ->assertJsonPath('handle', $handle);
});

test('AUTH-10: login complete rejects bad signature', function () {
    [$handle, $authenticator] = auth_register($this);
    $this->postJson('/auth/logout')->assertOk();

    $begin = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    $begin->assertOk();

    $credential = $authenticator->get($begin->json('publicKey'), config('webauthn.origin'), tamper: true);
    $this->postJson('/auth/login/complete', ['response' => $credential])->assertStatus(401);
    $this->getJson('/auth/status')->assertUnauthorized();
});

test('AUTH-11: status returns session (handle, role, tier)', function () {
    [$handle] = auth_register($this);

    $this->getJson('/auth/status')
        ->assertOk()
        ->assertJsonPath('handle', $handle)
        ->assertJsonPath('role', 'user')
        ->assertJsonPath('tier', 'free');
});

test('AUTH-12: status is 401 when unauthenticated', function () {
    $this->getJson('/auth/status')->assertUnauthorized();
});

test('AUTH-13: add passkey stores second credential', function () {
    [$handle] = auth_register($this);

    $second = new FakeAuthenticator();
    $begin = $this->postJson('/auth/add-passkey/begin', []);
    $begin->assertOk();

    $credential = $second->create($begin->json('publicKey'), config('webauthn.origin'));
    $this->postJson('/auth/add-passkey/complete', ['response' => $credential])
        ->assertOk()
        ->assertJsonPath('credential_id', $second->credentialIdB64());

    $listing = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    expect($listing->json('publicKey.allowCredentials'))->toHaveCount(2);
});

test('AUTH-14: delete passkey blocks removing last one', function () {
    [$handle] = auth_register($this);

    $begin = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    $begin->assertOk();
    $onlyId = $begin->json('publicKey.allowCredentials.0.id');

    $this->deleteJson("/auth/passkeys/{$onlyId}")->assertStatus(409);
});

test('AUTH-15: recovery token enrols new passkey and revokes old', function () {
    [$handle, $oldAuthenticator, $complete] = auth_register($this);
    $token = $complete->json('recovery_token');
    expect($token)->toBeString()->not->toBe('');

    $begin = $this->postJson('/auth/recovery', ['token' => $token]);
    $begin->assertOk();

    $fresh = new FakeAuthenticator();
    $credential = $fresh->create($begin->json('publicKey'), config('webauthn.origin'));
    $this->postJson('/auth/recovery', ['token' => $token, 'response' => $credential])
        ->assertOk()
        ->assertJsonPath('user.handle', $handle);

    // old credential revoked: login offers exactly the new one
    $listing = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    expect($listing->json('publicKey.allowCredentials.*.id'))
        ->toBe([$fresh->credentialIdB64()]);

    // the new passkey works
    $login = $this->postJson('/auth/login/begin', ['handle' => $handle]);
    $assertion = $fresh->get($login->json('publicKey'), config('webauthn.origin'));
    $this->postJson('/auth/login/complete', ['response' => $assertion])->assertOk();
});

test('AUTH-16: recovery rejects expired or consumed token', function () {
    [, , $complete] = auth_register($this);
    $token = $complete->json('recovery_token');

    // consume it
    $begin = $this->postJson('/auth/recovery', ['token' => $token]);
    $begin->assertOk();
    $credential = (new FakeAuthenticator())->create($begin->json('publicKey'), config('webauthn.origin'));
    $this->postJson('/auth/recovery', ['token' => $token, 'response' => $credential])->assertOk();

    // reuse (single-use → dead) → 401
    $this->postJson('/auth/recovery', ['token' => $token])->assertStatus(401);

    // never-issued token → 401
    $this->postJson('/auth/recovery', ['token' => 'nope-'.bin2hex(random_bytes(8))])
        ->assertStatus(401);
});

test('AUTH-17: logout kills session', function () {
    auth_register($this);
    $this->getJson('/auth/status')->assertOk();

    $this->postJson('/auth/logout')->assertOk();
    $this->getJson('/auth/status')->assertUnauthorized();
});

test('AUTH-18: session cookie flags (HttpOnly, Secure, SameSite=Strict)', function () {
    [, , $complete] = auth_register($this);

    $line = auth_session_cookie_line($complete);
    expect($line)->not->toBe('');

    $attributes = array_map('strtolower', auth_cookie_attributes($line));
    expect($attributes)->toContain('httponly');
    expect($attributes)->toContain('secure');
    expect($attributes)->toContain('samesite=strict');
});
