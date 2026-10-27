<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\Schema;
use MongoDB\Laravel\Schema\Blueprint;

/**
 * WI-101: the two collections the auth ceremonies need.
 * The remaining 11 collections + their indexes land with WI-102 (MIG-01..05).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('users', function (Blueprint $collection) {
            $collection->unique('handle');
            $collection->unique('email');
            $collection->index('recovery_token.hash');
        });

        Schema::create('credentials', function (Blueprint $collection) {
            $collection->unique('credential_id');
            $collection->index('user_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('credentials');
        Schema::dropIfExists('users');
    }
};
