<?php

/**
 * conncheck.php — connectivity smoke for the app's backing services.
 * test-plan §20.3: PHP-04 (REDIS → PONG), PHP-05 (MONGODB → connected to <db>).
 *
 * Redis has no server in this environment yet — the cache/queue wiring is
 * explicitly deferred (project-plan §9 server stack), so REDIS is reported
 * but not fatal. MongoDB failing is fatal (exit 1).
 *
 * Run in the app container:  php scripts/conncheck.php
 */

require __DIR__.'/../vendor/autoload.php';

$app = require __DIR__.'/../bootstrap/app.php';
$app->make(Illuminate\Contracts\Console\Kernel::class)->bootstrap();

$code = 0;

// ---- REDIS (PHP-04 — pending until a cache/queue WI stands up a server) ----
$host = (string) config('database.redis.default.host', '127.0.0.1');
$port = (int) config('database.redis.default.port', 6379);
$fp = @fsockopen($host, $port, $errno, $errstr, 1.0);
if ($fp) {
    fwrite($fp, "PING\r\n");
    $reply = trim((string) fgets($fp, 16));
    fclose($fp);
    echo 'REDIS: '.($reply === '+PONG' ? 'PONG' : "unexpected reply '{$reply}'").PHP_EOL;
} else {
    echo "REDIS: not reachable ({$host}:{$port}) — Redis wiring deferred (project-plan §9)".PHP_EOL;
}

// ---- MONGODB (PHP-05) ----
try {
    $db = (string) config('database.connections.mongodb.database');
    Illuminate\Support\Facades\DB::connection()->getDatabase()->command(['ping' => 1]);
    echo "MONGODB: connected to {$db}".PHP_EOL;
} catch (Throwable $e) {
    echo 'MONGODB: FAILED — '.$e->getMessage().PHP_EOL;
    $code = 1;
}

exit($code);
