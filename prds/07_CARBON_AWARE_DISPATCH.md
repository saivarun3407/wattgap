# PRD: Carbon-Aware Dispatch

**Status:** Hackathon + Week 2 | **Effort:** 3h | **Revenue:** Indirect (brand + ESG marketing)

---

## Problem

Batteries today optimize for price. But the grid's fuel mix changes every 5 minutes. When coal is on the margin, discharging helps avoid coal. When wind is abundant, charging is cleaner.

**Gap:** Ignoring fuel mix means we could be "discharging from coal, charging from wind" — the carbon story is backwards.

---

## Solution

1. **Ingest ERCOT fuel mix feed** (% coal, gas, wind, solar per 5 min).
2. **Weight discharge decisions by marginal fuel.** Score = price * (1 - carbon_reduction).
3. **Market to homeowners:** "You saved X kg CO2 this month" (alongside $).
4. **ESG scorecard:** Base fleet avoided Y tons CO2 annually.

**Output:** "$ + carbon avoided" combined metric for homeowners.

---

## MVP (Hackathon)

- [ ] Mock ERCOT fuel mix feed.
- [ ] Calculate marginal fuel (which fuel is on the edge when you discharge?).
- [ ] CO2 factor: kg CO2 per MWh by fuel type.
- [ ] Measure: kWh * CO2_factor = kg CO2 avoided per event.
- [ ] Report: "You earned $3.38 and avoided 4.2 kg CO2."

**Output:**
```
Event: Discharge 8.2 kWh
Price: $3.38
Marginal fuel: Coal (60% of dispatch causes coal to back down)
CO2 avoided: 8.2 kWh * 0.9 kg CO2/kWh = 7.38 kg CO2
Homeowner message: "$3.38 + 7.38 kg CO2"
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Fuel mix data loaded correctly | ✓ |
| CO2 factors are reasonable (coal ~0.9, gas ~0.4, wind ~0) | ✓ |
| CO2 avoided calculated correctly | ✓ |
| Homeowner can see carbon impact | ✓ |

---

## Stretch (Week 3)

- [ ] Real ERCOT generation mix API.
- [ ] Carbon pricing ($X per ton CO2) to monetize ESG.
- [ ] Homeowner dashboard showing monthly CO2 savings.

---

## Revenue Model

**Indirect revenue:**
- Premium positioning: "Green battery company" → higher price or retention.
- ESG marketing: "Base homes avoided X tons CO2" (B2B story).
- Estimated uplift: 2–5% premium or retention gain (~$X per home/year).

---

## Engineering Tasks

### Data
- [ ] **Task 7.1:** Mock or fetch ERCOT fuel mix feed.
- [ ] **Task 7.2:** CO2 factors per fuel type (reference EPA / EIA).

### Calculation
- [ ] **Task 7.3:** Marginal fuel scorer (which fuel backs down on discharge?).
- [ ] **Task 7.4:** CO2 avoided calculation (kWh * CO2_factor).

### Reporting
- [ ] **Task 7.5:** Combine $ + CO2 in homeowner receipt.
- [ ] **Task 7.6:** Monthly/annual CO2 digest.

---

## Acceptance Criteria

1. Fuel mix data flows.
2. CO2 factors are accurate.
3. CO2 avoided metric makes sense.
4. Homeowner sees $ + carbon in receipt.

---

## Dependencies

- Homeowner Receipt (extend with CO2 field).

---

## Owner & DRI

- **Product:** Marketing (ESG story) + sustainability.
- **Eng:** Data + reporting owner.

