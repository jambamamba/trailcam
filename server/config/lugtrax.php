<?php

return [

    /*
    |---------------------------------------------------------------------------
    | Device ingest (project-plan §7.3, §13.7)
    |---------------------------------------------------------------------------
    | device_rate_per_min: per-device request budget at the ingest surface —
    | over budget the device gets 429 + a jittered Retry-After (the fleet-wide
    | ~10% retry budget scales with this once the fleet WI lands, §7.3).
    | report_batch_max: batch cap enforced by validation (EVT-03).
    */

    'device_rate_per_min' => (int) env('DEVICE_RATE_PER_MIN', 120),

    'report_batch_max' => (int) env('DEVICE_BATCH_MAX', 20),

    /*
    |---------------------------------------------------------------------------
    | Factory provisioning (§16.2 stand-in)
    |---------------------------------------------------------------------------
    | POST /device/v1/provision models the contract-manufacturer step (burn
    | device_id + secret) until the factory-import WI lands. It refuses to
    | exist unless FACTORY_KEY is set, and only with a matching X-Factory-Key
    | header — dev/test/sim seed factory records with it.
    */

    'factory_key' => env('FACTORY_KEY'),

];
