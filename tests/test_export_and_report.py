import json

from conftest import make_sim, step_until_pending

from wattgap import report
from wattgap.export import build_pack, write


def test_evidence_pack(run, tmp_path):
    async def go():
        sim = await make_sim()
        b = await step_until_pending(sim)
        sim.desk.approve(b.id)
        await sim.step()
        sim.fleet.make_rogue()
        await sim.step()
        sim.kill_desk()
        for _ in range(8):
            await sim.step()
        await sim.stop()
        return sim
    sim = run(go())
    pack = build_pack(sim.audit)
    s = pack["summary"]
    assert s["approvals_count"] == 1 and s["quarantines_count"] == 1
    assert s["discharge_without_live_batch"] == 0
    jpath, hpath = write(pack, tmp_path)
    assert json.loads(jpath.read_text())["summary"]["events"] == len(sim.audit.events)
    assert "WattGap evidence pack" in hpath.read_text()


def test_report_numbers_are_consistent():
    rep = report.build()
    for d in rep["days"].values():
        p = d["per_home"]
        assert abs(d["gap_vs_fair"] - (p["wattgap"] - p["scheduled"])) < 0.011
    m = rep["month"]
    assert m["days"] == 30 and 0 <= m["days_won"] <= 30
    assert m["min_soc"] >= 0.2 - 1e-9
    for member in rep["members"].values():
        assert member["min_soc"] >= member["reserve_soc"] - 1e-9
