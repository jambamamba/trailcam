#!/usr/bin/env python3
"""
Infra smoke runner — SRV / SVC / PHP / MIG / BLD / SIM (test-plan §20).

Modeled on the wificam/lugtrax one-shot runner: Python 3 **stdlib only**
(`subprocess`, `argparse`, `pathlib`, `datetime`) per test-plan §1. It runs on
the host, where the docker CLI is available, and execs into the app container
(`trailcam-server`) and the Mongo container (`database-server`).

Implemented so far: MIG-01..05 + PHP-01..03/05 + SRV-01..03 (WI-102) and
SVC-01..04 + BLD-01..05 (WI-103). IDs whose work item has not landed
(PHP-04 Redis, SRV-04 MCP, SIM-01..06) are reported as **pending** and never
fail the run, per test-plan §1.1.

Usage:
    python3 tests/regression.py                 # every prefix
    python3 tests/regression.py -k mig,php      # subset (comma-separated)
    python3 tests/regression.py -k MIG-04       # single ID
    cat tests/reports/test-regression.md        # report of the last run

Exit code: 0 = no failures, 1 = at least one FAIL, 2 = bad selection.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "server"          # Laravel app (project-plan §18)
REPORT = REPO / "tests" / "reports" / "test-regression.md"

# -------------------------------------------------------------------------- #
# Environment defaults (override with flags)
# -------------------------------------------------------------------------- #


def _env_default(key: str, fallback: str) -> str:
    """Read KEY from server/.env (no dotenv dependency), else fallback."""
    env_file = APP / ".env"
    if env_file.exists():
        m = re.search(rf"^{re.escape(key)}=(.*)$", env_file.read_text(), re.M)
        if m and m.group(1).strip():
            return m.group(1).strip().strip('"').strip("'")
    return fallback


DEFAULT_APP_CONTAINER = "trailcam-server"
DEFAULT_MONGO_CONTAINER = "database-server"
DEFAULT_APP_WORKDIR = "/var/www/html"


class Ctx:
    """Runtime configuration shared by every check."""

    def __init__(self, args: argparse.Namespace):
        self.app_container = args.container
        self.mongo_container = args.mongo_container
        self.workdir = args.workdir
        self.db = args.db or _env_default("MONGODB_DATABASE", "wapiti")
        self.host = args.host


# -------------------------------------------------------------------------- #
# Small helpers (subprocess only — no third-party imports)
# -------------------------------------------------------------------------- #


def docker_exec(ctx: Ctx, *args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", "-w", ctx.workdir, ctx.app_container, *args],
        capture_output=True, text=True, timeout=timeout,
    )


def mongo_eval(ctx: Ctx, js: str, timeout: int = 60) -> str:
    """Run a mongosh snippet in the app DB; returns stripped stdout."""
    proc = subprocess.run(
        ["docker", "exec", "-e", "HOME=/tmp", ctx.mongo_container,
         "mongosh", "--quiet", ctx.db, "--eval", js],
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.stdout.strip()


# mongosh snippets (single-line, print exactly one OK/BAD token)
def js_unique_index(collection: str, field: str) -> str:
    return (
        "try{var ix=db.getCollection('" + collection + "').getIndexes();"
        "var ok=ix.some(function(i){return i.unique===true&&Object.keys(i.key).length===1&&i.key['" + field + "']===1;});"
        "print(ok?'OK':'BAD');}catch(e){print('BAD');}"
    )


def js_ttl(collection: str, field: str, seconds: int) -> str:
    return (
        "try{var ix=db.getCollection('" + collection + "').getIndexes();"
        "var t=null;ix.forEach(function(i){if(i.key['" + field + "']===1)t=i;});"
        "print(t&&t.expireAfterSeconds===" + str(seconds) + "?'OK':'BAD');"
        "}catch(e){print('BAD');}"
    )


def js_compound(collection: str, keys: list[str]) -> str:
    conds = "&&".join("i.key['%s']===1" % k for k in keys)
    return (
        "try{var ix=db.getCollection('" + collection + "').getIndexes();"
        "var ok=ix.some(function(i){return Object.keys(i.key).length===" + str(len(keys))
        + "&&" + conds + ";});print(ok?'OK':'BAD');}catch(e){print('BAD');}"
    )


def mongo_is(ctx: Ctx, js: str) -> tuple[bool, str]:
    out = mongo_eval(ctx, js)
    return out.splitlines()[-1].strip() == "OK" if out else False, out


# -------------------------------------------------------------------------- #
# Checks — implemented
# -------------------------------------------------------------------------- #


def check_mig_01(ctx: Ctx) -> tuple[bool, str]:
    """MIG-01: php artisan migrate:fresh runs clean (rc 0, migrations apply)."""
    proc = docker_exec(ctx, "php", "artisan", "migrate:fresh", "--force", timeout=300)
    out = (proc.stdout + proc.stderr).strip()
    ok = proc.returncode == 0 and re.search(r"DONE|Nothing to migrate", out) is not None
    return ok, f"rc={proc.returncode} :: {out.splitlines()[-1] if out else '(no output)'}"


def check_mig_02(ctx: Ctx) -> tuple[bool, str]:
    """MIG-02: users carry unique single-key indexes on handle AND email."""
    ok, out = mongo_is(
        ctx,
        "try{var ix=db.getCollection('users').getIndexes();"
        "var h=ix.some(function(i){return i.unique===true&&Object.keys(i.key).length===1&&i.key['handle']===1;});"
        "var e=ix.some(function(i){return i.unique===true&&Object.keys(i.key).length===1&&i.key['email']===1;});"
        "print(h&&e?'OK':'BAD');}catch(err){print('BAD');}")
    return ok, out or "(no output)"


def check_mig_03(ctx: Ctx) -> tuple[bool, str]:
    """MIG-03: cameras unique device_id (factory-provisioned, immutable)."""
    ok, out = mongo_is(ctx, js_unique_index("cameras", "device_id"))
    return ok, out or "(no output)"


def check_mig_04(ctx: Ctx) -> tuple[bool, str]:
    """MIG-04: pair_tokens TTL on expires_at, expireAfterSeconds = 900 (§6.1)."""
    ok, out = mongo_is(ctx, js_ttl("pair_tokens", "expires_at", 900))
    return ok, out or "(no output)"


def check_mig_05(ctx: Ctx) -> tuple[bool, str]:
    """MIG-05: photos compound index {camera_id, capture_at} (§6.1)."""
    ok, out = mongo_is(ctx, js_compound("photos", ["camera_id", "capture_at"]))
    return ok, out or "(no output)"


def check_php_01(ctx: Ctx) -> tuple[bool, str]:
    """PHP-01: artisan CLI boots — Laravel 12.x, rc 0."""
    proc = docker_exec(ctx, "php", "artisan", "list")
    if proc.returncode != 0:
        return False, f"artisan list rc={proc.returncode}"
    ver = docker_exec(ctx, "php", "artisan", "--version")
    m = re.search(r"Laravel Framework (\d+)\.", ver.stdout)
    ok = ver.returncode == 0 and m is not None and m.group(1) == "12"
    return ok, (ver.stdout.strip() or "(no version)") + " · artisan list rc=0"


def check_php_02(ctx: Ctx) -> tuple[bool, str]:
    """PHP-02: route:list carries /api/health (test-plan §20.3)."""
    proc = docker_exec(ctx, "php", "artisan", "route:list")
    ok = proc.returncode == 0 and "api/health" in proc.stdout
    return ok, "route present" if ok else f"rc={proc.returncode}, api/health missing"


def check_php_03(ctx: Ctx) -> tuple[bool, str]:
    """PHP-03: server/.env carries at least one APP_KEY=base64… line."""
    env_file = APP / ".env"
    if not env_file.exists():
        return False, ".env missing"
    n = len(re.findall(r"^APP_KEY=base64", env_file.read_text(), re.M))
    return n >= 1, f"count={n}"


def check_php_05(ctx: Ctx) -> tuple[bool, str]:
    """PHP-05: conncheck reaches MongoDB (test-plan §20.3)."""
    proc = docker_exec(ctx, "php", "scripts/conncheck.php")
    out = (proc.stdout + proc.stderr).strip()
    ok = proc.returncode == 0 and "connected to " in out and "FAILED" not in out
    return ok, out.splitlines()[-1] if out else "(no output)"


# -------------------------------------------------------------------------- #
# Infra helpers (HTTP over self-signed dev TLS)
# -------------------------------------------------------------------------- #


def _ssl_unverified():
    ctx_ssl = ssl.create_default_context()
    ctx_ssl.check_hostname = False
    ctx_ssl.verify_mode = ssl.CERT_NONE
    return ctx_ssl


def http_get_json(ctx: Ctx, path: str, timeout: int = 10) -> tuple[int, dict]:
    url = ctx.host.rstrip("/") + path
    with urllib.request.urlopen(url, timeout=timeout, context=_ssl_unverified()) as resp:
        return resp.status, json.loads(resp.read().decode() or "{}")


def service_script(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(REPO / "start-stop-services.sh"), *args],
        cwd=REPO, capture_output=True, text=True, timeout=timeout,
    )


def wait_health(ctx: Ctx, timeout: int = 60) -> tuple[bool, str]:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            status, body = http_get_json(ctx, "/api/health", timeout=5)
            if status == 200 and body.get("status") == "ok":
                return True, "healthy after (re)start"
            last = f"HTTP {status} status={body.get('status')!r}"
        except Exception as exc:  # noqa: BLE001 — boot race, keep polling
            last = str(exc)
        time.sleep(2)
    return False, f"not healthy within {timeout}s: {last}"


# ---- SVC (WI-103 — service group) ----


def check_svc_01(ctx: Ctx) -> tuple[bool, str]:
    proc = service_script(["--status"])
    first = (proc.stdout.splitlines() or [""])[0]
    return proc.returncode == 0 and "trailcam-server: RUNNING" in proc.stdout, first


def check_svc_02(ctx: Ctx) -> tuple[bool, str]:
    proc = docker_exec(ctx, "sh", "-c",
                       "grep -q default.wapiti.cam /etc/nginx/sites-enabled/* && sudo nginx -t")
    out = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0 and "syntax is ok" in out, out.splitlines()[-1] if out else ""


def check_svc_03(ctx: Ctx) -> tuple[bool, str]:
    # This machine publishes docker ports via iptables only (no host socket —
    # `ss` shows nothing even for working ports), so the publish is verified
    # with `docker port` instead of `ss -tlnp` (test-plan §20.2 env note).
    proc = subprocess.run(["docker", "port", "trailcam-server"],
                          capture_output=True, text=True, timeout=30)
    out = proc.stdout.strip()
    return proc.returncode == 0 and ":4444" in out, out.replace("\n", ", ")


def check_svc_04(ctx: Ctx) -> tuple[bool, str]:
    stop = service_script(["--stop", "--service=trailcam-server"])
    start = service_script(["--start", "--service=trailcam-server"])
    if start.returncode != 0:
        return False, f"start rc={start.returncode}: {start.stderr.strip()}"
    ok, detail = wait_health(ctx)
    return ok, f"stop:{stop.returncode} start:{start.returncode} · {detail}"


# ---- BLD (WI-103 — builder + test one-shot images) ----


def _image_inspect(name: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "image", "inspect", name],
                          capture_output=True, text=True, timeout=30)


def _run_builder(timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "run", "--rm", "-v", f"{APP}:/var/www/html", "trailcam-builder:v1"],
        capture_output=True, text=True, timeout=timeout,
    )


def check_bld_01(ctx: Ctx) -> tuple[bool, str]:
    proc = _image_inspect("trailcam-builder:v1")
    return proc.returncode == 0, "image listed" if proc.returncode == 0 else "image missing"


def check_bld_02(ctx: Ctx) -> tuple[bool, str]:
    proc = _run_builder()
    artifact = APP / "vendor" / "autoload.php"
    ok = proc.returncode == 0 and artifact.exists()
    return ok, f"builder rc={proc.returncode}, vendor/autoload.php={'present' if artifact.exists() else 'missing'}"


def check_bld_03(ctx: Ctx) -> tuple[bool, str]:
    proc = subprocess.run(
        ["docker", "image", "inspect", "-f", "{{json .Config.ExposedPorts}}", "trailcam-builder:v1"],
        capture_output=True, text=True, timeout=30,
    )
    out = proc.stdout.strip()
    return proc.returncode == 0 and out in ("null", "{}"), f"ExposedPorts={out or '?'}"


def check_bld_04(ctx: Ctx) -> tuple[bool, str]:
    proc = _run_builder()  # rerun the same build — must be idempotent
    return proc.returncode == 0, f"rerun rc={proc.returncode}"


def check_bld_05(ctx: Ctx) -> tuple[bool, str]:
    proc = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{REPO}:/repo", "trailcam-test:v1"],
        capture_output=True, text=True, timeout=600,
    )
    out = (proc.stdout + proc.stderr).strip()
    tails = [line for line in out.splitlines() if "passed" in line or "failed" in line]
    return proc.returncode == 0, tails[-1] if tails else f"rc={proc.returncode}"


# ---- SRV (service health; /mcp gate lands with the MCP WI) ----


def check_srv_01(ctx: Ctx) -> tuple[bool, str]:
    status, _ = http_get_json(ctx, "/api/health")
    return status == 200, f"HTTP {status}"


def check_srv_02(ctx: Ctx) -> tuple[bool, str]:
    _, body = http_get_json(ctx, "/api/health")
    return body.get("status") == "ok", f"status={body.get('status')!r}"


def check_srv_03(ctx: Ctx) -> tuple[bool, str]:
    _, body = http_get_json(ctx, "/api/health")
    return body.get("service") == "trailcam-server", f"service={body.get('service')!r}"


# -------------------------------------------------------------------------- #
# Registry — test-plan §20 (implemented checks first; pending = suite whose
# work item has not landed yet, per test-plan §1.1)
# -------------------------------------------------------------------------- #

# (id, prefix, check, expected, func_or_None, pending_note)
CASES: list[tuple[str, str, str, str, object, str]] = [
    # --- MIG (WI-102) ---
    ("MIG-01", "MIG", "`php artisan migrate:fresh`", "clean", check_mig_01, ""),
    ("MIG-02", "MIG", "users unique `handle` + `email`", "unique indexes", check_mig_02, ""),
    ("MIG-03", "MIG", "cameras unique `device_id`", "unique index", check_mig_03, ""),
    ("MIG-04", "MIG", "pair_tokens TTL on `expires_at`", "`expireAfterSeconds: 900`", check_mig_04, ""),
    ("MIG-05", "MIG", "photos compound index `{camera_id, capture_at}`", "present", check_mig_05, ""),

    # --- PHP (server boot) ---
    ("PHP-01", "PHP", "`php artisan list`", "Laravel 12.x, rc 0", check_php_01, ""),
    ("PHP-02", "PHP", "`php artisan route:list | grep api/health`", "route present", check_php_02, ""),
    ("PHP-03", "PHP", "`grep -c \"^APP_KEY=base64\" server/.env`", "≥ 1", check_php_03, ""),
    ("PHP-04", "PHP", "`php scripts/conncheck.php` → REDIS", "PONG", None, "cache/queue WI"),
    ("PHP-05", "PHP", "`php scripts/conncheck.php` → MONGODB", "connected to wapiti", check_php_05, ""),

    # --- SRV (health; /mcp gate lands with the MCP WI) ---
    ("SRV-01", "SRV", "`curl -k https://172.17.0.1:4444/api/health`", "200", check_srv_01, ""),
    ("SRV-02", "SRV", "… `| jq .status`", '"ok"', check_srv_02, ""),
    ("SRV-03", "SRV", "… `| jq .service`", '"trailcam-server"', check_srv_03, ""),
    ("SRV-04", "SRV", "`curl -k https://172.17.0.1:4444/mcp` (unauth)", "401 (endpoint alive, gated)", None, "MCP WI (S3)"),

    # --- SVC (WI-103 — service group script) ---
    ("SVC-01", "SVC", "`./start-stop-services.sh --status | grep trailcam`", "`trailcam-server: RUNNING`", check_svc_01, ""),
    ("SVC-02", "SVC", "nginx `-t` on `default.wapiti.cam`", "`syntax is ok`", check_svc_02, ""),
    ("SVC-03", "SVC", "`docker port trailcam-server | grep 4444`", "`0.0.0.0:4444`", check_svc_03, ""),
    ("SVC-04", "SVC", "stop + start cycle → health", "OK", check_svc_04, ""),

    # --- BLD (WI-103 — builder + test one-shot images) ---
    ("BLD-01", "BLD", "`docker images trailcam-builder:v1`", "image listed", check_bld_01, ""),
    ("BLD-02", "BLD", "builder artifacts exist post-build", "vendor/autoload.php present", check_bld_02, ""),
    ("BLD-03", "BLD", "builder is one-shot (no ports)", "`docker inspect` → no exposed ports", check_bld_03, ""),
    ("BLD-04", "BLD", "build idempotent (rerun OK)", "exit 0", check_bld_04, ""),
    ("BLD-05", "BLD", "`trailcam-test` image runs pytest", "exits per suite result", check_bld_05, ""),

    # --- SIM (WI-105 — fleet simulator) ---
    ("SIM-01", "SIM", "10 cams report at idle cadence for 10 min", "all 200s, no loss", None, "WI-105"),
    ("SIM-02", "SIM", "100 cams burst mode 5 min", "server survives; p95 < 300 ms", None, "WI-105"),
    ("SIM-03", "SIM", "20% cams offline / flaky", "reconnect replay works", None, "WI-105"),
    ("SIM-04", "SIM", "Mixed transports", "all ingested, tagged correctly", None, "WI-105"),
    ("SIM-05", "SIM", "Stale device_token", "401, no ingestion", None, "WI-104"),
    ("SIM-06", "SIM", "Config piggyback round-trip", "command delivered + acked", None, "WI-104"),
]


def select(token: str) -> list[tuple]:
    """Select cases by prefix (mig,php,srv,…) or exact ID (MIG-04)."""
    tok = token.strip().upper()
    if not tok:
        return []
    return [c for c in CASES if c[0] == tok or c[1] == tok]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="wapiti infra smoke (test-plan §20)")
    p.add_argument("-k", "--filter", default="",
                   help="comma-separated prefixes and/or IDs (e.g. mig,php or MIG-04)")
    p.add_argument("--container", default=DEFAULT_APP_CONTAINER,
                   help=f"app container (default {DEFAULT_APP_CONTAINER})")
    p.add_argument("--mongo-container", default=DEFAULT_MONGO_CONTAINER,
                   help=f"mongo container (default {DEFAULT_MONGO_CONTAINER})")
    p.add_argument("--workdir", default=DEFAULT_APP_WORKDIR,
                   help=f"artisan cwd inside the app container (default {DEFAULT_APP_WORKDIR})")
    p.add_argument("--db", default="", help="Mongo database (default: server/.env MONGODB_DATABASE)")
    p.add_argument("--host", default=_env_default("APP_URL", "https://172.17.0.1:4444"),
                   help="base URL for HTTP checks (SRV…)")
    args = p.parse_args(argv)
    ctx = Ctx(args)

    if args.filter.strip():
        selected: list[tuple] = []
        unknown: list[str] = []
        for tok in args.filter.split(","):
            hits = select(tok)
            if hits:
                selected.extend(hits)
            else:
                unknown.append(tok.strip())
        if unknown:
            print(f"unknown selection: {', '.join(unknown)} "
                  f"(prefixes: {', '.join(sorted({c[1] for c in CASES}))})", file=sys.stderr)
            return 2
    else:
        selected = list(CASES)

    results = []  # (id, check, expected, status, detail)
    for cid, prefix, check, expected, func, note in selected:
        if func is None:
            results.append((cid, check, expected, "PENDING", note))
            continue
        try:
            ok, detail = func(ctx)
        except Exception as exc:  # noqa: BLE001 — a crash is a failed check
            ok, detail = False, f"exception: {exc}"
        results.append((cid, check, expected, "PASS" if ok else "FAIL", detail))
        print(f"{'✅ PASS' if ok else '❌ FAIL'}  {cid}  {check}  → {detail}")

    n_pass = sum(1 for r in results if r[3] == "PASS")
    n_fail = sum(1 for r in results if r[3] == "FAIL")
    n_pend = sum(1 for r in results if r[3] == "PENDING")

    mark = {"PASS": "✅ PASS", "FAIL": "❌ FAIL", "PENDING": "⏳ pending"}
    lines = [
        "# wapiti infra smoke report — tests/regression.py",
        "",
        f"- Run: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- Selection: {args.filter or 'all prefixes'}",
        f"- App: container `{ctx.app_container}` (workdir `{ctx.workdir}`) · "
        f"Mongo: `{ctx.mongo_container}/{ctx.db}` · Host: {ctx.host}",
        "",
        "| ID | Check | Expected | Result |",
        "|---|---|---|---|",
    ]
    for cid, check, expected, status, detail in results:
        cell = mark[status]
        if status == "PENDING" and detail:
            cell += f" ({detail})"
        elif status == "FAIL":
            cell += f" — {detail}"
        lines.append(f"| {cid} | {check} | {expected} | {cell} |")
    lines += [
        "",
        f"**Totals: {n_pass} passed · {n_fail} failed · {n_pend} pending** "
        f"(of {len(results)} selected / {len(CASES)} documented infra IDs)",
        "",
        "Pending = suite specified in test-plan §20 whose work item has not landed; "
        "see project-plan.md §Work items.",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")

    print(f"\nTotals: {n_pass} passed · {n_fail} failed · {n_pend} pending → {REPORT}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
