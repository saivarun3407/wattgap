# PRD: Battery Health Optimization

**Status:** Hackathon + Week 3 | **Effort:** 4h | **Revenue:** Warranty extension + longevity

---

## Problem

Deep-cycling a battery (0–100% every day) degrades it faster than shallow cycles. Today's dispatch maximizes $, not longevity. Homeowner's 10-year battery might degrade to 80% capacity in 7 years due to aggressive dispatch.

**Gap:** No health-aware policy. We're burning through hardware to maximize short-term $.

---

## Solution

1. **Build degradation model:** Ah fade + calendar aging as function of depth-of-discharge (DoD) + temperature.
2. **Two policies:** Money-Max (aggressive) vs Health-Max (conservative).
3. **Measure NPV:** $ earned now vs battery replacement cost in 7–10 years.
4. **Recommend:** "Health-Max would extend battery 2 years, costs $X in lost $."

---

## MVP (Hackathon)

- [ ] LFP degradation curve (typical: 80% at 3000 cycles vs 10000 cycles for shallow).
- [ ] Two policies: Aggressive (80%+ DoD) vs Conservative (40%+ DoD).
- [ ] Measure: $ earned + years of battery life remaining per policy.
- [ ] Output: NPV trade-off ($ now vs longevity cost).

**Output:**
```
Policy: Money-Max
  $ earned (5yr): $500
  Battery health (5yr): 65% capacity
  Longevity: 7 years

Policy: Health-Max
  $ earned (5yr): $350
  Battery health (5yr): 85% capacity
  Longevity: 10 years

NPV difference: -$150 $ now, +$X longevity value
Recommendation: Health-Max if warranty extension premium > 2%.
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Degradation model is reasonable (matches LFP curves) | ✓ |
| Two policies run correctly | ✓ |
| $ vs longevity trade-off is clear | ✓ |
| NPV calculation is accurate | ✓ |

---

## Stretch (Week 4)

- [ ] Real degradation data from Base fleet (historical cycles, health check).
- [ ] Temperature impact on aging.
- [ ] Homeowner preference (risk tolerance).

---

## Revenue Model

**Indirect revenue through retention:**
- Homeowner sees "Health-Max extends battery 2–3 years" → stays longer.
- Lifetime value uplift: $X per home (2–3 years * ARPU).
- Warranty extension as premium upsell: $X per home/year.

---

## Engineering Tasks

### Model
- [ ] **Task 10.1:** Implement LFP degradation curve (Ah fade vs cycles).
- [ ] **Task 10.2:** Model calendar aging (% per year).

### Policies
- [ ] **Task 10.3:** Money-Max policy (aggressive discharge).
- [ ] **Task 10.4:** Health-Max policy (conservative discharge).

### Measurement
- [ ] **Task 10.5:** Track battery health % over time per policy.
- [ ] **Task 10.6:** Calculate years of battery life remaining.
- [ ] **Task 10.7:** NPV calculation ($ earned vs longevity cost).

---

## Acceptance Criteria

1. Degradation curves are LFP-accurate.
2. Two policies execute correctly.
3. Health-Max produces slower degradation (as expected).
4. NPV trade-off is calculable and meaningful.

---

## Dependencies

- Price-Aware Dispatch (underlying).

---

## Owner & DRI

- **Product:** Customer lifetime value (retention focus).
- **Eng:** Model + sim owner.

