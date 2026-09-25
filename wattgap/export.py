"""Compliance / evidence pack for one run: JSON plus a one-page HTML summary."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .audit import AuditLog

SECTIONS = {
    "decisions": ("dispatch",),
    "batches": ("batch_submitted", "batch_done"),
    "approvals": ("batch_approved",),
    "rejections": ("batch_rejected",),
    "expirations": ("batch_expired",),
    "alarms": (),  # dispatch lines that carried an alarm
    "quarantines": ("unit_quarantined",),
    "security": ("command_rejected", "telemetry_rejected"),
    "unit_health": ("unit_suspect", "unit_dead", "unit_recovered"),
    "member_protect": ("protect_on", "protect_off"),
    "chaos": ("kill_zone", "partition", "partition_healed", "stale_feed", "rogue_unit",
              "forged_command", "replayed_command", "desk_killed", "desk_revived"),
}


def build_pack(audit: AuditLog, economics: dict | None = None) -> dict:
    pack = {name: audit.of_kind(*kinds) for name, kinds in SECTIONS.items()}
    pack["alarms"] = [e for e in audit.events if e["kind"] == "dispatch" and e.get("alarm")]
    unsafe = [e for e in pack["decisions"] if e["delivered_mw"] > 0 and not e["batch"]]
    pack["summary"] = {
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "events": len(audit.events),
        **{f"{k}_count": len(v) for k, v in pack.items() if isinstance(v, list)},
        "mwh_delivered": round(sum(e["delivered_mw"] for e in pack["decisions"]) * 0.25, 3),
        "discharge_without_live_batch": len(unsafe),
    }
    if economics:
        pack["economics"] = economics
    return pack


def _rows(events: list[dict], cols: list[str]) -> str:
    head = "".join(f"<th>{c}</th>" for c in cols)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(e.get(c, '')))}</td>" for c in cols) + "</tr>" for e in events)
    return f"<table><tr>{head}</tr>{body}</table>" if events else "<p class=muted>None in this run.</p>"


def write(pack: dict, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath, hpath = out_dir / "evidence.json", out_dir / "evidence.html"
    jpath.write_text(json.dumps(pack, indent=2, default=str))
    s = pack["summary"]
    parts = [
        ("Approvals", pack["approvals"], ["seq", "actor", "batch", "target_mw"]),
        ("Rejections", pack["rejections"], ["seq", "actor", "batch", "target_mw"]),
        ("Expired batches (fail-closed)", pack["expirations"], ["seq", "batch", "why"]),
        ("Alarms", pack["alarms"], ["seq", "interval", "target_mw", "delivered_mw", "healthy", "alarm"]),
        ("Quarantines", pack["quarantines"], ["seq", "unit", "zone", "reported_soc", "physics_soc"]),
        ("Rejected messages", pack["security"], ["seq", "actor", "kind", "why", "unit"]),
        ("Member Protect", pack["member_protect"], ["seq", "kind", "actor", "cancelled"]),
        ("Chaos injected", pack["chaos"], ["seq", "kind", "zone", "killed", "of", "unit", "ticks"]),
        ("Every dispatch decision", pack["decisions"],
         ["seq", "interval", "batch", "target_mw", "delivered_mw", "charging_mw", "healthy", "alarm"]),
    ]
    sections = "".join(f"<h2>{t}</h2>{_rows(ev, cols)}" for t, ev, cols in parts)
    hpath.write_text(f"""<!doctype html><meta charset=utf-8><title>WattGap evidence pack</title>
<style>body{{font:14px system-ui;margin:32px;color:#1d2433}}h1{{margin:0}}table{{border-collapse:collapse;margin:8px 0 24px;width:100%}}
td,th{{border-bottom:1px solid #e3e6ec;padding:4px 8px;text-align:left;font-size:12px}}th{{background:#f5f6f8}}
.kpi{{display:inline-block;margin:12px 24px 12px 0}}.kpi b{{display:block;font-size:22px}}.muted{{color:#7a8294}}</style>
<h1>WattGap evidence pack</h1><p class=muted>Generated {s['generated']} · {s['events']} audit events · simulated fleet on real ERCOT prices</p>
<div class=kpi><b>{s['decisions_count']}</b>dispatch decisions</div><div class=kpi><b>{s['approvals_count']}</b>approvals</div>
<div class=kpi><b>{s['expirations_count']}</b>expired (fail-closed)</div><div class=kpi><b>{s['alarms_count']}</b>alarm ticks</div>
<div class=kpi><b>{s['quarantines_count']}</b>quarantined units</div><div class=kpi><b>{s['security_count']}</b>rejected messages</div>
<div class=kpi><b>{s['discharge_without_live_batch']}</b>discharges without a live batch</div>
{sections}""")
    return jpath, hpath
