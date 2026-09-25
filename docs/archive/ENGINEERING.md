> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# Engineering Roadmap: WattGap 11-Layer Platform

**Consolidated task list.** All 11 features broken into small engineering blocks. Phased by hackathon priority + week 1–3 follow-up.

---

## 48h Hackathon Sprint

**Goal:** Ship 11 policies side-by-side, prove stacking, demo revenue multiplier.

### Phase 1: Core Sim Engine (Hours 0–6)

Foundation for all policies. Build once, reuse 11x.

- [ ] **SIM-1.1:** ERCOT LMP CSV parser (288 5-min intervals).
- [ ] **SIM-1.2:** Battery simulator (SOC tracking, charge/discharge physics).
- [ ] **SIM-1.3:** Fleet aggregator (count online, sum kW, identify bottlenecks).
- [ ] **SIM-1.4:** Telemetry staleness checker (mark offline if data > 5min old).
- [ ] **SIM-1.5:** Modular dispatch engine (plugin architecture, all policies inherit from base).
- [ ] **SIM-1.6:** Metrics calculator ($ revenue, MWh moved, kg CO2, events).
- [ ] **SIM-1.7:** CLI: `python3 sim/run.py --policy [policy_name]`.

**Success:** All 11 policies can be enabled/disabled independently. Single run calculates all metrics.

---

### Phase 2: Tier 1 Policies (Hours 6–15)

P0 hackathon features. Already mostly built; polish + integrate.

#### Policy 1: Price-Aware Dispatch
- [ ] **POLICY-1.1:** Threshold logic (charge < p20, discharge > p80).
- [ ] **POLICY-1.2:** SoC headroom check (don't over-charge).
- [ ] **POLICY-1.3:** Test on spike day CSV.

#### Policy 2: Failure Orchestration
- [ ] **ORCH-2.1:** Online/offline state tracking per battery.
- [ ] **ORCH-2.2:** Rebalance logic (scale remaining units, don't exceed max).
- [ ] **ORCH-2.3:** ALARM condition (available < target).
- [ ] **ORCH-2.4:** Chaos injection: `--kill-zone WEST 30` to offline 30%.

#### Policy 3: Homeowner Receipt
- [ ] **RECEIPT-3.1:** Define receipt schema (battery_id, interval, action, prices, kWh, $).
- [ ] **RECEIPT-3.2:** Emit receipt JSON from dispatch logic.
- [ ] **RECEIPT-3.3:** Plain-text template (facts only).
- [ ] **RECEIPT-3.4:** Attach reason field (price spike, grid stress, forecast).

**Success:** Run all 3 policies, generate receipts, kill 30% of fleet, system survives.

---

### Phase 3: Tier 2 Policies (Hours 15–24)

Add 2 more revenue streams.

#### Policy 4: Price Forecast
- [ ] **FORECAST-4.1:** Load or mock ERCOT forecast (4–8h lookahead).
- [ ] **FORECAST-4.2:** Simple trend model (linear regression or ARIMA).
- [ ] **FORECAST-4.3:** Anticipatory dispatch (charge if forecast spike).
- [ ] **FORECAST-4.4:** Measure forecast-aware $ uplift.
- [ ] **FORECAST-4.5:** Backtest on 5 spike days.

#### Policy 5: Demand Response
- [ ] **DR-5.1:** Invert dispatch (avoid charging during peak).
- [ ] **DR-5.2:** Track avoided kWh.
- [ ] **DR-5.3:** Revenue calculation (avoided_kWh * $grid_rate).
- [ ] **DR-5.4:** Side-by-side comparison (energy arb vs DR).

**Success:** Forecast + DR both run, uplift is measurable (>10%).

---

### Phase 4: Tier 3 Policies (Hours 24–32)

Add 3 more: grid-aligned + carbon + stacking foundation.

#### Policy 6: Frequency Response
- [ ] **FREQ-6.1:** Mock ERCOT frequency feed (or historical).
- [ ] **FREQ-6.2:** Frequency response policy (inject when freq < 59.9 Hz).
- [ ] **FREQ-6.3:** Conflict detection (don't charge + freq response simultaneously).
- [ ] **FREQ-6.4:** Revenue stacking (energy + freq).

#### Policy 7: Carbon-Aware Dispatch
- [ ] **CARBON-7.1:** Mock ERCOT fuel mix feed.
- [ ] **CARBON-7.2:** CO2 factors per fuel (coal ~0.9, gas ~0.4, wind ~0).
- [ ] **CARBON-7.3:** Marginal fuel calculator.
- [ ] **CARBON-7.4:** kg CO2 avoided per event.
- [ ] **CARBON-7.5:** Extend receipt with CO2 field.

#### Policy 8: Grid Health Awareness
- [ ] **GRID-8.1:** Grid stress score (combine congestion + voltage + frequency).
- [ ] **GRID-8.2:** Weight dispatch by stress (higher stress = higher priority).
- [ ] **GRID-8.3:** Measure "grid help events" per month.
- [ ] **GRID-8.4:** Revenue potential calculation.

**Success:** All 8 policies run, can be compared side-by-side.

---

### Phase 5: Tier 4 Policies + Stacking (Hours 32–40)

Completion + optimization layer.

#### Policy 9: Revenue Stacking
- [ ] **STACK-9.1:** Conflict matrix (which ops can't run together).
- [ ] **STACK-9.2:** Ranking algorithm (greedy selection of highest $ opportunity).
- [ ] **STACK-9.3:** Measure stacking uplift vs single-stream.
- [ ] **STACK-9.4:** Output: "Stacking earned $X vs energy-only $Y (+P%)."

#### Policy 10: Battery Health Optimization
- [ ] **HEALTH-10.1:** LFP degradation curve (Ah fade vs cycles).
- [ ] **HEALTH-10.2:** Money-Max policy (aggressive).
- [ ] **HEALTH-10.3:** Health-Max policy (conservative).
- [ ] **HEALTH-10.4:** NPV calculation ($ now vs longevity cost).

#### Policy 11: Homeowner Engagement Dashboard (Mockup)
- [ ] **DASH-11.1:** Dashboard mockup ($ today, month, carbon, grid events, rank).
- [ ] **DASH-11.2:** Mode toggle (Smart vs Manual).
- [ ] **DASH-11.3:** Recent events list.
- [ ] **DASH-11.4:** Mock leaderboard (rank by $ earned).

**Success:** All 11 policies run, UI shows side-by-side comparison, one demo script ties everything together.

---

### Phase 6: Integration & Demo (Hours 40–48)

One script to rule them all.

- [ ] **INTEGRATION-1:** Master run script: `python3 sim/run.py --all-policies --spike-day data/spike_2026_09_15.csv`.
- [ ] **INTEGRATION-2:** Comparison table (all 11 policies, metrics: $, MWh, CO2, events, health%).
- [ ] **INTEGRATION-3:** HTML report (charts, receipts, leaderboard mock).
- [ ] **INTEGRATION-4:** Chaos demo script (kill 30%, watch rebalance).
- [ ] **INTEGRATION-5:** Doc: "How to interpret the 11-policy output."
- [ ] **INTEGRATION-6:** Demo walkthrough (3–5 min video script).

---

## Week 1–3 Follow-up

### Week 1: Polish + API

- [ ] **API-W1-1:** ERCOT forecast API integration (replace mock).
- [ ] **API-W1-2:** Real ERCOT fuel mix feed.
- [ ] **API-W1-3:** Frequency data real-time subscription.
- [ ] **API-W1-4:** Dashboard backend (auth + data API).

### Week 2: Stretch Features

- [ ] **STRETCH-W2-1:** Weather-driven positioning (NOAA wind forecast).
- [ ] **STRETCH-W2-2:** ML forecast model (LSTM on 7-day history).
- [ ] **STRETCH-W2-3:** Peer lending skeleton (graph representation).
- [ ] **STRETCH-W2-4:** Nash equilibrium proof-of-concept.

### Week 3: Engagement

- [ ] **ENGAGEMENT-W3-1:** Mobile dashboard (React Native mockup).
- [ ] **ENGAGEMENT-W3-2:** SMS/email notifications.
- [ ] **ENGAGEMENT-W3-3:** Referral program (database schema).
- [ ] **ENGAGEMENT-W3-4:** Monthly digest email template.

---

## Dependency Graph

```
SIM-1.x (core engine)
  ├─ POLICY-1.x (price-aware)
  │   ├─ ORCH-2.x (failure)
  │   ├─ RECEIPT-3.x (trust)
  │   ├─ FORECAST-4.x (anticipatory) ← requires 4.1 mock data
  │   ├─ DR-5.x (demand response)
  │   ├─ FREQ-6.x (frequency) ← requires 6.1 mock data
  │   ├─ CARBON-7.x (carbon) ← requires 7.1 mock data
  │   ├─ GRID-8.x (grid health) ← requires 8.1 mock data
  │   └─ STACK-9.x (revenue optimization) ← depends on 4–8
  ├─ HEALTH-10.x (battery aging)
  └─ DASH-11.x (engagement UI) ← mock, depends on all policies

INTEGRATION-1–6 (master script) ← depends on all policies
```

---

## Resource Allocation (Hackathon)

**Target:** 3 engineers, 48 hours.

| Person | Hours 0–12 | Hours 12–24 | Hours 24–36 | Hours 36–48 |
|--------|-----------|-----------|-----------|-----------|
| **Eng A (Sim)** | SIM-1.x | POLICY-1.x + ORCH-2.x | FORECAST-4.x + FREQ-6.x | INTEGRATION |
| **Eng B (Policies)** | SIM-1.x | RECEIPT-3.x + DR-5.x | CARBON-7.x + GRID-8.x | DASH-11.x |
| **Eng C (Optimization)** | SIM-1.x | STACK-9.x | HEALTH-10.x | Integration + docs |

---

## Branching Strategy

```
main (prod)
├─ sim-core (SIM-1.x) → merge before hour 6
├─ policies/price-aware (POLICY-1.x) → merge before hour 12
├─ policies/failure (ORCH-2.x) → merge before hour 12
├─ policies/receipt (RECEIPT-3.x) → merge before hour 18
├─ policies/forecast (FORECAST-4.x) → merge before hour 24
├─ policies/demand-response (DR-5.x) → merge before hour 24
├─ policies/frequency (FREQ-6.x) → merge before hour 32
├─ policies/carbon (CARBON-7.x) → merge before hour 32
├─ policies/grid-health (GRID-8.x) → merge before hour 32
├─ policies/stacking (STACK-9.x) → merge before hour 32
├─ policies/health (HEALTH-10.x) → merge before hour 40
├─ policies/dashboard (DASH-11.x) → merge before hour 40
└─ integration/demo (INTEGRATION-1–6) → merge at hour 47
```

---

## Acceptance Criteria (Hackathon)

1. **All 11 policies run independently** without errors.
2. **Metrics are accurate:** $ matches hand-calc, MWh sums correctly, CO2 is sensible.
3. **Chaos works:** Kill 30% of fleet, system rebalances or alarms safely.
4. **Demo completes in 3–5 minutes** (replay spike day → show all 11 policies → kill chaos → show receipts).
5. **Code is modular:** Adding policy #12 takes < 1h.

---

## Cut Priorities (If Behind)

If sprint falls behind:

1. **Must ship:** SIM-1.x, POLICY-1.x, ORCH-2.x, RECEIPT-3.x, STACK-9.x, INTEGRATION.
2. **Nice to have:** FORECAST-4.x, HEALTH-10.x, DASH-11.x.
3. **Stretch:** DR-5.x, FREQ-6.x, CARBON-7.x, GRID-8.x.

Worst case: 6 policies (1–3 + stacking) run and compared. Still wins "most commercializable" + "orchestration" tracks.

