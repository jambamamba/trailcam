<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;
use MongoDB\Laravel\Schema\Blueprint;

/**
 * WI-104 (device ingest):
 *  - device_events: raw stream from POST /device/v1/events (move_alert,
 *    door_open, tamper, button) — ING-09 reads it back; distinct from
 *    `alerts` (§6.1), which holds rule-triggered notifications for the feed.
 *  - ingest dedup indexes (§8.6 — at-least-once over the radio, exactly-once
 *    effects from ingest-side dedup on a unique index):
 *      heartbeats {camera_id, at}   — a lost ack must not double-count (ING-02)
 *      photos     {camera_id, sha256} — replaying a backlog batch is a no-op
 *                                       (ING-04)
 *    Schema::create cannot touch the pre-existing collections, so those two
 *    go through the driver's createIndex.
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('device_events', function (Blueprint $collection) {
            $collection->index(['camera_id', 'at']);
            $collection->index('at');
            $collection->index('type');
        });

        $db = DB::connection()->getDatabase();

        // WI-102 created {camera_id, at} as a plain index; the dedup key must
        // be unique, and Mongo refuses to reuse the auto-generated name with
        // different options — drop the old one first (same key pattern, so
        // every query it served keeps working).
        $heartbeats = $db->getCollection('heartbeats');
        try {
            $heartbeats->dropIndex('camera_id_1_at_1');
        } catch (\Throwable $e) {
            // index absent (fresh collection) — nothing to replace
        }

        $heartbeats->createIndex(['camera_id' => 1, 'at' => 1], ['unique' => true]);

        $db->getCollection('photos')
            ->createIndex(['camera_id' => 1, 'sha256' => 1], ['unique' => true]);
    }

    public function down(): void
    {
        $db = DB::connection()->getDatabase();

        $db->getCollection('photos')->dropIndex('camera_id_1_sha256_1');
        $db->getCollection('heartbeats')->dropIndex('camera_id_1_at_1');
        // restore the WI-102 non-unique form of the same key pattern
        $db->getCollection('heartbeats')->createIndex(['camera_id' => 1, 'at' => 1]);

        Schema::dropIfExists('device_events');
    }
};
