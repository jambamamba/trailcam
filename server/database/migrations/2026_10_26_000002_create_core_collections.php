<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\Schema;
use MongoDB\Laravel\Schema\Blueprint;

/**
 * WI-102: the 12 collections beyond the WI-101 auth pair (project-plan §6.1),
 * with the index set the queries in §6–§13 lean on. Together with
 * 2026_10_25_000001_create_auth_collections this is the full 14-collection
 * schema.
 *
 * Index rows exercised by tests (test-plan §20.4, run via tests/regression.py):
 *   MIG-01  migrate:fresh applies cleanly (both migrations)
 *   MIG-02  users unique handle + email            (WI-101 migration)
 *   MIG-03  cameras unique device_id
 *   MIG-04  pair_tokens TTL  expires_at expireAfterSeconds=900
 *   MIG-05  photos compound {camera_id, capture_at}
 *
 * Document shapes are §6.1 of project-plan.md; only indexed fields are pinned
 * here (Mongo is schemaless — the app owns validation).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('sites', function (Blueprint $collection) {
            $collection->index('owner_id');           // "my properties" scan
            $collection->index('created_at');
        });

        Schema::create('cameras', function (Blueprint $collection) {
            $collection->unique('device_id');         // MIG-03 — factory-provisioned, immutable
            $collection->index('owner_id');
            $collection->index('site_id');
            $collection->index('status');             // the wedge: healthy / at_risk / silent scan
        });

        Schema::create('photos', function (Blueprint $collection) {
            $collection->index(['owner_id', 'capture_at']);  // gallery by owner
            $collection->index(['camera_id', 'capture_at']); // MIG-05 — per-camera history
            $collection->index('storage_key');               // object lookup / GC
        });

        Schema::create('detections', function (Blueprint $collection) {
            $collection->index(['camera_id', 'capture_at']);
            $collection->index(['owner_id', 'capture_at']);
            $collection->index('class');              // species/activity digests (§11.2)
        });

        Schema::create('heartbeats', function (Blueprint $collection) {
            $collection->index(['camera_id', 'at']);  // dead-camera lookback
            $collection->index('expected_next_at');   // wedge engine: due / missed scan
            $collection->expire('at', 7776000);       // 90 d rolling window (§6.1, decided WI-102)
        });

        Schema::create('pair_tokens', function (Blueprint $collection) {
            $collection->unique('token');             // single-use PRT-xxxx-xxxx
            $collection->index('device_id');
            $collection->expire('expires_at', 900);   // MIG-04 — 15 min TTL (§6.1)
        });

        Schema::create('alert_rules', function (Blueprint $collection) {
            $collection->index('camera_id');
            $collection->index('class');
        });

        Schema::create('alerts', function (Blueprint $collection) {
            $collection->index(['camera_id', 'created_at']); // SSE feed /api/alerts/stream
            $collection->index('rule_id');
            $collection->index('notified');
        });

        Schema::create('share_links', function (Blueprint $collection) {
            $collection->unique('token');
            $collection->index('camera_id');
            $collection->index('expires_at');         // ≤ 7 d expiry sweep (§7.2)
        });

        Schema::create('subscriptions', function (Blueprint $collection) {
            $collection->unique('user_id');           // one subscription per user
            $collection->index('status');             // pause / lapse / active (§7.1)
        });

        Schema::create('ota_campaigns', function (Blueprint $collection) {
            $collection->index('fw_version');         // staged canary → 10% → 100% (§8.5)
            $collection->index('created_by');
        });

        Schema::create('audit_log', function (Blueprint $collection) {
            $collection->index('at');                 // append-only feed, newest first
            $collection->index('actor_id');
            $collection->index('camera_id');          // device-side audits (local_download, OTA, §5.4/§8.5)
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('audit_log');
        Schema::dropIfExists('ota_campaigns');
        Schema::dropIfExists('subscriptions');
        Schema::dropIfExists('share_links');
        Schema::dropIfExists('alerts');
        Schema::dropIfExists('alert_rules');
        Schema::dropIfExists('pair_tokens');
        Schema::dropIfExists('heartbeats');
        Schema::dropIfExists('detections');
        Schema::dropIfExists('photos');
        Schema::dropIfExists('cameras');
        Schema::dropIfExists('sites');
    }
};
