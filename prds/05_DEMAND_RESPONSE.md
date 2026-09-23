# PRD: Demand Response (Sell Not-Charging)

**Status:** Hackathon + Week 1 | **Effort:** 4h | **Revenue:** $X/home/month (10–20 $/MWh)

---

## Problem

Current model: Batteries arbitrage by discharging when expensive, charging when cheap.

Alternative: **Demand response** — grid pays batteries to *avoid charging* during peak hours. Revenue model is inverted: instead of trading price deltas, we sell "avoided load."

**Gap:** Base ignores demand response opportunities. Low-hanging revenue stream.

---

## Solution

1. **Invert dispatch logic:** Instead of "discharge at high price," offer "don't charge 16:00–21:00" to grid.
2. **Account revenue:** Grid pays $/MW for avoided load. Track avoided charging vs actual charging.
3. **Compare to energy arb:** Demand response is typically 10–20 $/MWh (lower than price arb), but steadier and requires less battery movement (less degradation).

**Output:** "Demand response earned $1.50/home today vs $2.86 from energy arb. Trade-off: less $ but 40% less degradation."

---

## MVP (Hackathon + Week 1)

- [ ] Implement DR policy: "Don't charge during peak hours (16:00–21:00)."
- [ ] Calculate avoided kWh vs actual charging pattern.
- [ ] Revenue: avoided_kWh * $grid_rate (assume $20/MWh).
- [ ] Compare to energy arb: $ per MWh moved vs $ per MWh avoided.

**Output:**
```
Policy: Energy Arb        → $584 (charge/discharge)
Policy: Demand Response   → $312 (avoid charging)
Energy Arb $/MWh moved   → $120 (high intensity, high $)
Demand Response $/MWh     → $20 (low intensity, steady $)

Recommendation: Stack them. DR when price-arb opportunity is weak.
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| DR policy implemented | ✓ |
| Avoided kWh tracked accurately | ✓ |
| $ per MWh avoided is 10–20x less than arb (as expected) | ✓ |
| Backtest shows DR revenue > $1/home/month | ✓ |

---

## Stretch (Week 2)

- [ ] ERCOT demand response program partnership.
- [ ] Real grid $/MW rate (not mock).
- [ ] Stacking logic: when to prefer DR over energy arb.

---

## Revenue Model

**Unit economics:**
- Assume $20/MWh for demand response.
- 40 kWh avoided charging, 1 event/week → ~$0.56/home/week.
- Annual: ~$29/home/year.
- **Value:** Lower $ but steadier, less grid risk (utilities love DR).

---

## Engineering Tasks

### Policy
- [ ] **Task 5.1:** DR policy (don't charge during peak hours).
- [ ] **Task 5.2:** Track avoided charging vs baseline charging pattern.

### Revenue
- [ ] **Task 5.3:** Calculate avoided kWh.
- [ ] **Task 5.4:** Revenue = avoided_kWh * grid_rate.

### Comparison
- [ ] **Task 5.5:** Side-by-side comparison (energy arb vs DR).
- [ ] **Task 5.6:** Recommend stacking (which policy at which time).

---

## Acceptance Criteria

1. DR policy runs without error.
2. Avoided kWh is tracked correctly.
3. Revenue is meaningful and lower than energy arb (as expected).
4. Can be combined with other policies.

---

## Dependencies

- Price-Aware Dispatch.

---

## Owner & DRI

- **Product:** Utility partnerships team (define program specifics).
- **Eng:** Dispatch policy owner.

