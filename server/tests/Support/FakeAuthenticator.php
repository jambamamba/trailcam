<?php

namespace Tests\Support;

use ParagonIE\ConstantTime\Base64UrlSafe;
use RuntimeException;

/**
 * Software authenticator for the Pest ceremonies — PHP twin of the
 * FakeAuthenticator in tests/test.py. Emits standards-compliant
 * `navigator.credentials.create/get` payloads (fmt=none, ES256/P-256) so the
 * server's real web-auth/webauthn-lib verification runs unmodified.
 */
final class FakeAuthenticator
{
    /** @var \OpenSSLAsymmetricKey */
    private $key;

    private string $x;

    private string $y;

    private string $credentialId;

    private int $signCount = 0;

    public function __construct()
    {
        $this->key = self::newKey();
        $details = openssl_pkey_get_details($this->key);
        $this->x = str_pad($details['ec']['x'], 32, "\x00", STR_PAD_LEFT);
        $this->y = str_pad($details['ec']['y'], 32, "\x00", STR_PAD_LEFT);
        $this->credentialId = random_bytes(32);
    }

    public function credentialIdB64(): string
    {
        return $this->b64($this->credentialId);
    }

    /** Client payload for the *complete endpoints (attestation). */
    public function create(array $options, string $origin): array
    {
        $clientData = $this->clientDataJson('webauthn.create', $options['challenge'], $origin);
        $rpHash = hash('sha256', $options['rp']['id'], true);
        $authData = $rpHash
            . "\x45"                       // flags: UP | UV | AT
            . pack('N', $this->signCount)
            . str_repeat("\x00", 16)       // aaguid
            . pack('n', strlen($this->credentialId))
            . $this->credentialId
            . $this->coseKey();

        $attestation = $this->cborMap([
            [$this->cborText('fmt'), $this->cborText('none')],
            [$this->cborText('attStmt'), $this->cborMap([])],
            [$this->cborText('authData'), $this->cborBytes($authData)],
        ]);

        return [
            'id' => $this->b64($this->credentialId),
            'rawId' => $this->b64($this->credentialId),
            'type' => 'public-key',
            'response' => [
                'clientDataJSON' => $this->b64($clientData),
                'attestationObject' => $this->b64($attestation),
                'transports' => ['internal'],
            ],
        ];
    }

    /** Client payload for login/complete (assertion). */
    public function get(array $options, string $origin, bool $tamper = false): array
    {
        $clientData = $this->clientDataJson('webauthn.get', $options['challenge'], $origin);
        $rpHash = hash('sha256', $options['rpId'], true);
        $authData = $rpHash . "\x05" . pack('N', $this->signCount); // flags: UP | UV
        $signature = $this->sign($authData . hash('sha256', $clientData, true), $tamper);

        return [
            'id' => $this->b64($this->credentialId),
            'rawId' => $this->b64($this->credentialId),
            'type' => 'public-key',
            'response' => [
                'clientDataJSON' => $this->b64($clientData),
                'authenticatorData' => $this->b64($authData),
                'signature' => $this->b64($signature),
            ],
        ];
    }

    // ------------------------------------------------------------------
    // Internals
    // ------------------------------------------------------------------

    private static function newKey()
    {
        $key = openssl_pkey_new([
            'curve_name' => 'prime256v1',
            'private_key_type' => OPENSSL_KEYTYPE_EC,
        ]);
        $key instanceof \OpenSSLAsymmetricKey || throw new RuntimeException('openssl_pkey_new failed');

        return $key;
    }

    private function clientDataJson(string $type, string $challenge, string $origin): string
    {
        return json_encode([
            'type' => $type,
            'challenge' => $challenge,
            'origin' => $origin,
            'crossOrigin' => false,
        ], JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    }

    private function coseKey(): string
    {
        return $this->cborMap([
            [$this->cborInt(1), $this->cborInt(2)],      // kty: EC2
            [$this->cborInt(3), $this->cborInt(-7)],     // alg: ES256
            [$this->cborInt(-1), $this->cborInt(1)],     // crv: P-256
            [$this->cborInt(-2), $this->cborBytes($this->x)],
            [$this->cborInt(-3), $this->cborBytes($this->y)],
        ]);
    }

    private function sign(string $message, bool $tamper): string
    {
        $key = $tamper ? self::newKey() : $this->key;
        openssl_sign($message, $der, $key, 'sha256');

        return $this->derToP1363($der);
    }

    /** DER ECDSA signature → raw r||s (P1363, 64 bytes). */
    private function derToP1363(string $der): string
    {
        $pos = 2;
        if ((ord($der[1]) & 0x80) !== 0) {
            $pos = 2 + (ord($der[1]) & 0x7f);
        }
        $parts = [];
        for ($i = 0; $i < 2; $i++) {
            ord($der[$pos]) === 0x02 || throw new RuntimeException('unexpected DER structure');
            $len = ord($der[$pos + 1]);
            $pos += 2;
            $parts[] = substr($der, $pos, $len);
            $pos += $len;
        }

        return $this->int32($parts[0]) . $this->int32($parts[1]);
    }

    private function int32(string $binary): string
    {
        $binary = ltrim($binary, "\x00");
        strlen($binary) <= 32 || throw new RuntimeException('integer larger than 32 bytes');

        return str_pad($binary, 32, "\x00", STR_PAD_LEFT);
    }

    private function head(int $major, int $length): string
    {
        $prefix = $major << 5;
        if ($length < 24) {
            return chr($prefix | $length);
        }
        if ($length < 256) {
            return chr($prefix | 24).chr($length);
        }
        if ($length < 65536) {
            return chr($prefix | 25).pack('n', $length);
        }

        return chr($prefix | 26).pack('N', $length);
    }

    private function cborText(string $value): string
    {
        return $this->head(3, strlen($value)).$value;
    }

    private function cborBytes(string $value): string
    {
        return $this->head(2, strlen($value)).$value;
    }

    private function cborInt(int $value): string
    {
        return $value >= 0 ? $this->head(0, $value) : $this->head(1, -$value - 1);
    }

    /**
     * @param  list<array{0: string, 1: string}>  $pairs
     */
    private function cborMap(array $pairs): string
    {
        $out = $this->head(5, count($pairs));
        foreach ($pairs as [$key, $value]) {
            $out .= $key.$value;
        }

        return $out;
    }

    private function b64(string $value): string
    {
        return Base64UrlSafe::encodeUnpadded($value);
    }
}
