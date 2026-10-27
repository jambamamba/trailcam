<?php

namespace App\Http\Controllers;

use App\Models\Camera;
use App\Models\PairToken;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * POST /api/pair-tokens (project-plan §8.3, §14) — mints the single-use
 * `PRT-xxxx-xxxx` claim token for a factory-provisioned, unclaimed device.
 * Optional `site_id` (owned by the caller) rides the token so a successful
 * device claim wires camera ↔ site in one step. The BLE/app half of pairing
 * is PR-01..08, its own work item (S2 / WI-205).
 */
class PairTokenController extends Controller
{
    public function store(Request $request): JsonResponse
    {
        $user = $this->user();

        $data = $request->validate([
            'device_id' => ['required', 'string', 'max:64'],
            'site_id' => ['nullable', 'string', 'max:64'],
        ]);

        $camera = Camera::where('device_id', $data['device_id'])->first();
        abort_unless($camera !== null, 404, 'unknown device');
        abort_if($camera->claimed_at !== null, 409, 'device already claimed');

        $token = 'PRT-'.bin2hex(random_bytes(2)).'-'.bin2hex(random_bytes(2));
        $expiresAt = now()->addMinutes(15);   // §6.1 — TTL index expireAfterSeconds 900 (MIG-04)

        PairToken::create([
            'token' => $token,
            'device_id' => $data['device_id'],
            'issued_by' => (string) $user->getKey(),
            'site_id' => $data['site_id'] ?? null,
            'expires_at' => $expiresAt,
            'created_at' => now(),
        ]);

        return response()->json([
            'token' => $token,
            'device_id' => $data['device_id'],
            'expires_at' => $expiresAt->toIso8601String(),
        ], 201);
    }

    private function user(): User
    {
        $id = session()->get('user_id');
        $user = is_string($id) && $id !== '' ? User::find($id) : null;
        abort_unless($user instanceof User, 401, 'unauthenticated');

        return $user;
    }
}
