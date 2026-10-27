# wapiti infra smoke report — tests/regression.py

- Run: 2026-10-26 18:01:02 UTC
- Selection: all prefixes
- App: container `trailcam-server` (workdir `/var/www/html`) · Mongo: `database-server/wapiti` · Host: https://172.17.0.1:4444

| ID | Check | Expected | Result |
|---|---|---|---|
| MIG-01 | `php artisan migrate:fresh` | clean | ✅ PASS |
| MIG-02 | users unique `handle` + `email` | unique indexes | ✅ PASS |
| MIG-03 | cameras unique `device_id` | unique index | ✅ PASS |
| MIG-04 | pair_tokens TTL on `expires_at` | `expireAfterSeconds: 900` | ✅ PASS |
| MIG-05 | photos compound index `{camera_id, capture_at}` | present | ✅ PASS |
| PHP-01 | `php artisan list` | Laravel 12.x, rc 0 | ✅ PASS |
| PHP-02 | `php artisan route:list | grep api/health` | route present | ✅ PASS |
| PHP-03 | `grep -c "^APP_KEY=base64" server/.env` | ≥ 1 | ✅ PASS |
| PHP-04 | `php scripts/conncheck.php` → REDIS | PONG | ⏳ pending (cache/queue WI) |
| PHP-05 | `php scripts/conncheck.php` → MONGODB | connected to wapiti | ✅ PASS |
| SRV-01 | `curl -k https://172.17.0.1:4444/api/health` | 200 | ✅ PASS |
| SRV-02 | … `| jq .status` | "ok" | ✅ PASS |
| SRV-03 | … `| jq .service` | "trailcam-server" | ✅ PASS |
| SRV-04 | `curl -k https://172.17.0.1:4444/mcp` (unauth) | 401 (endpoint alive, gated) | ⏳ pending (MCP WI (S3)) |
| SVC-01 | `./start-stop-services.sh --status | grep trailcam` | `trailcam-server: RUNNING` | ✅ PASS |
| SVC-02 | nginx `-t` on `default.wapiti.cam` | `syntax is ok` | ✅ PASS |
| SVC-03 | `docker port trailcam-server | grep 4444` | `0.0.0.0:4444` | ✅ PASS |
| SVC-04 | stop + start cycle → health | OK | ✅ PASS |
| BLD-01 | `docker images trailcam-builder:v1` | image listed | ✅ PASS |
| BLD-02 | builder artifacts exist post-build | vendor/autoload.php present | ✅ PASS |
| BLD-03 | builder is one-shot (no ports) | `docker inspect` → no exposed ports | ✅ PASS |
| BLD-04 | build idempotent (rerun OK) | exit 0 | ✅ PASS |
| BLD-05 | `trailcam-test` image runs pytest | exits per suite result | ✅ PASS |
| SIM-01 | 10 cams report at idle cadence for 10 min | all 200s, no loss | ⏳ pending (WI-105) |
| SIM-02 | 100 cams burst mode 5 min | server survives; p95 < 300 ms | ⏳ pending (WI-105) |
| SIM-03 | 20% cams offline / flaky | reconnect replay works | ⏳ pending (WI-105) |
| SIM-04 | Mixed transports | all ingested, tagged correctly | ⏳ pending (WI-105) |
| SIM-05 | Stale device_token | 401, no ingestion | ⏳ pending (WI-104) |
| SIM-06 | Config piggyback round-trip | command delivered + acked | ⏳ pending (WI-104) |

**Totals: 21 passed · 0 failed · 8 pending** (of 29 selected / 29 documented infra IDs)

Pending = suite specified in test-plan §20 whose work item has not landed; see project-plan.md §Work items.
