# GitHub Issues Tracker Template

**Copy these into GitHub Issues to track the 48h hackathon sprint.**

---

## Epic: WattGap 11-Layer Dispatch Platform

**Label:** `hackathon` `epic`  
**Milestone:** Hackathon 2026-09-27  
**Description:** Build and ship 11 dispatch policies + stacking optimization layer for home-battery revenue optimization.

---

## Phase 1: Core Sim Engine (Hours 0–6)

### Issue: SIM-1 Core Simulator Foundation
**Label:** `sim` `P0` `hackathon`  
**Points:** 5  
**Assigned:** Eng Lead  

**Tasks:**
- [ ] SIM-1.1: ERCOT LMP CSV parser (288 5-min intervals per day)
- [ ] SIM-1.2: Battery simulator (SOC tracking, charge/discharge physics, kW/kWh limits)
- [ ] SIM-1.3: Fleet aggregator (count online, sum kW, identify bottlenecks)
- [ ] SIM-1.4: Telemetry staleness checker (mark offline if data > 5min old)
- [ ] SIM-1.5: Modular dispatch engine (plugin architecture, all 11 policies inherit from base)
- [ ] SIM-1.6: Metrics calculator ($ revenue, MWh moved, kg CO2, grid events, battery health %)
- [ ] SIM-1.7: CLI interface (`python3 sim/run.py --policy [name]`)

**Success Criteria:**
- Single sim engine powers all 11 policies
- Metrics ($ and MWh) are accurate and reproducible
- CLI runs without errors
- Code is modular (adding policy #12 takes < 1h)

**Merge Target:** Before Hour 6

---

## Phase 2: Tier 1 Policies (Hours 6–15)

### Issue: POLICY-1 Price-Aware Dispatch (P0 Hackathon)
**Label:** `policy` `price-arbitrage` `P0` `hackathon`  
**Points:** 3  

**Tasks:**
- [ ] POLICY-1.1: Threshold logic (charge if LMP < p20 of last 24h, discharge if > p80)
- [ ] POLICY-1.2: SoC headroom check (don't over-charge)
- [ ] POLICY-1.3: Test and validate on spike day CSV

**Success Criteria:**
- WattGap $ > 0 on spike day
- Policy matches manual calculation
- Handles offline batteries gracefully

**Merge Target:** Before Hour 12

---

### Issue: ORCH-2 Failure Orchestration + Chaos (P0 Hackathon)
**Label:** `orchestration` `failure-handling` `P0` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] ORCH-2.1: Online/offline state tracking per battery (heartbeat + telemetry freshness)
- [ ] ORCH-2.2: Rebalance logic (scale remaining online units, don't exceed max kW)
- [ ] ORCH-2.3: ALARM condition (available MW < target MW)
- [ ] ORCH-2.4: Chaos injection (`--kill-zone WEST 30` to offline 30% of zone)

**Success Criteria:**
- Kill 30% of fleet, system doesn't crash
- Supervisor correctly calculates available MW
- Rebalance is safe (doesn't over-dispatch any unit)
- ALARM fires when target unmet

**Merge Target:** Before Hour 12

---

### Issue: RECEIPT-3 Homeowner Receipt Generation (P0 Hackathon)
**Label:** `receipts` `trust` `homeowner` `P0` `hackathon`  
**Points:** 2  

**Tasks:**
- [ ] RECEIPT-3.1: Define receipt schema (battery_id, interval, action, prices, kWh, $, reason)
- [ ] RECEIPT-3.2: Emit receipt JSON from dispatch logic
- [ ] RECEIPT-3.3: Plain-text template (facts only, no fluff)
- [ ] RECEIPT-3.4: Handle edge cases (HOLD action, offline battery, partial SoC)

**Success Criteria:**
- Every dispatch event has a receipt
- Receipt is readable by non-technical homeowner
- Facts match sim data
- Can be forwarded by support as proof

**Merge Target:** Before Hour 18

---

## Phase 3: Tier 2 Policies (Hours 15–24)

### Issue: FORECAST-4 Price Forecast + Anticipatory Dispatch
**Label:** `policy` `forecast` `ML` `hackathon`  
**Points:** 5  

**Tasks:**
- [ ] FORECAST-4.1: Load or mock ERCOT forecast (4–8h lookahead)
- [ ] FORECAST-4.2: Simple trend model (linear regression or ARIMA)
- [ ] FORECAST-4.3: Anticipatory dispatch (charge now if forecast shows spike 4h out)
- [ ] FORECAST-4.4: Measure forecast-aware $ uplift
- [ ] FORECAST-4.5: Backtest on 5+ spike days

**Success Criteria:**
- Forecast MAE < 20% (vs ERCOT actual)
- Forecast-aware $ > price-aware $ (by 10%+)
- No false alarms (don't over-charge on quiet days)
- Passes backtest

**Merge Target:** Before Hour 24

---

### Issue: DR-5 Demand Response (Sell Not-Charging)
**Label:** `policy` `demand-response` `hackathon`  
**Points:** 3  

**Tasks:**
- [ ] DR-5.1: Invert dispatch (don't charge during peak hours 16:00–21:00)
- [ ] DR-5.2: Track avoided kWh vs actual charging
- [ ] DR-5.3: Revenue calculation (avoided_kWh * $grid_rate)
- [ ] DR-5.4: Side-by-side comparison (energy arb vs demand response)

**Success Criteria:**
- DR policy runs without error
- Avoided kWh tracked correctly
- $ per MWh avoided is 10–20x less than energy arb (as expected)
- Revenue > $1/home/month

**Merge Target:** Before Hour 24

---

## Phase 4: Tier 3 Policies (Hours 24–32)

### Issue: FREQ-6 Frequency Response Integration
**Label:** `policy` `frequency-response` `grid-services` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] FREQ-6.1: Mock ERCOT frequency feed (or load historical data)
- [ ] FREQ-6.2: Frequency response policy (inject when freq < 59.9 Hz)
- [ ] FREQ-6.3: Conflict detection (don't charge + freq respond simultaneously)
- [ ] FREQ-6.4: Revenue stacking (energy + frequency)

**Success Criteria:**
- Frequency data ingestion works
- Frequency response policy triggers correctly
- Conflict detection prevents double-dispatch
- Stacking uplift is measurable

**Merge Target:** Before Hour 32

---

### Issue: CARBON-7 Carbon-Aware Dispatch
**Label:** `policy` `carbon` `ESG` `hackathon`  
**Points:** 3  

**Tasks:**
- [ ] CARBON-7.1: Mock ERCOT fuel mix feed
- [ ] CARBON-7.2: CO2 factors per fuel type (coal ~0.9, gas ~0.4, wind ~0)
- [ ] CARBON-7.3: Marginal fuel calculator
- [ ] CARBON-7.4: kg CO2 avoided per event
- [ ] CARBON-7.5: Extend receipt with CO2 field

**Success Criteria:**
- Fuel mix data loads correctly
- CO2 factors are reasonable
- CO2 avoided calculated correctly
- Homeowner receipt shows $ + CO2

**Merge Target:** Before Hour 32

---

### Issue: GRID-8 Grid Health Awareness
**Label:** `policy` `grid-services` `stability` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] GRID-8.1: Grid stress score (combine congestion + voltage + frequency)
- [ ] GRID-8.2: Weight dispatch by stress (higher stress = higher priority)
- [ ] GRID-8.3: Track "grid help events" per month
- [ ] GRID-8.4: Revenue potential calculation

**Success Criteria:**
- Grid stress score calculated and reasonable
- Dispatch changes based on grid stress
- Grid services revenue estimated
- Batteries help grid (measurable stability improvement)

**Merge Target:** Before Hour 32

---

## Phase 5: Tier 4 Policies + Stacking (Hours 32–40)

### Issue: STACK-9 Revenue Stacking Optimization
**Label:** `policy` `optimization` `revenue-stacking` `hackathon`  
**Points:** 5  

**Tasks:**
- [ ] STACK-9.1: Conflict matrix (which operations can't run together)
- [ ] STACK-9.2: Ranking algorithm (greedy selection of highest $ opportunity)
- [ ] STACK-9.3: Measure stacking uplift vs single-stream
- [ ] STACK-9.4: Output: "Stacking earned $X vs energy-only $Y (+P%)"

**Success Criteria:**
- Conflict detection is accurate
- Ranking chooses highest value opportunity
- Stacking uplift is measurable (>10%)
- No over-dispatch errors

**Merge Target:** Before Hour 40

---

### Issue: HEALTH-10 Battery Health Optimization
**Label:** `policy` `degradation` `longevity` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] HEALTH-10.1: LFP degradation curve (Ah fade vs cycles)
- [ ] HEALTH-10.2: Money-Max policy (aggressive dispatch)
- [ ] HEALTH-10.3: Health-Max policy (conservative dispatch)
- [ ] HEALTH-10.4: NPV calculation ($ now vs longevity cost)

**Success Criteria:**
- Degradation curves are LFP-accurate
- Two policies execute correctly
- Health-Max produces slower degradation
- NPV trade-off is calculable and meaningful

**Merge Target:** Before Hour 40

---

### Issue: DASH-11 Homeowner Engagement Dashboard (Mockup)
**Label:** `dashboard` `engagement` `UI` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] DASH-11.1: Dashboard mockup ($ today, month, carbon, grid events, rank)
- [ ] DASH-11.2: Mode toggle (Smart vs Manual)
- [ ] DASH-11.3: Recent events list
- [ ] DASH-11.4: Mock leaderboard (rank by $ earned)

**Success Criteria:**
- Dashboard displays accurate $ and carbon data
- Leaderboard is correct (no off-by-one errors)
- Mode toggle changes dispatch behavior
- Real-time updates within 30 seconds

**Merge Target:** Before Hour 40

---

## Phase 6: Integration & Demo (Hours 40–48)

### Issue: INTEGRATION-1 Master Run Script + Comparison UI
**Label:** `integration` `demo` `P0` `hackathon`  
**Points:** 4  

**Tasks:**
- [ ] INTEGRATION-1.1: Master run script (`python3 sim/run.py --all-policies --spike-day ...`)
- [ ] INTEGRATION-1.2: Comparison table (all 11 policies, metrics: $, MWh, CO2, events, health%)
- [ ] INTEGRATION-1.3: HTML report generation (charts, receipts, leaderboard)
- [ ] INTEGRATION-1.4: Chaos demo script (kill 30%, watch rebalance)
- [ ] INTEGRATION-1.5: Documentation ("How to interpret the 11-policy output")
- [ ] INTEGRATION-1.6: Demo walkthrough (3–5 min video script)

**Success Criteria:**
- All 11 policies run in single script
- Comparison is clear and accurate
- HTML report is readable and shareable
- Demo completes in 3–5 minutes
- Judges understand the revenue stacking story

**Merge Target:** Before Hour 47

---

## Stretch Goals (If Ahead of Schedule)

### Issue: WEATHER-W2 Weather-Driven Positioning
**Label:** `stretch` `forecast` `week-2`  
**Points:** 3  

---

### Issue: PEER-W2 Peer Lending Under Failure (Skeleton)
**Label:** `stretch` `orchestration` `week-2`  
**Points:** 5  

---

### Issue: NASH-W2 Nash Equilibrium Proof-of-Concept
**Label:** `stretch` `optimization` `week-2`  
**Points:** 4  

---

## How to Use This

1. **Copy each issue into GitHub Issues.**
2. **Tag with labels:** `hackathon`, `P0`, `sim`, `policy`, `grid-services`, etc.
3. **Assign to team members** (Eng A: sim + forecast, Eng B: policies, Eng C: optimization + integration).
4. **Update progress** as tasks complete (move to Done).
5. **Cut from bottom** if behind schedule (stretch > Tier 4 > Tier 3 > Tier 2, keep Tier 1 + integration).

---

## Acceptance Criteria (Hackathon Complete)

- [ ] All Tier 1 & 2 policies deployed + tested.
- [ ] Comparison UI shows 11 policies side-by-side.
- [ ] Chaos demo works (kill 30% fleet, rebalance safely).
- [ ] Homeowner receipts generated for 100% of events.
- [ ] Demo completes end-to-end in < 5 min.
- [ ] Code is modular (adding policy #12 takes < 1h).
- [ ] Engineering roadmap documented for Weeks 1–12.

---

## Metrics Tracking

| Metric | Target | Owner | Check Interval |
|--------|--------|-------|--------|
| All 11 policies run | ✓ | Eng Lead | Hour 32 |
| WattGap $ > 0 | ✓ | Eng A | Hour 8 |
| Forecast accuracy (MAE) | < 20% | Eng A | Hour 20 |
| Stacking uplift | > 10% | Eng C | Hour 36 |
| Chaos resilience (30% kill) | 100% safe rebalance | Eng B | Hour 28 |
| Demo runtime | < 5 min | All | Hour 44 |

