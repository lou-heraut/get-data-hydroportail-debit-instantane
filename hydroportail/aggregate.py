# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Aggregate an instantaneous series onto regular bins.

The mean of a bin is the time-weighted mean of WMO-No. 1044, § 6.12: the
trapezoidal integral of the series over the bin, divided by its length, with
the two bounds interpolated linearly between their neighbouring points. It is
exactly what HydroPortail serves as ``QmnH``, measured to the rounding of its
three significant digits. See docs/references.md and docs/findings.md.

Next to the mean, each bin carries its minimum and maximum, bounds included,
because a mean flattens the fronts that make a hydropeak while the maximum
keeps its peak; and the largest gap between neighbouring points that overlaps
it. ``mesure_suffisante`` is true when that gap does not exceed the bin.

**What that flag means depends on the status of the series.** On a raw
series, a gap is time the sensor did not record, and a bin wider than the gap
is the only honest one: aggregating finer would be inventing data. On a
validated series it is not: a long gap between two breakpoints is a stretch
of curve the producer certifies within its pruning tolerance, and whether it
is certified or a hole is read from the QIXnJ coverage map, not from the gap.
The flag is computed on both, and used to fill bins only on raw data. See the
decision on the roles of raw and validated data in docs/design.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_EPOCH = pd.Timestamp("1970-01-01", tz="UTC")


def _minutes(times: pd.Series | pd.DatetimeIndex) -> np.ndarray:
    """Minutes since the epoch, whatever the resolution of the timestamps."""
    return np.asarray((pd.to_datetime(times, utc=True) - _EPOCH)
                      / pd.Timedelta(minutes=1), dtype=float)


def largest_gap(t: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """For each bin, the largest gap between neighbouring points overlapping it.

    ``t`` and ``edges`` are in minutes, sorted. A gap overlaps a bin when the
    open interval between two points and the bin share some time. Most gaps
    touch one or two bins and are handled at once; the few that span more,
    which are the holes of a series, are filled one by one.
    """
    nb = len(edges) - 1
    gap = np.zeros(nb)
    g = np.diff(t)
    width = edges[1] - edges[0]
    lo = np.floor((t[:-1] - edges[0]) / width).astype(int)
    hi = np.ceil((t[1:] - edges[0]) / width).astype(int) - 1
    lo_c, hi_c = np.clip(lo, 0, nb - 1), np.clip(hi, 0, nb - 1)
    inside = (hi >= 0) & (lo <= nb - 1) & (g > 0)
    np.maximum.at(gap, lo_c[inside], g[inside])
    np.maximum.at(gap, hi_c[inside], g[inside])
    for i in np.nonzero(inside & (hi_c - lo_c > 1))[0]:
        span = slice(lo_c[i] + 1, hi_c[i])
        gap[span] = np.maximum(gap[span], g[i])
    return gap


def aggregate(times: pd.Series, values, minutes: int) -> pd.DataFrame:
    """Aggregate one series onto bins of ``minutes``, aligned on the epoch.

    ``times`` must be sorted and without duplicates, as one status level of
    one station is. Only the bins lying entirely between the first and the
    last point are returned, since a bound outside the series cannot be
    interpolated.
    """
    t = _minutes(times)
    v = np.asarray(values, dtype=float)
    if len(t) < 2:
        return pd.DataFrame(columns=["debut_pas", "debit_moyen_m3s",
                                     "debit_min_m3s", "debit_max_m3s",
                                     "plus_grand_ecart_min", "mesure_suffisante"])
    width = float(minutes)
    edges = np.arange(np.ceil(t[0] / width) * width, t[-1] + width / 2, width)
    edges = edges[edges <= t[-1]]
    nb = len(edges) - 1
    at_edges = np.interp(edges, t, v)

    # The piecewise linear curve through the points and the bounds, integrated.
    all_t = np.concatenate([t, edges])
    all_v = np.concatenate([v, at_edges])
    order = np.argsort(all_t, kind="stable")
    all_t, all_v = all_t[order], all_v[order]
    area = np.concatenate([[0.0], np.cumsum(np.diff(all_t) * (all_v[1:] + all_v[:-1]) / 2)])
    mean = np.diff(area[np.searchsorted(all_t, edges)]) / width

    # Extremes: the points strictly inside each bin, and both of its bounds.
    which = np.searchsorted(edges, t, side="right") - 1
    keep = (which >= 0) & (which < nb) & ~np.isin(t, edges)
    points = pd.Series(v[keep])
    low = points.groupby(which[keep]).min().reindex(range(nb)).to_numpy()
    high = points.groupby(which[keep]).max().reindex(range(nb)).to_numpy()
    low = np.fmin(low, np.minimum(at_edges[:-1], at_edges[1:]))
    high = np.fmax(high, np.maximum(at_edges[:-1], at_edges[1:]))

    gap = largest_gap(t, edges)
    return pd.DataFrame({
        "debut_pas": _EPOCH + pd.to_timedelta(edges[:-1], unit="min"),
        "debit_moyen_m3s": mean,
        "debit_min_m3s": low,
        "debit_max_m3s": high,
        "plus_grand_ecart_min": gap,
        "mesure_suffisante": gap <= width,
    })
