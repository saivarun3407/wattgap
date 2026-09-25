> **Archived, pre-event planning (Sep 23, 2026). Not a description of the shipped code.** Dollar figures, uplift percentages and claims about Base here were never computed or verified. See [README](../../README.md) and [PROJECT.md](../../PROJECT.md) for what is real.

# Other ideas (keep Nodal unless this list beats it)

Use this file to argue. Default remains [NODAL.md](./NODAL.md).

---

## Open Grid Data only (dashboards — easy to lose)

| Idea | Why it might work | Why it loses |
|---|---|---|
| Live ERCOT “weather” for prices | Pretty | They’ve seen 20 |
| Outage + LMP join (“this county is dark *and* expensive”) | Story | Weak orchestration |
| Duck-curve explainer for civilians | Cute | Not their job |
| Congestion heatmap | Real | Hard to finish; needs constraints data |

Promote to Nodal **inputs**, not standalone.

---

## Orchestration only (infra — easy to look generic)

| Idea | Why it might work | Why it loses |
|---|---|---|
| Job queue with retries for “install tickets” | Maps to “can’t Ctrl-Z a truck” | Needs fake ops data; less grid-native |
| Agent swarm that “manages a factory line” | They write factory software | Vague; not ERCOT |
| Kubernetes-for-batteries metaphor | Talk track | Zero product |

If you build install-ticket orchestration, **tie it to a battery that cannot dispatch until the ticket is closed.** Then it becomes a Nodal sibling.

---

## Commercializable only (product — easy to look like a startup pitch with no guts)

| Idea | Why it might work | Why it loses |
|---|---|---|
| Homeowner app: “run laundry at 2am” | Clear ICP | Too small vs Base’s VPP |
| Neighbor-share backup during outage | Viral | Regulatory / not 48h |
| “Battery as a paycheck” fintech | Hot | Needs real settlements |
| Installer routing (wrong house) | They care | Maps + logistics in 48h is death |

---

## Alternate “one idea” if Nodal is taken in the room

**Receipt-first:** skip the fleet optimizer. Ingest ERCOT. For **one** simulated Core, generate a live English receipt every interval. Operator view is a single unit. Weaker Orchestration — only win if the writing is devastatingly good and you still inject “comms down → no dispatch, here’s why.”

**Install lock:** orchestration of field jobs that **gates** dispatch. Commercializable as ops. Weaker Open Grid Data unless you still show prices.

**Illinois / PJM teaser:** same Nodal, second market tab. Only if Texas replay is done. They just entered PJM because of data-center load. Judges will notice you read the news.

---

## Kill list

- ChatGPT wrapper on ERCOT.com HTML
- Token/crypto VPP
- Hardware / firmware (you have a laptop)
- Claiming you control real Base batteries
- “AI agent that calls ERCOT” with no failure story
