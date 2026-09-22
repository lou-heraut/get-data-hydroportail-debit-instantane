#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Contrôles sur le jeu produit.

Quatre questions auxquelles les tests unitaires ne peuvent pas répondre, parce
qu'elles portent sur des données réelles et non sur des fonctions :

1. rien n'a été perdu entre ce que le service a servi et ce qui est sur disque ;
2. ce qu'on a est bien ce que Hub'Eau diffuse, au litre près ;
3. la passe pre_validated_and_validated reste contenue dans most_valid, ce qui
   est le pari sur lequel repose le choix de ne télécharger que deux passes ;
4. aucun code de qualité n'a échappé à la nomenclature figée.

Usage : python verifier_hydroportail.py --case 2026-09_jeu-de-test
"""

from __future__ import annotations

import argparse
import gzip
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

from hydroportail import api, paths
from hydroportail.download import DEFAULT_ROOT

logger = logging.getLogger("verification")


def _points_from_cache(cache: Path, code: str) -> pd.DataFrame:
    """Tout ce que le service a servi pour cette station, en Q instantané.

    Relu depuis les réponses brutes, sans repasser par le code de fusion :
    l'intérêt du contrôle est justement de ne pas refaire confiance à ce qu'on
    veut vérifier.
    """
    rows = []
    for file_path in sorted((cache / code).glob("*_Q_*.json.gz")):
        with gzip.open(file_path, "rt", encoding="utf-8") as stream:
            content = json.load(stream)
        if not isinstance(content, list):   # une fenêtre coupée en deux
            continue
        for point in content:
            rows.append((point["t"], int(point["v"]), int(point["s"]),
                         int(point["q"]), int(point["m"]), int(point["c"])))
    return pd.DataFrame(rows, columns=["t", "v", "s", "q", "m", "c"])


def check_no_loss(folder: Path, cache: Path) -> bool:
    """Tout point servi se retrouve dans measurements/, et rien n'y a été inventé."""
    logger.info("1. Non-perte entre le cache et les mesures")
    measurements = folder / "measurements"
    intact = True

    for file_path in sorted(measurements.glob("*.parquet")):
        code = file_path.stem
        served = _points_from_cache(cache, code)
        if served.empty:
            logger.warning("   %s : aucun cache, contrôle impossible", code)
            continue
        served = served.drop_duplicates()

        kept = pd.read_parquet(file_path)
        kept = pd.DataFrame({
            "t": kept["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "v": (kept["debit_m3s"] * 1000).round().astype("int64"),
            "s": kept["statut"].astype("int64"),
            "q": kept["qualification"].astype("int64"),
            "m": kept["methode"].astype("int64"),
            "c": kept["continuite"].astype("int64"),
        })

        joined_frame = served.merge(kept, how="outer", indicator=True)
        lost = int((joined_frame["_merge"] == "left_only").sum())
        invented = int((joined_frame["_merge"] == "right_only").sum())
        if lost or invented:
            intact = False
            logger.error("   %s : %d point(s) perdu(s), %d inventé(s)",
                         code, lost, invented)
        else:
            logger.info("   %s : %s points servis, tous présents",
                        code, f"{len(served):,}".replace(",", " "))
    return intact


def check_against_hubeau(folder: Path, code: str = "V720001002") -> bool:
    """Ce qu'on a est-il ce que Hub'Eau diffuse, au litre près.

    Hub'Eau ne sert l'instantané que sur un mois glissant, donc le recoupement
    ne peut porter que sur le récent. C'est suffisant : il s'agit d'établir que
    les deux services parlent bien de la même donnée, pas de tout revérifier.
    """
    logger.info("2. Recoupement avec Hub'Eau sur %s", code)
    file_path = folder / "measurements" / f"{code}.parquet"
    if not file_path.exists():
        logger.warning("   %s absent, contrôle sauté", code)
        return True

    try:
        http_response = requests.get(
            "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr",
            params={"code_entite": code, "grandeur_hydro": "Q",
                    "size": 20000, "format": "json"},
            headers={"User-Agent": api.USER_AGENT.format(version="verif")},
            timeout=300)
        observations = http_response.json().get("data") or []
    except (requests.RequestException, ValueError) as failure:
        logger.warning("   Hub'Eau injoignable (%s), contrôle sauté", failure)
        return True

    if not observations:
        logger.warning("   Hub'Eau ne rend rien, contrôle sauté")
        return True

    # Interrogé par code de station, Hub'Eau ne double pas ; c'est par code de
    # site qu'il rend chaque observation deux fois.
    theirs = pd.DataFrame({
        "t": [row["date_obs"] for row in observations],
        "v_hubeau": [float(row["resultat_obs"]) / 1000 for row in observations],
    }).drop_duplicates(subset="t")

    ours = pd.read_parquet(file_path)
    ours = ours[ours["statut"] == 4]
    ours = pd.DataFrame({
        "t": ours["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "v_ours": ours["debit_m3s"],
    }).drop_duplicates(subset="t")

    common = theirs.merge(ours, on="t")
    if common.empty:
        logger.warning("   aucun horodatage commun, contrôle sauté")
        return True
    gap = (common["v_hubeau"] - common["v_ours"]).abs().max()
    logger.info("   %d horodatages communs sur %d servis par Hub'Eau",
                len(common), len(theirs))
    logger.info("   écart maximal : %.6f m3/s", gap)
    if gap > 0.001:
        logger.error("   les deux services ne servent pas la même donnée")
        return False
    return True


def check_status_inclusion(folder: Path, cache: Path,
                           codes: list[str] | None = None) -> bool:
    """most_valid contient-elle toujours pre_validated_and_validated.

    C'est le pari qui autorise à ne télécharger que deux passes. Il a été
    vérifié sur huit cas, ce qui n'est pas une garantie : plutôt que de le
    laisser en pari, on le contrôle sur un échantillon à chaque passage. S'il
    casse un jour, on l'apprend ici et non au milieu d'une analyse.
    """
    logger.info("3. Inclusion de pre_validated_and_validated dans most_valid")
    stations = pd.read_csv(folder / "stations.csv", dtype={"code_station": "string"})
    carrying_codes = stations[stations["porte_debit"].astype(bool)]["code_station"].tolist()
    codes = codes or carrying_codes[:3]
    last_day = date.today() - timedelta(days=1)
    start = last_day - timedelta(days=120)
    correct = True

    for code in codes:
        file_path = folder / "measurements" / f"{code}.parquet"
        if not file_path.exists():
            continue
        intermediate = api.fetch_series(cache, code, "pre_validated_and_validated",
                                        start, last_day)
        if not intermediate:
            logger.info("   %s : rien de pré-validé sur la période, rien à vérifier", code)
            continue
        ours = pd.read_parquet(file_path)
        known_names = set(zip(ours["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         ours["statut"].astype(int)))
        missing_codes = [point for point in intermediate
                     if (point["t"], int(point["s"])) not in known_names]
        if missing_codes:
            correct = False
            logger.error("   %s : %d point(s) pré-validés absents de measurements/ ; "
                         "l'inclusion ne tient plus, il faut télécharger la "
                         "troisième passe", code, len(missing_codes))
        else:
            logger.info("   %s : %d points pré-validés, tous présents",
                        code, len(intermediate))
    return correct


def check_codes(folder: Path) -> bool:
    """Aucun code de qualité n'a échappé à la nomenclature figée."""
    logger.info("4. Codes de qualité connus")
    reference = pd.read_csv(folder / "ref_codes.csv")
    known_names = set(zip(reference["type"], reference["code"]))
    unknown_values = set()
    for file_path in sorted((folder / "measurements").glob("*.parquet")):
        frame = pd.read_parquet(file_path, columns=["statut", "qualification",
                                                    "methode", "continuite"])
        for column, kind in (("statut", "s"), ("qualification", "q"),
                             ("methode", "m"), ("continuite", "c")):
            for value in frame[column].unique():
                if (kind, int(value)) not in known_names:
                    unknown_values.add((kind, int(value)))
    if unknown_values:
        logger.error("   codes absents de ref_codes.csv : %s", sorted(unknown_values))
        logger.error("   la nomenclature Sandre a bougé, voir SOURCE.md")
        return False
    logger.info("   tous les codes rencontrés sont décrits")
    return True


def check_integrity(folder: Path) -> bool:
    """coverage.csv ne parle que de stations que stations.csv connaît."""
    logger.info("5. Intégrité référentielle")
    stations = pd.read_csv(folder / "stations.csv", dtype={"code_station": "string"})
    coverage = pd.read_csv(folder / "coverage.csv", dtype={"code_station": "string"})
    orphans = set(coverage["code_station"]) - set(stations["code_station"])
    if orphans:
        logger.error("   %d station(s) de coverage.csv absente(s) de "
                     "stations.csv : %s", len(orphans), sorted(orphans))
        return False
    logger.info("   %d lignes de couverture, aucune orpheline", len(coverage))
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Contrôle le jeu produit par un cas.")
    parser.add_argument("--case", required=True, metavar="NOM",
                        help="nom du cas à contrôler, ex. 2026-09_jeu-de-test")
    parser.add_argument("--root", default=DEFAULT_ROOT, metavar="CHEMIN",
                        help=f"racine des données (défaut : {DEFAULT_ROOT})")
    args = parser.parse_args(argv)
    folder, cache = paths(args.case, args.root)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not (folder / "stations.csv").exists():
        print(f"Aucun jeu de données dans {folder}.", file=sys.stderr)
        return 1

    results = [
        check_no_loss(folder, cache),
        check_against_hubeau(folder),
        check_status_inclusion(folder, cache),
        check_codes(folder),
        check_integrity(folder),
    ]
    logger.info("")
    if all(results):
        logger.info("Tous les contrôles passent.")
        return 0
    logger.error("%d contrôle(s) en échec.", sum(1 for ok in results if not ok))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
