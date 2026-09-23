# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Agrégation sur des pas réguliers.

Ce que chaque pas doit garantir : une moyenne qui est l'intégrale de la courbe,
des extrêmes qui encadrent toujours la moyenne, et un pas déclaré porté
seulement si aucun écart entre points voisins ne dépasse sa durée.
"""

import numpy as np
import pandas as pd
import pytest

from hydroportail.aggregate import aggregate


def _series(minutes, values, start="2024-03-01"):
    times = pd.Timestamp(start, tz="UTC") + pd.to_timedelta(minutes, unit="min")
    return pd.Series(times), np.asarray(values, dtype=float)


def test_a_constant_series_averages_to_itself():
    t, v = _series(np.arange(0, 121, 5), np.full(25, 12.5))
    out = aggregate(t, v, 15)
    assert np.allclose(out.debit_moyen_m3s, 12.5)
    assert out.pas_porte.all()


def test_a_ramp_averages_to_its_midpoint():
    # Linear in time: the mean over [a, b] is the value at the middle.
    t, v = _series([0, 60], [0.0, 60.0])
    out = aggregate(t, v, 15)
    assert np.allclose(out.debit_moyen_m3s, [7.5, 22.5, 37.5, 52.5])


def test_the_mean_is_weighted_by_time_not_by_points():
    # Points bunched in the first minutes must not outweigh the rest of the bin.
    t, v = _series([0, 1, 2, 3, 60], [100, 100, 100, 100, 100 - 57])
    out = aggregate(t, v, 60)
    expected = (3 * 100 + 57 * (100 + 43) / 2) / 60
    assert out.debit_moyen_m3s.iloc[0] == pytest.approx(expected)


def test_bounds_are_interpolated_and_count_in_the_extremes():
    # Nothing falls on 15 or 30: both bounds come from interpolation.
    t, v = _series([10, 20, 35], [0.0, 10.0, 40.0])
    out = aggregate(t, v, 15).set_index("debut_pas")
    row = out.iloc[0]  # the bin from 15 to 30
    assert row.debit_min_m3s == pytest.approx(5.0)
    assert row.debit_max_m3s == pytest.approx(30.0)


def test_the_mean_never_leaves_its_extremes():
    rng = np.random.default_rng(0)
    minutes = np.cumsum(rng.integers(1, 20, 400))
    t, v = _series(minutes, rng.gamma(2.0, 10.0, 400))
    out = aggregate(t, v, 15)
    assert (out.debit_moyen_m3s <= out.debit_max_m3s + 1e-9).all()
    assert (out.debit_moyen_m3s >= out.debit_min_m3s - 1e-9).all()


def test_a_bin_is_supported_only_if_no_gap_exceeds_it():
    # Points every 5 minutes, then a 50 minute hole, then every 5 again.
    minutes = list(range(0, 61, 5)) + list(range(110, 181, 5))
    t, v = _series(minutes, np.ones(len(minutes)))
    out = aggregate(t, v, 15).set_index("debut_pas")
    start = pd.Timestamp("2024-03-01", tz="UTC")
    hole = [start + pd.Timedelta(minutes=m) for m in (60, 75, 90, 105)]
    assert not out.loc[hole, "pas_porte"].any()
    assert out.loc[hole, "ecart_max_min"].eq(50).all()
    assert out.drop(index=hole).pas_porte.all()


def test_a_gap_equal_to_the_bin_is_supported():
    # Raw data at 15 minutes supports a 15 minute bin, not a 10 minute one.
    t, v = _series(np.arange(0, 121, 15), np.ones(9))
    assert aggregate(t, v, 15).pas_porte.all()
    assert not aggregate(t, v, 10).pas_porte.all()


def test_bins_are_aligned_on_round_times():
    # From 00:07 to 01:40, the whole 30 minute bins start at 00:30 and 01:00.
    t, v = _series([7, 100], [1.0, 1.0])
    out = aggregate(t, v, 30)
    start = pd.Timestamp("2024-03-01", tz="UTC")
    assert list(out.debut_pas) == [start + pd.Timedelta(minutes=m) for m in (30, 60)]
