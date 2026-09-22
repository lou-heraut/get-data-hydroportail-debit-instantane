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

Usage : python verifier_hydroportail.py --cas 2026-09_jeu-de-test
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

from hydroportail import api, chemins
from hydroportail.download import DEFAULT_ROOT

logger = logging.getLogger("verification")


def _points_du_cache(cache: Path, code: str) -> pd.DataFrame:
    """Tout ce que le service a servi pour cette station, en Q instantané.

    Relu depuis les réponses brutes, sans repasser par le code de fusion :
    l'intérêt du contrôle est justement de ne pas refaire confiance à ce qu'on
    veut vérifier.
    """
    lignes = []
    for fichier in sorted((cache / code).glob("*_Q_*.json.gz")):
        with gzip.open(fichier, "rt", encoding="utf-8") as flux:
            contenu = json.load(flux)
        if not isinstance(contenu, list):   # une fenêtre coupée en deux
            continue
        for point in contenu:
            lignes.append((point["t"], int(point["v"]), int(point["s"]),
                           int(point["q"]), int(point["m"]), int(point["c"])))
    return pd.DataFrame(lignes, columns=["t", "v", "s", "q", "m", "c"])


def verifier_non_perte(dossier: Path, cache: Path) -> bool:
    """Tout point servi se retrouve dans mesures/, et rien n'y a été inventé."""
    logger.info("1. Non-perte entre le cache et les mesures")
    mesures = dossier / "mesures"
    intact = True

    for fichier in sorted(mesures.glob("*.parquet")):
        code = fichier.stem
        servi = _points_du_cache(cache, code)
        if servi.empty:
            logger.warning("   %s : aucun cache, contrôle impossible", code)
            continue
        servi = servi.drop_duplicates()

        garde = pd.read_parquet(fichier)
        garde = pd.DataFrame({
            "t": garde["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "v": (garde["debit_m3s"] * 1000).round().astype("int64"),
            "s": garde["statut"].astype("int64"),
            "q": garde["qualification"].astype("int64"),
            "m": garde["methode"].astype("int64"),
            "c": garde["continuite"].astype("int64"),
        })

        fusion = servi.merge(garde, how="outer", indicator=True)
        perdus = int((fusion["_merge"] == "left_only").sum())
        inventes = int((fusion["_merge"] == "right_only").sum())
        if perdus or inventes:
            intact = False
            logger.error("   %s : %d point(s) perdu(s), %d inventé(s)",
                         code, perdus, inventes)
        else:
            logger.info("   %s : %s points servis, tous présents",
                        code, f"{len(servi):,}".replace(",", " "))
    return intact


def verifier_recoupement_hubeau(dossier: Path, code: str = "V720001002") -> bool:
    """Ce qu'on a est-il ce que Hub'Eau diffuse, au litre près.

    Hub'Eau ne sert l'instantané que sur un mois glissant, donc le recoupement
    ne peut porter que sur le récent. C'est suffisant : il s'agit d'établir que
    les deux services parlent bien de la même donnée, pas de tout revérifier.
    """
    logger.info("2. Recoupement avec Hub'Eau sur %s", code)
    fichier = dossier / "mesures" / f"{code}.parquet"
    if not fichier.exists():
        logger.warning("   %s absent, contrôle sauté", code)
        return True

    try:
        reponse = requests.get(
            "https://hubeau.eaufrance.fr/api/v2/hydrometrie/observations_tr",
            params={"code_entite": code, "grandeur_hydro": "Q",
                    "size": 20000, "format": "json"},
            headers={"User-Agent": api.USER_AGENT.format(version="verif")},
            timeout=300)
        donnees = reponse.json().get("data") or []
    except (requests.RequestException, ValueError) as erreur:
        logger.warning("   Hub'Eau injoignable (%s), contrôle sauté", erreur)
        return True

    if not donnees:
        logger.warning("   Hub'Eau ne rend rien, contrôle sauté")
        return True

    # Interrogé par code de station, Hub'Eau ne double pas ; c'est par code de
    # site qu'il rend chaque observation deux fois.
    leur = pd.DataFrame({
        "t": [ligne["date_obs"] for ligne in donnees],
        "v_hubeau": [float(ligne["resultat_obs"]) / 1000 for ligne in donnees],
    }).drop_duplicates(subset="t")

    notre = pd.read_parquet(fichier)
    notre = notre[notre["statut"] == 4]
    notre = pd.DataFrame({
        "t": notre["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "v_nous": notre["debit_m3s"],
    }).drop_duplicates(subset="t")

    commun = leur.merge(notre, on="t")
    if commun.empty:
        logger.warning("   aucun horodatage commun, contrôle sauté")
        return True
    ecart = (commun["v_hubeau"] - commun["v_nous"]).abs().max()
    logger.info("   %d horodatages communs sur %d servis par Hub'Eau",
                len(commun), len(leur))
    logger.info("   écart maximal : %.6f m3/s", ecart)
    if ecart > 0.001:
        logger.error("   les deux services ne servent pas la même donnée")
        return False
    return True


def verifier_inclusion_statuts(dossier: Path, cache: Path,
                               codes: list[str] | None = None) -> bool:
    """most_valid contient-elle toujours pre_validated_and_validated.

    C'est le pari qui autorise à ne télécharger que deux passes. Il a été
    vérifié sur huit cas, ce qui n'est pas une garantie : plutôt que de le
    laisser en pari, on le contrôle sur un échantillon à chaque passage. S'il
    casse un jour, on l'apprend ici et non au milieu d'une analyse.
    """
    logger.info("3. Inclusion de pre_validated_and_validated dans most_valid")
    stations = pd.read_csv(dossier / "stations.csv", dtype={"code_station": "string"})
    porteuses = stations[stations["porte_debit"].astype(bool)]["code_station"].tolist()
    codes = codes or porteuses[:3]
    fin = date.today() - timedelta(days=1)
    debut = fin - timedelta(days=120)
    correct = True

    for code in codes:
        fichier = dossier / "mesures" / f"{code}.parquet"
        if not fichier.exists():
            continue
        intermediaires = api.fetch_series(cache, code, "pre_validated_and_validated",
                                          debut, fin)
        if not intermediaires:
            logger.info("   %s : rien de pré-validé sur la période, rien à vérifier", code)
            continue
        notre = pd.read_parquet(fichier)
        connus = set(zip(notre["date_obs"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         notre["statut"].astype(int)))
        manquants = [point for point in intermediaires
                     if (point["t"], int(point["s"])) not in connus]
        if manquants:
            correct = False
            logger.error("   %s : %d point(s) pré-validés absents de mesures/ ; "
                         "l'inclusion ne tient plus, il faut télécharger la "
                         "troisième passe", code, len(manquants))
        else:
            logger.info("   %s : %d points pré-validés, tous présents",
                        code, len(intermediaires))
    return correct


def verifier_codes(dossier: Path) -> bool:
    """Aucun code de qualité n'a échappé à la nomenclature figée."""
    logger.info("4. Codes de qualité connus")
    reference = pd.read_csv(dossier / "ref_codes.csv")
    connus = set(zip(reference["type"], reference["code"]))
    inconnus = set()
    for fichier in sorted((dossier / "mesures").glob("*.parquet")):
        frame = pd.read_parquet(fichier, columns=["statut", "qualification",
                                                  "methode", "continuite"])
        for colonne, genre in (("statut", "s"), ("qualification", "q"),
                               ("methode", "m"), ("continuite", "c")):
            for valeur in frame[colonne].unique():
                if (genre, int(valeur)) not in connus:
                    inconnus.add((genre, int(valeur)))
    if inconnus:
        logger.error("   codes absents de ref_codes.csv : %s", sorted(inconnus))
        logger.error("   la nomenclature Sandre a bougé, voir SOURCE.md")
        return False
    logger.info("   tous les codes rencontrés sont décrits")
    return True


def verifier_integrite(dossier: Path) -> bool:
    """couverture.csv ne parle que de stations que stations.csv connaît."""
    logger.info("5. Intégrité référentielle")
    stations = pd.read_csv(dossier / "stations.csv", dtype={"code_station": "string"})
    couverture = pd.read_csv(dossier / "couverture.csv", dtype={"code_station": "string"})
    orphelines = set(couverture["code_station"]) - set(stations["code_station"])
    if orphelines:
        logger.error("   %d station(s) de couverture.csv absente(s) de "
                     "stations.csv : %s", len(orphelines), sorted(orphelines))
        return False
    logger.info("   %d lignes de couverture, aucune orpheline", len(couverture))
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Contrôle le jeu produit par un cas.")
    parser.add_argument("--cas", required=True, metavar="NOM",
                        help="nom du cas à contrôler, ex. 2026-09_jeu-de-test")
    parser.add_argument("--racine", default=DEFAULT_ROOT, metavar="CHEMIN",
                        help=f"racine des données (défaut : {DEFAULT_ROOT})")
    args = parser.parse_args(argv)
    dossier, cache = chemins(args.cas, args.racine)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not (dossier / "stations.csv").exists():
        print(f"Aucun jeu de données dans {dossier}.", file=sys.stderr)
        return 1

    resultats = [
        verifier_non_perte(dossier, cache),
        verifier_recoupement_hubeau(dossier),
        verifier_inclusion_statuts(dossier, cache),
        verifier_codes(dossier),
        verifier_integrite(dossier),
    ]
    logger.info("")
    if all(resultats):
        logger.info("Tous les contrôles passent.")
        return 0
    logger.error("%d contrôle(s) en échec.", sum(1 for ok in resultats if not ok))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
