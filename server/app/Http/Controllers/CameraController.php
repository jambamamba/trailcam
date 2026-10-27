<?php

namespace App\Http\Controllers;

use App\Models\Camera;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * Owner-scoped camera API — the user half of the ingest loop (project-plan
 * §14 "User app", §8.3/§8.6).
 *
 *   GET    /api/cameras/{id}          status + capture_config (WI-104)
 *   PATCH  /api/cameras/{id}/config   stages a config delta that rides the
 *                                     next device response (ING-05) and is
 *                                     acked by the call after that
 *   DELETE /api/cameras/{id}/device   unbind: revoke the device bearer
 *                                     (§15 "revocable on unbind", ING-07)
 *
 * Every lookup is owner-scoped: a camera belonging to another account is a
 * 404, never a 403 — no existence leak across users (ING-08).
 */
class CameraController extends Controller
{
    public function show(Request $request, string $id): JsonResponse
    {
        $camera = $this->ownedCamera($id);

        return response()->json([
            'id' => (string) $camera->getKey(),
            'device_id' => $camera->device_id,
            'status' => $camera->status ?? 'healthy',
            'mode' => $camera->mode ?? 'normal',
            'fw_version' => $camera->fw_version,
            'hw_version' => $camera->hw_version,
            'capture_config' => $camera->capture_config ?? Camera::defaultCaptureConfig(),
            'config_version' => (int) ($camera->config_version ?? 1),
            'claimed_at' => $camera->claimed_at?->toIso8601String(),
            'last_seen_at' => $camera->last_seen_at?->toIso8601String(),
            'last_photo_at' => $camera->last_photo_at?->toIso8601String(),
        ]);
    }

    /**
     * Stage a capture_config delta (§6.1 fields). It is not applied here: it
     * rides the next device response as `config` + `config_version` and is
     * committed when the device acks the version on a later call (ING-05).
     */
    public function updateConfig(Request $request, string $id): JsonResponse
    {
        $camera = $this->ownedCamera($id);

        $data = $request->validate([
            'photo_res' => ['sometimes', 'string', 'in:4k,2.5k'],
            'video' => ['sometimes', 'string', 'in:off,1080p10'],
            'simultaneous' => ['sometimes', 'boolean'],
            'ir' => ['sometimes', 'string', 'in:no_glow,low_glow,auto'],
            'interval_s' => ['sometimes', 'integer', 'min:60', 'max:86400'],
            'quiet_hours' => ['sometimes', 'nullable', 'array'],
            'instant_send' => ['sometimes', 'boolean'],
        ]);
        abort_if($data === [], 422, 'no config fields supplied');

        $version = (int) ($camera->config_version ?? 1) + 1;
        $camera->forceFill([
            'pending_config' => ['version' => $version, 'delta' => $data],
            'config_version' => $version,
        ])->save();

        return response()->json([
            'ok' => true,
            'config_version' => $version,
            'delta' => $data,
        ]);
    }

    /** Unbind the device bearer (§15): the presented token dies immediately. */
    public function unbindDevice(Request $request, string $id): JsonResponse
    {
        $camera = $this->ownedCamera($id);

        $camera->forceFill([
            'device_token' => null,
            'claimed_at' => null,
            'owner_id' => null,
            'status' => 'healthy',
        ])->save();

        return response()->json(['ok' => true, 'unbound' => true, 'device_id' => $camera->device_id]);
    }

    /**
     * Owner-scoped lookup — another account's camera is a 404 (ING-08), so a
     * probe cannot distinguish "exists elsewhere" from "does not exist".
     */
    private function ownedCamera(string $id): Camera
    {
        $user = $this->user();
        $camera = Camera::where('_id', $id)
            ->where('owner_id', (string) $user->getKey())
            ->first();
        abort_unless($camera instanceof Camera, 404, 'unknown camera');

        return $camera;
    }

    private function user(): User
    {
        $id = session()->get('user_id');
        $user = is_string($id) && $id !== '' ? User::find($id) : null;
        abort_unless($user instanceof User, 401, 'unauthenticated');

        return $user;
    }
}
