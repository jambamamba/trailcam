<?php

return [

    /*
    |------------------------------------------------------------------------
    | WebAuthn relying party
    |------------------------------------------------------------------------
    | RP_ID is fixed per environment (prod `wapiti.cam`, dev below) and is
    | never derived from the Host header (project-plan §10). WEBAUTHN_ORIGIN
    | is the single allowed ceremony origin; the client's clientDataJSON.origin
    | must match it exactly.
    |
    | Dev values (WI-101/WI-103): this machine's Docker publishes container
    | ports via iptables only — loopback never binds — so the dev origin is
    | the docker0 gateway IP with the host port. trailcam-server takes 4444
    | (the 4430–4443 block is occupied by the sibling projects, incl.
    | lugtrax-server on 4440 — project-plan §3.1).
    */

    'rp_id' => env('WEBAUTHN_RP_ID', '172.17.0.1'),

    'rp_name' => env('WEBAUTHN_RP_NAME', 'wapiti'),

    'origin' => env('WEBAUTHN_ORIGIN', 'https://172.17.0.1:4444'),

    /*
    |------------------------------------------------------------------------
    | Recovery tokens
    |------------------------------------------------------------------------
    | Single active single-use recovery token per user, re-issued on every
    | successful passkey enrollment (AUTH-15/16).
    */

    'recovery_ttl_minutes' => (int) env('RECOVERY_TTL_MINUTES', 10080),

];
