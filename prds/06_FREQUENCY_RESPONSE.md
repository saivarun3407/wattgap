# PRD: Frequency Response Integration

**Status:** Hackathon + Week 2 | **Effort:** 4h | **Revenue:** $X/home/month (stacking)

---

## Problem

ERCOT maintains grid frequency at 60 Hz. When frequency drops (high load, low generation), batteries can provide "frequency support" by injecting power. This is a separate revenue stream from energy arbitrage.

**Gap:** Batteries could participate in both energy markets AND frequency response, but we don't coordinate the two.

---

## Solution

1. **Ingest ERCOT frequency data** (published every 4 seconds).
2. **Score frequency response opportunities** alongside price opportunities.
3. **Manage slot conflicts:** Battery can't discharge for price *and* frequency simultaneously.
4. **Calculate revenue:** Stack frequency revenue on top of energy revenue.

**Hypothesis:** Stacking adds 5–15% to total revenue.

---

## MVP (Hackathon + Week 2)

- [ ] Mock ERCOT frequency feed (or use historical data).
- [ ] Frequency response policy: "If freq < 59.9 Hz, inject up to 5 kW for 10 min."
- [ ] Track revenue: $/MWh for frequency support (~$50/MWh typical).
- [ ] Conflict detection: Don't dispatch same battery for price + freq simultaneously.
- [ ] Measure: Energy-only $ vs Energy+Freq $ (stacking uplift).

**Output:**
```
Policy: Energy Arb only       → $584
Policy: Energy + Freq response → $648 (+11%)

Freq events: 3 per day
Avg freq support: 0.2 MW * 10 min = 0.033 MWh
Freq revenue: 0.033 * $50 = $1.65/event
Monthly (12 events): $19.80
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Frequency data ingestion works | ✓ |
| Frequency response policy triggers correctly | ✓ |
| Conflict detection prevents double-dispatch | ✓ |
| Stacking uplift is measurable | ✓ |

---

## Stretch (Week 3)

- [ ] ERCOT ancillary service market API integration.
- [ ] ML model to predict frequency drops (proactive positioning).
- [ ] Real-time revenue forecasting per service.

---

## Revenue Model

**Unit economics:**
- $50/MWh for frequency response (lower than energy arb).
- 3 events/day * 0.033 MWh * $50 = $4.95/home/month.
- Stacking: Total $ = energy + freq (not zero-sum).

---

## Engineering Tasks

### Data
- [ ] **Task 6.1:** Mock ERCOT frequency feed or load historical.
- [ ] **Task 6.2:** Parse frequency at 4-second intervals.

### Policy
- [ ] **Task 6.3:** Frequency response policy (inject when freq drops).
- [ ] **Task 6.4:** Conflict detection (don't charge + freq response at same time).

### Revenue
- [ ] **Task 6.5:** Calculate frequency support revenue.
- [ ] **Task 6.6:** Combine energy + frequency revenue.

---

## Acceptance Criteria

1. Frequency data flows correctly.
2. Frequency response policy triggers on drops.
3. No double-dispatch conflicts.
4. Revenue stacking shows uplift.

---

## Dependencies

- Price-Aware Dispatch.
- Failure Orchestration (handles scarcity).

---

## Owner & DRI

- **Product:** Markets (new ancillary service revenue).
- **Eng:** Dispatch + conflict management owner.

