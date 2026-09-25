> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# WattGap — product spec

## Problem (Base’s existing system)

Base Core is already in yards. The fleet already charges cheap and discharges tight. Inefficiency still happens because:

- ERCOT **reprices every 5 minutes** (SCED). Overnight TOU is the wrong clock.
- Public data (prices, load, mix, outages) is **not turned into a ranked opportunity list**.
- Units go **offline** (LTE, SOC telemetry freeze, install lock). A target that assumed 100% online over-dispatches the rest or misses MW.
- Homeowners see a battery that “did something.” No receipt → churn / tickets.

WattGap does not replace firmware or the real dispatcher. It is an **opportunity + efficiency layer** on top of public grid data and a simulated (then later real) fleet.

## What we build

### 1. Opportunity scanner (Open Grid Data)

Each interval, score every load zone:

```
charge_score  = cheap vs last-24h p20  AND  headroom in SOC
discharge_score = expensive vs p80 AND grid_tight (load or wind/solar drop)
```

Output: **ranked windows** — “LZ_HOUSTON 16:10–16:25 DISCHARGE, expected $412/MWh, fleet can deliver 1.8 MW online.”

That *is* “identify the opportunities.”

### 2. Efficiency gap (the name)

Run two policies on the same fleet + same prices:

| Policy | Rule |
|---|---|
| **Naive** | Charge 23:00–07:00, HOLD otherwise |
| **WattGap** | Charge at cheap, discharge at expensive+tight, HOLD if stale/offline |

Report: **WattGap $** = aware_revenue − naive_revenue, plus MWh moved in spike hours. If this number is ~0, the policy is wrong or the day was boring — switch to the spike CSV.

### 3. Fleet orchestration (when pieces fail)

Each battery = worker: heartbeat, SOC, max kW (20), energy (40 kWh), zone.

Supervisor:

- Tick every interval
- Skip offline / stale-price → HOLD
- If online kW < target: scale remaining to max, then **ALARM**
- Demo: `kill_west` drops 30% of West units mid-replay

### 4. Receipt (commercializable)

One unit, plain language from **facts only**:

> Your Core in Houston discharged 8.2 kWh (16:10–16:25) because LZ_HOUSTON was $412/MWh and system wind dropped 3 GW. Estimated credit $3.38. Naive overnight policy would have been HOLD ($0).

## Non-goals (48h)

- Real Base API / real customer batteries
- ML / RL dispatch
- Hardware, firmware, factory
- Live ERCOT as the only path (replay first)
- Crypto, laundry apps, generic dashboards with no $ gap

## Success = Base engineer says

“That’s the missed-money view we don’t have on a projector, and you actually killed nodes.”


## Extension: FleetPulse Desk

Weekend stretch on top of WattGap (see [PLAN.md](./PLAN.md)):

- HITL desk for high-impact batches (TTL fail-closed)
- Signed, replay-protected commands + rogue telemetry quarantine
- Audit log + compliance export for the “ADER/utility evidence” story

WattGap remains the **$ gap + opportunity** core. Desk does not replace policy math with an LLM.


See also the unified bible: [PROJECT.md](./PROJECT.md).
