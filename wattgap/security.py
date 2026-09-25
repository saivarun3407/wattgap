"""Signed, replay-protected messages between the supervisor and each battery (ed25519).

Every battery holds its own ed25519 private key, generated on the device, and enrolls only its
public key with the supervisor. The supervisor signs every command with its own key, so a unit
obeys nothing it can't verify. A captured command can't be replayed (nonce + timestamp), and it
can't be redirected either, because the target device id is inside the signature. A leaked or
misbehaving device key is revoked in the registry, and from then on that device's telemetry is refused.
"""

from __future__ import annotations

import json
import logging
import os
import secrets
from dataclasses import dataclass, field

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

log = logging.getLogger("wattgap.security")

MAX_SKEW_S = 30.0  # messages older (or newer) than this are rejected


def new_key() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def key_from_hex(seed_hex: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))


def public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def supervisor_key() -> Ed25519PrivateKey:
    """WATTGAP_SUPERVISOR_KEY (64 hex chars, an ed25519 seed) from the environment, else a dev key."""
    value = os.environ.get("WATTGAP_SUPERVISOR_KEY")
    if value:
        return key_from_hex(value)
    log.warning("WATTGAP_SUPERVISOR_KEY not set; generated an ephemeral dev key for this process")
    return new_key()


@dataclass(frozen=True)
class Signed:
    device_id: str  # the device this message is to (command) or from (telemetry)
    body: dict
    nonce: str
    ts: float
    sig: str

    def payload(self) -> bytes:
        return _payload(self.device_id, self.body, self.nonce, self.ts)

    def to_json(self) -> str:
        return json.dumps([self.device_id, self.body, self.nonce, self.ts, self.sig], separators=(",", ":"))

    @classmethod
    def from_json(cls, line: str | bytes) -> Signed:
        return cls(*json.loads(line))


def _payload(device_id: str, body: dict, nonce: str, ts: float) -> bytes:
    return json.dumps([device_id, body, nonce, ts], sort_keys=True, separators=(",", ":")).encode()


def sign(key: Ed25519PrivateKey, device_id: str, body: dict, ts: float, nonce: str | None = None) -> Signed:
    nonce = nonce or secrets.token_hex(8)
    return Signed(device_id, body, nonce, ts, key.sign(_payload(device_id, body, nonce, ts)).hex())


class Rejected(Exception):
    """A message failed signature, freshness, replay or registry checks."""


@dataclass
class Verifier:
    """Checks signature, timestamp window and nonce reuse against one public key."""

    public: Ed25519PublicKey
    seen: dict[str, float] = field(default_factory=dict)  # nonce -> ts

    @classmethod
    def for_hex(cls, pub_hex: str) -> Verifier:
        return cls(Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)))

    def verify(self, msg: Signed, now: float) -> dict:
        try:
            self.public.verify(bytes.fromhex(msg.sig), msg.payload())
        except (InvalidSignature, ValueError):
            raise Rejected("bad signature") from None
        if abs(now - msg.ts) > MAX_SKEW_S:
            raise Rejected("stale or future timestamp")
        if msg.nonce in self.seen:
            raise Rejected("replayed nonce")
        self.seen[msg.nonce] = msg.ts
        # nonces older than the skew window can never pass the timestamp check again
        if len(self.seen) > 64:
            for n in [n for n, t in self.seen.items() if now - t > MAX_SKEW_S]:
                del self.seen[n]
        return msg.body


@dataclass
class Registry:
    """The supervisor's device registry: enrolled public keys and revocations."""

    roster: set[str]  # device ids the fleet expects (from provisioning)
    keys: dict[str, str] = field(default_factory=dict)  # device id -> public key hex
    revoked: dict[str, str] = field(default_factory=dict)  # device id -> reason
    verifiers: dict[str, Verifier] = field(default_factory=dict)

    def enroll(self, hello: Signed, now: float) -> str:
        """Accept a device's self-signed hello {pubkey}. Keys are pinned: re-enrolling a new key is refused."""
        uid, pub = hello.device_id, hello.body.get("pubkey", "")
        if uid not in self.roster:
            raise Rejected("unknown device")
        if uid in self.revoked:
            raise Rejected("revoked device")
        if uid in self.keys and self.keys[uid] != pub:
            raise Rejected("key mismatch for enrolled device")
        verifier = Verifier.for_hex(pub)
        verifier.verify(hello, now)  # proof the sender holds the private key
        self.keys[uid], self.verifiers[uid] = pub, verifier
        return uid

    def revoke(self, uid: str, reason: str) -> None:
        self.revoked[uid] = reason
        self.verifiers.pop(uid, None)

    def verify(self, msg: Signed, now: float) -> dict:
        if msg.device_id in self.revoked:
            raise Rejected("revoked device")
        v = self.verifiers.get(msg.device_id)
        if v is None:
            raise Rejected("unknown device")
        return v.verify(msg, now)
