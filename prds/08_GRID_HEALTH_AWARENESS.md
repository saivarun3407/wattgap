# PRD: Grid Health Awareness

**Status:** Hackathon + Week 2 | **Effort:** 4h | **Revenue:** Grid services contracts

---

## Problem

Batteries today respond to prices. But grid operators care about stability: voltage, frequency deviation, transmission congestion. Batteries could help stabilize the grid *in addition to* arbitraging prices.

**Gap:** No "grid health score" input to dispatch. We're missing a revenue stream: grid services.

---

## Solution

1. **Ingest grid stress signals:** ERCOT congestion map, voltage data, frequency volatility.
2. **Score grid stress:** Combine congestion + voltage + frequency into "grid needs help now" metric.
3. **Dispatch when grid is weakest:** Prioritize helping grid over pure arbitrage.
4. **Revenue:** Potential grid service contracts (utility pays for stability).

---

## MVP (Hackathon)

- [ ] Mock grid stress score (combining congestion + voltage + frequency).
- [ ] Policy: Weight dispatch by grid stress (1.5x revenue multiplier when grid is stressed).
- [ ] Measure: "Grid stability events prevented" + potential revenue.
- [ ] Output: "Batteries helped grid X times, estimated $Y value."

**Output:**
```
Grid stress: 0–1 scale
Event 1: Stress=0.8 (high) → Discharge prioritized (higher revenue)
Event 2: Stress=0.2 (low)  → Hold (don't help unless price is good)

Month summary:
Grid help events: 12
Estimated grid services value: $48/home (at $X/MW/hour)
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Grid stress score calculated | ✓ |
| Dispatch prioritizes grid help | ✓ |
| Grid services revenue quantified | ✓ |
| Batteries improve grid stability metric | ✓ |

---

## Stretch (Week 3)

- [ ] ERCOT DSO (Distribution System Operator) partnership.
- [ ] Real grid services pricing.
- [ ] Predictive grid stress (anticipate before crisis).

---

## Revenue Model

**Potential grid services revenue:**
- $X per MWh for grid stability (varies by ERCOT region, service type).
- Estimated: $20–100/MW/hour = $0.5–2.5/home/month.

---

## Engineering Tasks

### Scoring
- [ ] **Task 8.1:** Combine congestion + voltage + frequency into grid stress score.
- [ ] **Task 8.2:** Normalize to 0–1 scale.

### Dispatch
- [ ] **Task 8.3:** Weight dispatch by grid stress (higher stress = higher priority).
- [ ] **Task 8.4:** Measure grid stability improvement.

### Revenue
- [ ] **Task 8.5:** Quantify grid services value.
- [ ] **Task 8.6:** Track "grid help events" per month.

---

## Acceptance Criteria

1. Grid stress score is calculated and reasonable.
2. Dispatch changes based on grid stress.
3. Grid services revenue is estimated.
4. Homeowner sees "You helped the grid" message.

---

## Dependencies

- ERCOT data feeds (congestion, voltage, frequency).

---

## Owner & DRI

- **Product:** Utility partnerships (define grid services programs).
- **Eng:** Scoring + dispatch owner.

