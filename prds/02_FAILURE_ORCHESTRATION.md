# PRD: Failure Orchestration

**Status:** Hackathon P0 | **Effort:** 3h | **Revenue:** Risk reduction

---

## Problem

A target of "discharge 2 MW fleet-wide" assumes 100% of batteries are online and responsive. In reality:
- LTE module fails (5–10% of fleet on any day).
- Telemetry stales (price data doesn't update).
- Battery goes offline mid-dispatch (low SoC, thermal limit, firmware crash).

**Gap:** Naive dispatch over-counts available capacity, then either:
1. Fails to hit the target (missed $).
2. Over-dispatches remaining healthy units (risk of brownout).

---

## Solution

Build a **supervisor layer** that:
1. **Tracks per-battery online/offline state** (heartbeat + price freshness).
2. **Calculates real available capacity** (online battery count * kW).
3. **If available < target:** Scale remaining online to max, then **ALARM**.
4. **Chaos injection (demo):** Kill 30% of fleet mid-dispatch, watch rebalance.

Output: Confidence score on whether target was hit safely.

---

## MVP (Hackathon)

- [ ] Battery agent: heartbeat (online flag) + telemetry timestamp.
- [ ] Supervisor: count online units, sum available kW.
- [ ] Rebalance logic: if online_kW < target_kW, max out remaining + ALARM.
- [ ] Chaos: `kill_zone(zone, pct)` to offline 30% of West.
- [ ] CLI: `python3 sim/run.py --chaos-west-30`

**Output:**
```
Interval: 16:10
Target MW:       2.0
Online batteries: 340 / 400 (85%)
Available MW:    1.7
Status:          ALARM (target unmet, max-ing remaining)
Rebalanced kW:   5.0 (was 5.0, now capped at 4.7 avg)
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Kill 30% of fleet, system doesn't break | ✓ |
| ALARM fires when available < target | ✓ |
| Remaining units rebalance without error | ✓ |
| Replay completes end-to-end | ✓ |

---

## Stretch (Week 1)

- [ ] Peer rebalancing (neighbor lending) instead of just max-out.
- [ ] Cascade failure detection (e.g., if zone goes offline, predict secondary failures).
- [ ] Predictive maintenance (RUL model to warn before failure).

---

## Revenue Model

**Risk reduction:**
- Prevents over-dispatch failures (reputation damage, grid penalties).
- Estimated value: $10–50k/year for Base (avoid one grid incident).
- Not direct revenue, but enables safe scaling to 50k+ homes.

---

## Engineering Tasks

### Agent / Fleet Model
- [ ] **Task 2.1:** Battery agent with online/offline state + heartbeat.
- [ ] **Task 2.2:** Telemetry staleness check (if price > 5min old, mark offline).
- [ ] **Task 2.3:** Fleet aggregator (count online, sum kW).

### Supervision & Rebalancing
- [ ] **Task 2.4:** Supervisor calculates real available MW.
- [ ] **Task 2.5:** Rebalance algorithm (scale remaining units proportionally to max).
- [ ] **Task 2.6:** ALARM condition (available < target).

### Chaos & Demo
- [ ] **Task 2.7:** Chaos injection: `kill_zone(zone, pct)` to offline batteries.
- [ ] **Task 2.8:** Replay with chaos enabled; measure target hit rate.

---

## Acceptance Criteria

1. Killing 30% of fleet does not crash the system.
2. Supervisor correctly identifies available capacity.
3. Rebalance is safe (doesn't over-dispatch any unit).
4. ALARM fires predictably.

---

## Dependencies

- Price-Aware Dispatch (runs on top of this).
- Sim fleet model (we have).

---

## Owner & DRI

- **Product:** Ops team (define ALARM thresholds, SLA).
- **Eng:** Fleet orchestration owner.

