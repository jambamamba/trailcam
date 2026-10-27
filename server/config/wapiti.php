<?php

return [

    /*
    |------------------------------------------------------------------------
    | Device ingest (project-plan §8.6, §14)
    |------------------------------------------------------------------------
    | FACTORY_KEY is the CM-provisioning stand-in used by /device/v1/provision
    | (§15: per-unit factory secrets at CM provisioning; the HTTP factory key
    | is the bench/test stand-in until the CM tooling lands). Empty = the
    | endpoint answers 404 so a mis-configured host never exposes it.
    |
    | device_rate_per_min is the per-device ingest budget (§8.6 fleet retry
    | budget, per-device edition): over budget → 429 + Retry-After.
    */

    'factory_key' => env('FACTORY_KEY', ''),

    'device_rate_per_min' => (int) env('DEVICE_RATE_PER_MIN', 120),

    'report_batch_max' => (int) env('REPORT_BATCH_MAX', 20),

    // §4.2/test-plan ING-03: a single 4K JPEG must fit; nginx allows 25M (§9).
    'photo_max_kb' => (int) env('PHOTO_MAX_KB', 12288),

    // §6.1 capture_config.interval_s → heartbeat cadence (§8.1 expected_next_at)
    'heartbeat_interval_s' => (int) env('HEARTBEAT_INTERVAL_S', 900),

];
