# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Fusion des passes, conversion, couverture.

Les trois autres endroits où de la donnée peut disparaître sans que rien ne le
signale : un point écrasé par le dédoublonnage, un litre pris pour un mètre
cube, une médiane inventée là où il n'y a pas d'intervalle.
"""

import pandas as pd

from hydroportail.download import _merge_passes, _resolution, _to_frame


def _point(t, v, s, q=16, m=8, c=0):
    return {"t": t, "v": v, "s": s, "q": q, "m": m, "c": c, "md": None}


# --------------------------------------------------------------------------
#  Conversion
# --------------------------------------------------------------------------

def test_values_go_from_litres_to_cubic_metres():
    frame = _to_frame("V720001002", [_point("2024-03-01T04:35:00Z", 2140000, 4)], False)
    assert frame.loc[0, "debit_m3s"] == 2140.0


def test_timestamps_are_read_as_utc():
    frame = _to_frame("V720001002", [_point("2024-03-01T04:35:00Z", 1000, 4)], False)
    stamp = frame.loc[0, "date_obs"]
    assert str(stamp.tz) == "UTC"
    assert (stamp.hour, stamp.minute) == (4, 35)


def test_codes_fit_in_an_eight_bit_integer():
    # Les valeurs rencontrées vont de 0 à 30 ; int8 va jusqu'à 127, et un
    # débordement se lirait comme un code négatif plausible.
    points = [_point("2024-03-01T00:00:00Z", 1000, 16, q=30, m=16, c=8)]
    frame = _to_frame("X", points, True)
    assert frame.loc[0, "statut"] == 16
    assert frame.loc[0, "qualification"] == 30
    assert frame.loc[0, "methode"] == 16
    assert frame.loc[0, "continuite"] == 8
    for column in ("statut", "qualification", "methode", "continuite"):
        assert frame[column].dtype == "int8"


def test_an_empty_pass_gives_an_empty_but_complete_table():
    frame = _to_frame("X", [], False)
    assert frame.empty
    assert "most_valid" in frame.columns


# --------------------------------------------------------------------------
#  Fusion des deux passes
# --------------------------------------------------------------------------

def test_a_timestamp_at_two_levels_gives_two_rows():
    raw = _to_frame("V", [_point("2024-03-01T01:55:00Z", 2170000, 4, q=16, m=8)], False)
    valid = _to_frame("V", [_point("2024-03-01T01:55:00Z", 2170000, 16, q=20, m=10)], True)
    merged = _merge_passes([raw, valid])
    assert len(merged) == 2
    assert set(merged["statut"]) == {4, 16}
    assert merged.loc[merged.statut == 16, "most_valid"].all()
    assert not merged.loc[merged.statut == 4, "most_valid"].any()


def test_the_same_point_served_by_both_passes_counts_once():
    # Cas des périodes récentes : most_valid rend exactement les points bruts,
    # aux mêmes valeurs. Une seule ligne doit en sortir, marquée most_valid.
    point = _point("2026-09-15T10:00:00Z", 1050000, 4)
    merged = _merge_passes([_to_frame("V", [point], False), _to_frame("V", [point], True)])
    assert len(merged) == 1
    assert bool(merged.loc[0, "most_valid"]) is True
    assert merged.loc[0, "statut"] == 4


def test_two_qualifications_under_one_status_do_not_overwrite():
    # C'est la raison de dédoublonner sur la ligne entière : une même série
    # brute mêle q=16 et q=12, et une clé (station, date, statut) fusionnerait
    # ces deux points en un seul.
    merged = _merge_passes([_to_frame("V", [
        _point("2026-09-15T10:00:00Z", 1050000, 4, q=16),
        _point("2026-09-15T10:05:00Z", 1060000, 4, q=12),
    ], False)])
    assert len(merged) == 2
    assert set(merged["qualification"]) == {12, 16}


def test_the_merge_sorts_by_date_then_status():
    merged = _merge_passes([_to_frame("V", [
        _point("2024-03-02T00:00:00Z", 1, 4),
        _point("2024-03-01T00:00:00Z", 2, 16),
        _point("2024-03-01T00:00:00Z", 2, 4),
    ], False)])
    assert list(merged["date_obs"].dt.day) == [1, 1, 2]
    assert list(merged["statut"]) == [4, 16, 4]


def test_no_pass_at_all_raises_nothing():
    assert _merge_passes([]).empty
    assert _merge_passes([_to_frame("V", [], False)]).empty


# --------------------------------------------------------------------------
#  Couverture
# --------------------------------------------------------------------------

def test_coverage_counts_points_days_and_gaps():
    points = [_point(f"2024-03-01T{h:02d}:00:00Z", 1000, 4) for h in range(0, 6)]
    points += [_point("2024-03-02T00:00:00Z", 1000, 4)]
    table = _resolution(_to_frame("V", points, False))
    row = table.iloc[0]
    assert row["annee"] == 2024
    assert row["statut"] == 4
    assert row["nb_points"] == 7
    assert row["jours_avec_donnees"] == 2
    assert row["intervalle_median_min"] == 60.0


def test_a_year_with_one_point_invents_no_resolution():
    # Aucun intervalle n'existe. Un zéro se lirait comme une résolution
    # parfaite, ce qui serait le contraire de la vérité.
    table = _resolution(_to_frame("V", [_point("2024-03-01T00:00:00Z", 1000, 4)], False))
    assert table.loc[0, "nb_points"] == 1
    assert pd.isna(table.loc[0, "intervalle_median_min"])
    assert pd.isna(table.loc[0, "intervalle_p90_min"])


def test_the_p90_separates_a_regular_series_from_a_gappy_one():
    regular = [_point(f"2024-03-01T{h:02d}:00:00Z", 1, 4) for h in range(0, 10)]
    gappy = [_point(f"2024-03-01T{h:02d}:00:00Z", 1, 16) for h in range(0, 9)]
    gappy += [_point("2024-03-01T23:00:00Z", 1, 16)]
    table = _resolution(_merge_passes([_to_frame("V", regular + gappy, False)]))
    by_status = table.set_index("statut")
    assert by_status.loc[4, "intervalle_median_min"] == by_status.loc[4, "intervalle_p90_min"]
    assert by_status.loc[16, "intervalle_p90_min"] > by_status.loc[16, "intervalle_median_min"]


def test_statuses_and_years_are_counted_separately():
    points = [_point("2023-12-31T23:00:00Z", 1, 4), _point("2024-01-01T00:00:00Z", 1, 4),
              _point("2024-01-01T00:05:00Z", 1, 16)]
    table = _resolution(_to_frame("V", points, False))
    assert len(table) == 3
    assert set(zip(table["annee"], table["statut"])) == {(2023, 4), (2024, 4), (2024, 16)}
