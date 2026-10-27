<?php

/*
|--------------------------------------------------------------------------
| Test Case
|--------------------------------------------------------------------------
|
| The WebAuthn ceremony suite (tests/Feature/AuthTest.php) runs in-process
| against the Laravel kernel; tests/test.py remains the catalog authority
| for HTTP behaviour against a live instance (test-plan.md §1.1).
|
*/

uses(Tests\TestCase::class)->in('Feature');
