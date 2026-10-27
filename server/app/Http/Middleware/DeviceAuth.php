<?php

namespace App\Http\Middleware;

use App\Models\Camera;
use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Symfony\Component\HttpFoundation\Response;

/**
 * Bearer device-token auth + per-device ingest budget (project-plan §14,
 * §8.6). The token presented on /device/v1/* is looked up as sha256(token)
 * against `cameras.device_token.hash`. On success the Camera is stashed as a
 * request attribute (`camera`) for controllers.
 *
 * Budget: fixed one-minute window per device (`cameras.rate_window {start,n}`).
 * Over `wapiti.device_rate_per_min` → 429 + jittered Retry-After (ING-06).
 * The window update is a raw CAS on `device_id` (unique) so concurrent
 * workers cannot double-open a window.
 */
class DeviceAuth
{
    public function handle(Request $request, Closure $next): Response
    {
        $bearer = $request->bearerToken();
        abort_unless($bearer !== null && $bearer !== '', 401, 'missing device token');

        $camera = Camera::where('device_token.hash', hash('sha256', $bearer))->first();
        abort_unless($camera !== null, 401, 'invalid device token');

        if (($retryAfter = $this->consumeBudget($camera)) !== null) {
            return response()->json([
                'error' => 'rate_limited',
                'retry_after' => $retryAfter,
            ], 429)->header('Retry-After', (string) $retryAfter);
        }

        $request->attributes->set('camera', $camera);

        return $next($request);
    }

    /**
     * Consume one unit of the device's per-minute budget.
     *
     * @return int|null null = allowed; int = seconds to wait (429 path)
     */
    private function consumeBudget(Camera $camera): ?int
    {
        $limit = max(1, (int) config('wapiti.device_rate_per_min', 120));
        $window = (int) floor(time() / 60) * 60;
        $coll = DB::connection()->getDatabase()->getCollection('cameras');

        $stored = $camera->rate_window ?? null;
        $storedStart = isset($stored['start']) ? (int) $stored['start'] : null;

        // Stale (or first-ever) window → open a fresh one, atomically.
        // `rate_window.start: null` matches both missing and null in Mongo.
        if ($storedStart === null || $storedStart < $window) {
            $reset = $coll->updateOne(
                ['device_id' => $camera->device_id, 'rate_window.start' => $storedStart],
                ['$set' => ['rate_window.start' => $window, 'rate_window.n' => 1]],
            );
            if ($reset->getMatchedCount() > 0) {
                return null;
            }
            // Lost the race to another worker — fall through to the increment.
        }

        $inc = $coll->updateOne(
            ['device_id' => $camera->device_id, 'rate_window.start' => $window, 'rate_window.n' => ['$lt' => $limit]],
            ['$inc' => ['rate_window.n' => 1]],
        );
        if ($inc->getMatchedCount() > 0) {
            return null;
        }

        // Over budget (or a lost race): seconds to the window end + jitter 0–5s.
        return max(1, $window + 60 - time() + random_int(0, 5));
    }
}
