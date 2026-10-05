# Test Plan — Trail Camera (wapiti)

Modeled on the **luggage-tracker / wificam / blip.io** test-plan methodology: Python `requests` + pytest as the primary suite, prefixed test IDs, E2E chain tests, regression documentation with Mermaid flowcharts, gap coverage after code review, and markdown report generation. Device-side suites follow the lugtrax DEV/SAT pattern; **COLD** (−40 °C chamber + mitten rig) and **PQT** (product qualification) capture the certification and marketing claims defined in `competitive-analysis.md` §4.2/§4.13 and project-plan §5/§13.

## Table of Contents

1. [Test suites](#1-test-suites)
2. [Test IDs — Auth (WebAuthn)](#2-test-ids--auth-webauthn)
3. [Test IDs — Pairing](#3-test-ids--pairing)
4. [Test IDs — Ingest (device API)](#4-test-ids--ingest-device-api)
5. [Test IDs — Heartbeat & dead-camera detection (the wedge)](#5-test-ids--heartbeat--dead-camera-detection-the-wedge)
6. [Test IDs — Cameras & config](#6-test-ids--cameras--config)
7. [Test IDs — Photos & detections](#7-test-ids--photos--detections)
8. [Test IDs — PIR / edge AI / false triggers](#8-test-ids--pir--edge-ai--false-triggers)
9. [Test IDs — Power & battery honesty](#9-test-ids--power--battery-honesty)
10. [Test IDs — Networking & connectivity](#10-test-ids--networking--connectivity)
11. [Test IDs — Alerts](#11-test-ids--alerts)
11bis. [Test IDs — Local download (BLE-gated AP)](#11bis-test-ids--local-download-ble-gated-on-demand-ap-mode)
11ter. [Test IDs — Encrypted-at-rest media](#11ter-test-ids--encrypted-at-rest-media)
12. [Test IDs — MCP](#12-test-ids--mcp)
13. [Test IDs — OTA](#13-test-ids--ota)
14. [Test IDs — Subscriptions](#14-test-ids--subscriptions)
15. [Test IDs — Sharing](#15-test-ids--sharing)
16. [Test IDs — Admin](#16-test-ids--admin)
17. [Test IDs — Browser E2E (PWA)](#17-test-ids--browser-e2e-pwa)
18. [E2E chain tests](#18-e2e-chain-tests)
19. [Gap coverage tests](#19-gap-coverage-tests)
20. [Infra suites (SRV / SVC / PHP / MIG / BLD / SIM)](#20-infra-suites)
21. [Device-side suites (CAM / PWR / NET / COLD / BAT)](#21-device-side-suites)
22. [Product qualification (PQT-01..14)](#22-product-qualification-pqt-0114)
23. [Feature-to-test coverage matrix](#23-feature-to-test-coverage-matrix)
24. [Regression tests](#24-regression-tests)
25. [How to run](#25-how-to-run)

---

## 1. Test suites

| Suite | Language | Framework | Purpose | Run |
|---|---|---|---|---|
| **API tests** (primary) | Python 3 | `requests` + `pytest` | All HTTP endpoints, E2E chains, gap coverage | `python3 tests/test.py --host https://localhost:4440 -v` |
| **PHP unit/feature** | PHP 8.5 | Pest | Policies, TierGuard, heartbeat engine, battery forecast, WebAuthn ceremonies | `php artisan test` |
| **Browser E2E** | TypeScript | Playwright | PWA flows incl. WebAuthn `navigator.credentials.*` | `npx playwright test` |
| **Infra smoke** | Python 3 | stdlib (`subprocess`, `urllib`) | One-shot runner for SRV/SVC/PHP/MIG/BLD/SIM; writes markdown report | `python3 tests/regression.py` |
| **Device suites (CAM/PWR/NET)** | Python 3 | `requests` + SSH (paramiko) + serial | Bench camera: boot, capture, modem, power, radio | `python3 tests/test.py --device <ip> -k test_cam` |
| **Platform image (YOCT)** | Shell/CI + Python checks | kas/bitbake container + paramiko | Yocto image reproducibility, read-only rootfs, A/B OTA substrate, suspend-resume soak | `./device/yocto/build.sh` + `python3 tests/test.py --device <ip> -k test_yoct` |
| **Cold chamber (COLD)** | Lab protocol | Chamber + mitten rig + power analyzer | −40 °C gates: swap, latch, boot, upload, forecast derate | Per §20.4 (lab-run, results filed) |
| **Product qualification (PQT)** | Lab protocol | Lab fixtures | Drop, IP67, thermal, vibration, latch cycles — certification evidence | Per §21 (lab-run, results filed) |
| **Device fleet simulator (SIM)** | Python 3 | `trailcam-sim` container | N simulated cameras drive ingest/heartbeat/alerts without hardware | `./start-stop-services.sh --start --service=trailcam-sim` |

### 1.1 Catalog authority (sync rule)

`tests/test.py` is the single source of truth: **every ID documented here must run, and every test that runs must be documented.** Until a suite exists, its IDs are **pending** (specified + expected, not yet implemented). No ID may exist in only one place; project-plan §16 and the regression report totals move in lockstep with this file. Nothing is implemented yet — **0 passed / 293 pending**.

### 1.2 Summary (per-prefix counts)

| Category | Prefix | Count | Run-state |
|---|---|---|---|
| Auth (WebAuthn) | AUTH | 18 | pending |
| Pairing | PR | 8 | pending |
| Ingest (device API) | ING | 10 | pending |
| Heartbeat / dead-camera | HB | 8 | pending |
| Cameras & config | CAM | 16 | pending |
| On-device verify | CAM-DEV | 14 | pending |
| Platform image | YOCT | 6 | pending |
| Photos & detections | IMG | 8 | pending |
| PIR / edge AI | PIR | 8 | pending |
| Power & battery | PWR | 10 | pending |
| Networking | NET | 10 | pending |
| Alerts | ALR | 10 | pending |
| MCP | MCP | 20 | pending |
| OTA | OTA | 8 | pending |
| Local download (AP mode) | LDL | 12 | pending |
| Encrypted-at-rest media | ENC | 8 | pending |
| Field battery trials | BAT | 6 | pending (field) |
| Subscriptions | SUB | 8 | pending |
| Sharing | SHR | 6 | pending |
| Admin | ADM | 8 | pending |
| E2E chains | E2E | 16 | pending |
| Gap coverage | GAP | 20 | pending |
| Server health | SRV | 4 | pending |
| Service group | SVC | 4 | pending |
| Server boot | PHP | 5 | pending |
| MongoDB migration | MIG | 5 | pending |
| Builder smoke | BLD | 5 | pending |
| Device simulator | SIM | 6 | pending |
| Browser E2E | BROWSER | 4 | pending |
| Cold chamber | COLD | 8 | pending (lab) |
| Product qualification | PQT | 14 | pending (lab) |
| **Total** | | **293** | **0 passed / 293 pending** |

---

## 2. Test IDs — Auth (WebAuthn)

Contract reused verbatim from wificam/lugtrax (`web-auth/webauthn-lib`, RP_ID fixed per environment). Every test mints unique handles/emails per run (wificam regression #2 lesson).

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| AUTH-01 | Register begin returns creation options | `POST /auth/register/begin` | 200, `publicKey.challenge` present |
| AUTH-02 | Register complete creates user + credential | `POST /auth/register/complete` | 201, session cookie set |
| AUTH-03 | Register begin rejects duplicate handle | `POST /auth/register/begin` | 409 |
| AUTH-04 | Register begin rejects duplicate email | `POST /auth/register/begin` | 409 |
| AUTH-05 | Register begin rejects short handle | `POST /auth/register/begin` | 422 |
| AUTH-06 | Register begin rejects invalid email | `POST /auth/register/begin` | 422 |
| AUTH-07 | Login begin returns request options | `POST /auth/login/begin` | 200, `publicKey.allowCredentials` present |
| AUTH-08 | Login begin rejects unknown handle | `POST /auth/login/begin` | 404 |
| AUTH-09 | Login complete verifies assertion, opens session | `POST /auth/login/complete` | 200, session cookie |
| AUTH-10 | Login complete rejects bad signature | `POST /auth/login/complete` | 401 |
| AUTH-11 | Status returns session (handle, role, tier) | `GET /auth/status` | 200 |
| AUTH-12 | Status 401 when unauthenticated | `GET /auth/status` | 401 |
| AUTH-13 | Add passkey stores second credential | `POST /auth/add-passkey/*` | 200 |
| AUTH-14 | Delete passkey blocks removing last one | `DELETE /auth/passkeys/{id}` | 409 |
| AUTH-15 | Recovery token enrolls new passkey, revokes old | `POST /auth/recovery` | 200 |
| AUTH-16 | Recovery rejects expired token | `POST /auth/recovery` | 401 |
| AUTH-17 | Logout kills session | `POST /auth/logout` | 200 |
| AUTH-18 | Session cookie flags (HttpOnly, Secure, SameSite=Strict) | (headers) | flags present |

---

## 3. Test IDs — Pairing

| ID | Description | Endpoint / surface | Expected |
|---|---|---|---|
| PR-01 | Pair token minted for known device_id | `POST /api/pair-tokens` | 201, `PRT-…`, 15-min TTL |
| PR-02 | Pair token rejected for unknown device_id | `POST /api/pair-tokens` | 404 |
| PR-03 | BLE handshake returns device_id + short code | (device BLE) | matches factory record |
| PR-04 | Pair via app writes token; camera posts `/device/v1/pair` | BLE + device API | 200, `device_token` issued |
| PR-05 | Pair token single-use | second pair attempt | 410 |
| PR-06 | Pair token expired → 410 | aged token | 410 |
| PR-07 | QR fallback: manual device_id + in-case code works | `POST /device/v1/pair` | 200 |
| PR-08 | Wi-Fi credentials handoff to C6 at setup | BLE write | C6 joins AP; live-aim stream reachable |

---

## 4. Test IDs — Ingest (device API)

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| ING-01 | Device token required on `/device/v1/*` | `POST /device/v1/reports` (no auth) | 401 |
| ING-02 | Telemetry report accepted | `POST /device/v1/reports` | 202, `heartbeats` row written |
| ING-03 | Photo multipart accepted (4K JPEG, ≤ 12 MB) | `POST /device/v1/photos` | 201, `photos` row + object stored |
| ING-04 | Batch manifest (offline backlog) ingested in order | `POST /device/v1/photos` (batch) | order preserved, deduped |
| ING-05 | Config piggyback round-trip | any device call | response carries pending config delta + ack on next call |
| ING-06 | Rate limits: burst beyond N/min | hammer ingest | 429 with `retry_after` |
| ING-07 | Stale/revoked device token | old token post-unbind | 401 |
| ING-08 | Cross-user camera isolation | owner-scoped queries | 404, no leakage |
| ING-09 | Move-alert event recorded | `POST /device/v1/events` | 202, event row + rule evaluation |
| ING-10 | fw/hw versions recorded on first report | first report | `cameras.fw_version` set |

---

## 5. Test IDs — Heartbeat & dead-camera detection (the wedge)

The product's headline feature: missed check-ins must be *detected and pushed*, never discovered by the user.

| ID | Description | Surface | Expected |
|---|---|---|---|
| HB-01 | On-schedule check-in keeps status `healthy` | sim: hourly cadence | `status=healthy`, `expected_next_at` advances |
| HB-02 | Missed check-in + grace → `at_risk` | sim: skip 1 interval | transition row + push "missed check-in (battery 61%, last photo 11:04)" |
| HB-03 | 2× grace missed → `silent` | sim: skip 2 intervals | status `silent`, email + push sent |
| HB-04 | Retry cadence before alerting | sim: flaky camera | server retries at backoff; no premature alert within grace |
| HB-05 | Reconnect backfills transition | silent camera reports again | status → `healthy`, transition history preserved |
| HB-06 | Quiet hours suppress alert *delivery* (not detection) | quiet-hours rule | detection at correct time; delivery deferred |
| HB-07 | Status reflected in list + MCP `list_cameras` | API + MCP | `status` field present and consistent |
| HB-08 | Heartbeat SLA dashboard metrics | ops endpoint | missed-detection latency p50/p95 exported |

---

## 6. Test IDs — Cameras & config

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| CAM-01 | Create camera (claim) binds owner | `POST /api/cameras/claim` | 201 |
| CAM-02 | Unclaimed device invisible in lists | `GET /api/cameras` | absent |
| CAM-03 | Rename + move to site | `PATCH /api/cameras/{id}` | 200 persisted |
| CAM-04 | Capture config validation (res enum, interval range, quiet hours) | `PATCH /api/cameras/{id}` | 422 out-of-range |
| CAM-05 | IR mode switch (no_glow/low_glow/auto) | `PATCH` + device piggyback | config reaches camera, acked |
| CAM-06 | Instant-send toggle | `PATCH` | forecast updates same request |
| CAM-07 | `GET /api/cameras/{id}/status` returns heartbeat + forecast + signal | status endpoint | all three blocks present |
| CAM-08 | Battery endpoint returns smart-pack telemetry | `GET …/battery` | `{gauge_pct, voltage_mv, temp_c, forecast_days, chemistry}` |
| CAM-09 | Theft-mode requires owner role | member call | 403 |
| CAM-10 | Theft-mode arm/disarm audited | `POST …/theft-mode` | `audit_log` row |
| CAM-11 | Rotate device token | `POST …/rotate-token` | old 401, new 200 |
| CAM-12 | Unbind → unclaimed, config wiped | `DELETE /api/cameras/{id}` | claim cleared |
| CAM-13 | Move-alert threshold config | `PATCH` | persisted, validated |
| CAM-14 | Signal diagnostics page data | `GET …/signal` | `{rsrp_dbm, rsrq_dbm, band, carrier, latency_ms_p50, last_towers[]}` |
| CAM-15 | Site CRUD + camera grouping | `/api/sites` | 201/200, listing grouped |
| CAM-16 | Cross-user camera access denied | `GET /api/cameras/{other}` | 404 |

---

## 7. Test IDs — Photos & detections

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| IMG-01 | Photo list paginated, newest first | `GET /api/cameras/{id}/photos` | cursor pagination |
| IMG-02 | Class filter (deer/human/vehicle/empty) | `?class=deer` | only matching |
| IMG-03 | `empty` detections present but `billed=false` | DB inspection | audit trail without plan consumption |
| IMG-04 | Signed photo URLs expire | thumb fetch after TTL | 403/410 |
| IMG-05 | Edge v1 classifier classes + confidence persisted | sim inject | `ai_class`, `ai_confidence` set |
| IMG-06 | Classifier below min-confidence → class `other` | sim inject low-conf | rule not fired |
| IMG-07 | Battery forecast reflects instant-send change | toggle + report | `forecast_days` drops accordingly |
| IMG-08 | Delivery latency recorded per photo | DB | `latency_ms` p50/p95 queryable |

---

## 8. Test IDs — PIR / edge AI / false triggers

Bench + simulated; the false-trigger ledger (P5) requires empties never to bill.

| ID | Description | Surface | Expected |
|---|---|---|---|
| PIR-01 | PIR wake → capture ≤ 1.5 s | bench | measured, logged |
| PIR-02 | Radar+PIR fusion confirms real motion | bench walkthrough | capture; `detection` row |
| PIR-03 | PIR-only (no radar corroboration) on vegetation motion | fan/brush rig | suppressed or low-confidence, no upload |
| PIR-04 | Headlight/sweep test (classic false trigger) | bench | suppressed by radar rejection |
| PIR-05 | Edge v0 empty-frame discard | sim | stored on camera, counted, not uploaded |
| PIR-06 | Sensitivity wizard recommendation generated | API | suggestion after N false triggers |
| PIR-07 | Quiet-hours capture policy honored | config | no captures in window (or stored-only per config) |
| PIR-08 | Timelapse mode exists but plan-safe | config | timelapse frames count against pool, warned at enable |

---

## 9. Test IDs — Power & battery honesty

| ID | Description | Surface | Expected |
|---|---|---|---|
| PWR-01 | Sleep current ≤ 120 µA average | power analyzer | measured value logged |
| PWR-02 | Energy per 2.5K cycle ≤ 1.1 Wh | power analyzer | within budget |
| PWR-03 | Energy per 4K+video cycle ≤ 2.2 Wh | power analyzer | within budget |
| PWR-04 | Wake-to-capture ≤ 1.5 s cold | bench | measured |
| PWR-05 | Smart-pack detection (pack-ID) | insert pack | chemistry + gauge populate |
| PWR-06 | NiMH profile warns on voltage sag | insert NiMH tray | in-app warning, derated forecast |
| PWR-07 | Alkaline advisory shown | insert alkaline | advisory, not block |
| PWR-08 | Charge interlock < 0 °C | cold chamber | charging suspended + advisory (no plating) |
| PWR-09 | Weather-adjusted forecast | set site, inject weather | derate applied, "16 days at −25 °F tonight" shape |
| PWR-10 | Burn-down vs model ±15% over 72 h | bench soak | within tolerance |

---

## 10. Test IDs — Networking & connectivity

| ID | Description | Surface | Expected |
|---|---|---|---|
| NET-01 | LTE attach multi-IMSI eSIM | bench | registered, APN up |
| NET-02 | Auto-carrier selection reports carrier | telemetry | `carrier` set correctly |
| NET-03 | Instant-send upload p50 < 60 s | bench | measured, `latency_ms` recorded |
| NET-04 | Store-and-forward on outage | faraday box → restore | backlog drains in order |
| NET-05 | PSM between events (modem off) | power analyzer | current drops to sleep budget |
| NET-06 | SMS fallback (theft mode, data down) | SMSC stub | SMS ingested authenticated |
| NET-07 | GNSS fix + move alert | bench outdoors | fix + accuracy recorded |
| NET-08 | Reserve-battery anti-theft ping | main power removed + moved > ½ mi | pings every 6 h on reserve rail |
| NET-09 | Wi-Fi AP scan diagnostics | C6 | ≥ 3 MACs reported for placement coach |
| NET-10 | OTA download over LTE without photo loss | OTA + concurrent triggers | no lost captures |

---

## 11. Test IDs — Alerts

| ID | Description | Endpoint / surface | Expected |
|---|---|---|---|
| ALR-01 | Human/vehicle alert pushes within SLA | sim inject | push ≤ 60 s |
| ALR-02 | Species digest weekly (Pro) | job | digest email generated |
| ALR-03 | Battery-low rule fires at threshold | sim | alert + forecast link |
| ALR-04 | Delivery-slow rule fires on latency degradation | sim | honest status alert |
| ALR-05 | Move-alert (accel) fires theft candidate | bench | candidate, server decides burst |
| ALR-06 | Quiet hours respected | config | no delivery in window |
| ALR-07 | Channels per rule (push/email/sms) | config | only configured channels |
| ALR-08 | SSE stream authenticated | `/api/alerts/stream` unauth | 401 |
| ALR-09 | Alert payload includes photo thumb | inspect | thumb URL present |
| ALR-10 | Alert dedup (burst of same class) | sim | single alert per window |

---

## 11bis. Test IDs — Local download (BLE-gated on-demand AP mode)

Detailed plan: `project-plan.md` §5.4. Session = BLE handshake (pairing bond required) → per-session
SSID + WPA2 key → HTTPS on `192.168.77.1` with token-pinned self-signed cert → media manifest +
range GETs from eMMC/microSD. Bench harness: BLE central script (phone substitute) + Wi-Fi STA
client + `requests` with `verify=False` + cert-transcript pin check.

| ID | Description | Surface | Expected |
|---|---|---|---|
| LDL-01 | BLE-only session mint: `DLT-` token over authenticated BLE | C6 BLE | token, 10 min TTL, single use |
| LDL-02 | Session refused without pairing bond (fresh BLE central) | C6 BLE | rejected; no AP started |
| LDL-03 | AP SSID + WPA2 key unique per session | Wi-Fi scan | no static creds; SSID `wapiti-dl-<id>` |
| LDL-04 | Join + TLS handshake with token-pinned cert | HTTPS | app connects; wrong token rejected |
| LDL-05 | Media manifest lists correct files (filter honored) | HTTPS | `from/until/class` filter exact |
| LDL-06 | Range GET + resume across AP drop | Wi-Fi toggle | chunk resume; no corruption (hash check) |
| LDL-07 | Full-res pull throughput: 20 × 4K JPEGs < 5 min | bench | measured, logged |
| LDL-08 | Hard 10-min session cap enforced by C6 watchdog | bench timer | AP off mid-transfer; service stopped |
| LDL-09 | AP never active outside a session (idle scan) | Wi-Fi scan | SSID absent in normal operation |
| LDL-10 | Rate limit: 1 session / 5 min | repeat | second attempt refused until window |
| LDL-11 | `local_download` audit row synced on next check-in | ingest | row present server-side |
| LDL-12 | Session power cost logged as `local_dl_s` telemetry | reports | forecast derates accordingly |

---

## 11ter. Test IDs — Encrypted-at-rest media

Spec: `project-plan.md` §15.1 (§2 matrix row 24). Per-file AES-256-GCM CEKs, per-device KEK (C6 eFuse
wrap + cloud escrow under the account KMS key), `fscrypt` media store on eMMC + microSD, paired-phone
keystore cache for offline decrypt, theft-revocable key release. Harness: bench camera + generic USB
SD reader + a second camera as card-thief + API checks on escrow release/revocation.

| ID | Description | Surface | Expected |
|---|---|---|---|
| ENC-01 | Fresh capture on microSD is ciphertext: card pulled and read in a generic reader | bench + reader | no JPEG/PNG magic, no plaintext EXIF anywhere on the volume |
| ENC-02 | eMMC media store encrypted: raw dump over debug shows no plaintext media | bench | no media signatures in dump |
| ENC-03 | Card from camera A inserted into camera B | bench | refused/unreadable; camera B boots and operates normally |
| ENC-04 | Tampered wrapped-CEK is rejected; file quarantined, not served | SoC | decrypt error logged once; no retry loop |
| ENC-05 | Escrowed KEK released only to a WebAuthn-authenticated session of the bound account | API | 403 without session; bound session receives key |
| ENC-06 | Theft arm revokes key release; re-claimed flagged serial cannot obtain keys | API + E2E-14..15 chain | release refused; audit row written |
| ENC-07 | Paired phone decrypts AP-downloaded media offline with cached KEK; non-paired phone cannot | §5.4 harness | owner sees gallery with no network; stranger sees ciphertext only |
| ENC-08 | Crypto overhead measured; tamper events audit-logged and synced | SoC + ingest | < 1% of capture burst; `enc_tamper` row synced on next check-in |

---

## 12. Test IDs — MCP

Scoped API keys (`read`/`write`/`theft:write`); hardened non-negotiables per project-plan §11.1.

| ID | Description | Tool / surface | Expected |
|---|---|---|---|
| MCP-01 | `list_cameras` returns fleet + status | tool call | JSON rows incl. `status` |
| MCP-02 | `get_camera` detail | tool call | config + forecast |
| MCP-03 | `get_photos` class filter | tool call | filtered |
| MCP-04 | `get_status` honest diagnostics | tool call | heartbeat/latency/forecast |
| MCP-05 | `set_capture_config` tier-checked | tool call | applied or clean error |
| MCP-06 | `set_ir_mode` remote switch | tool call | acked via piggyback |
| MCP-07 | `arm_theft` requires `theft:write` scope | read-key call | 403-equivalent JSON-RPC |
| MCP-08 | `arm_theft` audited | audit log | row with actor + args redacted |
| MCP-09 | `disarm_theft` restores idle | tool call | burst ends |
| MCP-10 | `get_alerts` windowed | tool call | recent alerts |
| MCP-11 | Session cookie rejected at `/mcp` | portal session | 401 JSON-RPC |
| MCP-12 | Revoked key rejected cleanly | revoked key | JSON-RPC error, no partial exec |
| MCP-13 | No tool mints/widens scopes | attempt | refused |
| MCP-14 | No tool invokes an LLM (no recursion) | design audit | pass |
| MCP-15 | Reads audited too | audit log | rows present |
| MCP-16 | Row caps enforced (list/history) | huge fleet | capped |
| MCP-17 | Cross-user camera_id → 404-equivalent | isolation | no data leak |
| MCP-18 | Rate limited with clean error | hammer | JSON-RPC 429 shape |
| MCP-19 | Token economy: responses compact JSON | inspect | no verbose dumps |
| MCP-20 | `arm_theft` rate-limited | repeat | limited, audited |

---

## 13. Test IDs — OTA

| ID | Description | Surface | Expected |
|---|---|---|---|
| OTA-01 | Signed artifact verified before install | tampered artifact | rejected |
| OTA-02 | Staged rollout canary → 10% → 100% | campaign API | cohorts honored |
| OTA-03 | A/B swap + boot counter | device | slot flips, boots |
| OTA-04 | Rollback on boot failure | bad image | reverts, counter logged |
| OTA-05 | Anti-downgrade version policy | older version | rejected |
| OTA-06 | C6 co-processor firmware artifact separate | campaign | correct target |
| OTA-07 | `rollback_of` linkage | campaign API | audit chain |
| OTA-08 | Non-admin cannot create campaigns | user call | 403 |

---

## 14. Test IDs — Subscriptions

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| SUB-01 | Public plans endpoint lists 3 tiers + prices | `GET /api/subscription/plans` | 200 |
| SUB-02 | Checkout creates pending subscription | `POST /api/subscription` | 201 |
| SUB-03 | Tier activation unlocks caps | webhook stub | `users.tier` updated |
| SUB-04 | Free tier: 1 camera max | 2nd claim | 402 + `upgrade_url` |
| SUB-05 | Pro: 10 cameras max | 11th claim | 402 |
| SUB-06 | Free tier photo pool: 50/mo | 51st photo | stored, not delivered; advisory |
| SUB-07 | Pause anytime → $0, cameras keep Free behavior | pause flow | no charge, 1 check-in/day |
| SUB-08 | Lapse → Free tier (never a brick) | expiry | camera alive on Free floor |

---

## 15. Test IDs — Sharing

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| SHR-01 | Member invite by handle, site-scoped | `POST /api/sites/{id}/members` | 201 |
| SHR-02 | Member sees live + history, cannot arm/config | member session | 200 / 403 split |
| SHR-03 | Share link minted with expiry ≤ 7 d | `POST /api/cameras/{id}/share-links` | 201 |
| SHR-04 | Public link shows scoped data only | `GET /api/share/{token}` | no owner PII beyond scope |
| SHR-05 | Revoked link → 410 immediately | revoke | 410 |
| SHR-06 | Renders audited + rate-limited per link | fetch loop | 429 after N |

---

## 16. Test IDs — Admin

| ID | Description | Endpoint | Expected |
|---|---|---|---|
| ADM-01 | Bootstrap creates seed admin | `php artisan wapiti:bootstrap-admin` | user + enrollment URL |
| ADM-02 | Bootstrap prints enrollment URL | console | contains RP_ID |
| ADM-03 | Admin lists users/cameras | `GET /admin/api/*` | 200 |
| ADM-04 | Admin updates user tier/role | `PATCH /admin/api/users/{id}` | 200 |
| ADM-05 | Non-admin blocked | user call | 403 |
| ADM-06 | Admin views audit log | `GET /admin/api/audit-log` | append-only rows |
| ADM-07 | Admin views fleet health (status counts) | `GET /admin/api/health` | healthy/at_risk/silent counts |
| ADM-08 | GDPR export/erase | `POST /admin/api/users/{id}/erase` | erased + report |

---

## 17. Test IDs — Browser E2E (PWA)

Playwright against the PWA; WebAuthn via Chromium virtual authenticator.

| ID | Description | Surface | Expected |
|---|---|---|---|
| BROWSER-01 | Login via passkey (virtual authenticator) | Playwright | gallery loads, session cookie set |
| BROWSER-02 | Claim camera via QR + pair-token flow | Playwright | camera appears in grid |
| BROWSER-03 | Status grid reflects at_risk/silent transitions live | Playwright + SSE | status updates without reload |
| BROWSER-04 | Photo gallery class filter + share-link mint in UI | Playwright | filtered view; link fetches scoped JSON |

---

## 18. E2E chain tests

Chained API scenarios; each builds on the previous; failure aborts the chain.

### E2E: Full happy path (E2E-01 → E2E-08)

**Purpose:** prove the product loop — signup → claim → first photo → heartbeat → alert → share → cleanup.

| ID | Step |
|---|---|
| E2E-01 | Register (WebAuthn begin/complete) |
| E2E-02 | Create site "North 40" |
| E2E-03 | Claim simulated camera (pair token → `/device/v1/pair`) |
| E2E-04 | First photo delivered ≤ 60 s (instant-send) |
| E2E-05 | Config: quiet hours + IR auto + simultaneous photo/video |
| E2E-06 | Sim deer capture → photo + detection rows, push alert |
| E2E-07 | Sim miss check-in → `at_risk` push → reconnect → `healthy` (HB-02..05 path) |
| E2E-08 | Mint share link → anonymous fetch → scoped JSON → revoke → 410 |

### E2E: Cold-season resilience (E2E-09 → E2E-13)

| ID | Step |
|---|---|
| E2E-09 | Set site location (weather anchor) |
| E2E-10 | Inject cold snap weather → forecast derates (PWR-09 shape) |
| E2E-11 | Sim offline 48 h → ring buffer accumulates |
| E2E-12 | Reconnect → backlog drains in order, heartbeat restores |
| E2E-13 | Battery-low alert path with honest forecast |

### E2E: Theft + tiers (E2E-14 → E2E-16)

| ID | Step |
|---|---|
| E2E-14 | Move-alert → theft arm → burst cadence observed → disarm via MCP |
| E2E-15 | Reserve-battery ping path while main power removed (NET-08) |
| E2E-16 | Free user: cam #2 claim → 402 + upgrade_url; upgrade → success; pool cap advisory |

---

## 19. Gap coverage tests

Added after code review (wificam GAP pattern).

| ID | Description | Catches |
|---|---|---|
| GAP-01 | Site with empty name → 422 | Validation |
| GAP-02 | Pair token for foreign device_id → 404 | Enumeration |
| GAP-03 | Photo manifest with NaN coords → 422 | Malformed input |
| GAP-04 | Negative accuracy → 422 | Range |
| GAP-05 | Quiet hours crossing midnight accepted | Edge |
| GAP-06 | Capture config interval below tier floor → 422 | TierGuard |
| GAP-07 | IR switch mid-write (power loss) → recovers valid config | Robustness |
| GAP-08 | Alert rule unknown class → 422 | Enum |
| GAP-09 | Theft-mode on unclaimed camera → 409 | State machine |
| GAP-10 | Pack swap reported while camera offline → pending state | State machine |
| GAP-11 | device_token reuse after unbind → 401 | Token lifecycle |
| GAP-12 | Duplicate photos in batch manifest → deduped | Ingest hygiene |
| GAP-13 | Share-link token collision → 409 or retry | Uniqueness |
| GAP-14 | Export of zero-photo range → valid empty zip | Edge |
| GAP-15 | OTA manifest downgrade → rejected | Version policy |
| GAP-16 | MCP call with foreign camera_id → 404-equivalent | Isolation |
| GAP-17 | SSE unauthenticated → 401 | Auth |
| GAP-18 | 429 shape includes `retry_after` | API hygiene |
| GAP-19 | Mongo state: heartbeat row exists after check-in | Side effects |
| GAP-20 | Mongo state: `status` transitions persist with timestamps | Side effects |

---

## 20. Infra suites (SRV / SVC / PHP / MIG / BLD / SIM)

House conventions (lugtrax §15), all pending.

### 20.1 Server health (SRV-01..04)
`curl -k https://localhost:4440/api/health` → 200, `.status=ok`, `.service=trailcam-server`; `/mcp` unauth → 401.

### 20.2 Service group (SVC-01..04)
`./start-stop-services.sh --status | grep trailcam` → RUNNING; nginx `-t` ok; `ss -tlnp | grep 4440` LISTEN; stop/start cycle healthy.

### 20.3 Server boot (PHP-01..05)
`php artisan list` ok; route present; `APP_KEY` set; conncheck → REDIS PONG; conncheck → MongoDB wapiti.

### 20.4 MongoDB migration (MIG-01..05)
`migrate:fresh` clean; users unique handle/email; cameras unique `device_id`; `pair_tokens` TTL 900 s; photos compound index `{camera_id, capture_at}`.

### 20.5 Builder smoke (BLD-01..05)
Image listed; artifacts exist; one-shot (no ports); build idempotent; `trailcam-test` runs pytest.

### 20.6 Device simulator (SIM-01..06)
10 cams idle cadence 10 min no loss; 100 cams burst p95 < 300 ms; 20% flaky → replay ok; mixed transports tagged; stale token → 401; config piggyback round-trip.

---

## 21. Device-side suites

### 21.1 On-device verification (CAM-DEV, runs as `CAM` suite over SSH/serial)

| ID | Check | Expected |
|---|---|---|
| CAM-DEV-01 | Device reachable (SSH/serial) | shell OK |
| CAM-DEV-02 | Boot from cold to capture-ready ≤ 1.5 s | measured |
| CAM-DEV-03 | 4K still capture + JPEG valid | EXIF sane |
| CAM-DEV-04 | 1080p10 clip + simultaneous photo | both files valid |
| CAM-DEV-05 | IR arrays switch independently | luminance delta measured |
| CAM-DEV-06 | LCD aim preview shows scene | manual + frame grab |
| CAM-DEV-07 | PIR wake latency | ≤ spec |
| CAM-DEV-08 | eMMC + microSD write | both mounts OK |
| CAM-DEV-09 | RTC keeps time across power removal | supercap ride-through |
| CAM-DEV-10 | Fuel gauge + temp sensors read | plausible values |
| CAM-DEV-11 | Modem attach + upload | 202 |
| CAM-DEV-12 | BLE pairing surface | app connects |
| CAM-DEV-13 | Wi-Fi live aim stream | ≤ 3 s latency |
| CAM-DEV-14 | Watchdog resets hung SoC | auto-recovery logged |

### 21.2 Power (PWR bench — see §9) · 21.3 Networking (NET bench — see §10)

### 21.4 Cold chamber (COLD-01..08) — lab-run, −40 °C, mitten rig

| ID | Test | Method | Pass criteria |
|---|---|---|---|
| COLD-01 | Soak −40 °C 24 h, then boot + capture + upload | chamber | full function |
| COLD-02 | PIR wake + capture at −40 °C | chamber | latency ≤ 2× room-temp spec |
| COLD-03 | LTE upload at −40 °C | chamber | delivered; latency recorded honestly |
| COLD-04 | Battery forecast derate matches measured burn-down | chamber + analyzer | ±15% |
| **COLD-05** | **One-hand gloved pack swap < 20 s at −40 °C** | mitten rig, timed | **the box claim gate** |
| **COLD-06** | **Latch + gasket 500 cycles at −40 °C w/ simulated mittens** | fixture | seal intact → IP67 retest passes |
| COLD-07 | Charge interlock below 0 °C (standard pack) | chamber | no charge current; advisory in app |
| COLD-08 | Arctic (LTO) pack charges at −30 °C | chamber | charge proceeds within spec |

### 21.5 Platform image (YOCT-01..06) — wificam §2.2 pattern, on the camera

| ID | Check | Expected |
|---|---|---|
| YOCT-01 | `device/yocto/build.sh` produces `wapiti-image.swu` deterministically | build ID recorded; rebuild reproducible |
| YOCT-02 | Read-only rootfs enforced; persistent state only on `/data` partition | writes outside `/data` fail |
| YOCT-03 | `.swu` RSA signature verified by SWUpdate | tampered image rejected on device |
| YOCT-04 | A/B slot update + boot-counter rollback (device-level, pairs with OTA-03/04) | slot flips; bad image reverts |
| YOCT-05 | Suspend-to-RAM soak: 10,000 wake/sleep cycles | no leaks/wedges; resume ≤ 1.5 s wake-to-capture |
| YOCT-06 | SPDX license manifest generated per build | manifest filed for compliance (§13) |

### 21.6 Field battery-life trials (BAT-01..06) — field/lab-run, real burn-down

Extends PQT-12 (72 h bench burn-down) to **real-world trials**: the prototype runs the usage
profiles from `competitive-analysis.md` §4.2 (heavy usage defined in Ah) in actual deployment
conditions, taking photos/videos and uploading over LTE (and Wi-Fi/AP for BAT-06). Current-logger
telemetry + fuel-gauge ring buffer provide measured mAh/day; results are **documented in the results
log below** (raw CSV under `tests/reports/battery/`) — these measured lines replace the estimates in
competitive-analysis §4.2 and print on the box.

| ID | Trial | Method | Pass criteria |
|---|---|---|---|
| BAT-01 | Standby baseline: 7-day idle run | bench, current logger + fuel gauge | avg sleep ≤ 120 µA; no runaway wakeups in log |
| BAT-02 | Light profile, 14 days: 10 photos/day, instant-send, hourly check-in | field unit, real captures + LTE uploads | measured Ah/day within ±15% of §4.2 light row; log entry filed |
| BAT-03 | **Heavy profile, 14 days: 100 photos/day, 100% instant-send, 2 × 30 s clips** | field unit, LTE uploads | measured Ah/day within ±15% of §4.2 heavy row (~0.23); evidence pack for marketing |
| BAT-04 | Cold trial: 7 days, typical profile, −20 °C…−40 °C | winter field or chamber | derate matches published curve; no cliff-off; forecast honest within ±15% |
| BAT-05 | Solar rig: heavy profile + 7 W panel, autumn sun | field | net-positive daily charge; < 0 °C charge interlock demonstrated in log |
| BAT-06 | Upload-path energy split: same 20-photo set via LTE vs Wi-Fi/AP pull | bench, A/B | AP path ≥ 3× cheaper per photo; §5.4 claim validated |

**Results log (real trials — fill as runs complete; never pre-filled):**

| Date | Unit / serial | Trial | Measured Ah/day | Forecast | Δ | Notes |
|---|---|---|---|---|---|---|
| — | — | — | — | — | — | *(pending prototype)* |

---

## 22. Product qualification (PQT-01..14) — lab-executed, certification evidence

| ID | Test | Method / standard | Pass criteria |
|---|---|---|---|
| PQT-01 | Drop 1.5 m × 6 faces × 2 | IEC 60068-2-31 | functional, enclosure intact |
| PQT-02 | Immersion 1 m / 30 min | IEC 60529 (IP67) | dry internal inspection |
| PQT-03 | Dust chamber | IEC 60529 (IP6X) | no ingress |
| PQT-04 | Thermal cycling −40 ↔ +85 °C × 20 | IEC 60068-2-14 | functional each soak |
| PQT-05 | Cold soak −40 °C operation | MIL-STD-810H 502-style | boots, captures, uploads |
| PQT-06 | Hot soak +85 °C + solar-panel input | MIL-STD-810H 501-style | no thermal shutdown |
| PQT-07 | Vibration (tree/transport profile) | IEC 60068-2-64 | functional, no rattle |
| PQT-08 | Strap/mount pull + torque | fixture | mount holds, threads intact |
| PQT-09 | Paddle-lever life ≥ 5,000 actuations | fixture | functional |
| PQT-10 | Salt-fog exposure | IEC 60068-2-11 | contacts OK |
| PQT-11 | Battery swap cycles ≥ 500 w/ gasket check | fixture | seals; IP67 retest passes |
| PQT-12 | 72 h soak: adaptive burn-down vs forecast model | bench | ±15% |
| PQT-13 | IR LED array life + thermal derate | fixture | 96′/80′ ranges hold |
| PQT-14 | Security box + python-lock engagement | fixture | tamper event reported |

PQT/COLD artifacts (lab reports, photos, serials) filed under `tests/reports/pqt/` and referenced by the certification matrix (project-plan §13).

> **Status (planning):** hardware exists as design only (project-plan §4). EVK bench units required for §20; chamber + fixtures for COLD/PQT. Every device-side ID is pending.

---

## 23. Feature-to-test coverage matrix

| Feature (project-plan §) | Test IDs | Coverage |
|---|---|---|
| WebAuthn auth (§10) | AUTH-01..18 | Full |
| Pairing / claim (§8.3) | PR-01..08, CAM-01..02, E2E-03 | Full |
| Heartbeat / dead-camera (§8.1) — **the wedge** | HB-01..08, E2E-07, GAP-19..20, SIM-03 | Full |
| Ingest + piggyback (§14) | ING-01..10, SIM-06 | Full |
| Capture pipeline + IR (§1 goals) | CAM-DEV-03..06, IMG-01..02 | Full |
| PIR/radar + false-trigger discipline (§11.2) | PIR-01..08, IMG-03..06 | Full |
| Power family + honest battery (§5) | PWR-01..10, COLD-04..08, IMG-07, PQT-12 | Full |
| Field battery-life trials / measured burn-down (§5, competitive-analysis §4.2) | BAT-01..06 | Full (field) |
| Mitten-swap chassis (§5.3) | **COLD-05..06**, PQT-09, PQT-11 | Full (lab) |
| Tree mount — strap slots + ¼-20 boss (§5.3) | PQT-08 | Full (lab) |
| Local download AP mode (§5.4) | LDL-01..12 | Full |
| Encrypted-at-rest media (§15.1) | ENC-01..08 | Full |
| Networking + store-and-forward (§8.2) | NET-01..10, E2E-11..12 | Full |
| Anti-theft + reserve GPS (§8.4) | NET-07..08, E2E-14..15, CAM-09..10 | Full |
| Alerts (§8) | ALR-01..10 | Full |
| MCP (§11.1) | MCP-01..20, GAP-16..17 | Full |
| OTA (§8.5) | OTA-01..08, CAM-DEV-14, YOCT-03..04 | Full |
| Platform image / substrate (wificam §2.2 pattern) | YOCT-01..06 | Full |
| Subscriptions / pause / lapse (§7.1) | SUB-01..08, E2E-16 | Full |
| Sharing (§7.2) | SHR-01..06, E2E-08 | Full |
| Admin + GDPR (§14) | ADM-01..08 | Full |
| PWA (project-plan WI-305) | BROWSER-01..04 | Full |
| Infra (§9, §17) | SRV/SVC/PHP/MIG/BLD/SIM | Full |
| Durability + cert claims (§13) | PQT-01..14, COLD-01..08 | Full (lab) |
| Live streaming (non-goal, v1 = bursts) | — | Out of scope |
| Crowdsourced finding (non-goal) | — | Out of scope |

---

## 24. Regression tests

After every bug fix, append an entry (newest first): **Problem → Root cause → Fix → Tests → Mermaid**. Env-only failures go to the registry, never mistaken for regressions (wificam §18 convention). No entries yet — template below.

### Template

```markdown
### N. <Short title>

**Problem:** <What broke>

**Root cause:** <Why it broke>

**Fix:** <What changed>

**Tests:** `<ID>` — <description>

\`\`\`mermaid
flowchart TD
    A["Before"] --> B["Broken path"]
    C["After"] --> D["Fixed path"]
    style B fill:#e44,color:#fff
    style D fill:#2d6,color:#fff
\`\`\`
```

### Illustrative entry (format example — not a real event)

```markdown
### 1. Camera reported healthy through a 30-hour outage

**Problem:** A camera that lost power stayed `healthy` for 30 h; the user found a dead camera at the property.

**Root cause:** The heartbeat worker compared `expected_next_at` to wall clock without the grace window, but a timezone bug made grace = 24 h instead of 2 h.

**Fix:** Grace derived from the camera's own cadence server-side (mode-aware evaluator), unit-tested across DST boundaries.

**Tests:** `HB-03` — 2× grace → silent; `HB-05` — reconnect backfills transition.

\`\`\`mermaid
flowchart TD
    A["Check-in due"] --> B{"within grace?"}
    B -- yes --> C["healthy"]
    B -- no --> D["at_risk → silent<br/>(derived server-side)"]
    style D fill:#2d6,color:#fff
\`\`\`
```

### Env-only failure registry (empty at start)

| ID | Failure | Why environment-only | Status |
|---|---|---|---|
| *(none yet)* | | | |

---

## 25. How to run

```bash
# Infra smoke (SRV/SVC/PHP/MIG/BLD/SIM)
python3 tests/regression.py
python3 tests/regression.py -k srv,php
cat tests/reports/test-regression.md

# Full API suite — host side
python3 tests/test.py --host https://localhost:4440 -v

# Full suite — in container (recommended)
./start-stop-services.sh --start --service=trailcam-test

# Single prefix / single test
python3 tests/test.py -k "test_auth"
python3 tests/test.py -k "test_hb"
python3 tests/test.py -k "test_auth_01"

# Device suites (bench camera over SSH; chamber for COLD)
python3 tests/test.py --device <bench-ip> -k "test_cam"
python3 tests/test.py --device <bench-ip> -k "test_pwr"
python3 tests/test.py --device <bench-ip> -k "test_net"

# Simulator fleet
./start-stop-services.sh --start --service=trailcam-sim

# PHP + browser
php artisan test
npx playwright test

# COLD/PQT: executed at lab; file artifacts under tests/reports/pqt/ and update §1.2 counts.
```

### Output

```
tests/reports/test-report-YYYYMMDD_HHMMSS.md   # full report
tests/reports/test-report.md                    # symlink → latest
tests/reports/pqt/                              # certification evidence bundle (PQT + COLD)
```
