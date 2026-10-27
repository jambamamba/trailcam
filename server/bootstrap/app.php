<?php

use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // The WebAuthn ceremonies are bound to a session challenge and the
        // configured origin, so /auth/* is exempt from CSRF token checks;
        // /device/v1/* has no browser session at all (bearer + factory key).
        $middleware->validateCsrfTokens(except: [
            'auth/*',
            'device/*',
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        //
    })->create();
