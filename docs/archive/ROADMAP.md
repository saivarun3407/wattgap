> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# WattGap Product Roadmap

**Vision:** Build the operational intelligence layer for home-battery VPPs — from price arbitrage to grid partnership.

**48h Hackathon Goal:** Demonstrate 11 dispatch policies + the platform to compare them.  
**6mo Post-Hackathon:** Launch MVP with Tiers 1–2 (price-aware + forecast).  
**12–18mo:** Full stack (all 11 layers stacking revenue).

---

## Tier 1: Price-Aware Foundation (P0 — Hackathon)

What we ship by Sunday night. These three features prove the core concept.

### 1. Price-Aware Dispatch
- **What:** Real-time dispatch based on ERCOT 5-min LMP. Charge cheap, discharge expensive.
- **User:** Base VPP operator, markets intern.
- **Metric:** $ gap vs naive overnight charge (baseline).
- **Effort:** Already built. Polish + CSV replay.
- **Revenue:** $0 (foundation layer).

### 2. Failure Orchestration
- **What:** When 30% of fleet dies, remaining units rebalance or alarm (don't over-dispatch).
- **User:** Base ops (trust + uptime).
- **Metric:** % fleet alive + whether target achieved or safely alarmed.
- **Effort:** Sim + chaos injection. Already in HACK.md.
- **Revenue:** Risk reduction (fewer cascade failures).

### 3. Homeowner Receipt
- **What:** Plain-language explanation of why a battery moved. Builds trust.
- **User:** Homeowner, Base support.
- **Metric:** Churn reduction (measure in follow-on), support ticket deflation.
- **Effort:** Template + structured fields from sim.
- **Revenue:** Retention uplift (~$X per home over lifetime).

---

## Tier 2: Forecasting + Demand Response (Hackathon Sprint + Week 1)

Smart positioning. These unlock the next revenue layer.

### 4. Price Forecast + Anticipatory Dispatch
- **What:** Predict ERCOT LMP 4–8h ahead. Position fleet now to capture predicted spikes.
- **User:** Markets team (better timing), VPP operator (risk reduction).
- **Metric:** $ uplift vs reactive dispatch (10–25% expected).
- **Effort:** Model (ARIMA or simple linear trend) + dispatch logic. ~6h.
- **Revenue:** Direct; $X per home per month.
- **Dependencies:** ERCOT forecast API (or 1-day lookback model).

### 5. Demand Response (Sell Not-Charging)
- **What:** Instead of "when to discharge," offer "when to avoid charging" to grid. Flip revenue model.
- **User:** Markets (new product), grid operator (preferred).
- **Metric:** Revenue per MWh avoided vs discharge revenue. Likely 20–50% lower but less degradation.
- **Effort:** Invert dispatch logic + accounting. ~4h.
- **Revenue:** Complementary stream (~$X per home, lower volatility).
- **Dependencies:** Grid program partnerships.

---

## Tier 3: Grid Partnership + Stacking (Hackathon + Week 2)

Revenue multiplication through coordination.

### 6. Frequency Response Integration
- **What:** Overlay frequency response opportunities (ERCOT publishes freq every 4s). Batteries can participate even at mid-SoC.
- **User:** Markets (new market), grid ops.
- **Metric:** Revenue per MWh (lower $/MWh but higher deployment %). Stacking with price dispatch.
- **Effort:** Frequency data fetch + slot conflict logic. ~4h.
- **Revenue:** $Y per home per month (lower than energy arb, higher utilization).
- **Dependencies:** ERCOT frequency API.

### 7. Carbon-Aware Dispatch
- **What:** Weight discharge decisions by grid fuel mix. Discharge when coal is on margin, charge during wind/solar.
- **User:** Homeowner (carbon story), Base (ESG/marketing).
- **Metric:** MWh marginal coal avoided. ESG scorecard.
- **Effort:** Fuel mix data + weighting. ~3h.
- **Revenue:** Indirect (brand story + premium marketing).
- **Dependencies:** ERCOT fuel mix feed.

### 8. Grid Health Awareness
- **What:** Real-time grid stress signals (congestion, voltage, frequency volatility). Dispatch when grid needs help.
- **User:** Operator (grid stability), homeowner (contributing to reliability).
- **Metric:** Grid stability score (voltage deviation, frequency excursions prevented). $ value of grid services.
- **Effort:** Stress metric aggregation + dispatch weighting. ~4h.
- **Revenue:** Potential grid service contracts (regulatory + utility partnerships).
- **Dependencies:** ERCOT congestion map API.

### 9. Revenue Stacking (Product Layer)
- **What:** UI/logic to identify which revenue streams (energy arb, freq response, demand response, grid services) a battery should pursue. Optimization layer.
- **User:** Operator (maximum ROI), markets analyst.
- **Metric:** Total revenue per home. Utilization of available stacking opportunities.
- **Effort:** Conflict detection + ranking algorithm. ~5h.
- **Revenue:** Multiplier effect (10–30% uplift from optimal stacking).
- **Dependencies:** All revenue stream implementations above.

---

## Tier 4: Degradation + Engagement (Hackathon + Week 3)

Longevity + retention.

### 10. Battery Health Optimization
- **What:** Track degradation (Ah fade, calendar aging). Dispatch policy that trades off $ now vs battery longevity (health-aware vs money-max).
- **User:** Homeowner (warranty), Base (fleet lifespan).
- **Metric:** Years of battery life remaining + cumulative $ loss from degradation (NPV).
- **Effort:** Aging model + two-policy benchmark. ~4h.
- **Revenue:** Warranty extension upsell; longevity story.
- **Dependencies:** Battery degradation curves (LFP typical).

### 11. Homeowner Engagement Dashboard
- **What:** Real-time visibility into $ saved, carbon avoided, grid helped, neighborhood leaderboard. One-click "let Base optimize" vs manual mode.
- **User:** Homeowner (retention + transparency), Base (engagement metrics).
- **Metric:** Engagement score, churn reduction, opt-in rate for smart dispatch.
- **Effort:** Frontend + real-time data pipe. ~6h.
- **Revenue:** Retention + upsell (people who see $ stay).
- **Dependencies:** API for homeowner view.

---

## Stretch (Post-Hackathon)

### 12. Weather-Driven Positioning
- **What:** Predict fuel mix shift (NOAA wind forecast + cloud cover). Position for coming price regime.
- **Effort:** ~3h (complement to forecast).
- **Impact:** 5–10% uplift on forecast accuracy.

### 13. Peer Lending Under Failure
- **What:** Neighbor lending (credit-based trades within a neighborhood microgrid).
- **Effort:** ~8h (graph + settlement logic).
- **Impact:** Reduces "partial fleet" revenue loss by 15–20%.

### 14. Nash Equilibrium / Congestion Pricing
- **What:** Internal virtual price to prevent all batteries discharging at once.
- **Effort:** ~5h (congestion model + economic dispatch).
- **Impact:** Stability + revenue predictability.

---

## Success Metrics (Overall)

| Metric | Hackathon | Week 1 | Month 1 | Month 3 |
|--------|-----------|--------|---------|---------|
| **WattGap $ (vs naive, per home/mo)** | +$8–12 | +$12–18 | +$18–30 | +$30–50 |
| **Fleet alive (% uptime)** | 98%+ | 98%+ | 99%+ | 99%+ |
| **Forecast accuracy (MAE)** | — | 15% | 10% | 8% |
| **Revenue stacking ratio** | 1.0 | 1.2 | 1.5 | 1.8 |
| **Churn rate** | — | <2%/mo | <1.5%/mo | <1%/mo |
| **Carbon avoided (kg CO2/home/yr)** | — | 500 | 2000 | 5000 |

---

## Dependencies & Blocking Issues

1. **ERCOT data access:** LMP (we have), forecast (API key?), frequency (real-time feed?), fuel mix (public CSV).
2. **Base internal:** Fleet API (simulator OK for now), homeowner notification channel.
3. **Regulatory:** Demand response + frequency response require ERCOT/utility agreements (post-hackathon).

---

## Phasing (Post-Hackathon)

**Phase 0 (Week 1):** Price + forecast + receipt. Launch to 100 homes. Measure $ uplift + churn.  
**Phase 1 (Month 1):** Add demand response + carbon. Expand to 1k homes. Secondary revenue stream.  
**Phase 2 (Month 2–3):** Frequency + grid health + stacking UI. 5k homes. Multi-stream revenue model.  
**Phase 3 (Month 4–6):** Degradation model + engagement dashboard. 50k homes. Retention focus.  
**Phase 4 (Month 6+):** Peer lending, weather, Nash. Scale to full Base footprint.

---

## Commercialization (Who Buys)

| Layer | Buyer | Price Model | Addressable |
|-------|-------|-------------|------------|
| **Price-aware dispatch** | Base VPP ops | % of arbitrage uplift (20% cut) | Existing fleet |
| **Forecast** | Markets team | Flat fee or $/MWh | Internal |
| **Demand response** | Grid operator | $/MW capacity | New program |
| **Frequency response** | ERCOT/utility | $/MWh | New market |
| **Carbon** | Marketing + ESG | Brand premium | Existing + new |
| **Engagement dashboard** | Homeowner | Included (retention) | Existing |

**Year 1 Revenue Projection:** $X per home * Y homes * 12mo (conservative: $8–15/home/mo).

---

## Exec Summary

We're building the "tiered optimization engine" for home-battery VPPs. Tier 1 (price-aware) ships this weekend. Tier 2 (forecast + demand response) launches Week 1. Tiers 3–4 stack $50+/home/month by Month 3, unlocking the retention + growth story for Base's home-battery business.

**Hackathon demo:** 11 dispatch policies side-by-side. One UI showing the roadmap.

**Post-hackathon focus:** Forecast accuracy + demand response partnerships.

