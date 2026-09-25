> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../../README.md) and [PROJECT.md](../../../PROJECT.md) for what is real.

# PRD: Homeowner Receipt

**Status:** Hackathon P0 | **Effort:** 2h | **Revenue:** Retention (churn reduction)

---

## Problem

Homeowner sees: "Core discharged 8.2 kWh yesterday. Got $3.38."  
Homeowner thinks: "Why? Did something go wrong? Why not more?"

**Gap:** Without a receipt, homeowners don't understand the *why*. This erodes trust and drives support tickets. Churn risk.

---

## Solution

Generate a **plain-language receipt** for each dispatch event:

> Your Core in Houston discharged 8.2 kWh (16:10–16:25) because LZ_HOUSTON was $412/MWh (spike vs baseline $120/MWh) and system wind dropped 3 GW. Naive overnight policy would have been HOLD ($0). Estimated credit: $3.38.

Facts: price, zone, fuel mix change, grid stress, policy comparison, $ value. No BS, no LLM theater.

---

## MVP (Hackathon)

- [ ] Template: `Receipt(battery_id, interval, action, LMP, baseline_price, reason, kWh, $, naive_action, naive_$)`.
- [ ] Populate from structured fields in sim output.
- [ ] Render as plain text (Email-friendly).
- [ ] Handle edge cases: partial SoC, HOLD (no discharge), offline battery.

**Output:**
```
RECEIPT: Core #1234 | 2026-09-15 16:10–16:25

ACTION:        Discharge 8.2 kWh
REASON:        LMP spike + wind drop
PRICE:         $412/MWh (p95 of day)
BASELINE:      $120/MWh (typical for this hour)
GRID STRESS:   Wind 3 GW drop in LZ_HOUSTON
CREDIT:        $3.38

COMPARISON (naive overnight policy): HOLD ($0)
DIFFERENCE:    +$3.38 vs doing nothing

---
Questions? Contact Base Support.
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Receipt generated for every dispatch event | ✓ |
| Facts are accurate vs sim data | ✓ |
| Readable in plain English | ✓ |
| Support can forward as evidence | ✓ |

---

## Stretch (Week 1)

- [ ] HTML version for web dashboard.
- [ ] Per-month digest ("You earned $47 this month, saved X kg CO2, helped grid Y times").
- [ ] Homeowner notification (email/SMS when big earning event).

---

## Revenue Model

**Retention impact:**
- Reduces churn from "why did my battery do that?" → support ticket → unhappy customer.
- Estimated churn reduction: 5–10% (homeowners who see receipts stay 3mo longer).
- Lifetime value uplift: $X per home (5–10 months extension * ARPU).

---

## Engineering Tasks

### Data & Template
- [ ] **Task 3.1:** Define receipt schema (battery_id, interval, action, prices, reason, kWh, $, naive_comparator).
- [ ] **Task 3.2:** Emit receipt JSON from dispatch logic (structured output).

### Rendering
- [ ] **Task 3.3:** Plain-text template (facts only, no fluff).
- [ ] **Task 3.4:** Handle edge cases (HOLD, offline, partial SoC).

### Integration
- [ ] **Task 3.5:** Attach receipt to homeowner notification (mock email).
- [ ] **Task 3.6:** Verify receipt facts match sim data.

---

## Acceptance Criteria

1. Every dispatch event has a receipt.
2. Receipt contains facts (price, reason, grid stress, naive comparison).
3. Readable by non-technical homeowner.
4. Can be forwarded by support as proof.

---

## Dependencies

- Price-Aware Dispatch (provides dispatch facts).
- Failure Orchestration (provides rebalance context).

---

## Owner & DRI

- **Product:** Customer ops (defines trust narrative).
- **Eng:** Data/export owner.

