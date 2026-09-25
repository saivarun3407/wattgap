"""Signed, replay-protected messages between the supervisor and each battery.

Every device gets its own HMAC-SHA256 key derived from one fleet secret, so a leaked
device key cannot forge commands for any other device.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from dataclasses import dataclass, field

log = logging.getLogger("wattgap.security")

MAX_SKEW_S = 30.0  # messages older (or newer) than this are rejected


def fleet_secret() -> bytes:
    """WATTGAP_FLEET_SECRET from the environment, or a fresh dev secret for this process."""
    value = os.environ.get("WATTGAP_FLEET_SECRET")
    if value:
        return value.encode()
    log.warning("WATTGAP_FLEET_SECRET not set; generated an ephemeral dev secret")
    return secrets.token_hex(32).encode()


def device_key(secret: bytes, device_id: str) -> bytes:
    return hmac.new(secret, f"device:{device_id}".encode(), hashlib.sha256).digest()


@dataclass(frozen=True)
class Signed:
    device_id: str
    body: dict
    nonce: str
    ts: float
    sig: str

    def payload(self) -> bytes:
        return _payload(self.device_id, self.body, self.nonce, self.ts)


def _payload(device_id: str, body: dict, nonce: str, ts: float) -> bytes:
    return json.dumps([device_id, body, nonce, ts], sort_keys=True, separators=(",", ":")).encode()


def sign(key: bytes, device_id: str, body: dict, ts: float, nonce: str | None = None) -> Signed:
    nonce = nonce or secrets.token_hex(8)
    sig = hmac.new(key, _payload(device_id, body, nonce, ts), hashlib.sha256).hexdigest()
    return Signed(device_id, body, nonce, ts, sig)


class Rejected(Exception):
    """A message failed signature, freshness or replay checks."""


@dataclass
class Verifier:
    """Checks signature, timestamp window and nonce reuse for one device key."""

    key: bytes
    seen: dict[str, float] = field(default_factory=dict)  # nonce -> ts

    def verify(self, msg: Signed, now: float) -> dict:
        expected = hmac.new(self.key, msg.payload(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, msg.sig):
            raise Rejected("bad signature")
        if abs(now - msg.ts) > MAX_SKEW_S:
            raise Rejected("stale or future timestamp")
        if msg.nonce in self.seen:
            raise Rejected("replayed nonce")
        self.seen[msg.nonce] = msg.ts
        # nonces older than the skew window can never pass the timestamp check again
        for n in [n for n, t in self.seen.items() if now - t > MAX_SKEW_S]:
            del self.seen[n]
        return msg.body
