<?php

namespace App\Http\Controllers;

use App\Models\Camera;
use App\Models\PairToken;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Validation\Rule;
use Throwable;

/**
 * Device API (project-plan §14, flows §8.2/§8.3/§8.6) — bearer auth + ingest
 * budget arrive via the DeviceAuth middleware; controllers read the Camera
 * from the request attributes.
 *
 *   POST   /device/v1/provision   factory-keyed CM stand-in (§15) — seeds an
 *                                 unclaimed camera + factory secret
 *   POST   /device/v1/pair        claim: token + factory secret → device_token
 *   POST   /device/v1/reports     telemetry + heartbeat, batch ≤ 20 (§8.6),
 *                                 dedup on {camera_id, at} (ING-02)
 *   POST   /device/v1/photos      multipart manifest + files, dedup on
 *                                 {camera_id, sha256} (ING-03/04)
 *   POST   /device/v1/events      move_alert / door_open / tamper / button
 *                                 stream + rule evaluation (ING-09)
 *   POST   /device/v1/ota/ack     campaign receipt
 *   GET    /device/v1/config      on-demand config after long offline
 *
 * Every device POST accepts an `Idempotency-Key` header (§8.6) and echoes the
 * config/commands piggyback (§14): a staged config delta rides the next
 * response and is acked by the following call (ING-05).
 */
class DeviceController extends Controller
{
    // ------------------------------------------------------------------
    // Provisioning (factory / test-fixture stand-in)
    // ------------------------------------------------------------------

    public function provision(Request $request): JsonResponse
    {
        $key = config('wapiti.factory_key');
        abort_unless(is_string($key) && $key !== '', 404, 'not found');
        abort_unless(hash_equals($key, (string) $request->header('X-Factory-Key', '')), 403, 'bad factory key');

        $data = $request->validate([
            'device_id' => ['required', 'string', 'max:64', 'regex:/^[A-Za-z0-9_-]+$/'],
            'secret' => ['required', 'string', 'min:16', 'max:128'],
            'fw_version' => ['nullable', 'string', 'max:32'],
            'hw_version' => ['nullable', 'string', 'max:32'],
        ]);

        Camera::where('device_id', $data['device_id'])->exists() && abort(409, 'device already provisioned');

        $camera = Camera::create([
            'device_id' => $data['device_id'],
            'factory_secret_hash' => hash('sha256', $data['secret']),
            'fw_version' => $data['fw_version'] ?? '0.0.0',
            'hw_version' => $data['hw_version'] ?? 'WC-1',
            'mode' => 'normal',
            'status' => 'healthy',
            'capture_config' => Camera::defaultCaptureConfig(),
            'config_version' => 1,
            'pending_config' => null,
            'created_at' => now(),
        ]);

        return response()->json([
            'device_id' => $data['device_id'],
            'camera_id' => (string) $camera->getKey(),
            'provisioned' => true,
        ], 201);
    }

    // ------------------------------------------------------------------
    // Pairing / claim (§8.3)
    // ------------------------------------------------------------------

    public function pair(Request $request): JsonResponse
    {
        $data = $request->validate([
            'device_id' => ['required', 'string', 'max:64'],
            'secret' => ['required', 'string', 'min:16', 'max:128'],
            'pair_token' => ['required', 'string', 'max:32'],
        ]);

        $camera = Camera::where('device_id', $data['device_id'])->first();
        abort_unless($camera !== null, 404, 'unknown device');
        abort_if($camera->claimed_at !== null, 409, 'already claimed');

        abort_unless(
            is_string($camera->factory_secret_hash ?? null)
            && hash_equals($camera->factory_secret_hash, hash('sha256', $data['secret'])),
            401,
            'bad factory secret',
        );

        $pairToken = PairToken::where('token', $data['pair_token'])
            ->where('device_id', $data['device_id'])
            ->first();
        abort_unless($pairToken !== null, 401, 'invalid pair token');
        abort_if($pairToken->consumed_at !== null, 410, 'pair token already used');
        abort_unless(
            $pairToken->expires_at instanceof Carbon && $pairToken->expires_at->isFuture(),
            410,
            'pair token expired',
        );

        $now = now();
        $deviceToken = bin2hex(random_bytes(32));

        $camera->forceFill([
            'claimed_at' => $now,
            'owner_id' => (string) $pairToken->issued_by,
            'site_id' => $camera->site_id ?? ($pairToken->site_id ?? null),
            'status' => 'healthy',
            'device_token' => ['hash' => hash('sha256', $deviceToken), 'issued_at' => $now],
        ])->save();

        $pairToken->forceFill(['consumed_at' => $now])->save();

        return response()->json([
            'device_token' => $deviceToken,
            'device_id' => $camera->device_id,
            'camera_id' => (string) $camera->getKey(),
            'capture_config' => $camera->capture_config ?? Camera::defaultCaptureConfig(),
        ]);
    }

    // ------------------------------------------------------------------
    // Report ingest — telemetry + heartbeat (§8.1, §8.6)
    // ------------------------------------------------------------------

    public function reports(Request $request): JsonResponse
    {
        $max = max(1, (int) config('wapiti.report_batch_max', 20));
        $data = $request->validate([
            'reports' => ['required', 'array', 'min:1', 'max:'.$max],
            'reports.*.at' => ['required', 'date'],
            'reports.*.lat' => ['nullable', 'numeric', 'between:-90,90'],
            'reports.*.lon' => ['nullable', 'numeric', 'between:-180,180'],
            'reports.*.src' => ['nullable', Rule::in(['gnss', 'wifi', 'cell', 'ntn'])],
            'reports.*.battery_snapshot' => ['nullable', 'array'],
            'reports.*.signal_snapshot' => ['nullable', 'array'],
            'reports.*.transport' => ['nullable', Rule::in(['https', 'lte', 'wifi', 'sms'])],
            'reports.*.fw_version' => ['nullable', 'string', 'max:32'],
            'reports.*.hw_version' => ['nullable', 'string', 'max:32'],
        ]);

        $camera = $this->camera($request);
        $now = now();
        $idempotency = (string) $request->header('Idempotency-Key', '');
        $accepted = 0;
        $duplicates = 0;
        $last = null;

        foreach ($data['reports'] as $report) {
            $row = [
                'camera_id' => (string) $camera->getKey(),
                'owner_id' => $camera->owner_id ?? null,
                'at' => Carbon::parse($report['at']),
                'battery_snapshot' => $report['battery_snapshot'] ?? null,
                'signal_snapshot' => $report['signal_snapshot'] ?? null,
                'transport' => $report['transport'] ?? 'https',
                'fw_version' => $report['fw_version'] ?? $camera->fw_version,
                'hw_version' => $report['hw_version'] ?? $camera->hw_version,
                'location' => isset($report['lat'])
                    ? ['lat' => (float) $report['lat'], 'lon' => (float) ($report['lon'] ?? 0), 'src' => $report['src'] ?? null]
                    : null,
                'idempotency_key' => $idempotency !== '' ? $idempotency : null,
                'received_at' => $now,
            ];

            try {
                DB::table('heartbeats')->insert($row);   // unique {camera_id, at} → §8.6 dedup
                $accepted++;
                $last = $row;
            } catch (Throwable $e) {
                if (! str_contains($e->getMessage(), 'E11000')) {
                    throw $e;
                }
                $duplicates++;                          // lost-ack replay: counted, never re-applied
                $last ??= $row;
            }
        }

        // Touch last-known state (ING-10: fw/hw from the first report win).
        $cameraUpdate = ['last_seen_at' => $now];
        if ($last !== null) {
            if (! empty($data['reports'][count($data['reports']) - 1]['fw_version'])) {
                $cameraUpdate['fw_version'] = $data['reports'][count($data['reports']) - 1]['fw_version'];
            }
            if (! empty($data['reports'][count($data['reports']) - 1]['hw_version'])) {
                $cameraUpdate['hw_version'] = $data['reports'][count($data['reports']) - 1]['hw_version'];
            }
        }
        $camera->forceFill($cameraUpdate)->save();

        $interval = (int) (($camera->capture_config['interval_s'] ?? null) ?? config('wapiti.heartbeat_interval_s', 900));

        return response()->json(array_merge(
            [
                'queued' => true,
                'count' => $accepted,
                'duplicates' => $duplicates,
                'heartbeat' => [
                    'at' => $now->toIso8601String(),
                    'expected_next_at' => $now->copy()->addSeconds($interval)->toIso8601String(),
                ],
                'camera' => [
                    'fw_version' => $camera->fw_version,
                    'hw_version' => $camera->hw_version,
                    'last_seen_at' => $camera->last_seen_at?->toIso8601String(),
                ],
            ],
            $this->piggyback($camera, $request),
        ), 202);
    }

    // ------------------------------------------------------------------
    // Photo ingest — multipart manifest + files (§8.2, §14)
    // ------------------------------------------------------------------

    public function photos(Request $request): JsonResponse
    {
        $maxKb = max(1024, (int) config('wapiti.photo_max_kb', 12288));
        $data = $request->validate([
            'manifest' => ['required', 'string', 'max:200000'],
            'files' => ['nullable', 'array', 'max:50'],
            'files.*' => ['file', 'max:'.$maxKb],
        ]);

        $manifest = json_decode($data['manifest'], true);
        abort_unless(is_array($manifest) && $manifest !== [], 422, 'manifest must be a JSON array');
        abort_unless(count($manifest) <= 50, 422, 'manifest too large');

        $files = $request->file('files', []);
        if ($files instanceof \Illuminate\Http\UploadedFile) {
            $files = [$files];
        }
        if (! is_array($files)) {
            $files = [];
        }
        abort_unless(
            $files === [] || count($files) === count($manifest),
            422,
            'files count must match manifest order',
        );

        $camera = $this->camera($request);
        $now = now();
        $idempotency = (string) $request->header('Idempotency-Key', '');
        $accepted = [];
        $duplicates = [];
        $order = [];

        foreach (array_values($manifest) as $i => $entry) {
            abort_unless(is_array($entry), 422, 'manifest entries must be objects');

            $entry = validator([
                'sha256' => $entry['sha256'] ?? null,
                'kind' => $entry['kind'] ?? 'photo',
                'bytes' => $entry['bytes'] ?? 0,
                'capture_at' => $entry['capture_at'] ?? null,
                'res' => $entry['res'] ?? null,
                'ai_class' => $entry['ai_class'] ?? null,
                'ai_confidence' => $entry['ai_confidence'] ?? null,
                'transmitted' => $entry['transmitted'] ?? null,
            ], [
                'sha256' => ['required', 'string', 'regex:/^[a-f0-9]{64}$/'],
                'kind' => ['required', Rule::in(['photo', 'video', 'live_burst'])],
                'bytes' => ['required', 'integer', 'min:0'],
                'capture_at' => ['required', 'date'],
                'res' => ['nullable', 'string', 'max:16'],
                'ai_class' => ['nullable', 'string', 'max:32'],
                'ai_confidence' => ['nullable', 'numeric', 'between:0,1'],
                'transmitted' => ['nullable', 'boolean'],
            ])->validate();

            $storageKey = 'objects/'.$camera->device_id.'/'.$entry['sha256'];
            $order[] = $entry['sha256'];

            // Store first (content-addressed → replaying a backlog rewrites the
            // same object harmlessly), then insert; the unique index dedups.
            $file = $files[$i] ?? null;
            if ($file !== null && ! Storage::disk('objects')->exists($storageKey)) {
                Storage::disk('objects')->put($storageKey, (string) file_get_contents($file->getRealPath()));
            }

            try {
                DB::table('photos')->insert([
                    'camera_id' => (string) $camera->getKey(),
                    'owner_id' => $camera->owner_id ?? null,
                    'site_id' => $camera->site_id ?? null,
                    'kind' => $entry['kind'],
                    'res' => $entry['res'],
                    'bytes' => (int) $entry['bytes'],
                    'storage_key' => $storageKey,
                    'thumb_key' => null,
                    'sha256' => $entry['sha256'],
                    'ai_class' => $entry['ai_class'],
                    'ai_confidence' => $entry['ai_confidence'],
                    'transmitted' => (bool) ($entry['transmitted'] ?? true),
                    'idempotency_key' => $idempotency !== '' ? $idempotency : null,
                    'capture_at' => Carbon::parse($entry['capture_at']),
                    'created_at' => $now,
                ]);
                $accepted[] = ['sha256' => $entry['sha256'], 'storage_key' => $storageKey];
            } catch (Throwable $e) {
                if (! str_contains($e->getMessage(), 'E11000')) {
                    throw $e;
                }
                $duplicates[] = $entry['sha256'];       // ING-04: replay = no-op
            }
        }

        if ($accepted !== []) {
            $camera->forceFill(['last_photo_at' => $now])->save();
        }

        return response()->json(array_merge(
            [
                'accepted' => $accepted,
                'duplicates' => $duplicates,
                'order' => $order,                       // manifest order preserved
                'count' => count($accepted),
            ],
            $this->piggyback($camera, $request),
        ), 201);
    }

    // ------------------------------------------------------------------
    // Events, OTA receipts, on-demand config
    // ------------------------------------------------------------------

    public function events(Request $request): JsonResponse
    {
        $data = $request->validate([
            'type' => ['required', Rule::in(['move_alert', 'door_open', 'tamper', 'button'])],
            'at' => ['required', 'date'],
            'payload' => ['nullable', 'array'],
        ]);

        $camera = $this->camera($request);
        $now = now();

        $eventId = (string) new \MongoDB\BSON\ObjectId();
        $insert = DB::table('device_events')->insert([
            '_id' => $eventId,
            'camera_id' => (string) $camera->getKey(),
            'device_id' => $camera->device_id,
            'owner_id' => $camera->owner_id ?? null,
            'type' => $data['type'],
            'at' => Carbon::parse($data['at']),
            'payload' => $data['payload'] ?? [],
            'received_at' => $now,
        ]);

        // Rule evaluation (§8.4/§14): map the event to a rule class and fan
        // out an alert per matching rule. Alert *definition* lands with the
        // alert-rules API (WI-303), so an empty rule set evaluates to zero —
        // the evaluation itself runs on every event (ING-09).
        $class = match ($data['type']) {
            'move_alert' => 'move_alert',
            'door_open', 'tamper' => 'human',
            default => null,
        };

        $cameraRules = DB::table('alert_rules')
            ->where('camera_id', (string) $camera->getKey())
            ->get();
        $rulesEvaluated = count($cameraRules);   // every rule on this camera is examined

        $alertsCreated = 0;
        if ($class !== null) {
            $rules = collect($cameraRules)->where('class', $class)->values();

            foreach ($rules as $rule) {
                DB::table('alerts')->insert([
                    'rule_id' => (string) ($rule['_id'] ?? ''),
                    'camera_id' => (string) $camera->getKey(),
                    'payload' => ['event' => $data['type'], 'at' => $data['at'], 'camera_id' => (string) $camera->getKey()],
                    'notified' => false,
                    'created_at' => $now,
                ]);
                $alertsCreated++;
            }
        }

        return response()->json(array_merge(
            [
                'recorded' => (bool) $insert,
                'event_id' => $insert ? $eventId : null,
                'rules_evaluated' => $rulesEvaluated,
                'alerts_created' => $alertsCreated,
            ],
            $this->piggyback($camera, $request),
        ), 202);
    }

    public function otaAck(Request $request): JsonResponse
    {
        $data = $request->validate([
            'campaign_id' => ['required', 'string', 'max:64'],
            'status' => ['required', Rule::in(['applied', 'rolled_back'])],
        ]);

        $camera = $this->camera($request);
        $camera->forceFill([
            'ota_ack' => [
                'campaign_id' => $data['campaign_id'],
                'status' => $data['status'],
                'at' => now(),
            ],
        ])->save();

        return response()->json(array_merge(['ok' => true], $this->piggyback($camera, $request)));
    }

    public function config(Request $request): JsonResponse
    {
        $camera = $this->camera($request);

        return response()->json(array_merge(
            [
                'camera' => [
                    'device_id' => $camera->device_id,
                    'fw_version' => $camera->fw_version,
                    'hw_version' => $camera->hw_version,
                    'mode' => $camera->mode ?? 'normal',
                    'status' => $camera->status ?? 'healthy',
                ],
            ],
            $this->piggyback($camera, $request),
        ));
    }

    // ------------------------------------------------------------------
    // Helpers
    // ------------------------------------------------------------------

    /** The authenticated camera (set by DeviceAuth). */
    private function camera(Request $request): Camera
    {
        /** @var Camera $camera */
        $camera = $request->attributes->get('camera');
        abort_unless($camera instanceof Camera, 401, 'invalid device token');

        return $camera;
    }

    /**
     * Config + commands piggyback (§14): the response carries the effective
     * config (current + any staged delta) and, when the request acknowledges a
     * version (`applied_version`), the delta is committed and the ack rides
     * the *next* response — ING-05's round trip.
     *
     * @return array<string, mixed>
     */
    private function piggyback(Camera $camera, Request $request): array
    {
        $pending = $camera->pending_config ?? null;
        $applied = $camera->capture_config ?? Camera::defaultCaptureConfig();
        $acked = null;

        $appliedVersion = $request->input('applied_version');
        if (is_array($pending)
            && is_numeric($appliedVersion)
            && (int) $appliedVersion >= (int) ($pending['version'] ?? 0)
        ) {
            $applied = array_merge($applied, $pending['delta'] ?? []);
            $acked = (int) $pending['version'];
            $camera->forceFill([
                'capture_config' => $applied,
                'config_version' => $acked,
                'pending_config' => null,
            ])->save();
            $pending = null;
        }

        $effective = array_merge($applied, is_array($pending) ? ($pending['delta'] ?? []) : []);
        $version = is_array($pending) ? (int) $pending['version'] : (int) ($camera->config_version ?? 1);

        return [
            'config' => $effective,
            'config_version' => $version,
            'config_ack' => $acked,
            'commands' => $camera->pending_commands ?? [],
        ];
    }
}
