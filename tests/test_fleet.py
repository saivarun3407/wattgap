import json

from conftest import make_sim, step_until_pending

from wattgap.econ import SPEC


def test_fleet_size_is_not_hard_coded(run):
    async def go():
        sim = await make_sim(size=37)
        rep = await sim.step()
        await sim.stop()
        return rep
    rep = run(go())
    assert rep.total == 37 and rep.healthy == 37


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


def test_kill_30_percent_rebalances_to_target(run):
    async def go():
        sim = await make_sim(size=200)
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        victims = sim.fleet.kill_zone("LZ_HOUSTON", 0.3)
        silent = await sim.step()
        rebalanced = await sim.step()
        await sim.stop()
        return victims, silent, rebalanced
    victims, silent, rebalanced = run(go())
    assert len(victims) == 15  # 30% of the 50 Houston units
    assert silent.delivered_mw < silent.target_mw and silent.alarm
    assert abs(rebalanced.delivered_mw - rebalanced.target_mw) < 1e-6 and not rebalanced.alarm
    assert rebalanced.healthy == 185


def test_alarm_and_degraded_when_capacity_cannot_cover(run):
    async def go():
        sim = await make_sim(size=100)
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        for z in ("LZ_HOUSTON", "LZ_NORTH", "LZ_SOUTH"):
            sim.fleet.kill_zone(z, 1.0)
        await sim.step()
        rep = await sim.step()
        await sim.stop()
        return rep
    rep = run(go())
    assert "short" in rep.alarm and rep.degraded
    assert rep.delivered_mw < rep.target_mw


def test_partition_goes_suspect_then_recovers(run):
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
        sim = await make_sim(start="13:45")
        sim.fleet.stale_feed(1)
        rep = await sim.step()
        await sim.stop()
        return rep
    rep = run(go())
    assert set(rep.zone_actions.values()) == {"HOLD"} and rep.delivered_mw == 0


def test_rogue_soc_spoof_is_quarantined(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        uid = sim.fleet.make_rogue()
        await sim.step()
        await sim.stop()
        return sim, uid
    sim, uid = run(go())
    assert sim.fleet.records[uid].state == "quarantined"
    assert any(e["kind"] == "unit_quarantined" and e["unit"] == uid for e in sim.audit.events)


def test_units_reject_forged_and_replayed_commands(run):
    async def go():
        sim = await make_sim()
        await sim.step()
        forged, replayed = sim.forge_command(), sim.replay_command()
        await sim.step()
        await sim.stop()
        return sim, forged, replayed
    sim, forged, replayed = run(go())
    whys = {e["actor"]: e["why"] for e in sim.audit.of_kind("command_rejected")}
    assert whys == {forged: "bad signature", replayed: "replayed nonce"}


def test_protect_cancels_earning_and_locks_reserve(run):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        before = {u: x.battery.soc for u, x in sim.fleet.units.items()}
        sim.fleet.protect(True)
        reps = [await sim.step() for _ in range(3)]
        after = {u: x.battery.soc for u, x in sim.fleet.units.items()}
        await sim.stop()
        return sim, b, before, after, reps
    sim, b, before, after, reps = run(go())
    assert b.status == "cancelled"
    assert all(r.delivered_mw == 0 for r in reps)
    assert all(after[u] >= before[u] - 1e-9 for u in before)
    assert all(r.reserve >= SPEC.reserve_soc for r in sim.fleet.records.values())


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
