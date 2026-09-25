> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# FleetPulse Desk — build plan (extends WattGap)

This is the plan we locked for Base Power × AITX (Sep 25–27, 2026).
**WattGap (this repo) is the spine.** FleetPulse Desk is the ops/security layer on top — not a second product.

## Honest frame

A weekend build does **not** clear Base’s real bottlenecks. It should:

1. Put a **real-ish $ gap** on the projector (Open Grid Data) — WattGap already does this.
2. Show dispatch **holds under failure** (Orchestration).
3. Name a buyer and a loop Base might hire you to harden (Commercializable).

Do not claim “we solved Base’s control plane.”

## One product, three faces

```
ERCOT-shaped prices (CSV → later live)
        │
        ├─► Opportunity scanner + naive vs aware $     ← WattGap today
        ├─► Spike / scarcity signal (rules first)
        └─► Live planner → MW target + per-home reserve
                │
                ▼
         Pending batch (TTL) + decision audit log
                │
         Desk: Approve | Reject | Protect          ← HITL
                │
                ▼
     Signed command bus (device id, anti-replay)   ← security lane
                │
                ▼
     Battery agents + chaos (offline %, partition)
                │
                ▼
     Receipt + compliance export (JSON/HTML)
```

| Track | What judges see |
|---|---|
| Open Grid Data | Replay / live-ish LMP → ranked windows + WattGap $ |
| Orchestration | Kill nodes / desk; rebalance or alarm; fail closed |
| Most Commercializable | Buyer = Base fleet ops (+ sales ROI tab). Desk + evidence pack |

## Merge map (idea → layer)

| Idea | In product as |
|---|---|
| Dispatch replay + zone $ | WattGap replay / ROI tab |
| Price-spike early warning | Signal engine (rules → optional light model) |
| Outage / ZIP battery-need | Slide + ranked table only (no GIS) |
| Fleet coordinator + chaos | Core runtime (extend `sim/`) |
| Zero-trust command path | Signed commands + rogue spoof demo |
| Multi-agent negotiator | Audit log fields (homeowner / price / target) — not chat theater |
| Homeowner ROI estimator | Sales mode reusing replay math |
| VPP compliance pack | Export of dispatch + approvals + telemetry facts |
| HITL desk | Approve / Reject / Protect + TTL on desk death |

## 48h ship list

### P0 (must demo or cut claim)

1. ERCOT-shaped LMP (real dump preferred; `sample_prices.csv` backup).
2. WattGap $ = aware − naive on same series (fix naive so overnight hours exist in the file).
3. 100–500 sim batteries (claim “scales to 10k”; don’t freeze the laptop).
4. Coordinator MW target under **live chaos** (kill zone, coordinator stun).
5. Desk approve/reject + **TTL expire if desk dies** (no silent execute).
6. Signed commands + one **rogue spoof / false SoC** → quarantine.
7. Per-decision audit line.
8. One compliance export (JSON + one-page HTML).
9. One ROI/replay view (one zone, monthly or spike-day $).

### P1 (only if ahead)

- Light spike model + summer backtest chart
- Address → ROI polish
- ZIP need scores as a static ranked table

### P2 (slide only)

- Full 12-month all-zone heatmaps
- Real ADER settlement with ERCOT
- True 10k concurrent agents
- Full multi-party negotiation UI

### Cut order if behind

ZIP map → ML spike → pretty ROI → **keep** chaos + signed + desk + signal + WattGap $ + export.

## Modes

1. **Autopilot (low risk):** small SoC tweaks under $/kW cap auto-apply.
2. **Desk required (high risk):** discharge above X kW or below reserve → Approve.
3. **Protect:** cancel earn batches; lock homeowner reserve.

## Demo arc (~4–5 min)

1. Replay: WattGap $ on a spike day vs naive.
2. Spike alert → planner opens batch.
3. Desk approves → signed commands fan out.
4. Chaos: kill ~15–30% + rogue SoC → quarantine; stay in tolerance or ALARM.
5. Kill desk mid-pending → batch expires; **zero** unsafe discharge.
6. Export compliance pack + one homeowner receipt.
7. Close: “Not your prod dispatcher — the missed-$ view and fail-closed loop you’d hire us to harden.”

## Schema sketch

```
Battery: id, zone, soc, online, reserve_soc, last_seen
Signal:  interval, zone, price, load_frac, wind_drop, action_hint
Batch:   id, created_at, ttl_s, status (pending|approved|rejected|expired), target_mw, items[]
BatchItem: battery_id, action, kw
SignedCommand: batch_id, battery_id, action, nonce, ts, signature
AuditEvent: ts, actor (planner|desk|guard|chaos), fields...
EvidencePack: batches[], commands[], telemetry_digest, wattgap_dollars
```

## Repo layout (target)

```
sim/           # keep: policy, fleet, run (WattGap $ + kill)
desk/          # pending batches, TTL, approve API (add)
security/      # sign + verify + rogue demo (add)
web/           # one page: chart, $, kill, desk, receipt (add)
data/          # quiet day + spike day CSVs
PLAN.md        # this file
PRODUCT.md     # product truth
HACK.md        # hour-by-hour
```

## Relation to existing WattGap code

Already good and should stay:

- Clear $ projector number
- Naive vs aware policies (no ML dispatch)
- Zone kill mid-replay
- Receipt from facts
- Honest non-goals

Gaps to close before Friday (see also HACK.md):

- Sample window starts midday → naive overnight never fires → naive $ = 0 and gap looks fake. **Fix the CSV or the naive window.**
- Kill marks offline but does not rebalance a fleet MW target / ALARM path yet.
- No UI, no desk, no signing, no real ERCOT dump.

Build **on** `sim/`, don’t rewrite it.

## Success line (say this)

“That’s the missed-money view, a desk that fails closed, and signed dispatch — with nodes dying on purpose.”
