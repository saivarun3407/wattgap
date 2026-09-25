import pytest

from wattgap.security import MAX_SKEW_S, Registry, Rejected, Signed, Verifier, key_from_hex, new_key, public_hex, sign

KEY = new_key()
PUB = public_hex(KEY)


def verifier():
    return Verifier.for_hex(PUB)


def test_valid_message_verifies():
    msg = sign(KEY, "core-1", {"action": "HOLD"}, ts=100.0)
    assert verifier().verify(msg, now=100.0) == {"action": "HOLD"}


def test_tampered_body_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    forged = Signed(msg.device_id, {"kw": 20.0}, msg.nonce, msg.ts, msg.sig)
    with pytest.raises(Rejected, match="signature"):
        verifier().verify(forged, now=100.0)


def test_retargeted_device_id_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="signature"):
        verifier().verify(Signed("core-2", msg.body, msg.nonce, msg.ts, msg.sig), now=100.0)


def test_wrong_key_rejected():
    msg = sign(new_key(), "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="signature"):
        verifier().verify(msg, now=100.0)


def test_garbage_signature_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="signature"):
        verifier().verify(Signed(msg.device_id, msg.body, msg.nonce, msg.ts, "zz"), now=100.0)


def test_replay_rejected():
    v = verifier()
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    v.verify(msg, now=100.0)
    with pytest.raises(Rejected, match="replayed"):
        v.verify(msg, now=101.0)


def test_stale_and_future_timestamps_rejected():
    msg = sign(KEY, "core-1", {"kw": 1.0}, ts=100.0)
    with pytest.raises(Rejected, match="stale"):
        verifier().verify(msg, now=100.0 + MAX_SKEW_S + 1)
    with pytest.raises(Rejected, match="stale"):
        verifier().verify(msg, now=100.0 - MAX_SKEW_S - 1)


def test_nonce_cache_is_bounded():
    v = verifier()
    for t in range(200):
        v.verify(sign(KEY, "core-1", {}, ts=float(t * 10)), now=float(t * 10))
    assert len(v.seen) <= 64 + 1


def test_wire_format_round_trips():
    msg = sign(KEY, "core-1", {"kw": 1.5}, ts=100.0)
    assert Signed.from_json(msg.to_json()) == msg


def test_key_from_env_style_hex_is_stable():
    seed = "11" * 32
    assert public_hex(key_from_hex(seed)) == public_hex(key_from_hex(seed))


def enroll(reg, key, uid="core-1", ts=100.0):
    return reg.enroll(sign(key, uid, {"pubkey": public_hex(key)}, ts), ts)


def test_registry_enrolls_verifies_and_revokes():
    reg = Registry({"core-1"})
    enroll(reg, KEY)
    assert reg.verify(sign(KEY, "core-1", {"soc": 0.5}, 101.0), 101.0) == {"soc": 0.5}
    reg.revoke("core-1", "stolen")
    with pytest.raises(Rejected, match="revoked"):
        reg.verify(sign(KEY, "core-1", {"soc": 0.5}, 102.0), 102.0)
    with pytest.raises(Rejected, match="revoked"):
        enroll(reg, KEY, ts=103.0)


def test_registry_refuses_strangers_key_swaps_and_unproven_keys():
    reg = Registry({"core-1"})
    with pytest.raises(Rejected, match="unknown device"):
        enroll(reg, KEY, uid="core-9")
    enroll(reg, KEY)
    with pytest.raises(Rejected, match="mismatch"):
        enroll(reg, new_key(), ts=101.0)
    other = Registry({"core-1"})
    claim = sign(new_key(), "core-1", {"pubkey": PUB}, 100.0)  # claims KEY's public half without holding it
    with pytest.raises(Rejected, match="signature"):
        other.enroll(claim, 100.0)
    with pytest.raises(Rejected, match="unknown device"):
        other.verify(sign(KEY, "core-1", {}, 100.0), 100.0)
