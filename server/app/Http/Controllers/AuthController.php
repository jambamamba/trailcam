<?php

namespace App\Http\Controllers;

use App\Models\Credential;
use App\Models\User;
use App\Services\WebauthnService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Validation\ValidationException;
use ParagonIE\ConstantTime\Base64UrlSafe;
use Throwable;
use Webauthn\Exception\WebauthnException;

/**
 * The wificam-style WebAuthn contract (project-plan §10, §14):
 *
 *   POST   /auth/register/begin|complete
 *   POST   /auth/add-passkey/begin|complete
 *   POST   /auth/login/begin|complete
 *   POST   /auth/logout
 *   GET    /auth/status
 *   DELETE /auth/passkeys/{id}
 *   POST   /auth/recovery
 *
 * Sessions are plain Laravel sessions with Secure/HttpOnly/SameSite=Strict
 * cookies; a session cookie is only set after a verified ceremony.
 */
class AuthController extends Controller
{
    public function __construct(private readonly WebauthnService $webauthn) {}

    // ------------------------------------------------------------------
    // Registration
    // ------------------------------------------------------------------

    public function registerBegin(Request $request): JsonResponse
    {
        $data = $request->validate([
            'handle' => ['required', 'string', 'min:3', 'max:30', 'regex:/^[A-Za-z0-9_-]+$/'],
            'email' => ['required', 'email', 'max:254'],
        ]);

        User::where('handle', $data['handle'])->exists() && abort(409, 'handle already registered');
        User::where('email', $data['email'])->exists() && abort(409, 'email already registered');

        $challenge = $this->webauthn->newChallenge();
        $userHandle = Base64UrlSafe::encodeUnpadded(random_bytes(32));

        $this->putCeremony('register', $challenge, [
            'handle' => $data['handle'],
            'email' => $data['email'],
            'user_handle' => $userHandle,
        ]);

        $options = $this->webauthn->creationOptions($challenge, $userHandle, $data['handle']);

        return response()->json(['publicKey' => $this->webauthn->toJson($options)]);
    }

    public function registerComplete(Request $request): JsonResponse
    {
        $pending = $this->requireCeremony('register');
        $request->validate(['response' => ['required', 'array']]);

        $options = $this->webauthn->creationOptions(
            $pending['challenge'],
            $pending['user_handle'],
            $pending['handle'],
        );

        try {
            $record = $this->webauthn->verifyAttestation(
                $this->webauthn->credentialFromJson((array) $request->input('response')),
                $options,
            );
        } catch (WebauthnException $e) {
            abort(401, 'registration ceremony failed: '.$e->getMessage());
        }

        $user = $this->createUser($pending['handle'], $pending['email'], $pending['user_handle']);
        Credential::create($this->webauthn->credentialDocument($record, (string) $user->getKey()));

        $recoveryToken = $this->issueRecoveryToken($user);
        $this->startSession($user);

        return response()->json([
            'user' => $this->userPayload($user),
            'recovery_token' => $recoveryToken,
        ], 201);
    }

    // ------------------------------------------------------------------
    // Add a passkey to the signed-in account
    // ------------------------------------------------------------------

    public function addPasskeyBegin(Request $request): JsonResponse
    {
        $user = $this->currentUser() ?? abort(401, 'unauthenticated');

        $challenge = $this->webauthn->newChallenge();
        $this->putCeremony('add_passkey', $challenge, ['user_id' => (string) $user->getKey()]);

        $options = $this->webauthn->creationOptions(
            $challenge,
            $user->user_handle,
            $user->handle,
            $this->credentialIds($user),
        );

        return response()->json(['publicKey' => $this->webauthn->toJson($options)]);
    }

    public function addPasskeyComplete(Request $request): JsonResponse
    {
        $pending = $this->requireCeremony('add_passkey');
        $request->validate(['response' => ['required', 'array']]);

        $user = $this->findUser($pending['user_id']) ?? abort(401, 'unauthenticated');

        $options = $this->webauthn->creationOptions(
            $pending['challenge'],
            $user->user_handle,
            $user->handle,
            $this->credentialIds($user),
        );

        try {
            $record = $this->webauthn->verifyAttestation(
                $this->webauthn->credentialFromJson((array) $request->input('response')),
                $options,
            );
        } catch (WebauthnException $e) {
            abort(401, 'add-passkey ceremony failed: '.$e->getMessage());
        }

        $document = $this->webauthn->credentialDocument($record, (string) $user->getKey());
        try {
            Credential::create($document);
        } catch (Throwable $e) {
            $this->rethrowUnlessDuplicate($e);
            abort(409, 'credential already enrolled');
        }

        $recoveryToken = $this->issueRecoveryToken($user);
        $this->refreshSession($user);

        return response()->json([
            'credential_id' => $document['credential_id'],
            'recovery_token' => $recoveryToken,
        ]);
    }

    // ------------------------------------------------------------------
    // Login
    // ------------------------------------------------------------------

    public function loginBegin(Request $request): JsonResponse
    {
        $data = $request->validate([
            'handle' => ['required', 'string', 'max:30'],
        ]);

        $user = User::where('handle', $data['handle'])->first();
        $user !== null || abort(404, 'unknown handle');

        $credentialIds = $this->credentialIds($user);
        $credentialIds !== [] || abort(404, 'no passkeys enrolled');

        $challenge = $this->webauthn->newChallenge();
        $this->putCeremony('login', $challenge, [
            'user_id' => (string) $user->getKey(),
            'allow' => $credentialIds,
        ]);

        $options = $this->webauthn->requestOptions($challenge, $credentialIds);

        return response()->json(['publicKey' => $this->webauthn->toJson($options)]);
    }

    public function loginComplete(Request $request): JsonResponse
    {
        $pending = $this->requireCeremony('login');
        $request->validate(['response' => ['required', 'array']]);

        $user = $this->findUser($pending['user_id']) ?? abort(401, 'unknown credential');

        $options = $this->webauthn->requestOptions($pending['challenge'], $pending['allow'] ?? []);

        try {
            $credentialJson = $this->webauthn->credentialFromJson((array) $request->input('response'));
            $credential = Credential::where('user_id', (string) $user->getKey())
                ->where('credential_id', Base64UrlSafe::encodeUnpadded($credentialJson->rawId))
                ->first();
            $credential !== null || abort(401, 'unknown credential');

            $record = $this->webauthn->verifyAssertion($credential, $credentialJson, $options, $user->user_handle);
        } catch (WebauthnException $e) {
            abort(401, 'login ceremony failed: '.$e->getMessage());
        }

        $credential->update([
            'counter' => $record->counter,
            'backup_eligible' => $record->backupEligible,
            'backup_status' => $record->backupStatus,
            'uv_initialized' => $record->uvInitialized,
        ]);

        $this->startSession($user);

        return response()->json(['user' => $this->userPayload($user)]);
    }

    // ------------------------------------------------------------------
    // Session
    // ------------------------------------------------------------------

    public function status(Request $request): JsonResponse
    {
        $user = $this->currentUser() ?? abort(401, 'unauthenticated');

        return response()->json([
            'authenticated' => true,
            'handle' => $user->handle,
            'role' => $user->role,
            'tier' => $user->tier,
        ]);
    }

    public function logout(Request $request): JsonResponse
    {
        session()->invalidate();

        return response()->json(['ok' => true]);
    }

    // ------------------------------------------------------------------
    // Passkey management
    // ------------------------------------------------------------------

    public function destroyPasskey(Request $request, string $id): JsonResponse
    {
        $user = $this->currentUser() ?? abort(401, 'unauthenticated');

        $credential = Credential::where('user_id', (string) $user->getKey())
            ->where('credential_id', $id)
            ->first();
        $credential !== null || abort(404, 'unknown passkey');

        $remaining = Credential::where('user_id', (string) $user->getKey())->count();
        $remaining > 1 || abort(409, 'cannot remove the last passkey');

        $credential->delete();

        return response()->json(['ok' => true, 'remaining' => $remaining - 1]);
    }

    // ------------------------------------------------------------------
    // Recovery (single endpoint, two phases: challenge → attestation)
    // ------------------------------------------------------------------

    public function recovery(Request $request): JsonResponse
    {
        $data = $request->validate([
            'token' => ['required', 'string', 'max:128'],
            'response' => ['sometimes', 'array'],
        ]);

        $hash = hash('sha256', $data['token']);
        $user = User::where('recovery_token.hash', $hash)->first();
        $stored = $user?->recovery_token;
        if (is_object($stored)) {
            $stored = (array) $stored; // BSON document → array
        }

        $valid = $user !== null
            && is_array($stored)
            && ($stored['hash'] ?? null) === $hash
            && ! empty($stored['expires_at'])
            && Carbon::parse($stored['expires_at'])->isFuture();
        $valid || abort(401, 'invalid or expired recovery token');

        $session = (array) session('webauthn', []);
        $readyToComplete = ($session['purpose'] ?? null) === 'recovery'
            && ($session['token_hash'] ?? null) === $hash
            && $request->has('response');

        if (! $readyToComplete) {
            $challenge = $this->webauthn->newChallenge();
            $this->putCeremony('recovery', $challenge, [
                'user_id' => (string) $user->getKey(),
                'token_hash' => $hash,
            ]);

            $options = $this->webauthn->creationOptions($challenge, $user->user_handle, $user->handle);

            return response()->json(['publicKey' => $this->webauthn->toJson($options)]);
        }

        $options = $this->webauthn->creationOptions(
            $session['challenge'],
            $user->user_handle,
            $user->handle,
        );

        try {
            $record = $this->webauthn->verifyAttestation(
                $this->webauthn->credentialFromJson((array) $request->input('response')),
                $options,
            );
        } catch (WebauthnException $e) {
            abort(401, 'recovery ceremony failed: '.$e->getMessage());
        }

        // Enrol the new passkey, revoke every old one, consume + re-issue the token.
        Credential::where('user_id', (string) $user->getKey())->delete();
        Credential::create($this->webauthn->credentialDocument($record, (string) $user->getKey()));

        $recoveryToken = $this->issueRecoveryToken($user);
        $this->startSession($user);

        return response()->json([
            'user' => $this->userPayload($user),
            'recovery_token' => $recoveryToken,
        ]);
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    private function createUser(string $handle, string $email, string $userHandle): User
    {
        try {
            return User::create([
                'handle' => $handle,
                'email' => $email,
                'role' => 'user',
                'tier' => 'free',
                'user_handle' => $userHandle,
                'push_tokens' => [],
            ]);
        } catch (Throwable $e) {
            $this->rethrowUnlessDuplicate($e);
            abort(409, 'handle or email already registered');
        }
    }

    /** @return list<string> base64url credential ids for the user */
    private function credentialIds(User $user): array
    {
        return Credential::where('user_id', (string) $user->getKey())
            ->pluck('credential_id')
            ->map(fn ($id) => (string) $id)
            ->values()
            ->all();
    }

    private function issueRecoveryToken(User $user): string
    {
        $token = Base64UrlSafe::encodeUnpadded(random_bytes(32));
        $user->update([
            'recovery_token' => [
                'hash' => hash('sha256', $token),
                'expires_at' => Carbon::now()
                    ->addMinutes((int) config('webauthn.recovery_ttl_minutes'))
                    ->toIso8601String(),
            ],
        ]);

        return $token;
    }

    private function currentUser(): ?User
    {
        $id = session('user_id');

        return is_string($id) && $id !== '' ? $this->findUser($id) : null;
    }

    private function findUser(string $id): ?User
    {
        return User::where('_id', $id)->first();
    }

    /** @return array{handle: string, role: string, tier: string} */
    private function userPayload(User $user): array
    {
        return [
            'handle' => $user->handle,
            'role' => $user->role,
            'tier' => $user->tier,
        ];
    }

    private function startSession(User $user): void
    {
        session()->regenerate();
        session()->put('user_id', (string) $user->getKey());
        session()->forget('webauthn');
    }

    private function refreshSession(User $user): void
    {
        $this->startSession($user);
    }

    /**
     * @param  array<string, mixed>  $state
     * @return array{purpose: string, challenge: string} & array<string, mixed>
     */
    private function putCeremony(string $purpose, string $challenge, array $state): array
    {
        $ceremony = $state + ['challenge' => $challenge, 'purpose' => $purpose];
        session()->put('webauthn', $ceremony);

        return $ceremony;
    }

    /**
     * @return array{purpose: string, challenge: string} & array<string, mixed>
     */
    private function requireCeremony(string $purpose): array
    {
        $ceremony = (array) session('webauthn', []);
        (($ceremony['purpose'] ?? null) === $purpose && isset($ceremony['challenge']))
            || abort(400, 'ceremony not started or expired');

        return $ceremony;
    }

    private function rethrowUnlessDuplicate(Throwable $e): void
    {
        $message = $e->getMessage();
        $isDuplicate = str_contains($message, 'E11000')
            || str_contains($message, 'duplicate key')
            || (string) $e->getCode() === '11000';

        $isDuplicate || throw $e;
    }
}
