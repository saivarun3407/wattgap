# WattGap Strategy: From Hackathon to $X/Home/Month

**Lenny Rachitsky-style product strategy for the 11-layer revenue platform.**

---

## One Sentence

WattGap finds the home-battery fleet revenue Base leaves on the table through 11 stacked dispatch policies, starting with price arbitrage and layering on forecast, demand response, grid services, carbon, and homeowner engagement—resulting in $30–50+ revenue per home per month by Month 3.

---

## Problem

**Base's bottleneck:** Batteries are dumb. Charge overnight, hold during day. ERCOT reprices every 5 minutes; Base's policy reprices every... never.

**The gap:** On spike days, the fleet leaves $3–8 per home on the table by not dispatching optimally. Scale to 50k homes = $150–400k left on table per spike day.

**Why this matters:** Home batteries are commoditizing (falling prices). Revenue per unit is the differentiator. Without dispatch optimization, home batteries become a low-margin product.

---

## Solution Overview

Build a **modular dispatch engine** that:

1. **Starts simple:** Price-aware arbitrage (charge cheap, discharge expensive).
2. **Adds visibility:** Homeowner receipts so they understand (and stay).
3. **Stacks revenue:** Layer in forecast, demand response, frequency response, grid services, carbon.
4. **Optimizes:** Automatically select which revenue stream per battery per interval to maximize total $.
5. **Preserves hardware:** Trade off short-term $ for battery longevity (health-aware dispatch).
6. **Engages users:** Real-time dashboard showing $ earned, carbon saved, grid helped, neighborhood leaderboard.

**Philosophy:** All policies run in parallel on the same simulator. One UI shows the trade-offs. Operator (or algorithm) picks the best strategy.

---

## Product Strategy (Post-Hackathon)

### Phase 0: Hackathon (This Weekend)

**Goal:** Prove the concept. Show 11 dispatch policies running side-by-side. Demonstrate stacking revenue multiplier.

**Shipping:**
- Python sim with 11 pluggable dispatch policies.
- Comparison table ($ revenue, MWh moved, CO2 saved, grid helped, battery health %).
- Chaos demo (kill 30%, watch rebalance).
- Homeowner receipt generation.
- Engineering roadmap for 6–12mo.

**Outcome:** Judges see "this is the foundation. We've proven the tech. Now we just scale the revenue layers."

---

### Phase 1: MVP Launch (Week 1–2)

**Goal:** Get 100 homes on Price-Aware + Forecast. Measure $ uplift + churn impact.

**Shipping:**
- Live ERCOT API integration (replace CSV).
- Real Base fleet data (replace simulator).
- Price-Aware dispatch in production (already built, just integrate).
- Forecast model live (trade accuracy for speed; fine-tune later).
- Homeowner receipt email.
- Retention dashboard (simple: today's $, month-to-date $, recent events).

**Success metrics:**
- $12–18/home/month average revenue (vs baseline $8–12).
- Churn < 2%/month (vs typical HVAC 1–2%, we're tracking same or better).
- Forecast accuracy 15% MAE (good enough for dispatch).

**Revenue:** 100 homes * $15/home/month * 20% cut = $300/month for Base.

---

### Phase 2: Revenue Stacking (Month 2–3)

**Goal:** Layer in 3 more revenue streams. Expand to 5k homes. Hit $30–40/home/month.

**Shipping:**
- Demand Response policy + utility partnerships (ERCOT or local utility demand response program).
- Frequency Response policy + ERCOT ancillary services integration.
- Carbon-Aware Dispatch (ESG marketing story).
- Revenue Stacking UI (which policy when? conflict resolution).

**Success metrics:**
- $30–40/home/month (3–4x baseline).
- Stacking uplift measurable (10–30% above energy arb alone).
- Three revenue streams active in production.

**Revenue:** 5k homes * $35/home/month * 20% cut = $35k/month for Base.

---

### Phase 3: Engagement & Retention (Month 4–6)

**Goal:** Full homeowner experience. Expand to 50k homes. Hit $45–50/home/month through engagement.

**Shipping:**
- Real-time engagement dashboard (mobile + web).
- Neighborhood leaderboard (gamification).
- Monthly digest emails ($X earned, Y kg CO2, Z grid events).
- SMS alerts on big earning events.
- Referral program (invite a neighbor, both get $X).
- Battery health optimization (trade short-term $ for longevity).

**Success metrics:**
- Churn < 1%/month (half of baseline; people who see the dashboard stay).
- Engagement score up 50% (daily active users, time on app).
- $45–50/home/month (hardware degradation offset by stacking).
- 50k homes on platform.

**Revenue:** 50k homes * $47/home/month * 20% cut = $470k/month for Base.

---

## Unit Economics (Conservative)

| Metric | Value |
|--------|-------|
| **Addressable:** Base home batteries today | 200–500 homes |
| **Target Year 1:** | 50k homes |
| **Revenue per home (Phase 3):** | $45–50/month |
| **Base's cut (20% of uplift):** | $9–10/month |
| **Implied annual revenue (Phase 3):** | $450–500/month per X homes |
| **Gross margin:** | 85%+ (mostly software, API calls, cloud) |
| **Payback on tech investment:** | <6 months for 50k homes |

---

## Competitive Moats

1. **Data ownership:** We see 50k homes' worth of dispatch + grid feedback. Others don't.
2. **Stacking algorithm:** No one else does revenue stacking (optimize which service when).
3. **Retention:** Homeowners who see $ daily stay longer (our dashboard is a moat).
4. **Partnerships:** Utilities trust us because we improve their grid (frequency, demand response).

---

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| **ERCOT API limits or unavailability** | Build 1-day lookback model; graceful degradation to CSV. |
| **Forecast accuracy misses spikes** | Start with conservative thresholds; measure MAE weekly. Tune aggressively. |
| **Homeowners reject stacking (complexity)** | Offer "autopilot" button; auto-selects best policy. One-click. |
| **Utility demand response program doesn't scale** | Direct-to-homeowner revenue model (they keep 80%, Base keeps 20%). Less regulatory friction. |
| **Battery degradation cost hurts retention** | Health-aware dispatch as upsell (warranty extension for 20% $ cut). |

---

## Organization & Ownership

### Roles

| Role | Responsibilities |
|------|------------------|
| **Product Lead** | Roadmap prioritization, metrics targets, user narrative. |
| **Eng Lead** | Technical phasing, API integrations, ship readiness. |
| **Markets Lead** | Revenue stream definition, utility partnerships, $/MWh pricing. |
| **Growth Lead** | Homeowner engagement, churn analysis, referral program. |

### Cadence

- **Weekly check-ins:** Revenue KPIs, churn, forecast accuracy, dispatch errors.
- **Bi-weekly planning:** Next sprint priorities, cut vs stretch.
- **Monthly reviews:** Business review (ARR, CAC, LTV, net retention), product review (features shipped, tech debt).

---

## Measures of Success

### Hackathon (Sunday 23:59)

- [ ] All 11 policies run without error.
- [ ] Comparison table shows stacking uplift (>10%).
- [ ] Chaos demo completes (kill 30%, rebalance).
- [ ] Homeowner receipt is readable and accurate.
- [ ] Demo takes < 5 minutes.
- [ ] Judges say, "That's the foundation for scaling home-battery revenue."

### Phase 1 (Week 2)

- [ ] 100 homes on price-aware dispatch in production.
- [ ] Forecast MAE < 20%.
- [ ] Revenue $15/home/month average.
- [ ] Churn < 2%/month.

### Phase 3 (Month 6)

- [ ] 50k homes active.
- [ ] Revenue $45–50/home/month.
- [ ] Churn < 1%/month.
- [ ] ARR for Base: $450–500k/month from WattGap.

---

## Narrative for Investors / Judges

> We built a dispatch engine that finds the money batteries leave on the table. Starting with price arbitrage ($8–12/home/month), we layer in forecast, demand response, frequency response, and grid services. By Month 3, batteries earn $45–50/month through stacked revenue streams. Homeowners see their $ daily, so they stay (1% churn vs 2%+ industry average). The platform is modular (add a policy in an afternoon), and we own the data from 50k homes, so no competitor can copy us. This is how home batteries stop being a commodity and start being a revenue engine.

---

## Next Steps

1. **Hackathon (48h):** Build and ship 11 policies.
2. **Week 1:** Cherry-pick price-aware + forecast for MVP launch (100 homes).
3. **Week 2–4:** Measure, tune, prepare for Phase 2.
4. **Month 2:** Layer in demand response + frequency.
5. **Month 3:** Full engagement + stacking.
6. **Month 6:** Reach 50k homes, hit $500k/month.

**Ownership:** You (CEO) own the roadmap. Eng lead owns 48h sprint. Markets lead owns partnership hunt (ERCOT, utilities). Growth lead owns retention + engagement.

---

## Files in This Repo

- **ROADMAP.md** — Product roadmap (Tier 1–4, success metrics, dependencies).
- **ENGINEERING.md** — Engineering task breakdown (48h phasing, resource allocation, cut priorities).
- **prds/** — 11 individual PRDs (problem, solution, metrics, engineering tasks for each feature).
- **sim/** — Python simulator (core, all policies).
- **README.md** — Quick start.

---

## TL;DR

**This weekend:** Build 11 dispatch policies, show stacking revenue 2–5x. 

**Month 1:** Launch 2 policies to 100 homes, measure $15–18/home/month.

**Month 6:** 50k homes, $45–50/home/month, churn <1%/month, ARR $500k/month for Base.

