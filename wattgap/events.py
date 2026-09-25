"""Do UT home football games move Austin power prices?  A backtest on public data.

Hypothesis (docs/IDEAS.md, "Events and outside signals"): ~100k people at DKR-Texas Memorial Stadium
show up in the price around kickoff.  A stadium is ~10-20 MW and the Austin Energy load zone (LZ_AEN)
peaks in the thousands of MW, so the prior is "no zonal effect"; this measures it.

Data:
  * data/events/ut_home_games.csv  kickoff times of every Texas home game at DKR, 2023-2025, from ESPN's
    public schedule endpoint (site.api.espn.com ... /teams/251/schedule?season=YYYY), retrieved 2026-09-25.
  * data/archive/rt_{year}.csv.gz  15-min real-time settlement point prices (NP6-785-ER, `make archive`).
    The archive has load zones and hubs only.  Resource-node history (e.g. DECKER_GT, SANDHSYD_*) needs
    the ERCOT Public API key, so the nodal test is not possible here.
Design:
  * Game days = Saturday home games.  Controls = every other Saturday from Aug 26 to Nov 30 of the same
    season, optionally also dropping ACL Fest and F1 US GP Saturdays.
  * Window = kickoff - 2 h to kickoff + 4 h (24 intervals).  Each control day is read over the *same clock
    window* as the game it is compared with, so time-of-day is held fixed.
  * Per game: delta = metric(game day) - mean (or, robust to one scarcity Saturday, median) of the metric
    over the season's control days.  Metrics: LZ_AEN price,
    LZ_AEN - HB_HUBAVG, LZ_AEN - LZ_LCRA (the zone around Austin).
  * Uncertainty: bootstrap over games and control days (95% CI) and a within-season permutation test (labels shuffled across
    that season's Saturdays, windows kept with the game labels).
Run:  python -m wattgap.events   (writes data/derived/events_backtest.json)
"""

from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean, median

from wattgap.data import read_archive

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "data" / "events" / "ut_home_games.csv"
OUT = ROOT / "data" / "derived" / "events_backtest.json"
SEASONS = (2023, 2024, 2025)
BEFORE, AFTER = timedelta(hours=2), timedelta(hours=4)
# Austin mega-event Saturdays (ACL Fest weekends, F1 US GP), dropped from controls in the "clean" variant.
MEGA = {date(2023, 10, 7), date(2023, 10, 14), date(2023, 10, 21), date(2024, 10, 5), date(2024, 10, 12),
        date(2024, 10, 19), date(2025, 10, 4), date(2025, 10, 11), date(2025, 10, 18)}
METRICS = {
    "LZ_AEN": lambda p: p["LZ_AEN"],
    "LZ_AEN - HB_HUBAVG": lambda p: p["LZ_AEN"] - p["HB_HUBAVG"],
    "LZ_AEN - LZ_LCRA": lambda p: p["LZ_AEN"] - p["LZ_LCRA"],
}


def read_games(path: Path = GAMES) -> list[datetime]:
    """Kickoffs (CT) of Saturday home games."""
    with path.open() as f:
        return [datetime.fromisoformat(r["kickoff_ct"]) for r in csv.DictReader(f) if r["weekday"] == "Sat"]


def saturdays(season: int) -> list[date]:
    d = date(season, 8, 26)
    d += timedelta(days=(5 - d.weekday()) % 7)
    out = []
    while d <= date(season, 11, 30):
        out.append(d)
        d += timedelta(days=7)
    return out


def window_mean(series: dict[datetime, dict[str, float]], day: date, kickoff: datetime, metric) -> float | None:
    """Mean of metric over [kickoff-2h, kickoff+4h) at the same clock time on `day`."""
    start = datetime.combine(day, kickoff.timetz().replace(tzinfo=None)).replace(tzinfo=kickoff.tzinfo)
    # re-localize so DST differences between the game and the control day don't shift the window
    start = start.replace(tzinfo=None)
    vals = [metric(p) for t, p in series.items() if start - BEFORE <= t.replace(tzinfo=None) < start + AFTER]
    return mean(vals) if len(vals) >= 20 else None


def deltas(series, games: list[datetime], controls: dict[int, list[date]], metric, agg=mean) -> list[float]:
    out = []
    for g in games:
        game = window_mean(series, g.date(), g, metric)
        ctrl = [v for d in controls[g.year] if (v := window_mean(series, d, g, metric)) is not None]
        if game is not None and ctrl:
            out.append(game - agg(ctrl))
    return out


def bootstrap_ci(series, games, controls, metric, agg=mean, n: int = 5000, seed: int = 7) -> tuple[float, float]:
    """95% CI of the mean delta, resampling games *and* each season's control Saturdays (both are samples)."""
    rng = random.Random(seed)
    game_v = {g: window_mean(series, g.date(), g, metric) for g in games}
    ctrl_v = {g: {d: window_mean(series, d, g, metric) for d in controls[g.year]} for g in games}
    ms = []
    for _ in range(n):
        picked = {s: rng.choices(controls[s], k=len(controls[s])) for s in controls}
        ds = []
        for g in rng.choices(games, k=len(games)):
            ctrl = [v for d in picked[g.year] if (v := ctrl_v[g][d]) is not None]
            if game_v[g] is not None and ctrl:
                ds.append(game_v[g] - agg(ctrl))
        ms.append(mean(ds))
    ms.sort()
    return ms[int(0.025 * n)], ms[int(0.975 * n) - 1]


def permutation_p(series, games, controls, metric, agg=mean, n: int = 2000, seed: int = 11) -> float:
    """Two-sided p: shuffle which Saturdays are 'game days' within each season, keep kickoff windows."""
    obs = abs(mean(deltas(series, games, controls, metric, agg)))
    rng = random.Random(seed)
    by_season: dict[int, list[datetime]] = {}
    for g in games:
        by_season.setdefault(g.year, []).append(g)
    # precompute every Saturday's window mean for every kickoff window
    cache = {}
    for s, gs in by_season.items():
        days = sorted(set(controls[s]) | {g.date() for g in gs})
        for g in gs:
            for d in days:
                cache[(g, d)] = window_mean(series, d, g, metric)
    hits = 0
    for _ in range(n):
        ds = []
        for s, gs in by_season.items():
            days = sorted(set(controls[s]) | {g.date() for g in gs})
            fake = rng.sample(days, len(gs))
            rest = [d for d in days if d not in fake]
            for g, d in zip(gs, fake):
                ctrl = [v for c in rest if (v := cache[(g, c)]) is not None]
                if cache[(g, d)] is not None and ctrl:
                    ds.append(cache[(g, d)] - agg(ctrl))
        hits += abs(mean(ds)) >= obs
    return (hits + 1) / (n + 1)


def load_series(seasons=SEASONS) -> dict[datetime, dict[str, float]]:
    series = {}
    for y in seasons:
        starts, cols = read_archive("rt", y)
        for k, t in enumerate(starts):
            if t.month in (8, 9, 10, 11) and t.weekday() == 5:
                series[t] = {p: cols[p][k] for p in ("LZ_AEN", "HB_HUBAVG", "LZ_LCRA")}
    return series


def run(n_perm: int = 2000) -> dict:
    series = load_series()
    games = [g for g in read_games() if g.year in SEASONS]
    game_days = {g.date() for g in games}
    variants = {
        "all other Saturdays": {s: [d for d in saturdays(s) if d not in game_days] for s in SEASONS},
        "excluding ACL and F1 Saturdays": {s: [d for d in saturdays(s) if d not in game_days | MEGA] for s in SEASONS},
    }
    out = {"games": len(games), "window": "kickoff -2 h to +4 h, 15-min RT SPP", "source_games": str(GAMES.relative_to(ROOT)),
           "controls": {k: sum(len(v) for v in c.values()) for k, c in variants.items()}, "results": []}
    for vname, controls in variants.items():
        for aname, agg in (("mean", mean), ("median", median)):
            for mname, metric in METRICS.items():
                ds = deltas(series, games, controls, metric, agg)
                lo, hi = bootstrap_ci(series, games, controls, metric, agg)
                out["results"].append({
                    "controls": vname, "baseline": f"{aname} of controls", "metric": mname, "n_games": len(ds),
                    "n_controls": sum(len(v) for v in controls.values()),
                    "mean_delta": round(mean(ds), 2), "median_delta": round(median(ds), 2),
                    "ci95": [round(lo, 2), round(hi, 2)],
                    "perm_p": round(permutation_p(series, games, controls, metric, agg, n=n_perm), 3),
                })
    return out


def main() -> None:  # pragma: no cover - CLI
    res = run()
    OUT.write_text(json.dumps(res, indent=1) + "\n")
    print(f"{res['games']} Saturday home games; controls {res['controls']}")
    print("| Controls | Baseline | Metric | n games | Mean delta $/MWh | Median | 95% CI (bootstrap) | Permutation p |")
    print("|---|---|---|---:|---:|---:|---|---:|")
    for r in res["results"]:
        print(f"| {r['controls']} | {r['baseline']} | {r['metric']} | {r['n_games']} | {r['mean_delta']:+.2f} | {r['median_delta']:+.2f} | "
              f"[{r['ci95'][0]:+.2f}, {r['ci95'][1]:+.2f}] | {r['perm_p']} |")


if __name__ == "__main__":  # pragma: no cover
    main()
