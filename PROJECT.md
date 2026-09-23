# WattGap = one project (Base Power × AITX · Sep 25–27, 2026)

**Hiring hackathon.** Judges = Base eng. Thrive + a16z on the poster.  
Luma: https://luma.com/aitx-94j6

This repo is the **single** weekend build. Everything we discussed folds in here — not three apps.

## One sentence

WattGap finds the **$ Base’s home-battery fleet leaves on the table** from public ERCOT-shaped data, turns that into **CHARGE / HOLD / DISCHARGE** for a simulated fleet, **survives node death** (and a dead ops desk), uses **signed commands**, and prints a **homeowner receipt** + **compliance export**.

## Tracks (one demo, three boxes)

| Track | What we show |
|---|---|
| **Open Grid Data** | Replay spike + quiet day → ranked opportunities + WattGap $ (aware − naive) |
| **Orchestration** | Independent battery workers; kill 30%; rebalance or ALARM; desk TTL fail-closed |
| **Most Commercializable** | Buyer = Base fleet ops (+ sales ROI). Receipt + evidence pack |

## Honest bottleneck claim

We do **not** clear Base’s production bottlenecks in 48h. We demonstrate the *shape* of the hard problems (missed $, partial fleet, human gate, command integrity, proof). Say that out loud in the demo.

## Architecture (unified)

```
ERCOT-shaped prices/load/mix (CSV replay → optional live)
        │
        ├─ Opportunity scanner + naive vs aware $     ← sim/ today
        ├─ Spike / scarcity signal (rules first)
        └─ Planner → MW target + per-home reserve
                │
                ▼
         Pending batch (TTL) + decision audit log
                │
         Desk: Approve | Reject | Protect             ← HITL
                │
                ▼
     Signed command bus (device id, anti-replay)      ← security
                │
                ▼
     Battery agents + chaos (offline %, partition)
                │
                ▼
     Receipt + compliance export (JSON/HTML)
```

## Modes

1. **Autopilot (low risk):** small SoC tweaks under cap auto-apply.  
2. **Desk required (high risk):** big discharge / below reserve → Approve.  
3. **Protect:** cancel earn batches; lock homeowner reserve.

## Idea → layer map (nothing orphaned)

| Idea | Where it lives |
|---|---|
| Dispatch replay + zone $ | `sim/` + ROI tab |
| Price-spike early warning | Signal engine (rules → optional light model) |
| Outage / ZIP battery-need | Slide + ranked table only (no GIS) |
| Fleet coordinator + chaos | `sim/fleet.py` + kill demo |
| Zero-trust command path | `security/` (signed cmds + rogue spoof) |
| Multi-agent negotiator | Audit log fields — not chat theater |
| Homeowner ROI estimator | Sales mode reusing replay math |
| VPP compliance / audit pack | Export of logs + approvals |
| HITL desk | `desk/` Approve/Reject/Protect + TTL |
| Nodal (origin brainstorm) | Same spine — see `docs/ORIGIN_NODAL.md` |

## 48h P0 (ship or drop claim)

1. Real-ish LMP CSV (quiet + spike); fix naive window so overnight exists.  
2. WattGap $ on projector.  
3. 100–500 sim batteries; MW target under live chaos.  
4. Desk + TTL expire on desk death.  
5. Signed commands + one rogue SoC spoof → quarantine.  
6. Audit line per decision.  
7. One compliance export.  
8. One ROI/replay view (one zone).

**Cut order if behind:** ZIP map → ML spike → pretty ROI → keep chaos + signed + desk + signal + WattGap $ + export.

## Demo arc (~4–5 min)

1. Replay: WattGap $ vs naive on spike day.  
2. Spike → planner opens batch.  
3. Desk approves → signed commands fan out.  
4. Chaos: kill ~15–30% + rogue SoC → quarantine; tolerance or ALARM.  
5. Kill desk mid-pending → batch expires; zero unsafe discharge.  
6. Export pack + one receipt.  
7. Close: “Not your prod control plane — the missed-$ view and fail-closed loop you’d hire us to harden.”

## Repo map

| Path | Role |
|---|---|
| [PROJECT.md](./PROJECT.md) | **This file — source of truth** |
| [PLAN.md](./PLAN.md) | FleetPulse Desk build detail |
| [PRODUCT.md](./PRODUCT.md) | Product spec |
| [HACK.md](./HACK.md) | Hour-by-hour |
| [docs/HACKATHON.md](./docs/HACKATHON.md) | Event / Base / tracks |
| [docs/ORIGIN_NODAL.md](./docs/ORIGIN_NODAL.md) | Earlier Nodal spec (merged in) |
| [docs/ORIGIN_BRAINSTORM.md](./docs/ORIGIN_BRAINSTORM.md) | Kill list / alternates |
| `sim/` | Runnable opportunity + fleet (today) |
| `desk/` | TBD weekend |
| `security/` | TBD weekend |
| `web/` | TBD weekend |
| `data/` | CSVs |

## Run now

```bash
python3 sim/run.py
```

## Success line

“That’s the missed-money view, a desk that fails closed, and signed dispatch — with nodes dying on purpose.”
