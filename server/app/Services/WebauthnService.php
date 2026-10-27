<?php

namespace App\Services;

use App\Models\Credential;
use ParagonIE\ConstantTime\Base64UrlSafe;
use Symfony\Component\Serializer\SerializerInterface;
use Symfony\Component\Uid\Uuid;
use Webauthn\AttestationStatement\AttestationStatementSupportManager;
use Webauthn\AttestationStatement\NoneAttestationStatementSupport;
use Webauthn\AuthenticatorAssertionResponse;
use Webauthn\AuthenticatorAssertionResponseValidator;
use Webauthn\AuthenticatorAttestationResponse;
use Webauthn\AuthenticatorAttestationResponseValidator;
use Webauthn\AuthenticatorSelectionCriteria;
use Webauthn\CeremonyStep\CeremonyStepManagerFactory;
use Webauthn\CredentialRecord;
use Webauthn\Denormalizer\WebauthnSerializerFactory;
use Webauthn\Exception\WebauthnException;
use Webauthn\PublicKeyCredential;
use Webauthn\PublicKeyCredentialCreationOptions;
use Webauthn\PublicKeyCredentialDescriptor;
use Webauthn\PublicKeyCredentialParameters;
use Webauthn\PublicKeyCredentialRequestOptions;
use Webauthn\PublicKeyCredentialRpEntity;
use Webauthn\PublicKeyCredentialUserEntity;
use Webauthn\TrustPath\CertificateTrustPath;
use Webauthn\TrustPath\EmptyTrustPath;
use Webauthn\TrustPath\TrustPath;

/**
 * Ceremony plumbing for the /auth/* endpoints (project-plan §10).
 *
 * - Challenges are raw 32-byte values held in the session; the wire format is
 *   base64url (handled by the library's serializer).
 * - RP_ID + origin come from config/webauthn.php — fixed per environment,
 *   never derived from the Host header.
 * - Stored CredentialRecords keep every binary field base64url-encoded so the
 *   Mongo documents stay JSON-safe.
 */
class WebauthnService
{
    public const ALG_ES256 = -7;

    public const ALG_RS256 = -257;

    private SerializerInterface $serializer;

    public function __construct()
    {
        $attestationSupport = new AttestationStatementSupportManager([
            new NoneAttestationStatementSupport(),
        ]);
        $this->serializer = (new WebauthnSerializerFactory($attestationSupport))->create();
    }

    public function rpId(): string
    {
        return (string) config('webauthn.rp_id');
    }

    public function origin(): string
    {
        return (string) config('webauthn.origin');
    }

    /** Fresh raw challenge (library compares raw-to-raw). */
    public function newChallenge(): string
    {
        return random_bytes(32);
    }

    /**
     * @param  list<string>  $excludeCredentialIds  base64url ids already enrolled
     */
    public function creationOptions(
        string $challenge,
        string $userHandleB64,
        string $handle,
        array $excludeCredentialIds = [],
    ): PublicKeyCredentialCreationOptions {
        $exclude = array_map(
            fn (string $id): PublicKeyCredentialDescriptor => PublicKeyCredentialDescriptor::create(
                PublicKeyCredentialDescriptor::CREDENTIAL_TYPE_PUBLIC_KEY,
                Base64UrlSafe::decodeNoPadding($id),
                [],
            ),
            $excludeCredentialIds,
        );

        return PublicKeyCredentialCreationOptions::create(
            rp: PublicKeyCredentialRpEntity::create((string) config('webauthn.rp_name'), $this->rpId()),
            user: new PublicKeyCredentialUserEntity($handle, Base64UrlSafe::decodeNoPadding($userHandleB64), $handle),
            challenge: $challenge,
            pubKeyCredParams: [
                PublicKeyCredentialParameters::createPk(self::ALG_ES256),
                PublicKeyCredentialParameters::createPk(self::ALG_RS256),
            ],
            authenticatorSelection: new AuthenticatorSelectionCriteria(
                userVerification: AuthenticatorSelectionCriteria::USER_VERIFICATION_REQUIREMENT_PREFERRED,
            ),
            attestation: 'none',
            excludeCredentials: $exclude,
        );
    }

    /**
     * @param  list<string>  $allowCredentialIds  base64url ids
     */
    public function requestOptions(string $challenge, array $allowCredentialIds): PublicKeyCredentialRequestOptions
    {
        $allow = array_map(
            fn (string $id): PublicKeyCredentialDescriptor => PublicKeyCredentialDescriptor::create(
                PublicKeyCredentialDescriptor::CREDENTIAL_TYPE_PUBLIC_KEY,
                Base64UrlSafe::decodeNoPadding($id),
                [],
            ),
            $allowCredentialIds,
        );

        return PublicKeyCredentialRequestOptions::create(
            challenge: $challenge,
            rpId: $this->rpId(),
            allowCredentials: $allow,
            userVerification: AuthenticatorSelectionCriteria::USER_VERIFICATION_REQUIREMENT_PREFERRED,
        );
    }

    /** Options → browser JSON (base64url-encoded challenge, user.id, credential ids…). */
    public function toJson(PublicKeyCredentialCreationOptions|PublicKeyCredentialRequestOptions $options): array
    {
        $normalized = $this->serializer->normalize($options, 'json');

        return is_array($normalized) ? $normalized : (array) $normalized;
    }

    /** Client credential JSON (id/rawId/response…) → PublicKeyCredential. */
    public function credentialFromJson(array $data): PublicKeyCredential
    {
        $credential = $this->serializer->denormalize($data, PublicKeyCredential::class, 'json');
        $credential instanceof PublicKeyCredential || throw new WebauthnException('Invalid credential payload');

        return $credential;
    }

    /** @throws WebauthnException when the attestation is not valid */
    public function verifyAttestation(
        PublicKeyCredential $credential,
        PublicKeyCredentialCreationOptions $options,
    ): CredentialRecord {
        $response = $credential->response;
        $response instanceof AuthenticatorAttestationResponse
            || throw new WebauthnException('Expected an attestation response');

        $factory = $this->factory();

        return AuthenticatorAttestationResponseValidator::create($factory->creationCeremony())
            ->check($response, $options, $this->rpId());
    }

    /** @throws WebauthnException when the assertion is not valid */
    public function verifyAssertion(
        Credential $credential,
        PublicKeyCredential $credentialJson,
        PublicKeyCredentialRequestOptions $options,
        string $userHandleB64,
    ): CredentialRecord {
        $response = $credentialJson->response;
        $response instanceof AuthenticatorAssertionResponse
            || throw new WebauthnException('Expected an assertion response');

        $factory = $this->factory();

        return AuthenticatorAssertionResponseValidator::create($factory->requestCeremony())
            ->check(
                $this->toCredentialRecord($credential),
                $response,
                $options,
                $this->rpId(),
                Base64UrlSafe::decodeNoPadding($userHandleB64),
            );
    }

    /** Stored passkey → library record. */
    public function toCredentialRecord(Credential $credential): CredentialRecord
    {
        return CredentialRecord::create(
            Base64UrlSafe::decodeNoPadding((string) $credential->credential_id),
            (string) $credential->type,
            $this->toList($credential->transports),
            (string) $credential->attestation_type,
            $this->trustPathFromArray($this->assoc($credential->trust_path)),
            Uuid::fromString((string) $credential->aaguid),
            Base64UrlSafe::decodeNoPadding((string) $credential->public_key),
            Base64UrlSafe::decodeNoPadding((string) $credential->user_handle),
            (int) ($credential->counter ?? 0),
            $this->assoc($credential->other_ui),
            $credential->backup_eligible,
            $credential->backup_status,
            $credential->uv_initialized,
        );
    }

    /** Validated record → document for the `credentials` collection. */
    public function credentialDocument(CredentialRecord $record, string $userId): array
    {
        return [
            'user_id' => $userId,
            'credential_id' => Base64UrlSafe::encodeUnpadded($record->publicKeyCredentialId),
            'type' => $record->type,
            'transports' => $record->transports,
            'attestation_type' => $record->attestationType,
            'trust_path' => $this->trustPathToArray($record->trustPath),
            'aaguid' => $record->aaguid->toRfc4122(),
            'public_key' => Base64UrlSafe::encodeUnpadded($record->credentialPublicKey),
            'user_handle' => Base64UrlSafe::encodeUnpadded($record->userHandle),
            'counter' => $record->counter,
            'backup_eligible' => $record->backupEligible,
            'backup_status' => $record->backupStatus,
            'uv_initialized' => $record->uvInitialized,
            'other_ui' => $record->otherUI,
        ];
    }

    /**
     * Normalise a stored list-like value: native PHP array (BSON array),
     * stdClass/BSON document, or a legacy JSON string.
     *
     * @return list<mixed>
     */
    private function toList(mixed $value): array
    {
        if (is_string($value)) {
            $value = json_decode($value, true);
        }
        if ($value instanceof \Traversable) {
            $value = iterator_to_array($value);
        }
        is_array($value) || ($value = is_object($value) ? (array) $value : []);

        return array_values($value);
    }

    /**
     * Normalise a stored map-like value (see toList); null when absent.
     *
     * @return array<string, mixed>|null
     */
    private function assoc(mixed $value): ?array
    {
        if ($value === null || $value === '') {
            return null;
        }
        if (is_string($value)) {
            $value = json_decode($value, true);
        }
        if ($value instanceof \Traversable) {
            $value = iterator_to_array($value);
        }
        if (is_object($value)) {
            $value = (array) $value;
        }

        return is_array($value) ? $value : null;
    }

    private function factory(): CeremonyStepManagerFactory
    {
        $factory = new CeremonyStepManagerFactory();
        $factory->setAllowedOrigins([$this->origin()]);

        return $factory;
    }

    /**
     * @param  array<string, mixed>|null  $trustPath
     */
    private function trustPathFromArray(?array $trustPath): TrustPath
    {
        return match ($trustPath['type'] ?? 'empty') {
            'empty' => new EmptyTrustPath(),
            'x5c' => new CertificateTrustPath(array_values($trustPath['certificates'] ?? [])),
            default => throw new WebauthnException('Unsupported trust path'),
        };
    }

    /**
     * @return array<string, mixed>
     */
    private function trustPathToArray(TrustPath $trustPath): array
    {
        return match (true) {
            $trustPath instanceof EmptyTrustPath => ['type' => 'empty'],
            $trustPath instanceof CertificateTrustPath => [
                'type' => 'x5c',
                'certificates' => $trustPath->certificates,
            ],
            default => throw new WebauthnException('Unsupported trust path: '.get_class($trustPath)),
        };
    }
}
