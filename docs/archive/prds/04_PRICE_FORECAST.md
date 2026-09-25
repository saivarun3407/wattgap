> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../../README.md) and [PROJECT.md](../../../PROJECT.md) for what is real.

# PRD: Price Forecast + Anticipatory Dispatch

**Status:** Hackathon + Week 1 | **Effort:** 6h | **Revenue:** 10–25% $ uplift

---

## Problem

Price-Aware Dispatch reacts to *current* prices. But ERCOT publishes a price forecast (SCED 4-8h ahead). Batteries could **position now** for predicted spikes 4h out.

**Gap:** Without forecast, we miss spikes we could have seen coming. Reactive dispatch leaves $20–50 on the table per home per spike day.

---

## Solution

1. **Fetch or build a price forecast** (4–8h lookahead).
   - Use ERCOT published forecast (if API available).
   - Fallback: Simple 1-day-lookback ARIMA or linear trend.
2. **Anticipatory dispatch:** If forecast says spike in 4h, start charging cheap now (if SoC allows).
3. **Measure uplift:** $ earned from forecast vs reactive baseline.

**Hypothesis:** Forecast dispatch earns 10–25% more than reactive price-aware.

---

## MVP (Hackathon + Week 1)

- [ ] Implement simple price forecast model (linear trend or ARIMA on 1-day history).
- [ ] Dispatch policy: "If forecast(t+4h) > p90, charge now if SoC < 80%."
- [ ] Measure: Forecast-aware $ vs Price-Aware $ vs Naive $.
- [ ] Backtest on 5 sample days (mix of spike + quiet).

**Output:**
```
Policy: Price-Aware      → $584
Policy: Forecast-Aware   → $712 (+22%)
Uplift per home          → $0.64
Uplift $/month (4 spikes) → $2.56
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Forecast model built in <6h | ✓ |
| Forecast MAE < 20% (vs ERCOT actual) | ✓ |
| Forecast-aware $ > price-aware $ | ✓ |
| Passes backtest on 5 days | ✓ |
| No false alarms (dispatch on non-spikes) | ✓ |

---

## Stretch (Week 2)

- [ ] Live ERCOT forecast API integration.
- [ ] ML model (LSTM on 7-day history).
- [ ] Confidence intervals (only dispatch if forecast confidence > 80%).

---

## Revenue Model

**Direct uplift:**
- Conservative: 10% more $ than price-aware.
- $0.86/home/day (price-aware) * 0.10 * 30 days = $2.58/home/month.
- Scale: $2.58 * 50k homes = $129k/month fleet revenue.
- Base's cut (20%): $25.8k/month.

---

## Engineering Tasks

### Forecasting
- [ ] **Task 4.1:** Fetch or mock ERCOT price forecast data.
- [ ] **Task 4.2:** Implement simple trend model (ARIMA or linear regression).
- [ ] **Task 4.3:** Calculate forecast MAE vs actual prices.

### Dispatch Logic
- [ ] **Task 4.4:** Anticipatory dispatch policy (charge if forecast spike).
- [ ] **Task 4.5:** Threshold tuning (p90? p95?).
- [ ] **Task 4.6:** Measure forecast-aware $ revenue.

### Validation
- [ ] **Task 4.7:** Backtest on 5+ spike days.
- [ ] **Task 4.8:** Check for false alarms (don't over-charge on quiet days).
- [ ] **Task 4.9:** Compare to baseline (ensure uplift is real).

---

## Acceptance Criteria

1. Forecast model trains without error.
2. Forecast-aware policy earns more $ than reactive policy.
3. Uplift is measurable and meaningful (>5%).
4. Backtest is repeatable and passes on new data.

---

## Dependencies

- Price-Aware Dispatch (runs on top).
- ERCOT price data (we have samples).

---

## Owner & DRI

- **Product:** Markets team (forecast accuracy targets, commercialize).
- **Eng:** ML/forecast owner.

