"""The runnable stories: `make demo`, `make demo-net`, `make report`. Slower than the unit tests (~12 s)."""

import asyncio
import json

from wattgap import demo, netdemo, report


def test_demo_story_writes_a_clean_evidence_pack(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(demo, "OUT", tmp_path)
    asyncio.run(demo.main())
    pack = json.loads((tmp_path / "evidence.json").read_text())
    s = pack["summary"]
    assert s["discharge_without_live_batch"] == 0
    assert s["alarms_count"] >= 1 and s["recommits_count"] >= 1 and s["revocations_count"] == 1
    assert "evidence.json" in capsys.readouterr().out


def test_network_demo_survives_kill_9(capsys):
    asyncio.run(netdemo.main())
    out = capsys.readouterr().out
    assert "ALARM" in out and "37/40" in out


def test_report_prints_every_row(capsys):
    report.main()
    out = capsys.readouterr().out
    assert "spike 2023-09-06" in out and "Sep 2023 (30 days)" in out and "LZ_SOUTH" in out
