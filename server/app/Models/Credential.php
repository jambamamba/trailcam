<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model as MongoModel;

/**
 * A stored WebAuthn passkey (project-plan §5.2 `credentials`).
 * `credential_id` is the base64url (no padding) credential id; every binary
 * field of the CredentialRecord is stored base64url-encoded so the document
 * stays JSON-safe in Mongo.
 */
class Credential extends MongoModel
{
    protected $collection = 'credentials';

    /**
     * @var list<string>
     */
    protected $fillable = [
        'user_id',
        'credential_id',
        'type',
        'transports',
        'attestation_type',
        'trust_path',
        'aaguid',
        'public_key',
        'user_handle',
        'counter',
        'backup_eligible',
        'backup_status',
        'uv_initialized',
        'other_ui',
        'nickname',
    ];

    // No `array` casts: nested values are stored as native BSON. Readers in
    // WebauthnService normalise BSON documents/arrays and tolerate rows that
    // were written as JSON strings before that rule.
}
