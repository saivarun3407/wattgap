import json

from conftest import make_sim, step_until_pending

from wattgap import fleetmath as fm
from wattgap.econ import SPEC


def state_of(sim, uid):
    return fm.STATE_NAMES[sim.fleet.state[sim.fleet.index[uid]]]


def test_fleet_size_is_not_hard_coded(run):
    async def go():
        sim = await make_sim(size=37)
        rep = await sim.step()
        await sim.stop()
        return sim, rep
    sim, rep = run(go())
    assert rep.total == 37 and rep.healthy == 37 and len(sim.fleet.registry.keys) == 37


def test_no_discharge_without_desk_approval(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        reps = [await sim.step() for _ in range(3)]  # never approved
        await sim.stop()
        return b, reps
    b, reps = run(go())
    assert b.target_mw > 0.25  # above the auto-apply cap
    assert all(r.delivered_mw == 0 for r in reps)


def test_small_batches_auto_apply_under_cap(run):
    async def go():
        sim = await make_sim(size=12)  # 12 homes: the whole commitment is under the cap
        for _ in range(8):
            await sim.step()
        await sim.stop()
        return sim
    sim = run(go())
    earn = [b for b in sim.desk.batches.values() if b.kind == "earn"]
    assert earn and all(b.status in ("auto", "done") and b.target_mw <= 0.25 for b in earn)


def test_expired_batches_never_execute(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.kill_desk()
        reps = [await sim.step() for _ in range(3)]  # desk heartbeat goes stale
        approved = sim.desk.approve(b.id)
        reps += [await sim.step() for _ in range(2)]
        await sim.stop()
        return b, approved, reps
    b, approved, reps = run(go())
    assert b.status == "expired" and not approved
    assert all(r.delivered_mw == 0 for r in reps)


def test_commitments_are_per_zone_with_headroom(run):
    async def go():
        sim = await make_sim(size=200)
        b = await step_until_pending(sim)
        await sim.stop()
        return sim, b
    sim, b = run(go())
    assert b.zone_mw and abs(sum(b.zone_mw.values()) - b.target_mw) < 1e-9
    f = sim.fleet
    sustain = fm.usable_kw(f.soc, f.reserve, hours=1.0)
    for z, mw in b.zone_mw.items():
        cap = sum(sustain[f.index[u]] for u in f.zone_ids(z)) / 1000
        assert mw <= 0.7 * cap + 1e-9  # 30% of what the zone can sustain is held back


def test_kill_30_percent_rebalances_to_target(run):
    async def go():
        sim = await make_sim(size=200)
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        victims = sim.fleet.kill_zone(b.zones[0], 0.3)
        silent = await sim.step()
        rebalanced = await sim.step()
        await sim.stop()
        return victims, silent, rebalanced
    victims, silent, rebalanced = run(go())
    assert len(victims) == 15  # 30% of the zone's 50 units, really stopped
    assert silent.delivered_mw < silent.target_mw and "silent" in silent.alarm
    assert abs(rebalanced.delivered_mw - rebalanced.target_mw) < 1e-6 and not rebalanced.alarm
    assert rebalanced.healthy == 185


def test_broken_zone_alarms_then_recommits(run):
    async def go():
        sim = await make_sim(size=100, start="15:45")
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        zone = max(b.zone_mw, key=b.zone_mw.get)
        sim.fleet.kill_zone(zone, 1.0)
        silent = await sim.step()
        broken = await sim.step()
        after = await sim.step()
        await sim.stop()
        return sim, b, zone, silent, broken, after
    sim, b, zone, silent, broken, after = run(go())
    assert silent.alarm and f"{zone} short" in broken.alarm and broken.degraded
    assert b.zone_mw[zone] == 0.0  # re-committed down to what the dead zone can do
    assert not after.alarm and abs(after.delivered_mw - after.target_mw) < 1e-6
    e = sim.audit.of_kind("commitment_recommitted")[0]
    assert e["zone"] == zone and e["to_mw"] == 0.0 and sim.audit.of_kind("commitment_broken")


def test_partition_goes_suspect_then_dead_then_recovers(run):
    async def go():
        sim = await make_sim()
        sim.fleet.partition("LZ_WEST", ticks=2)
        a = await sim.step()
        b = await sim.step()
        c = await sim.step()
        await sim.stop()
        return sim, a, b, c
    sim, a, b, c = run(go())
    assert a.healthy == 30 and b.healthy == 30 and c.healthy == 40
    kinds = [e["kind"] for e in sim.audit.events]
    assert "unit_suspect" in kinds and "unit_dead" in kinds and "unit_recovered" in kinds


def test_stale_feed_holds(run):
    async def go():
        sim = await make_sim(start="15:15")
        sim.fleet.stale_feed(1)
        rep = await sim.step()
        await sim.stop()
        return rep
    rep = run(go())
    assert set(rep.zone_actions.values()) == {"HOLD"} and rep.delivered_mw == 0


def test_rogue_soc_spoof_is_quarantined_and_revocable(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        uid = sim.fleet.make_rogue()
        await sim.step()
        quarantined = state_of(sim, uid)
        sim.fleet.revoke(uid)
        await sim.step()
        await sim.stop()
        return sim, uid, quarantined
    sim, uid, quarantined = run(go())
    assert quarantined == "quarantined" and state_of(sim, uid) == "revoked"
    assert any(e["kind"] == "unit_quarantined" and e["unit"] == uid for e in sim.audit.events)
    assert uid in sim.fleet.registry.revoked


def test_units_reject_forged_replayed_and_redirected_commands(run):
    async def go():
        sim = await make_sim()
        await sim.step()
        forged, replayed = sim.forge_command(), sim.replay_command()
        _, redirected = sim.redirect_command()
        await sim.step()
        await sim.stop()
        return sim, forged, replayed, redirected
    sim, forged, replayed, redirected = run(go())
    whys = {e["actor"]: e["why"] for e in sim.audit.of_kind("command_rejected")}
    assert whys == {forged: "bad signature", replayed: "replayed nonce", redirected: "addressed to another device"}


def test_protect_cancels_earning_and_locks_reserve(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        devices = sim.fleet.transport.devices
        before = {u: d.battery.soc for u, d in devices.items()}
        sim.fleet.protect(True)
        reps = [await sim.step() for _ in range(3)]
        after = {u: d.battery.soc for u, d in devices.items()}
        await sim.stop()
        return sim, b, before, after, reps
    sim, b, before, after, reps = run(go())
    assert b.status == "cancelled"
    assert all(r.delivered_mw == 0 for r in reps)
    assert all(after[u] >= before[u] - 1e-9 for u in before)
    assert (sim.fleet.reserve >= SPEC.reserve_soc).all()


def test_devices_never_breach_their_reserve(run):
    async def go():
        sim = await make_sim(size=40, start="14:45")
        for _ in range(24):
            for b in [b for b in sim.desk.batches.values() if b.status == "pending"]:
                sim.desk.approve(b.id)
            await sim.step()
        await sim.stop()
        return sim
    sim = run(go())
    socs = [d.battery.soc for d in sim.fleet.transport.devices.values()]
    assert sum(h.delivered_mw for h in sim.fleet.history) > 0
    assert min(socs) >= SPEC.reserve_soc - 1e-9


def test_exports_net_out_home_use(run):
    async def go():
        sim = await make_sim(size=40, start="14:45")
        reps = []
        for _ in range(8):
            for b in [b for b in sim.desk.batches.values() if b.status == "pending"]:
                sim.desk.approve(b.id)
            reps.append(await sim.step())
        await sim.stop()
        return reps
    reps = run(go())
    busy = [r for r in reps if r.delivered_mw > 0]
    assert busy and all(r.home_mw > 0 for r in reps)
    for r in busy:
        assert r.export_mw < r.delivered_mw  # homes used part of the discharge behind the meter
        assert r.export_mw >= r.delivered_mw - r.home_mw - 1e-9


def test_audit_log_is_append_only_jsonl(run, tmp_path):
    path = tmp_path / "audit.jsonl"

    async def go():
        sim = await make_sim(audit_path=path)
        for _ in range(5):
            await sim.step()
        await sim.stop()
        return sim
    sim = run(go())
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert lines == sim.audit.events
    assert [e["seq"] for e in lines] == list(range(1, len(lines) + 1))
    assert sum(e["kind"] == "dispatch" for e in lines) == 5  # one decision line per tick


def test_member_protect_locks_only_that_home(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        home = next(u for u in sim.fleet.ids if sim.fleet.zone[sim.fleet.index[u]] == sim.fleet.zone[0])
        sim.fleet.protect_home(home, True)
        sim.desk.approve(b.id)
        await sim.step()
        view_on = sim.fleet.home_view(home)
        others = [u for u in sim.fleet.ids if u != home and sim.fleet.commanded[sim.fleet.index[u]] > 0]
        sim.fleet.protect_home(home, False)
        view_off = sim.fleet.home_view(home)
        await sim.stop()
        return view_on, view_off, others
    view_on, view_off, others = run(go())
    assert view_on["protected"] and view_on["action"] != "DISCHARGE" and view_on["reserve"] >= view_on["soc"] - 0.01
    assert others  # the rest of the fleet still earned
    assert not view_off["protected"] and view_off["reserve"] == SPEC.reserve_soc
