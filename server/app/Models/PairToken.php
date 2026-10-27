<?php

namespace App\Models;

use MongoDB\Laravel\Eloquent\Model as MongoModel;

/**
 * Single-use claim token `PRT-xxxx-xxxx` (project-plan §8.3): 15-minute TTL
 * (Mongo TTL index on `expires_at`, expireAfterSeconds: 900 — MIG-04),
 * consumed by POST /device/v1/pair. `site_id` (optional) is the binding hook
 * the minting session passes so a successful claim wires camera ↔ site.
 */
class PairToken extends MongoModel
{
    protected $collection = 'pair_tokens';

    /**
     * @var list<string>
     */
    protected $fillable = [
        'token',
        'device_id',
        'issued_by',
        'site_id',
        'expires_at',
        'consumed_at',
        'created_at',
    ];

    /**
     * @var array<string, string>
     */
    protected $casts = [
        'expires_at' => 'datetime',
        'consumed_at' => 'datetime',
        'created_at' => 'datetime',
    ];
}
