"""Vectorized per-tick fleet math (numpy): headroom, per-zone allocation, SoC physics checks.

One array slot per unit. These functions carry no per-unit Python loop, so the supervisor's
arithmetic stays cheap at a million units; per-device crypto is the part that doesn't vectorize.
"""

from __future__ import annotations

import numpy as np

from .data import INTERVAL_H
from .econ import SPEC, Spec

HEALTHY, SUSPECT, DEAD, QUARANTINED, REVOKED = range(5)
STATE_NAMES = ("healthy", "suspect", "dead", "quarantined", "revoked")
DEAD_AFTER_MISSES = 2
SOC_TOLERANCE = 0.02  # reported SoC may drift this far from physics before quarantine


def usable_kw(soc: np.ndarray, reserve: np.ndarray, spec: Spec = SPEC, hours: float = INTERVAL_H) -> np.ndarray:
    """Grid-side kW each unit can deliver for `hours` without touching its reserve."""
    usable = np.maximum(0.0, (soc - np.maximum(reserve, spec.reserve_soc)) * spec.capacity_kwh)
    return np.minimum(spec.power_kw, usable * spec.leg_eff / hours)


def room_kw(soc: np.ndarray, spec: Spec = SPEC, hours: float = INTERVAL_H) -> np.ndarray:
    return np.minimum(spec.power_kw, np.maximum(0.0, (spec.max_soc - soc) * spec.capacity_kwh) / spec.leg_eff / hours)


def zone_sums(values: np.ndarray, zone: np.ndarray, n_zones: int) -> np.ndarray:
    return np.bincount(zone, weights=values, minlength=n_zones)


def allocate(target_kw: np.ndarray, headroom: np.ndarray, zone: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spread each zone's target over its units in proportion to headroom.

    `headroom` is 0 for units that must not work. Returns (kW per unit, shortfall kW per zone).
    """
    total = zone_sums(headroom, zone, len(target_kw))
    share = np.divide(target_kw, total, out=np.zeros_like(target_kw), where=total > 0)
    return headroom * np.minimum(share, 1.0)[zone], np.maximum(0.0, target_kw - total)


def expected_soc(soc: np.ndarray, grid_kw: np.ndarray, spec: Spec = SPEC, hours: float = INTERVAL_H) -> np.ndarray:
    """SoC after delivering (+) or drawing (-) `grid_kw` for `hours`, with the per-leg loss."""
    kwh = grid_kw * hours
    return soc - np.where(kwh > 0, kwh / spec.leg_eff, kwh * spec.leg_eff) / spec.capacity_kwh


def implausible(reported: np.ndarray, soc: np.ndarray, grid_kw: np.ndarray) -> np.ndarray:
    return np.abs(reported - expected_soc(soc, grid_kw)) > SOC_TOLERANCE


def heartbeat(state: np.ndarray, misses: np.ndarray, pinged: np.ndarray, replied: np.ndarray) -> np.ndarray:
    """Update misses/state in place for pinged units. Returns the new state array (suspect, then dead)."""
    missed = pinged & ~replied
    misses[missed] += 1
    misses[replied] = 0
    new = state.copy()
    new[missed] = np.where(misses[missed] >= DEAD_AFTER_MISSES, DEAD, SUSPECT)
    new[replied] = HEALTHY
    return new
