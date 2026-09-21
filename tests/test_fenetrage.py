# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Windowing: the one place where data can vanish without a trace.

A gap of a single day between two windows loses everything it holds, and an
overlap counts the same points twice. Neither shows up in any total, which is
why this is tested on synthetic input rather than left to a real run.
"""

from datetime import date, timedelta

from hydroportail.api import (
    MAX_WINDOW_DAYS,
    MIN_WINDOW_DAYS,
    QUOTA_MAX,
    TARGET_POINTS,
    _step_for,
    span_for,
    walk,
)


def _recording(points_per_day):
    """A fake fetcher that notes the windows it is asked for."""
    asked = []

    def fetch(start, stop):
        asked.append((start, stop))
        days = (stop - start).days + 1
        return [{"t": None}] * int(points_per_day * days)

    return asked, fetch


def _covers_exactly(asked, start, end):
    """Windows tile the period: contiguous, in order, no gap, no overlap."""
    assert asked, "aucune fenêtre demandée"
    assert asked[0][0] == start
    assert asked[-1][1] == end
    for (_, previous_end), (next_start, _) in zip(asked, asked[1:]):
        assert next_start == previous_end + timedelta(days=1), (
            f"trou ou recouvrement entre {previous_end} et {next_start}")
    for begin, finish in asked:
        assert begin <= finish


# --------------------------------------------------------------------------
#  The invariant that matters
# --------------------------------------------------------------------------

def test_les_fenetres_pavent_la_periode_quelle_que_soit_la_densite():
    start, end = date(1981, 1, 1), date(2026, 9, 20)
    for density in (288, 96, 12, 1, 0.2, 0.01):
        asked, fetch = _recording(density)
        walk(start, end, fetch)
        _covers_exactly(asked, start, end)


def test_une_periode_d_un_seul_jour_donne_une_seule_fenetre():
    day = date(2024, 3, 1)
    asked, fetch = _recording(288)
    walk(day, day, fetch)
    assert asked == [(day, day)]


def test_une_periode_vide_ne_demande_rien():
    asked, fetch = _recording(288)
    assert walk(date(2024, 3, 2), date(2024, 3, 1), fetch) == []
    assert asked == []


def test_aucun_point_n_est_perdu_ni_compte_deux_fois():
    start, end = date(2020, 1, 1), date(2024, 12, 31)
    asked, fetch = _recording(10)
    points = walk(start, end, fetch)
    assert len(points) == 10 * ((end - start).days + 1)


# --------------------------------------------------------------------------
#  The adaptation, which is what makes one rule fit both shapes of series
# --------------------------------------------------------------------------

def test_une_serie_dense_reste_sur_des_fenetres_d_environ_un_an():
    # Tarascon raw: 105 209 points a year, about 288 a day.
    asked, fetch = _recording(288)
    walk(date(2014, 1, 1), date(2024, 12, 31), fetch)
    widths = [(stop - begin).days + 1 for begin, stop in asked]
    assert all(300 <= w <= 400 for w in widths[:-1]), widths


def test_une_serie_eparse_elargit_ses_fenetres():
    # Tarascon most_valid: 6 077 points a year, about 17 a day. Sixteen years
    # of that is one window, so the whole period costs a handful of requests.
    asked, fetch = _recording(6077 / 365)
    walk(date(1994, 12, 1), date(2026, 9, 20), fetch)
    assert len(asked) <= 5, [(str(a), str(b)) for a, b in asked]
    assert (asked[1][1] - asked[1][0]).days + 1 > 10 * 365


def test_une_zone_sans_donnee_est_traversee_de_plus_en_plus_vite():
    asked, fetch = _recording(0)
    walk(date(1900, 1, 1), date(2026, 9, 20), fetch)
    widths = [(stop - begin).days + 1 for begin, stop in asked]
    assert widths[1] > widths[0]
    assert len(asked) < 20, widths


def test_span_for_reste_dans_les_bornes():
    assert span_for(0) == MAX_WINDOW_DAYS
    assert span_for(-1) == MAX_WINDOW_DAYS
    assert span_for(10_000_000) == MIN_WINDOW_DAYS
    assert span_for(1e-9) == MAX_WINDOW_DAYS
    assert span_for(288) == TARGET_POINTS // 288


# --------------------------------------------------------------------------
#  The quota, which the step exists to satisfy and nothing else
# --------------------------------------------------------------------------

def test_le_step_fait_toujours_passer_la_fenetre_sous_le_quota():
    for days in (1, 30, 365, 366, 3650, MAX_WINDOW_DAYS):
        assert days * 1440 / _step_for(days) <= QUOTA_MAX, days


def test_le_step_reste_a_un_sur_les_fenetres_courtes():
    # 500 000 minutes is about 347 days; below that nothing needs to be raised.
    assert _step_for(1) == 1
    assert _step_for(347) == 1


def test_le_step_monte_ce_qu_il_faut_sur_seize_ans():
    # The case that closed the question: a sixteen year window is refused with
    # a step of 1, and accepted from 17 on.
    days = 16 * 365
    assert _step_for(days) == 17
    assert days * 1440 / 1 > QUOTA_MAX


# --------------------------------------------------------------------------
#  Cutting a window the server refused
# --------------------------------------------------------------------------

def test_la_coupe_en_deux_couvre_exactement_la_fenetre():
    from hydroportail.api import split_window

    for days in (2, 3, 4, 365, 366, 2922, 3000):
        start = date(2010, 1, 1)
        end = start + timedelta(days=days - 1)
        halves = split_window(start, end)
        _covers_exactly(halves, start, end)
        assert len(halves) == 2
        # Both halves must shrink, otherwise the recursion never terminates.
        for begin, finish in halves:
            assert (finish - begin).days + 1 < days


def test_le_step_ne_depasse_jamais_ce_que_le_formulaire_accepte():
    # « Le pas de temps doit être compris entre 1 et 30 », dit la source. C'est
    # cette borne qui plafonne la largeur d'une fenêtre, pas le quota seul.
    from hydroportail.api import MAX_STEP, MAX_WINDOW_DAYS

    assert _step_for(MAX_WINDOW_DAYS) <= MAX_STEP
    with __import__("pytest").raises(Exception):
        _step_for(MAX_WINDOW_DAYS + 1000)


def test_les_fenetres_restent_sous_la_largeur_maximale():
    start, end = date(1900, 1, 1), date(2026, 9, 20)
    for density in (0, 0.5, 288):
        asked, fetch = _recording(density)
        walk(start, end, fetch, first_span=MAX_WINDOW_DAYS)
        _covers_exactly(asked, start, end)
        for begin, finish in asked:
            assert (finish - begin).days + 1 <= MAX_WINDOW_DAYS


def test_le_step_vaut_toujours_un_hors_de_la_famille_instantanee():
    # Piège silencieux : dans la famille journalière, step est le « n » du nom.
    # QIXnJ avec step=20 rend des maxima sur vingt jours, soit un vingtième des
    # lignes, et rien dans la réponse ne le signale.
    for days in (1, 365, 46000):
        assert _step_for(days, "daily") == 1
        assert _step_for(days, "monthly") == 1
