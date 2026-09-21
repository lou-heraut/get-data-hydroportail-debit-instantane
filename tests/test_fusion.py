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

def test_les_valeurs_passent_du_litre_au_metre_cube():
    frame = _to_frame("V720001002", [_point("2024-03-01T04:35:00Z", 2140000, 4)], False)
    assert frame.loc[0, "debit_m3s"] == 2140.0


def test_les_horodatages_sont_lus_en_utc():
    frame = _to_frame("V720001002", [_point("2024-03-01T04:35:00Z", 1000, 4)], False)
    stamp = frame.loc[0, "date_obs"]
    assert str(stamp.tz) == "UTC"
    assert (stamp.hour, stamp.minute) == (4, 35)


def test_les_codes_tiennent_dans_un_entier_de_huit_bits():
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


def test_une_passe_vide_donne_une_table_vide_mais_complete():
    frame = _to_frame("X", [], False)
    assert frame.empty
    assert "most_valid" in frame.columns


# --------------------------------------------------------------------------
#  Fusion des deux passes
# --------------------------------------------------------------------------

def test_un_horodatage_a_deux_niveaux_donne_deux_lignes():
    raw = _to_frame("V", [_point("2024-03-01T01:55:00Z", 2170000, 4, q=16, m=8)], False)
    valid = _to_frame("V", [_point("2024-03-01T01:55:00Z", 2170000, 16, q=20, m=10)], True)
    merged = _merge_passes([raw, valid])
    assert len(merged) == 2
    assert set(merged["statut"]) == {4, 16}
    assert merged.loc[merged.statut == 16, "most_valid"].all()
    assert not merged.loc[merged.statut == 4, "most_valid"].any()


def test_le_meme_point_rendu_par_les_deux_passes_ne_compte_qu_une_fois():
    # Cas des périodes récentes : most_valid rend exactement les points bruts,
    # aux mêmes valeurs. Une seule ligne doit en sortir, marquée most_valid.
    point = _point("2026-09-15T10:00:00Z", 1050000, 4)
    merged = _merge_passes([_to_frame("V", [point], False), _to_frame("V", [point], True)])
    assert len(merged) == 1
    assert bool(merged.loc[0, "most_valid"]) is True
    assert merged.loc[0, "statut"] == 4


def test_deux_qualifications_sous_le_meme_statut_ne_s_ecrasent_pas():
    # C'est la raison de dédoublonner sur la ligne entière : une même série
    # brute mêle q=16 et q=12, et une clé (station, date, statut) fusionnerait
    # ces deux points en un seul.
    merged = _merge_passes([_to_frame("V", [
        _point("2026-09-15T10:00:00Z", 1050000, 4, q=16),
        _point("2026-09-15T10:05:00Z", 1060000, 4, q=12),
    ], False)])
    assert len(merged) == 2
    assert set(merged["qualification"]) == {12, 16}


def test_la_fusion_trie_par_date_puis_statut():
    merged = _merge_passes([_to_frame("V", [
        _point("2024-03-02T00:00:00Z", 1, 4),
        _point("2024-03-01T00:00:00Z", 2, 16),
        _point("2024-03-01T00:00:00Z", 2, 4),
    ], False)])
    assert list(merged["date_obs"].dt.day) == [1, 1, 2]
    assert list(merged["statut"]) == [4, 16, 4]


def test_aucune_passe_ne_donne_pas_d_erreur():
    assert _merge_passes([]).empty
    assert _merge_passes([_to_frame("V", [], False)]).empty


# --------------------------------------------------------------------------
#  Couverture
# --------------------------------------------------------------------------

def test_la_couverture_compte_les_points_les_jours_et_les_ecarts():
    points = [_point(f"2024-03-01T{h:02d}:00:00Z", 1000, 4) for h in range(0, 6)]
    points += [_point("2024-03-02T00:00:00Z", 1000, 4)]
    table = _resolution(_to_frame("V", points, False))
    row = table.iloc[0]
    assert row["annee"] == 2024
    assert row["statut"] == 4
    assert row["nb_points"] == 7
    assert row["jours_avec_donnees"] == 2
    assert row["intervalle_median_min"] == 60.0


def test_une_annee_a_un_seul_point_n_invente_pas_de_resolution():
    # Aucun intervalle n'existe. Un zéro se lirait comme une résolution
    # parfaite, ce qui serait le contraire de la vérité.
    table = _resolution(_to_frame("V", [_point("2024-03-01T00:00:00Z", 1000, 4)], False))
    assert table.loc[0, "nb_points"] == 1
    assert pd.isna(table.loc[0, "intervalle_median_min"])
    assert pd.isna(table.loc[0, "intervalle_p90_min"])


def test_le_p90_separe_une_serie_reguliere_d_une_serie_trouee():
    reguliere = [_point(f"2024-03-01T{h:02d}:00:00Z", 1, 4) for h in range(0, 10)]
    trouee = [_point(f"2024-03-01T{h:02d}:00:00Z", 1, 16) for h in range(0, 9)]
    trouee += [_point("2024-03-01T23:00:00Z", 1, 16)]
    table = _resolution(_merge_passes([_to_frame("V", reguliere + trouee, False)]))
    par_statut = table.set_index("statut")
    assert par_statut.loc[4, "intervalle_median_min"] == par_statut.loc[4, "intervalle_p90_min"]
    assert par_statut.loc[16, "intervalle_p90_min"] > par_statut.loc[16, "intervalle_median_min"]


def test_les_statuts_et_les_annees_sont_comptes_separement():
    points = [_point("2023-12-31T23:00:00Z", 1, 4), _point("2024-01-01T00:00:00Z", 1, 4),
              _point("2024-01-01T00:05:00Z", 1, 16)]
    table = _resolution(_to_frame("V", points, False))
    assert len(table) == 3
    assert set(zip(table["annee"], table["statut"])) == {(2023, 4), (2024, 4), (2024, 16)}
