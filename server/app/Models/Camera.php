<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model as MongoModel;

/**
 * The camera (project-plan §6.1 `cameras`). WI-104 adds the device-ingest
 * fields: `factory_secret_hash` (burned at CM provisioning, §15), `device_token`
 * {hash, issued_at} (bearer auth, rotated at claim/pair), `capture_config` +
 * `config_version` / `pending_config` (§14 config piggyback) and `rate_window`
 * {start, n} (ingest budget → 429 + Retry-After, §8.6 fleet budget).
 *
 * References (`owner_id`, `site_id`) are stored as id strings — the same
 * convention the auth collections use for `credentials.user_id`.
 */
class Camera extends MongoModel
{
    protected $collection = 'cameras';

    /**
     * @var list<string>
     */
    protected $fillable = [
        'device_id',
        'owner_id',
        'site_id',
        'claimed_at',
        'factory_secret_hash',
        'device_token',
        'fw_version',
        'hw_version',
        'power',
        'signal',
        'mode',
        'status',
        'capture_config',
        'config_version',
        'pending_config',
        'last_seen_at',
        'last_photo_at',
        'ota_ack',
        'rate_window',
        'created_at',
    ];

    /**
     * @var array<string, string>
     */
    protected $casts = [
        'claimed_at' => 'datetime',
        'last_seen_at' => 'datetime',
        'last_photo_at' => 'datetime',
        'created_at' => 'datetime',
    ];

    /**
     * §6.1 capture_config defaults — the free-tier floor, overwritten by the
     * owner's PATCH (§7.1: every camera feature is in the plan, no add-ons).
     *
     * @return array<string, mixed>
     */
    public static function defaultCaptureConfig(): array
    {
        return [
            'photo_res' => '2.5k',
            'video' => 'off',
            'simultaneous' => false,
            'ir' => 'auto',
            'interval_s' => 900,
            'quiet_hours' => null,
            'instant_send' => false,
        ];
    }
}
