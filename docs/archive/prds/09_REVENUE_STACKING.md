> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../../README.md) and [PROJECT.md](../../../PROJECT.md) for what is real.

# PRD: Revenue Stacking (Multi-Stream Optimization)

**Status:** Hackathon + Week 2 | **Effort:** 5h | **Revenue:** 10–30% uplift through optimal stacking

---

## Problem

Batteries can earn from: energy arbitrage, demand response, frequency response, grid services, capacity market. But a single battery can't do all simultaneously. Charging blocks frequency response. Discharging for price might miss a grid service opportunity.

**Gap:** No optimizer that recommends which revenue stream to pursue when.

---

## Solution

1. **Score all opportunities** (price arb, demand response, freq response, grid services).
2. **Detect conflicts:** Don't charge + freq respond at same time.
3. **Rank by NPV:** Choose highest value opportunity per interval.
4. **Measure uplift:** Stacking revenue vs single-stream baseline.

---

## MVP (Hackathon)

- [ ] Conflict matrix: which operations can't run simultaneously.
- [ ] Ranking algorithm: greedy selection of highest-value opportunity per interval.
- [ ] Measure: Total $ from stacking vs single-stream baseline.
- [ ] Output: "Stacking earned $X vs Energy-only $Y (+P%)."

**Output:**
```
Interval 16:10
Opportunities:
  Energy arb:      $0.82 (charge cheap)
  Demand response: $0.25 (avoid charging)
  Frequency:       $0.12 (support grid)
  Grid services:   $0.40 (voltage help)

Ranking:
  1. Energy arb ($0.82) → SELECTED
  Conflicts: None. Execute.

Monthly stacking: $847
Monthly energy-only: $584
Uplift: +45%
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Conflict matrix is correct | ✓ |
| Ranking algorithm runs without error | ✓ |
| Stacking uplift is > 10% | ✓ |
| No over-dispatch (conflicts resolved) | ✓ |

---

## Stretch (Week 3)

- [ ] ML-based ranking (learn which opportunities correlate best).
- [ ] Dynamic pricing (higher price for energy-only vs stacking).
- [ ] Homeowner controls (e.g., "prioritize carbon" vs "maximize $").

---

## Revenue Model

**Multiplier effect:**
- Energy arb: $0.86/home/day.
- Add forecast: $1.05/home/day (+22%).
- Add stacking: $1.30/home/day (+45% over energy-only).
- Scale: $1.30 * 30 * 50k homes = $1.95M/month fleet.

---

## Engineering Tasks

### Scoring
- [ ] **Task 9.1:** Fetch all opportunity scores (price, freq, grid, demand).
- [ ] **Task 9.2:** Normalize scores to $ for comparison.

### Conflict Detection
- [ ] **Task 9.3:** Conflict matrix (which ops can't run together).
- [ ] **Task 9.4:** Check conflicts before dispatch.

### Ranking
- [ ] **Task 9.5:** Greedy ranking algorithm (highest $ first).
- [ ] **Task 9.6:** Handle ties (secondary criteria: degradation impact).

### Measurement
- [ ] **Task 9.7:** Track stacking uplift over time.
- [ ] **Task 9.8:** A/B comparison (stacking vs single-stream).

---

## Acceptance Criteria

1. Conflict detection is accurate.
2. Ranking chooses highest value opportunity.
3. Stacking uplift is measurable.
4. No over-dispatch errors.

---

## Dependencies

- All revenue stream policies (price, forecast, demand, frequency, grid, carbon).

---

## Owner & DRI

- **Product:** Revenue optimization owner.
- **Eng:** Optimization algorithm owner.

