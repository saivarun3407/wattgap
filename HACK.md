# 48h plan

**Before Friday**

- [ ] Dump one **quiet day** + one **spike day** of ERCOT settlement prices (or GridStatus). Drop into `data/`. Keep `sample_prices.csv` as backup.
- [ ] Optional: ERCOT public API key. Do not bet the demo on it.
- [ ] `python3 sim/run.py` works on a clean laptop.

**Hours 0–6** — scanner + $ gap  
Wire real CSV columns. Print top 10 opportunities. Naive vs aware $.

**Hours 6–16** — UI  
One page: price chart, fleet MW, WattGap $, opportunity list. Kill button.

**Hours 16–24** — failure  
West LTE kill. Alarm if target missed. Log.

**Hours 24–32** — receipt  
One house, one interval, generated from struct fields (optional LLM sentence).

**Hours 32–48** — freeze, 3-min script, sleep.

**Cut first:** map, PJM, live API, extra models.
