<?php

namespace App\Models;

use Illuminate\Support\Str;
use MongoDB\Laravel\Eloquent\Model as MongoModel;

/**
 * A wapiti account (project-plan §6.1 `users`). WebAuthn-only — no passwords:
 * passkeys live in the `credentials` collection, and a single-use recovery
 * token hash rides on this document (re-issued per passkey enrollment).
 */
class User extends MongoModel
{
    protected $collection = 'users';

    /**
     * @var list<string>
     */
    protected $fillable = [
        'handle',
        'email',
        'role',
        'tier',
        'user_handle',
        'recovery_token',
        'push_tokens',
        'last_seen_at',
    ];

    /**
     * Nested values (recovery_token, push_tokens) are stored as native BSON
     * documents — no `array` cast, which would JSON-encode them and break
     * dot-path queries such as `recovery_token.hash`.
     *
     * @return array<string, string>
     */
    protected function casts(): array
    {
        return [
            'last_seen_at' => 'datetime',
        ];
    }

    public static function makeHandle(): string
    {
        return 'user-'.Str::lower(Str::random(12));
    }
}
