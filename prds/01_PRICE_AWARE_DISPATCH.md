# PRD: Price-Aware Dispatch

**Status:** Hackathon P0 | **Effort:** 4h | **Revenue:** Foundation layer

---

## Problem

Base's batteries today use **overnight TOU charging** (23:00–07:00, HOLD otherwise). ERCOT reprices every 5 minutes. This policy leaves money on the table on spike days — missing discharge opportunities that could generate $3–8/home or more per high-price window.

**Gap:** Base has no real-time opportunity scanner. Markets intern manually reviews 288 daily 5-min intervals looking for arbitrage opportunities. That's not scalable and always late.

---

## Solution

Build a **price-aware dispatch policy** that automatically:
1. **Charges** at cheap windows (LMP < p20 of last 24h) if SoC headroom exists.
2. **Discharges** at expensive windows (LMP > p80) if SoC available.
3. **Holds** otherwise (or if telemetry is stale/offline).

Output: A **$ gap** number — how much more revenue this policy generates vs the naive overnight policy on the same day.

---

## MVP (Hackathon)

- [ ] Replay 1 spike day + 1 quiet day from CSV (ERCOT LMP data).
- [ ] Implement two policies: Naive (overnight) + Price-Aware (above).
- [ ] Print: WattGap $ = aware_revenue − naive_revenue.
- [ ] Handle telemetry staleness (skip offline batteries).
- [ ] CLI: `python3 sim/run.py`

**Output format:**
```
Day: 2026-09-15 (spike)
Policy: naive         → $412 (fleet revenue)
Policy: price-aware   → $584 (fleet revenue)
WattGap gap           → $172 (per-day fleet uplift)
WattGap $/home        → $0.86 (for 200 homes)
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Replay runs without error | ✓ |
| WattGap $ > 0 on spike day | ✓ |
| Handles 30% offline gracefully | ✓ |
| Output matches manual calculation | ✓ |

---

## Stretch (Week 1)

- [ ] Live ERCOT API instead of CSV.
- [ ] Real Base fleet data (replace simulator).
- [ ] Dashboard showing daily WattGap $.
- [ ] Per-zone breakdown (HOUSTON vs WEST vs NORTH).

---

## Revenue Model

**Unit Economics:**
- Assumes $0.086/kWh arbitrage (buy at $0.05, sell at $0.12+).
- 40 kWh battery, 1 spike day / week → ~$3.44/home/week.
- Conservative annual: ~$150/home/year.
- **Base's cut:** 20% of uplift = $30/home/year per fleet (200 homes = $6k/year).

**Note:** This is the foundation. Revenue stacking (Tier 3) multiplies this 2–3x.

---

## Engineering Tasks

### Sim Engine
- [ ] **Task 1.1:** Parse ERCOT LMP CSV into price array (288 5-min intervals/day).
- [ ] **Task 1.2:** Implement battery simulator (SOC tracking, charge/discharge rates).
- [ ] **Task 1.3:** Implement Naive policy (charge 23:00–07:00, HOLD).
- [ ] **Task 1.4:** Implement Price-Aware policy (threshold-based dispatch).

### Metrics & Output
- [ ] **Task 1.5:** Calculate revenue ($ moved * LMP).
- [ ] **Task 1.6:** Calculate MWh moved per policy (for grid transparency).
- [ ] **Task 1.7:** CLI script to run replay and print comparison.

### Validation
- [ ] **Task 1.8:** Verify naive policy $ matches hand-calculated baseline.
- [ ] **Task 1.9:** Test with 100, 500 battery fleet sizes.
- [ ] **Task 1.10:** Handle offline battery (mark HOLD, don't count toward MW target).

---

## Acceptance Criteria

1. Two dispatch policies run on same price data.
2. WattGap $ is positive and meaningful (>$50/day for 200 homes).
3. Output is repeatable and matches manual checks.
4. Code is modular (easy to add policy #3 next sprint).

---

## Dependencies

- ERCOT sample price CSV (we have).
- Python sim framework (we have).

---

## Owner & DRI

- **Product:** Markets team (define success, commercialize).
- **Eng:** Sim owner (modular dispatch engine).

