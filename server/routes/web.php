<?php

use App\Http\Controllers\AuthController;
use App\Http\Controllers\CameraController;
use App\Http\Controllers\DeviceController;
use App\Http\Controllers\PairTokenController;
use App\Http\Middleware\DeviceAuth;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

/*
|---------------------------------------------------------------------------
| Auth — WebAuthn (project-plan §10, §14)
|---------------------------------------------------------------------------
| The 10-endpoint contract reused verbatim from wificam/lugtrax. Session
| backed (web group); CSRF is exempted for /auth/* because every ceremony is
| bound to a session challenge + the configured origin (bootstrap/app.php).
|
| Note the add-passkey paths: our contract (§10/§14, test-plan AUTH-13) mounts
| them directly under /auth/, not under /auth/register/.
*/
Route::prefix('auth')->group(function () {
    Route::post('/register/begin', [AuthController::class, 'registerBegin']);
    Route::post('/register/complete', [AuthController::class, 'registerComplete']);
    Route::post('/add-passkey/begin', [AuthController::class, 'addPasskeyBegin']);
    Route::post('/add-passkey/complete', [AuthController::class, 'addPasskeyComplete']);
    Route::post('/login/begin', [AuthController::class, 'loginBegin']);
    Route::post('/login/complete', [AuthController::class, 'loginComplete']);
    Route::post('/logout', [AuthController::class, 'logout']);
    Route::get('/status', [AuthController::class, 'status']);
    Route::delete('/passkeys/{id}', [AuthController::class, 'destroyPasskey']);
    Route::post('/recovery', [AuthController::class, 'recovery']);
});

/*
|---------------------------------------------------------------------------
| Device API (§14) — CSRF-exempt (bootstrap/app.php): devices are not
| browsers. provision/pair authenticate themselves (factory key / token+secret);
| the rest sit behind the DeviceAuth bearer + per-device ingest budget (§8.6).
|---------------------------------------------------------------------------
*/
Route::prefix('device/v1')->group(function () {
    Route::post('/provision', [DeviceController::class, 'provision']);
    Route::post('/pair', [DeviceController::class, 'pair']);

    Route::middleware(DeviceAuth::class)->group(function () {
        Route::post('/reports', [DeviceController::class, 'reports']);
        Route::post('/photos', [DeviceController::class, 'photos']);
        Route::post('/events', [DeviceController::class, 'events']);
        Route::post('/ota/ack', [DeviceController::class, 'otaAck']);
        Route::get('/config', [DeviceController::class, 'config']);
    });
});

/*
|---------------------------------------------------------------------------
| User app (§14) — session + XSRF, owner-scoped (ING-05/07/08)
|---------------------------------------------------------------------------
*/
Route::post('/api/pair-tokens', [PairTokenController::class, 'store']);
Route::get('/api/cameras/{id}', [CameraController::class, 'show']);
Route::patch('/api/cameras/{id}/config', [CameraController::class, 'updateConfig']);
Route::delete('/api/cameras/{id}/device', [CameraController::class, 'unbindDevice']);

/*
|---------------------------------------------------------------------------
| Health — test-plan SRV-01..03 (service group + regression runner probe this)
|---------------------------------------------------------------------------
*/
Route::get('/api/health', function () {
    try {
        DB::connection()->getDatabase()->command(['ping' => 1]);

        return response()->json([
            'status'  => 'ok',
            'service' => 'trailcam-server',
            'db'      => 'mongodb:'.config('database.connections.mongodb.database'),
            'time'    => now()->toIso8601String(),
        ]);
    } catch (\Throwable $e) {
        return response()->json([
            'status'  => 'degraded',
            'service' => 'trailcam-server',
            'error'   => 'database unreachable',
        ], 503);
    }
});
