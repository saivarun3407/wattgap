# PRD: Homeowner Engagement Dashboard

**Status:** Hackathon + Week 3 | **Effort:** 6h | **Revenue:** Retention + engagement upsell

---

## Problem

Homeowner gets monthly bill: "Core earned $42 this month." No visibility into *why*, *when*, or *how much it helped*.

**Gap:** Passive experience → low engagement. Homeowner doesn't know they're making $. They might churn.

---

## Solution

1. **Real-time dashboard:** $ earned today, carbon saved, grid helped, neighborhood rank.
2. **Leaderboard:** "Your neighborhood saved $X this month" (gamification).
3. **One-click smart dispatch:** "Let Base optimize" vs manual mode.
4. **Notifications:** "Big earning event happened right now: +$3.42" (SMS/email).

---

## MVP (Hackathon)

- [ ] Simple dashboard showing:
  - Today's $: $X earned so far
  - Month to date: $Y earned
  - Carbon avoided: Z kg CO2
  - Grid events: N times helped
  - Neighborhood rank: Xth out of 500 homes
- [ ] Mode toggle: "Smart (Base optimizes)" vs "Manual (I set the schedule)".
- [ ] Recent events list (last 5 dispatch decisions).

**Output:**
```
┌─────────────────────────────────────┐
│ Your Core (Houston)                 │
├─────────────────────────────────────┤
│ Today's earnings:     $2.14         │
│ This month:           $47.82        │
│ Carbon avoided:       224 kg CO2    │
│ Grid events:          12 times      │
│ Neighborhood rank:    #47 / 500     │
│                                     │
│ [Smart Dispatch ✓] [Manual    ]     │
├─────────────────────────────────────┤
│ Recent events:                      │
│ 16:10 Discharged 8.2kWh → +$3.38   │
│ 15:45 Charged during wind peak      │
│ ...                                 │
└─────────────────────────────────────┘
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Dashboard loads and updates in real-time | ✓ |
| $ earned is accurate | ✓ |
| Leaderboard works (no ties or off-by-one) | ✓ |
| Mode toggle executes correctly | ✓ |
| Recent events show correct decisions | ✓ |

---

## Stretch (Week 4)

- [ ] Mobile app (iOS/Android).
- [ ] Customizable alerts (SMS/email on big earns).
- [ ] Referral program ("Invite a neighbor, both get $5").
- [ ] Monthly digest email ("You earned $48, saved 450 kg CO2").

---

## Revenue Model

**Engagement-driven retention:**
- Homeowners who see the dashboard (active engagement) have 50% lower churn.
- Churn reduction: $X per home over lifetime (2–3 months saved).
- Referral upsell: $X per referred home.

---

## Engineering Tasks

### Frontend
- [ ] **Task 11.1:** React component for dashboard (cards: $, carbon, grid, rank).
- [ ] **Task 11.2:** Real-time data subscription (WebSocket or polling).
- [ ] **Task 11.3:** Mode toggle (Smart vs Manual).
- [ ] **Task 11.4:** Recent events list.

### Backend
- [ ] **Task 11.5:** API endpoint for homeowner view (auth + billing data).
- [ ] **Task 11.6:** Leaderboard query (rank by $ earned this month).
- [ ] **Task 11.7:** Real-time event feed (dispatch decisions → homeowner updates).

### Notifications
- [ ] **Task 11.8:** Mock SMS/email on big earning events.
- [ ] **Task 11.9:** Monthly digest logic.

---

## Acceptance Criteria

1. Dashboard displays accurate $ and carbon data.
2. Leaderboard is correct (no off-by-one errors).
3. Mode toggle changes dispatch behavior.
4. Real-time updates within 30 seconds.
5. Homeowner engagement increases (mock metrics for hackathon).

---

## Dependencies

- Homeowner Receipt (event data).
- Carbon-Aware Dispatch (carbon metric).
- All dispatch policies (for leaderboard).

---

## Owner & DRI

- **Product:** Growth + retention (engagement KPIs).
- **Eng:** Frontend + API owner.

