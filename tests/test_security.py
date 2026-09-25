import pytest

from wattgap.security import MAX_SKEW_S, Rejected, Verifier, device_key, sign

KEY = device_key(b"secret", "core-1")


def test_valid_message_verifies():
    msg = sign(KEY, "core-1", {"action": "HOLD"}, ts=100.0)
    assert Verifier(KEY).verify(msg, now=100.0) == {"action": "HOLD"}


def test_tampered_body_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    forged = type(msg)(msg.device_id, {"kw": 20.0}, msg.nonce, msg.ts, msg.sig)
    with pytest.raises(Rejected, match="signature"):
        Verifier(KEY).verify(forged, now=100.0)


def test_wrong_key_rejected():
    msg = sign(device_key(b"guess", "core-1"), "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="signature"):
        Verifier(KEY).verify(msg, now=100.0)


def test_replay_rejected():
    v = Verifier(KEY)
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    v.verify(msg, now=100.0)
    with pytest.raises(Rejected, match="replayed"):
        v.verify(msg, now=101.0)


def test_stale_timestamp_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="stale"):
        Verifier(KEY).verify(msg, now=100.0 + MAX_SKEW_S + 1)


def test_keys_are_per_device():
    assert device_key(b"secret", "core-1") != device_key(b"secret", "core-2")
