#!/usr/bin/env python3
"""wapiti / trailcam API test suite — the catalog authority (test-plan.md §1.1).

Currently implemented: AUTH-01..18 (WI-101, WebAuthn scaffold) and
ING-01..10 (WI-104, device ingest — driven by an in-test device client that
the WI-105 fleet simulator builds on). Every other prefix stays pending until
its work item lands; when a suite is added here its run-state in
docs/test-plan.md moves in lockstep (§1.2 counts + §1.1 totals).

Ceremonies are driven by a software FakeAuthenticator (the wificam
FakeAuthenticator pattern): a P-256 keypair builds standards-compliant
`navigator.credentials.create/get` payloads so the server's real
web-auth/webauthn-lib verification runs unmodified.

Usage (test-plan §25):

    python3 tests/test.py --host https://172.17.0.1:4444 -v
    python3 tests/test.py -k test_auth_01
    python3 tests/test.py --host https://172.17.0.1:4444 --verify-tls

Dev origin note (project-plan §3.1): the docker0 gateway IP — Docker
publishes container ports via iptables only, loopback never binds. The
WI-103 nginx/TLS site serves `https://172.17.0.1:4444`, which is also the
WebAuthn origin; a plain-HTTP run (`php artisan serve`) would need
`--host http://… --origin http://…` to match config/webauthn.php.

Reports land in tests/reports/test-report-<UTC>.md with
tests/reports/test-report.md symlinked to the latest run.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import hashlib
import json
import os
import re
import secrets
import sys
from urllib.parse import unquote, urlparse

import pytest
import requests
import urllib3

# --------------------------------------------------------------------------- #
# Runtime configuration (exported via env by main() so pytest's re-import of
# this file sees the same values)
# --------------------------------------------------------------------------- #

HOST = os.environ.get("TRAILCAM_HOST", "https://172.17.0.1:4444")
ORIGIN = os.environ.get("TRAILCAM_ORIGIN", "https://172.17.0.1:4444")
VERIFY_TLS = os.environ.get("TRAILCAM_VERIFY_TLS", "") == "1"
WRITE_REPORT = os.environ.get("TRAILCAM_NO_REPORT", "") != "1"

# Catalog total from docs/test-plan.md §1.2 — keep in lockstep.
CATALOG_TOTAL = 307

DEFAULT_HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}


def _is_private_host(hostname: str) -> bool:
    if hostname in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:
        return True
    if hostname.startswith("172."):  # docker bridges (172.16/12)
        return True
    if hostname.startswith(("192.168.", "10.")):
        return True
    return False


def new_client() -> requests.Session:
    """A fresh browser-like client with its own cookie jar."""
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    session.verify = VERIFY_TLS
    return session


def _attach_xsrf(client: requests.Session) -> None:
    """Mirror the browser's XSRF dance: echo the XSRF-TOKEN cookie back as the
    X-XSRF-TOKEN header (Laravel web middleware requires it on /api/*)."""
    token = client.cookies.get("XSRF-TOKEN")
    if token:
        client.headers["X-XSRF-TOKEN"] = unquote(token)


def post(client: requests.Session, path: str, payload: dict | None = None):
    _attach_xsrf(client)
    return client.post(HOST + path, json=payload if payload is not None else {})


def get(client: requests.Session, path: str):
    return client.get(HOST + path)


def unique_handle() -> str:
    return "u" + secrets.token_hex(6)


# --------------------------------------------------------------------------- #
# Minimal CBOR encoder (attestation object + COSE key are the only structures
# a fmt=none authenticator must emit)
# --------------------------------------------------------------------------- #


def _cbor_head(major: int, length: int) -> bytes:
    if length < 24:
        return bytes([major << 5 | length])
    if length < 256:
        return bytes([major << 5 | 24, length])
    if length < 65536:
        return bytes([major << 5 | 25]) + length.to_bytes(2, "big")
    return bytes([major << 5 | 26]) + length.to_bytes(4, "big")


def cbor_text(value: str) -> bytes:
    raw = value.encode()
    return _cbor_head(3, len(raw)) + raw


def cbor_bytes(value: bytes) -> bytes:
    return _cbor_head(2, len(value)) + value


def cbor_int(value: int) -> bytes:
    if value >= 0:
        return _cbor_head(0, value)
    return _cbor_head(1, -1 - value)


def cbor_map(items: list[tuple[bytes, bytes]]) -> bytes:
    out = _cbor_head(5, len(items))
    for key, value in items:
        out += key + value
    return out


# --------------------------------------------------------------------------- #
# FakeAuthenticator — software authenticator (P-256 / ES256, fmt=none)
# --------------------------------------------------------------------------- #


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def b64u_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class FakeAuthenticator:
    """Builds WebAuthn ceremony payloads with its own ES256 keypair."""

    def __init__(self) -> None:
        from cryptography.hazmat.primitives.asymmetric import ec

        self.key = ec.generate_private_key(ec.SECP256R1())
        numbers = self.key.public_key().public_numbers()
        self.x = numbers.x.to_bytes(32, "big")
        self.y = numbers.y.to_bytes(32, "big")
        self.credential_id = secrets.token_bytes(32)
        self.sign_count = 0

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _client_data(kind: str, challenge: str, origin: str) -> bytes:
        payload = {
            "type": kind,
            "challenge": challenge,
            "origin": origin,
            "crossOrigin": False,
        }
        return json.dumps(payload, separators=(",", ":")).encode()

    def _cose_key(self) -> bytes:
        return cbor_map(
            [
                (cbor_int(1), cbor_int(2)),  # kty: EC2
                (cbor_int(3), cbor_int(-7)),  # alg: ES256
                (cbor_int(-1), cbor_int(1)),  # crv: P-256
                (cbor_int(-2), cbor_bytes(self.x)),
                (cbor_int(-3), cbor_bytes(self.y)),
            ]
        )

    @staticmethod
    def _to_p1363(der: bytes) -> bytes:
        from cryptography.hazmat.primitives.asymmetric import utils

        r, s = utils.decode_dss_signature(der)
        return r.to_bytes(32, "big") + s.to_bytes(32, "big")

    def _sign(self, message: bytes, *, tamper: bool = False) -> bytes:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec

        key = self.key
        if tamper:  # sign with a key that never registered → verification must fail
            key = ec.generate_private_key(ec.SECP256R1())
        return self._to_p1363(key.sign(message, ec.ECDSA(hashes.SHA256())))

    # -- ceremonies ------------------------------------------------------

    def create(self, options: dict, origin: str) -> dict:
        """navigator.credentials.create() → server `response` payload."""
        rp_id = options["rp"]["id"]
        client_data = self._client_data("webauthn.create", options["challenge"], origin)

        rp_hash = hashlib.sha256(rp_id.encode()).digest()
        flags = 0x45  # UP | UV | AT
        counter = self.sign_count
        authenticator_data = (
            rp_hash
            + bytes([flags])
            + counter.to_bytes(4, "big")
            + b"\x00" * 16  # aaguid
            + len(self.credential_id).to_bytes(2, "big")
            + self.credential_id
            + self._cose_key()
        )
        attestation_object = cbor_map(
            [
                (cbor_text("fmt"), cbor_text("none")),
                (cbor_text("attStmt"), cbor_map([])),
                (cbor_text("authData"), cbor_bytes(authenticator_data)),
            ]
        )
        return {
            "id": b64u(self.credential_id),
            "rawId": b64u(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64u(client_data),
                "attestationObject": b64u(attestation_object),
                "transports": ["internal"],
            },
        }

    def get(self, options: dict, origin: str, *, tamper: bool = False) -> dict:
        """navigator.credentials.get() → server `response` payload."""
        rp_id = options["rpId"]
        client_data = self._client_data("webauthn.get", options["challenge"], origin)

        rp_hash = hashlib.sha256(rp_id.encode()).digest()
        flags = 0x05  # UP | UV
        authenticator_data = rp_hash + bytes([flags]) + self.sign_count.to_bytes(4, "big")
        signed = authenticator_data + hashlib.sha256(client_data).digest()
        signature = self._sign(signed, tamper=tamper)

        return {
            "id": b64u(self.credential_id),
            "rawId": b64u(self.credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": b64u(client_data),
                "authenticatorData": b64u(authenticator_data),
                "signature": b64u(signature),
            },
        }


# --------------------------------------------------------------------------- #
# Flow helpers
# --------------------------------------------------------------------------- #


def register(
    client: requests.Session | None = None,
    *,
    handle: str | None = None,
    email: str | None = None,
    authenticator: FakeAuthenticator | None = None,
):
    """Full registration ceremony. Returns (handle, authenticator, final response)."""
    client = client or new_client()
    handle = handle or unique_handle()
    email = email or f"{handle}@example.com"
    authenticator = authenticator or FakeAuthenticator()

    begin = post(client, "/auth/register/begin", {"handle": handle, "email": email})
    assert begin.status_code == 200, f"begin failed: {begin.status_code} {begin.text}"
    options = begin.json()["publicKey"]

    credential = authenticator.create(options, ORIGIN)
    complete = post(client, "/auth/register/complete", {"response": credential})
    assert complete.status_code == 201, f"complete failed: {complete.status_code} {complete.text}"
    return handle, authenticator, complete


def login_begin(client: requests.Session, handle: str) -> dict:
    response = post(client, "/auth/login/begin", {"handle": handle})
    assert response.status_code == 200, f"login begin failed: {response.status_code} {response.text}"
    return response.json()["publicKey"]


def session_cookie_attributes(set_cookie_lines: list[str]) -> list[str]:
    """Attributes of the session cookie (everything except XSRF-TOKEN)."""
    session_lines = [line for line in set_cookie_lines if not line.startswith("XSRF-TOKEN=")]
    assert session_lines, f"no session cookie in Set-Cookie: {set_cookie_lines}"
    return [part.strip() for part in session_lines[0].split(";")[1:]]


# --------------------------------------------------------------------------- #
# Device client + ingest flow helpers (WI-104 — §8.3 pairing chain)
# --------------------------------------------------------------------------- #

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_ROOT = os.path.join(REPO_ROOT, "server")


def factory_key() -> str:
    """X-Factory-Key for /device/v1/provision: env → server/.env → empty."""
    key = os.environ.get("TRAILCAM_FACTORY_KEY", "")
    if key:
        return key
    try:
        with open(os.path.join(SERVER_ROOT, ".env")) as fh:
            for line in fh:
                if line.startswith("FACTORY_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except OSError:
        pass
    return ""


def device_client(token: str) -> requests.Session:
    client = new_client()
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def patch(client: requests.Session, path: str, payload: dict):
    _attach_xsrf(client)
    return client.patch(HOST + path, json=payload)


def delete(client: requests.Session, path: str):
    _attach_xsrf(client)
    return client.delete(HOST + path)


def provision(device_id: str, secret: str, **versions) -> requests.Response:
    client = new_client()
    client.headers["X-Factory-Key"] = factory_key()
    payload = {"device_id": device_id, "secret": secret}
    payload.update({k: v for k, v in versions.items() if v is not None})
    return client.post(HOST + "/device/v1/provision", json=payload, headers=DEFAULT_HEADERS)


def setup_camera(client: requests.Session | None = None) -> dict:
    """Register → provision → pair token → pair (the §8.3 chain).

    Returns the session client, handle, camera id, device ids and the live
    device bearer token — the fixture the ingest tests build on (the WI-105
    fleet simulator drives the same flow).
    """
    client = client or new_client()
    handle, _, _ = register(client)

    device_id = "WC-1-" + secrets.token_hex(4)
    secret = secrets.token_hex(16)
    prov = provision(device_id, secret)
    assert prov.status_code == 201, f"provision failed: {prov.status_code} {prov.text}"

    minted = post(client, "/api/pair-tokens", {"device_id": device_id})
    assert minted.status_code == 201, f"pair token failed: {minted.status_code} {minted.text}"

    pair = post(
        new_client(),
        "/device/v1/pair",
        {"device_id": device_id, "secret": secret, "pair_token": minted.json()["token"]},
    )
    assert pair.status_code == 200, f"pair failed: {pair.status_code} {pair.text}"

    return {
        "client": client,
        "handle": handle,
        "device_id": device_id,
        "secret": secret,
        "camera_id": pair.json()["camera_id"],
        "device_token": pair.json()["device_token"],
    }


def sample_report(**overrides) -> dict:
    report = {
        "at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "battery_snapshot": {"voltage_mv": 6120, "gauge_pct": 87},
        "signal_snapshot": {"rsrp_dbm": -92, "rsrq_dbm": -10, "band": 4},
        "transport": "https",
        "fw_version": "0.1.0",
        "hw_version": "WC-1",
    }
    report.update(overrides)
    return report


def sample_photo_bytes() -> bytes:
    """A JPEG-shaped payload (SOI … EOI) — enough for the multipart path."""
    return b"\xff\xd8\xff\xe0" + secrets.token_bytes(256) + b"\xff\xd9"


def photo_manifest(payload: bytes, **overrides) -> dict:
    entry = {
        "sha256": hashlib.sha256(payload).hexdigest(),
        "kind": "photo",
        "bytes": len(payload),
        "capture_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "res": "4k",
        "transmitted": True,
    }
    entry.update(overrides)
    return entry


# --------------------------------------------------------------------------- #
# AUTH-01 → AUTH-18 (WI-101)
# --------------------------------------------------------------------------- #


def test_auth_01_register_begin_returns_creation_options():
    """AUTH-01: POST /auth/register/begin → 200 with publicKey.challenge."""
    client = new_client()
    response = post(
        client,
        "/auth/register/begin",
        {"handle": unique_handle(), "email": f"{unique_handle()}@example.com"},
    )
    assert response.status_code == 200, response.text
    public_key = response.json()["publicKey"]
    assert public_key["challenge"], "publicKey.challenge missing"
    # base64url, no padding
    assert re.fullmatch(r"[A-Za-z0-9_-]+", public_key["challenge"])


def test_auth_02_register_complete_creates_user_and_session():
    """AUTH-02: register/complete → 201, session cookie set, status shows user."""
    client = new_client()
    handle, _authenticator, response = register(client)
    assert response.status_code == 201
    assert response.json()["user"]["handle"] == handle
    assert client.cookies, "no session cookie stored"
    status = get(client, "/auth/status")
    assert status.status_code == 200
    assert status.json()["handle"] == handle


def test_auth_03_register_begin_rejects_duplicate_handle():
    """AUTH-03: duplicate handle → 409."""
    existing_handle, _, _ = register()
    client = new_client()
    response = post(
        client,
        "/auth/register/begin",
        {"handle": existing_handle, "email": f"{unique_handle()}@example.com"},
    )
    assert response.status_code == 409, response.text


def test_auth_04_register_begin_rejects_duplicate_email():
    """AUTH-04: duplicate email → 409."""
    handle = unique_handle()
    first_email = f"{handle}@example.com"
    register(handle=handle, email=first_email)

    response = post(
        new_client(),
        "/auth/register/begin",
        {"handle": unique_handle(), "email": first_email},
    )
    assert response.status_code == 409, response.text


def test_auth_05_register_begin_rejects_short_handle():
    """AUTH-05: handle shorter than 3 chars → 422."""
    response = post(new_client(), "/auth/register/begin", {"handle": "ab", "email": "a@example.com"})
    assert response.status_code == 422, response.text


def test_auth_06_register_begin_rejects_invalid_email():
    """AUTH-06: malformed email → 422."""
    response = post(
        new_client(),
        "/auth/register/begin",
        {"handle": unique_handle(), "email": "not-an-email"},
    )
    assert response.status_code == 422, response.text


def test_auth_07_login_begin_returns_request_options():
    """AUTH-07: login/begin → 200 with non-empty publicKey.allowCredentials."""
    handle, _, _ = register()
    response = post(new_client(), "/auth/login/begin", {"handle": handle})
    assert response.status_code == 200, response.text
    public_key = response.json()["publicKey"]
    assert "allowCredentials" in public_key
    assert len(public_key["allowCredentials"]) >= 1
    assert public_key["allowCredentials"][0]["id"]


def test_auth_08_login_begin_rejects_unknown_handle():
    """AUTH-08: unknown handle → 404."""
    response = post(new_client(), "/auth/login/begin", {"handle": "ghost-" + unique_handle()})
    assert response.status_code == 404, response.text


def test_auth_09_login_complete_verifies_assertion_and_opens_session():
    """AUTH-09: valid assertion → 200 + session cookie."""
    handle, authenticator, _ = register()
    client = new_client()  # a different browser than the one that registered
    options = login_begin(client, handle)
    credential = authenticator.get(options, ORIGIN)
    response = post(client, "/auth/login/complete", {"response": credential})
    assert response.status_code == 200, response.text
    assert response.json()["user"]["handle"] == handle
    status = get(client, "/auth/status")
    assert status.status_code == 200
    assert status.json()["handle"] == handle


def test_auth_10_login_complete_rejects_bad_signature():
    """AUTH-10: assertion signed by an unregistered key → 401."""
    handle, authenticator, _ = register()
    client = new_client()
    options = login_begin(client, handle)
    credential = authenticator.get(options, ORIGIN, tamper=True)
    response = post(client, "/auth/login/complete", {"response": credential})
    assert response.status_code == 401, response.text
    assert get(client, "/auth/status").status_code == 401


def test_auth_11_status_returns_session():
    """AUTH-11: GET /auth/status → 200 with handle, role, tier."""
    client = new_client()
    handle, _, _ = register(client)
    response = get(client, "/auth/status")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handle"] == handle
    assert body["role"] == "user"
    assert body["tier"] == "free"


def test_auth_12_status_unauthenticated_is_401():
    """AUTH-12: GET /auth/status without a session → 401."""
    response = get(new_client(), "/auth/status")
    assert response.status_code == 401, response.text


def test_auth_13_add_passkey_stores_second_credential():
    """AUTH-13: add-passkey/begin+complete → 200 and the account holds two passkeys."""
    client = new_client()
    handle, _first, _ = register(client)

    second = FakeAuthenticator()
    begin = post(client, "/auth/add-passkey/begin", {})
    assert begin.status_code == 200, begin.text
    options = begin.json()["publicKey"]

    credential = second.create(options, ORIGIN)
    complete = post(client, "/auth/add-passkey/complete", {"response": credential})
    assert complete.status_code == 200, complete.text
    assert complete.json()["credential_id"] == b64u(second.credential_id)

    # both credentials must now be offered at login
    listing = login_begin(new_client(), handle)
    assert len(listing["allowCredentials"]) == 2


def test_auth_14_delete_passkey_blocks_removing_last_one():
    """AUTH-14: deleting the only passkey → 409."""
    client = new_client()
    handle, _authenticator, _ = register(client)
    options = login_begin(client, handle)
    only_id = options["allowCredentials"][0]["id"]
    response = client.delete(HOST + f"/auth/passkeys/{only_id}")
    assert response.status_code == 409, response.text


def _complete_recovery(client: requests.Session, token: str) -> tuple[FakeAuthenticator, requests.Response]:
    begin = post(client, "/auth/recovery", {"token": token})
    assert begin.status_code == 200, f"recovery begin failed: {begin.status_code} {begin.text}"
    options = begin.json()["publicKey"]
    fresh = FakeAuthenticator()
    credential = fresh.create(options, ORIGIN)
    complete = post(client, "/auth/recovery", {"token": token, "response": credential})
    assert complete.status_code == 200, f"recovery complete failed: {complete.status_code} {complete.text}"
    return fresh, complete


def test_auth_15_recovery_enrolls_new_passkey_and_revokes_old():
    """AUTH-15: recovery token enrols a new passkey → 200; old passkeys revoked."""
    client = new_client()
    handle, old_authenticator, response = register(client)
    token = response.json()["recovery_token"]
    assert token

    new_authenticator, complete = _complete_recovery(client, token)
    assert complete.status_code == 200
    assert complete.json()["user"]["handle"] == handle

    # old credential must be gone: login offers exactly the new one
    options = login_begin(new_client(), handle)
    ids = [entry["id"] for entry in options["allowCredentials"]]
    assert ids == [b64u(new_authenticator.credential_id)]
    assert b64u(old_authenticator.credential_id) not in ids

    # the new passkey really works
    verify_client = new_client()
    options = login_begin(verify_client, handle)
    credential = new_authenticator.get(options, ORIGIN)
    assert post(verify_client, "/auth/login/complete", {"response": credential}).status_code == 200


def test_auth_16_recovery_rejects_expired_or_consumed_token():
    """AUTH-16: consumed (single-use) or unknown recovery token → 401."""
    client = new_client()
    _handle, _authenticator, response = register(client)
    token = response.json()["recovery_token"]

    # consume it
    _fresh, complete = _complete_recovery(client, token)
    assert complete.status_code == 200

    # reuse (single-use → treated as expired/dead) → 401
    reuse = post(new_client(), "/auth/recovery", {"token": token})
    assert reuse.status_code == 401, reuse.text

    # never-issued token → 401
    bogus = post(new_client(), "/auth/recovery", {"token": "PRT-" + secrets.token_hex(16)})
    assert bogus.status_code == 401, bogus.text


def test_auth_17_logout_kills_session():
    """AUTH-17: POST /auth/logout → 200 and the session no longer authenticates."""
    client = new_client()
    handle, _, _ = register(client)
    assert get(client, "/auth/status").status_code == 200

    response = post(client, "/auth/logout", {})
    assert response.status_code == 200, response.text
    assert get(client, "/auth/status").status_code == 401
    assert handle  # silence linters


def test_auth_18_session_cookie_flags():
    """AUTH-18: session cookie carries HttpOnly, Secure and SameSite=Strict."""
    client = new_client()
    handle, _, response = register(client)
    set_cookies = response.raw.headers.getlist("Set-Cookie")
    attributes = session_cookie_attributes(set_cookies)
    lowered = [attribute.lower() for attribute in attributes]
    assert "httponly" in lowered, attributes
    assert "secure" in lowered, attributes
    assert "samesite=strict" in lowered, attributes
    assert handle


# --------------------------------------------------------------------------- #
# ING-01 → ING-10 (WI-104 — device ingest, §14)
# --------------------------------------------------------------------------- #


def test_ingest_01_device_token_required():
    """ING-01: /device/v1/* without a bearer token → 401."""
    response = post(new_client(), "/device/v1/reports", {"reports": [sample_report()]})
    assert response.status_code == 401, response.text

    bogus = device_client("deadbeef" * 8)
    assert post(bogus, "/device/v1/reports", {"reports": [sample_report()]}).status_code == 401


def test_ingest_02_report_accepted():
    """ING-02: report → 202, heartbeats row written (expected_next_at echoed);
    a lost-ack replay of the same report is deduped, never double-counted."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])
    report = sample_report()

    response = post(dev, "/device/v1/reports", {"reports": [report]})
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["queued"] is True and body["count"] == 1
    assert body["heartbeat"]["expected_next_at"], "heartbeats row must carry expected_next_at"

    again = post(dev, "/device/v1/reports", {"reports": [report]})
    assert again.status_code == 202, again.text
    replay = again.json()
    assert replay["count"] == 0 and replay["duplicates"] == 1, replay


def test_ingest_03_photo_multipart():
    """ING-03: single photo multipart → 201, photos row + object on disk."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])
    payload = sample_photo_bytes()
    manifest = photo_manifest(payload)

    dev.headers.pop("Content-Type", None)   # let requests set the multipart boundary
    response = dev.post(
        HOST + "/device/v1/photos",
        data={"manifest": json.dumps([manifest])},
        files=[("files[]", ("frame.jpg", payload, "image/jpeg"))],
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["count"] == 1 and body["accepted"][0]["sha256"] == manifest["sha256"]

    storage_key = body["accepted"][0]["storage_key"]
    on_disk = os.path.join(SERVER_ROOT, "storage", "app", storage_key)
    assert os.path.exists(on_disk), f"object not stored: {on_disk}"


def test_ingest_04_batch_manifest_order_and_dedup():
    """ING-04: offline backlog batch → order preserved; replay deduped."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])
    payloads = [sample_photo_bytes() for _ in range(3)]
    manifest = [photo_manifest(p) for p in payloads]
    expected = [m["sha256"] for m in manifest]
    files = [("files[]", (f"frame{i}.jpg", p, "image/jpeg")) for i, p in enumerate(payloads)]

    dev.headers.pop("Content-Type", None)
    response = dev.post(HOST + "/device/v1/photos", data={"manifest": json.dumps(manifest)}, files=files)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["order"] == expected, "manifest order must be preserved"
    assert body["count"] == 3 and body["duplicates"] == [], body

    replay = dev.post(HOST + "/device/v1/photos", data={"manifest": json.dumps(manifest)}, files=files)
    assert replay.status_code == 201, replay.text
    again = replay.json()
    assert again["count"] == 0 and again["duplicates"] == expected, again


def test_ingest_05_config_piggyback_round_trip():
    """ING-05: staged delta rides the next response; the call after the device
    acks the version carries config_ack (§14)."""
    fx = setup_camera()
    patched = patch(
        fx["client"],
        f"/api/cameras/{fx['camera_id']}/config",
        {"instant_send": True, "ir": "no_glow"},
    )
    assert patched.status_code == 200, patched.text
    version = patched.json()["config_version"]

    dev = device_client(fx["device_token"])
    first = dev.get(HOST + "/device/v1/config").json()
    assert first["config"]["instant_send"] is True, first
    assert first["config"]["ir"] == "no_glow"
    assert first["config_version"] == version
    assert first["config_ack"] is None

    acked = dev.get(HOST + "/device/v1/config", params={"applied_version": version}).json()
    assert acked["config_ack"] == version, acked

    third = dev.get(HOST + "/device/v1/config").json()
    assert third["config_ack"] is None
    assert third["config"]["instant_send"] is True   # applied, not reverted


def test_ingest_06_rate_limit():
    """ING-06: burst beyond the per-device budget → 429 + retry_after."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])
    limit = int(os.environ.get("TRAILCAM_RATE_LIMIT", "120"))  # wapiti.device_rate_per_min

    response = None
    for _ in range(limit + 25):
        response = dev.get(HOST + "/device/v1/config")
        if response.status_code == 429:
            break

    assert response is not None and response.status_code == 429, (
        f"expected 429 inside {limit + 25} requests, got {response.status_code}"
    )
    assert "Retry-After" in response.headers, response.headers
    body = response.json()
    assert body["error"] == "rate_limited"
    assert isinstance(body["retry_after"], int) and body["retry_after"] >= 1, body


def test_ingest_07_stale_token_after_unbind():
    """ING-07: revoked (unbound) device token → 401, no ingestion."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])
    assert post(dev, "/device/v1/reports", {"reports": [sample_report()]}).status_code == 202

    unbound = delete(fx["client"], f"/api/cameras/{fx['camera_id']}/device")
    assert unbound.status_code == 200, unbound.text
    assert unbound.json()["unbound"] is True

    stale = post(dev, "/device/v1/reports", {"reports": [sample_report()]})
    assert stale.status_code == 401, stale.text


def test_ingest_08_cross_user_isolation():
    """ING-08: another account's camera is a 404 — no existence leak, no
    staged delta, nothing written."""
    fx = setup_camera()          # user A
    intruder = new_client()
    register(intruder)           # user B

    assert get(intruder, f"/api/cameras/{fx['camera_id']}").status_code == 404
    assert patch(
        intruder, f"/api/cameras/{fx['camera_id']}/config", {"instant_send": True}
    ).status_code == 404
    assert delete(intruder, f"/api/cameras/{fx['camera_id']}/device").status_code == 404

    # the owner still sees an untouched config, and no delta was staged
    own = get(fx["client"], f"/api/cameras/{fx['camera_id']}")
    assert own.status_code == 200, own.text
    assert own.json()["capture_config"]["instant_send"] is False

    dev = device_client(fx["device_token"])
    cfg = dev.get(HOST + "/device/v1/config").json()
    assert cfg["config"]["instant_send"] is False, cfg


def test_ingest_09_move_alert_event_recorded():
    """ING-09: move-alert event → 202, device_events row + rule evaluation."""
    fx = setup_camera()
    dev = device_client(fx["device_token"])

    response = post(
        dev,
        "/device/v1/events",
        {
            "type": "move_alert",
            "at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "payload": {"motion_class": "human", "confidence": 0.82},
        },
    )
    assert response.status_code == 202, response.text
    body = response.json()
    assert body["recorded"] is True and body["event_id"], body
    assert isinstance(body["rules_evaluated"], int), body
    assert isinstance(body["alerts_created"], int), body
    # alert rules are defined by the WI-303 API — none exist yet
    assert body["alerts_created"] == 0, body


def test_ingest_10_fw_hw_recorded_on_first_report():
    """ING-10: first report's fw/hw versions land on cameras.fw_version."""
    fx = setup_camera()          # provision default: fw 0.0.0
    dev = device_client(fx["device_token"])

    response = post(
        dev,
        "/device/v1/reports",
        {"reports": [sample_report(fw_version="0.9.7", hw_version="WC-1.1")]},
    )
    assert response.status_code == 202, response.text
    assert response.json()["camera"]["fw_version"] == "0.9.7"
    assert response.json()["camera"]["hw_version"] == "WC-1.1"

    # and it persists for the next call
    cfg = dev.get(HOST + "/device/v1/config").json()
    assert cfg["camera"]["fw_version"] == "0.9.7", cfg


# --------------------------------------------------------------------------- #
# Markdown report (test-plan §25 output contract)
# --------------------------------------------------------------------------- #

_ID_RE = re.compile(r"::test_([a-z]+)_(\d+)")

# Test-function family → catalog prefix (test-plan §1.1 sync rule: an ID must read the
# same in this report as it does in docs/test-plan.md — `test_ingest_01` is catalog
# `ING-01`, not `INGEST-01`).
_PREFIX_ALIASES = {"ingest": "ING"}


class _ReportPlugin:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call" or (report.when == "setup" and report.failed):
            match = _ID_RE.search(report.nodeid)
            if match:
                prefix = _PREFIX_ALIASES.get(match.group(1), match.group(1))
                test_id = f"{prefix.upper()}-{int(match.group(2)):02d}"
            else:
                test_id = report.nodeid
            self.rows.append((test_id, report.nodeid.split("::")[-1], report.outcome))

    def pytest_sessionfinish(self, session, exitstatus):
        if not WRITE_REPORT or not self.rows:
            return
        passed = sum(1 for row in self.rows if row[2] == "passed")
        failed = len(self.rows) - passed
        now = _dt.datetime.now(_dt.timezone.utc)
        stamp = now.strftime("%Y%m%d_%H%M%S")
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")
        os.makedirs(reports_dir, exist_ok=True)

        lines = [
            "# wapiti trailcam test report",
            "",
            f"- **When (UTC):** {now.strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Host:** {HOST}",
            f"- **Suite:** API ({len(self.rows)} IDs run)",
            f"- **Result:** {passed} passed / {failed} failed",
            f"- **Catalog:** {CATALOG_TOTAL} IDs total (docs/test-plan.md §1.2); "
            f"{CATALOG_TOTAL - len(self.rows)} not run by this suite (other suites + "
            f"unlanded work items — cross-suite totals in §1.1)",
            "",
            "| ID | Test | Result |",
            "|---|---|---|",
        ]
        lines += [f"| {test_id} | {name} | {outcome} |" for test_id, name, outcome in self.rows]
        lines.append("")

        report_path = os.path.join(reports_dir, f"test-report-{stamp}.md")
        with open(report_path, "w") as handle:
            handle.write("\n".join(lines))

        latest = os.path.join(reports_dir, "test-report.md")
        if os.path.islink(latest) or os.path.exists(latest):
            os.remove(latest)
        os.symlink(os.path.basename(report_path), latest)


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    global HOST, ORIGIN, VERIFY_TLS, WRITE_REPORT

    argv = list(sys.argv[1:] if argv is None else argv)

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--host", default=HOST, help="base URL under test (default %(default)s)")
    parser.add_argument("--origin", default=ORIGIN, help="WebAuthn origin the fake authenticator states")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="force TLS verification (default: verify only for non-loopback/non-private hosts)",
    )
    parser.add_argument("--no-report", action="store_true", help="skip the markdown report")
    known, pytest_argv = parser.parse_known_args(argv)

    HOST = known.host.rstrip("/")
    ORIGIN = known.origin
    VERIFY_TLS = known.verify_tls or not _is_private_host(urlparse(HOST).hostname or "")
    WRITE_REPORT = not known.no_report

    # pytest re-imports this file as the test module — carry the config over.
    os.environ["TRAILCAM_HOST"] = HOST
    os.environ["TRAILCAM_ORIGIN"] = ORIGIN
    os.environ["TRAILCAM_VERIFY_TLS"] = "1" if VERIFY_TLS else "0"
    os.environ["TRAILCAM_NO_REPORT"] = "" if WRITE_REPORT else "1"

    if not VERIFY_TLS:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    target = os.path.abspath(__file__)
    plugin = _ReportPlugin()

    rc = pytest.main([target, "-v", *pytest_argv], plugins=[plugin])
    return int(rc)


if __name__ == "__main__":
    raise SystemExit(main())
