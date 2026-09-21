# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Columns, types, controlled vocabulary and datapackage metadata.

Single source of truth for the version number: ``SCRIPT_VERSION`` below is
re-exported by ``hydroportail/__init__.py``. Moving it implies moving it in
``pyproject.toml`` and ``CITATION.cff`` too.
"""

from __future__ import annotations

SCRIPT_VERSION = "0.1.0"

LICENSE = {
    "name": "GPL-3.0-or-later",
    "title": "GNU General Public License v3.0 or later",
    "path": "https://www.gnu.org/licenses/gpl-3.0.html",
}

#: Landing page of the source. The series themselves come from the AJAX route
#: of the station page, which is documented in SOURCE.md.
SOURCE_URL = "https://hydro.eaufrance.fr/"


# --------------------------------------------------------------------------
#  Quality codes
#
#  Every point carries four Sandre codes. Without this table they are opaque
#  integers; with it they are the producer's own quality information. The case
#  that shows why it matters is q=12, "Douteuse": the producer flags the point
#  as suspect, and 35 % of the recent raw data at Tarascon carries it.
#
#  The table is frozen here rather than fetched from the Sandre at every run:
#  twenty rows that move once a decade do not justify depending on a third
#  service, nor letting a Sandre outage break a HydroPortail download. The
#  control step warns when a code absent from this table shows up in the data,
#  which is the only moment one needs to learn that a nomenclature moved.
#
#  Beware when refreshing it: the nomenclatures whose title fits best are the
#  wrong ones. 507 "Méthode d'obtention du résultat de l'observation hydro"
#  holds neither code 8 nor 10; 72 "Code de continuité du point" holds only 1
#  and 2; 508 "Qualification de la donnée de l'observation" has no "Douteuse".
#  Match on the code values, then check against the labels Hub'Eau serves in
#  observations_tr. Full account in SOURCE.md.
# --------------------------------------------------------------------------

#: Sandre nomenclature backing each of the four codes.
NOMENCLATURES = {
    "s": ("510", "Statut de l'observation"),
    "q": ("515", "Qualification de l'observation"),
    "m": ("512", "Méthode d'obtention du résultat"),
    "c": ("923", "Continuité de la donnée de l'observation hydrométrique"),
}

#: (type, code) -> (libelle, definition). The definition is left empty where
#: the Sandre gives none and no measurement established one.
REF_CODES: dict[tuple[str, int], tuple[str, str]] = {
    # s, statut : how far the value has travelled through validation
    ("s", 0): ("Sans validation", ""),
    ("s", 4): ("Brute", "Donnée non traitée, telle qu'acquise"),
    ("s", 8): ("Corrigé", "Donnée corrigée"),
    ("s", 12): ("Pré-validé", "Donnée pré-validée"),
    ("s", 16): ("Validé", "Donnée contrôlée et qualifiée par le producteur"),

    # q, qualification : what the producer thinks of the value itself
    ("q", 0): ("Neutre", ""),
    ("q", 4): ("Faible", ""),
    ("q", 8): ("Forte", ""),
    ("q", 12): ("Douteuse", "Le producteur signale cette valeur comme suspecte"),
    ("q", 16): ("Non qualifiée", "Aucun jugement porté sur cette valeur"),
    ("q", 20): ("Bonne", ""),
    ("q", 30): ("Valeur estimée (~)", ""),

    # m, methode : how the value was obtained
    ("m", 0): ("MES", "Mesurée"),
    ("m", 4): ("REC", "Reconstituée"),
    ("m", 8): ("CAL", "Calculée, par exemple un débit tiré d'une hauteur"),
    ("m", 10): ("EXP", "Expertisée, issue du jugement d'un hydromètre"),
    ("m", 12): ("Interpolation", "Interpolée par un système automatique"),
    ("m", 14): ("EST", "Estimée"),
    ("m", 16): ("Forçage", ""),

    # c, continuite : whether the series breaks at this point
    ("c", 0): ("Continue", ""),
    ("c", 1): ("Discontinue", ""),
    ("c", 2): ("Discontinue faible", ""),
    ("c", 4): ("Discontinue faible", ""),
    ("c", 6): ("Discontinue neutre", ""),
    ("c", 8): ("Discontinue forte", ""),
}


def ref_codes_rows() -> list[dict[str, object]]:
    """The controlled vocabulary, as the rows of ``ref_codes.csv``."""
    rows = []
    for (kind, code), (label, definition) in REF_CODES.items():
        nomenclature, title = NOMENCLATURES[kind]
        rows.append({
            "type": kind,
            "code": code,
            "libelle": label,
            "definition": definition,
            "nomenclature_sandre": nomenclature,
            "nom_nomenclature": title,
            "source": "https://api.sandre.eaufrance.fr/referentiels/v1/nsa.json",
        })
    return rows


def unknown_codes(seen: dict[str, set[int]]) -> list[tuple[str, int]]:
    """Codes present in the data but absent from :data:`REF_CODES`.

    The control step reports these rather than silently writing empty labels:
    an unknown code means the nomenclature moved, and that is worth knowing.
    """
    return sorted(
        (kind, code)
        for kind, codes in seen.items()
        for code in codes
        if (kind, code) not in REF_CODES
    )
