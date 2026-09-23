# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Columns, types, controlled vocabulary and datapackage metadata.

Single source of truth for the version number: ``SCRIPT_VERSION`` below is
re-exported by ``hydroportail/__init__.py``. Moving it implies moving it in
``pyproject.toml`` and ``CITATION.cff`` too.
"""

from __future__ import annotations

from typing import Any, Sequence

SCRIPT_VERSION = "2.0.0"

LICENSE = {
    "name": "GPL-3.0-or-later",
    "title": "GNU General Public License v3.0 or later",
    "path": "https://www.gnu.org/licenses/gpl-3.0.html",
}

#: Landing page of the source. The series themselves come from the AJAX route
#: of the station page, which is documented in docs/findings.md.
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
#  observations_tr. Full account in docs/findings.md.
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


# --------------------------------------------------------------------------
#  Tables
#
#  Column names are never translated from their source. Those coming from
#  Hub'Eau keep its spelling, accents included; those we derive are named in
#  French like the rest; `raw` and `most_valid` keep their English names
#  because they are HydroPortail's own product names. See docs/design.md.
# --------------------------------------------------------------------------

def _f(name: str, kind: str, description: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "type": kind, "description": description, **extra}


FIELDS: dict[str, list[dict[str, Any]]] = {
    "stations": [
        _f("code_station", "string", "Code Sandre de la station, tel que demandé."),
        _f("libelle_station", "string", "Libellé de la station (Hub'Eau)."),
        _f("libelle_cours_eau", "string", "Cours d'eau (Hub'Eau)."),
        _f("code_site", "string",
           "Site hydrométrique auquel la station se rattache. Un site regroupe "
           "plusieurs stations, parfois de plusieurs opérateurs, dont les "
           "débits peuvent différer de plusieurs pour cent."),
        _f("stations_soeurs", "string",
           "Autres stations du même site, séparées par un point-virgule."),
        _f("station_debit_du_site", "string",
           "Quand la station demandée ne porte aucun débit instantané, celle de "
           "son site qui en porte, si elle existe. Vide sinon."),
        _f("descriptif_station", "string", "Opérateur ou description (Hub'Eau)."),
        _f("type_station", "string",
           "Type Hub'Eau. Ne prédit pas la présence de débit : une station STD "
           "peut en porter et une DEB être vide."),
        _f("influence_locale_station", "integer", "Code d'influence locale (Hub'Eau)."),
        _f("en_service", "boolean", "Station en service au référentiel (Hub'Eau)."),
        _f("code_commune_station", "string", "Code INSEE de la commune (Hub'Eau)."),
        _f("libelle_commune", "string", "Commune (Hub'Eau)."),
        _f("code_departement", "string", "Département (Hub'Eau)."),
        _f("latitude_station", "number", "Latitude WGS84 (Hub'Eau)."),
        _f("longitude_station", "number", "Longitude WGS84 (Hub'Eau)."),
        _f("altitude_ref_alti_station", "number", "Altitude du zéro de l'échelle (Hub'Eau)."),
        _f("date_ouverture_station", "date", "Ouverture au référentiel (Hub'Eau)."),
        _f("date_fermeture_station", "date", "Fermeture au référentiel (Hub'Eau)."),
        _f("porte_debit", "boolean",
           "La station porte-t-elle une chronique de débit instantané. Établi "
           "par la carte de couverture, jamais par une sonde ponctuelle : une "
           "sonde ne peut pas prouver une absence."),
        _f("date_debut_instantane", "date",
           "Premier jour où une chronique instantanée existe. Souvent bien "
           "postérieur à l'ouverture de la station."),
        _f("date_fin_instantane", "date", "Dernier jour de la chronique instantanée."),
        _f("jours_avec_donnees", "integer",
           "Nombre de jours portant une donnée instantanée, entre ces deux dates."),
        _f("taux_couverture", "number",
           "Part des jours de la période qui portent une donnée, de 0 à 1."),
    ],
    "coverage": [
        _f("code_station", "string", "Code Sandre de la station."),
        _f("annee", "integer", "Année civile."),
        _f("statut", "integer",
           "Code de statut Sandre 510, parce que brut et validé n'ont ni la "
           "même profondeur ni la même densité. Voir ref_codes.csv."),
        _f("jours_avec_donnees", "integer",
           "Jours de l'année portant une donnée de ce statut. L'inventaire le "
           "renseigne d'avance depuis la carte de couverture, qui étiquette "
           "chaque jour par le statut de son maximum journalier ; le compte "
           "exact remplace cette estimation dès que la chronique est "
           "téléchargée."),
        _f("nb_points", "integer",
           "Nombre de points effectivement téléchargés. Vide tant que la "
           "chronique ne l'a pas été : vide veut dire « pas encore mesuré », "
           "jamais « mesuré à zéro »."),
        _f("intervalle_median_min", "number",
           "Médiane des écarts entre deux points consécutifs, en minutes. Ce "
           "n'est pas un pas de temps : l'instantané n'a aucune régularité "
           "garantie, et cette valeur varie d'un facteur vingt au cours de la "
           "vie d'une station. Vide tant que la chronique n'a pas été prise."),
        _f("intervalle_p90_min", "number",
           "Neuvième décile des mêmes écarts. Lu avec la médiane, il sépare "
           "une série régulière d'une série qui alterne rafales et silences."),
    ],
    "ref_codes": [
        _f("type", "string", "Le code décrit : s statut, q qualification, m méthode, c continuité."),
        _f("code", "integer", "Valeur portée par le point."),
        _f("libelle", "string", "Libellé Sandre."),
        _f("definition", "string", "Sens du code, quand la source ou la mesure l'établit."),
        _f("nomenclature_sandre", "string", "Numéro de la nomenclature Sandre."),
        _f("nom_nomenclature", "string", "Intitulé de la nomenclature."),
        _f("source", "string", "D'où la table est tirée."),
    ],
    "measurements": [
        _f("code_station", "string", "Code Sandre de la station."),
        _f("date_obs", "datetime", "Horodatage UTC du point."),
        _f("debit_m3s", "number",
           "Débit en m3/s, converti depuis les litres par seconde de la source."),
        _f("statut", "integer", "Code s, nomenclature Sandre 510."),
        _f("qualification", "integer",
           "Code q, nomenclature Sandre 515. La valeur 12 signifie « douteuse » "
           "et n'est pas rare : c'est le seul drapeau de qualité par point."),
        _f("methode", "integer", "Code m, nomenclature Sandre 512."),
        _f("continuite", "integer", "Code c, nomenclature Sandre 923."),
        _f("most_valid", "boolean",
           "Le point a été rendu par la passe most_valid, celle que le "
           "producteur arbitre. Ne se déduit pas du statut : sur les périodes "
           "récentes où rien de mieux n'existe, most_valid rend le brut."),
    ],
}

PRIMARY_KEYS = {
    "stations": ["code_station"],
    "coverage": ["code_station", "annee", "statut"],
    "ref_codes": ["type", "code"],
}

TABLES = ("stations", "coverage", "ref_codes")


def columns(table: str) -> list[str]:
    return [field["name"] for field in FIELDS[table]]


# --------------------------------------------------------------------------
#  datapackage.json
# --------------------------------------------------------------------------

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SOURCE_AJAX = "https://hydro.eaufrance.fr/stationhydro/ajax/{code}/series"
HUBEAU_DOC = "https://hubeau.eaufrance.fr/page/api-hydrometrie"
SANDRE_NSA = "https://api.sandre.eaufrance.fr/referentiels/v1/nsa.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _resource(folder: Path, table: str, rows: int) -> dict[str, Any]:
    path = folder / f"{table}.csv"
    resource = {
        "name": table,
        "path": f"{table}.csv",
        "format": "csv",
        "mediatype": "text/csv",
        "encoding": "utf-8",
        "bytes": path.stat().st_size,
        "hash": f"sha256:{sha256(path)}",
        "x_nb_lignes": rows,
        "dialect": {"delimiter": ",", "quoteChar": '"', "header": True,
                    "lineTerminator": "\n"},
        "schema": {
            "fields": FIELDS[table],
            "primaryKey": PRIMARY_KEYS[table],
            "missingValues": [""],
        },
    }
    if table == "coverage":
        resource["schema"]["foreignKeys"] = [{
            "fields": "code_station",
            "reference": {"resource": "stations", "fields": "code_station"},
        }]
    return resource


def _measurements_resources(folder: Path) -> list[dict[str, Any]]:
    """One entry per station, so that its fingerprint is its own.

    That granularity is the point: at the next pass, a station whose hash
    moved is a station whose past was rewritten, which is exactly what a
    revised rating curve does and what no date based logic would catch.
    """
    measurements = folder / "measurements"
    if not measurements.exists():
        return []
    entries = []
    for path in sorted(measurements.glob("*.parquet")):
        entries.append({
            "name": f"measurements/{path.stem}",
            "path": f"measurements/{path.name}",
            "format": "parquet",
            "mediatype": "application/vnd.apache.parquet",
            "bytes": path.stat().st_size,
            "hash": f"sha256:{sha256(path)}",
            "x_code_station": path.stem,
        })
    return entries


def build_datapackage(folder: Path, row_counts: dict[str, int],
                      coverage: dict[str, Any],
                      statuses: Sequence[str]) -> dict[str, Any]:
    """Machine readable metadata for the dataset (Frictionless v2).

    The parquet files are described outside "resources": a Frictionless
    validator cannot check a binary resource and would wrongly report the
    package invalid. They stay fully documented here, with their fingerprints.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "$schema": "https://datapackage.org/profiles/2.0/datapackage.json",
        "name": "hydroportail-debit-instantane",
        "title": "Débit instantané des cours d'eau français, depuis HydroPortail",
        "description": (
            "Chroniques de debit instantane telles qu'HydroPortail les diffuse, "
            "a leur pas natif, avec les quatre codes de qualite du Sandre "
            "conservés par point. Une ligne par point publie : un horodatage "
            "publie a deux niveaux de validation donne deux lignes, ce qui est "
            "la stricte verite de ce que la source diffuse. Aucun filtrage de "
            "qualite n'est applique."
        ),
        "version": SCRIPT_VERSION,
        "created": now,
        "keywords": ["debit", "hydrometrie", "instantane", "eclusee",
                     "cours d'eau", "France", "HydroPortail", "Sandre"],
        "licenses": [LICENSE],
        "sources": [
            {"title": "HydroPortail", "path": SOURCE_URL},
            {"title": "API Hub'Eau hydrométrie, référentiel des stations",
             "path": HUBEAU_DOC},
            {"title": "Nomenclatures Sandre 510, 515, 512 et 923", "path": SANDRE_NSA},
        ],
        "resources": [_resource(folder, table, row_counts.get(table, 0))
                      for table in TABLES if (folder / f"{table}.csv").exists()],
        "x_ressources_derivees": _measurements_resources(folder),
        "x_provenance": {
            "route": SOURCE_AJAX,
            "telecharge_le": now,
            "script": f"hydroportail v{SCRIPT_VERSION}",
            "passes": list(statuses),
            "note": (
                "Les valeurs sont reprises telles que servies, a deux "
                "transformations pres : la conversion des litres par seconde en "
                "m3/s, et le dedoublonnage de l'union des passes sur la ligne "
                "entiere. La colonne most_valid dit quelle passe a rendu le "
                "point ; elle ne se deduit pas du statut, puisque sur les "
                "periodes recentes la passe most_valid rend le point brut "
                "lui-meme. La table ref_codes.csv et les colonnes de resolution "
                "de coverage.csv sont ajoutees par ce script."
            ),
            "avertissements": [
                "Melanger les statuts par periode a un sens, c'est ce que fait "
                "le producteur ; les melanger par horodatage n'en a pas.",
                "La serie validee est une courbe a points de rupture, pas un "
                "echantillonnage : la lire sans interpoler sous-echantillonne "
                "sans le dire.",
                "qualification = 12 signifie « douteuse » et n'est pas rare : "
                "c'est le seul drapeau de qualite porte par chaque point.",
                "La resolution se decide station par station et annee par "
                "annee, d'ou coverage.csv.",
            ],
        },
        "x_couverture": coverage,
    }


def write_datapackage(folder: Path, content: dict[str, Any]) -> Path:
    path = folder / "datapackage.json"
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path
