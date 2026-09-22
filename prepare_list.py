#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Met au propre la liste de stations reçue, et la confronte au service.

La demande arrive sous la forme d'un tableur : des libellés, et des codes qui
sont pour l'essentiel des codes de **site** et non des codes de **station**. Or
les chroniques vivent sur les stations, et un code de site interrogé tel quel
rend la série de sa station de référence sans dire laquelle. Passer le tableur
à `--file` donnerait donc un jeu d'apparence normale et d'origine inconnue.
Voir la section « Site et station » de SOURCE.md.

Ce script fait trois choses, dans cet ordre :

1. il lit le tableur et normalise ce qui s'y trouve, codes comme libellés ;
2. il demande à Hub'Eau les stations de chaque site ;
3. il demande à HydroPortail, pour chaque station candidate, si elle porte du
   débit instantané, par la carte de couverture `QIXnJ` qui coûte une requête
   de deux secondes et ne télécharge aucune chronique.

Il écrit une table de correspondance, une ligne par code demandé, qui dit quelle
station a été retenue et pourquoi, et signale ce qui demande un regard humain.
Cette table se relit et se corrige à la main : c'est elle qu'on donnera ensuite
à `--file`, jamais le tableur.

Usage : python preparer_liste.py [--case 2026-09_eclusees-rmc]
"""

from __future__ import annotations

import argparse
import difflib
import logging
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from hydroportail import api, paths
from hydroportail.download import DEFAULT_ROOT

logger = logging.getLogger("preparation")

#: Un sous-dossier par demande, nommé `aaaa-mm_sujet`, et à l'intérieur des noms
#: fixes : le dossier porte la date, les fichiers portent leur rôle. La
#: convention et ce qui va où sont dans CLAUDE.md.
CASES = Path("cases")
DEFAULT_CASE = "2026-09_eclusees-rmc"
SPREADSHEET = "received-list.xlsx"
OUTPUT = "resolved-stations.csv"
ARBITRATIONS = "arbitrations.csv"
SELECTED = "stations.txt"

#: Le vocabulaire de la colonne `cas` d'arbitrages.csv. Court et tenu : il sert
#: à un lecteur pressé qui cherche si sa situation ressemble à une des nôtres.
ARBITRATION_KINDS = ("remplacement", "deux-exploitants", "qualite-declaree")

#: Espace de nommage du format xlsx, qui n'est qu'un zip de XML.
_XL = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

#: Les colonnes attendues dans le tableur reçu, et leur nom de sortie.
HEADERS = {
    "Rivieres": "cours_eau_demande",
    "Station_HY": "libelle_demande",
    "Code_hydroportail": "code_demande",
    "Producteur": "producteur_demande",
}

COLUMNS = [
    "ligne_source", "code_demande", "type_code_demande", "libelle_demande",
    "cours_eau_demande", "producteur_demande",
    "code_site", "code_station", "libelle_station", "cours_eau_station",
    "en_service", "stations_du_site", "stations_avec_debit",
    "date_debut_instantane", "date_fin_instantane", "jours_avec_donnees",
    "concordance_libelle", "choix", "alerte",
]


# --------------------------------------------------------------------------
#  Lire le tableur, sans dépendance supplémentaire
# --------------------------------------------------------------------------

def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """La table des chaînes, où les cellules de texte pointent par indice."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    racine = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(bout.text or "" for bout in item.iter(_XL + "t"))
            for item in racine]


def _cell_value(cellule: ET.Element, chaines: Sequence[str]) -> str:
    """Le contenu d'une cellule, en texte, quel que soit son mode de stockage."""
    if cellule.get("t") == "inlineStr":
        return "".join(bout.text or "" for bout in cellule.iter(_XL + "t"))
    brut = cellule.find(_XL + "v")
    if brut is None or brut.text is None:
        return ""
    if cellule.get("t") == "s":
        indice = int(brut.text)
        return chaines[indice] if indice < len(chaines) else ""
    return brut.text


def read_spreadsheet(chemin: Path) -> list[dict[str, str]]:
    """Le tableur reçu, lu avec la bibliothèque standard.

    Un .xlsx est un zip de XML, et openpyxl ne servirait ici qu'à lire ce
    fichier unique : la trentaine de lignes ci-dessus évite une dépendance de
    plus dans un dépôt qui n'en a que trois. La lecture est stricte, et une
    structure inattendue lève plutôt que de passer inaperçue.
    """
    with zipfile.ZipFile(chemin) as archive:
        chaines = _shared_strings(archive)
        feuilles = [nom for nom in archive.namelist()
                    if nom.startswith("xl/worksheets/sheet")]
        if len(feuilles) != 1:
            raise ValueError(f"{chemin} : {len(feuilles)} feuilles, une seule attendue.")
        racine = ET.fromstring(archive.read(feuilles[0]))

    brutes: list[tuple[int, dict[str, str]]] = []
    for ligne in racine.iter(_XL + "row"):
        cellules: dict[str, str] = {}
        for cellule in ligne.iter(_XL + "c"):
            colonne = "".join(c for c in cellule.get("r", "") if c.isalpha())
            cellules[colonne] = _cell_value(cellule, chaines).strip()
        brutes.append((int(ligne.get("r", 0)), cellules))

    if not brutes:
        raise ValueError(f"{chemin} : feuille vide.")
    _, entete = brutes[0]
    noms = {colonne: HEADERS[titre] for colonne, titre in entete.items()
            if titre in HEADERS}
    manquantes = set(HEADERS.values()) - set(noms.values())
    if manquantes:
        raise ValueError(f"{chemin} : colonnes absentes, {', '.join(sorted(manquantes))}.")

    lignes = []
    for numero, cellules in brutes[1:]:
        ligne = {nom: cellules.get(colonne, "") for colonne, nom in noms.items()}
        if not any(ligne.values()):
            continue
        ligne["ligne_source"] = numero
        lignes.append(ligne)
    return lignes


def read_arbitrations(chemin: Path) -> dict[str, tuple[str, str, str]]:
    """Les choix faits à la main, par code demandé, avec leur motif.

    Le script ne sait trancher qu'au libellé, et le libellé d'une liste désigne
    un site, pas un instrument : là où plusieurs stations d'un même site portent
    du débit, la décision revient à quelqu'un qui sait ce qu'il cherche. Elle
    vit ici plutôt que dans le CSV produit, qui se réécrit à chaque passage, et
    elle porte son motif pour que personne n'ait à refaire l'enquête.
    """
    if not chemin.exists():
        return {}
    table = pd.read_csv(chemin, dtype=str).fillna("")
    manquantes = {"code_demande", "code_station", "cas", "motif"} - set(table.columns)
    if manquantes:
        raise ValueError(f"{chemin} : colonnes absentes, {', '.join(sorted(manquantes))}.")
    inconnus = sorted(set(table["cas"].str.strip()) - set(ARBITRATION_KINDS))
    if inconnus:
        raise ValueError(f"{chemin} : cas inconnu(s), {', '.join(inconnus)}. "
                         f"Le vocabulaire est {', '.join(ARBITRATION_KINDS)}.")
    return {ligne.code_demande.strip(): (ligne.code_station.strip(),
                                         ligne.cas.strip(), ligne.motif.strip())
            for ligne in table.itertuples() if ligne.code_demande.strip()}


# --------------------------------------------------------------------------
#  Normaliser
# --------------------------------------------------------------------------

_ESPACES = re.compile(r"\s+")
_SITE = re.compile(r"[A-Z][0-9A-Z]{7}")
_STATION = re.compile(r"[A-Z][0-9A-Z]{9}")


def normalise_code(brut: str) -> str:
    """Le code sans ses espaces internes ni sa casse.

    Trois codes du tableur en portent une, ``W103 0003`` par exemple, ce qui
    suffirait à les rendre introuvables.
    """
    return _ESPACES.sub("", (brut or "").replace(" ", " ")).upper()


def code_kind(code: str) -> str:
    """``site`` à huit caractères, ``station`` à dix, ``inconnu`` sinon."""
    if _SITE.fullmatch(code):
        return "site"
    if _STATION.fullmatch(code):
        return "station"
    return "inconnu"


def _comparable(texte: str) -> str:
    """Un libellé réduit à ce qui se compare : sans accent, ponctuation ni casse."""
    decompose = unicodedata.normalize("NFD", texte or "")
    sans_accent = "".join(c for c in decompose if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", sans_accent.lower()).split())


def similarity(attendu: str, trouve: str) -> float:
    """Ressemblance de deux libellés, entre 0 et 1.

    Le tableur écrit ``L_Arc_a_Aiguebelle`` là où le référentiel écrit
    ``L'Arc à Aiguebelle`` : la comparaison sert à repérer le code qui désigne
    autre chose que ce que son libellé annonce, et à départager les stations
    d'un même site.
    """
    if not attendu or not trouve:
        return 0.0
    return round(difflib.SequenceMatcher(
        None, _comparable(attendu), _comparable(trouve)).ratio(), 3)


def _extent(points: Sequence[dict[str, Any]]) -> tuple[str, str, int]:
    """Premier jour, dernier jour, jours distincts portant de la donnée.

    Même règle que l'inventaire, jours distincts et non points, pour que les
    deux tables disent la même chose de la même station.
    """
    jours = sorted({str(point.get("t", ""))[:10] for point in points
                    if len(str(point.get("t", ""))) >= 10})
    return (jours[0], jours[-1], len(jours)) if jours else ("", "", 0)


# --------------------------------------------------------------------------
#  Résoudre
# --------------------------------------------------------------------------

def _candidates(lignes, records, par_site) -> dict[str, list[str]]:
    """Les stations à sonder pour chaque code demandé.

    Pour un code de site, les stations que Hub'Eau lui rattache. Pour un code de
    station, ce code et ses soeurs, parce qu'une liste fournie par un tiers peut
    désigner la station qui ne porte que la hauteur d'eau.
    """
    candidates = {}
    for ligne in lignes:
        code, genre = ligne["code_demande"], ligne["type_code_demande"]
        site = ligne["code_site"]
        soeurs = [row.get("code_station") for row in par_site.get(site, [])
                  if row.get("code_station")]
        if genre == "station":
            candidates[code] = sorted(set(soeurs) | {code})
        else:
            candidates[code] = sorted(set(soeurs))
    return candidates


def _select(ligne, candidates, jours, records, non_servies):
    """La station retenue pour un code demandé, et la phrase qui dit pourquoi."""
    code, genre = ligne["code_demande"], ligne["type_code_demande"]
    porteuses = [c for c in candidates if jours.get(c, 0) > 0]

    def rang(station: str) -> tuple[float, int]:
        libelle = (records.get(station) or {}).get("libelle_station", "")
        return (similarity(ligne["libelle_demande"], libelle), jours.get(station, 0))

    if not porteuses:
        if not candidates:
            return "", "aucune station rattachée à ce code"
        if set(candidates) <= set(non_servies):
            return "", "HydroPortail ne sert aucune station de ce site"
        if any(code in non_servies for code in candidates):
            # L'absence n'est pas établie : une station du site n'a pas pu être
            # sondée, et une station non sondée ne prouve rien.
            return "", ("aucune station sondable du site ne porte de débit, "
                        "une autre est refusée par le service")
        return "", "aucune station du site ne porte de débit instantané"
    if genre == "station" and code in porteuses:
        return code, "code de station fourni, il porte du débit"
    if genre == "station":
        return max(porteuses, key=rang), "station fournie sans débit, remplacée par une soeur du site"
    if len(porteuses) == 1:
        return porteuses[0], "seule station du site à porter du débit"
    return max(porteuses, key=rang), "plusieurs stations du site portent du débit, retenue par son libellé"


#: Au delà de ce rapport, une soeur mieux fournie que la station retenue mérite
#: un regard : le libellé a tranché, la donnée dit peut-être autre chose.
SIBLING_RATIO = 2.0


def _warnings(ligne: dict[str, Any], candidates: Sequence[str],
             jours: dict[str, int], non_servies: dict[str, str],
             arbitre: bool = False) -> str:
    """Ce qui demande un regard humain sur cette ligne, en clair.

    Une ligne arbitrée garde ce qui relève du service, qui reste vrai, et perd
    ce qui relevait du choix : il a été fait, et le motif est dans « choix ».
    """
    motifs = []
    for code in candidates:
        if code in non_servies:
            motifs.append(f"HydroPortail {non_servies[code]} {code}")
    retenue = ligne["code_station"]
    if retenue and not arbitre:
        soeurs = [(jours.get(code, 0), code) for code in candidates if code != retenue]
        if soeurs:
            mieux, code = max(soeurs)
            if mieux >= SIBLING_RATIO * max(jours.get(retenue, 0), 1):
                motifs.append(f"{code} porte {mieux} jours contre "
                              f"{jours.get(retenue, 0)} à la station retenue")
    if ligne["type_code_demande"] == "inconnu":
        motifs.append("code de forme inattendue")
    if not ligne["stations_du_site"]:
        motifs.append("code inconnu du référentiel Hub'Eau")
    if not ligne["code_station"]:
        # Le pourquoi est dans « choix », qui distingue l'absence établie de la
        # station que le service a refusé de sonder.
        motifs.append("aucune station retenue")
    if not arbitre and len(str(ligne["stations_avec_debit"]).split(";")) > 1:
        motifs.append("plusieurs stations du site portent du débit")
    if not arbitre and ligne["code_station"] and ligne["concordance_libelle"] < 0.6:
        motifs.append("libellé éloigné de celui du référentiel")
    if ligne["code_station"] and ligne["type_code_demande"] == "station" \
            and ligne["code_station"] != ligne["code_demande"]:
        motifs.append("station demandée remplacée")
    return " ; ".join(motifs)


def prepare(case: str = DEFAULT_CASE, root: str = DEFAULT_ROOT) -> pd.DataFrame:
    """Du tableur reçu à la table de correspondance, en trois passes."""
    demande = CASES / case
    if not demande.is_dir():
        raise FileNotFoundError(f"{demande} : ce dossier de demande n'existe pas.")
    sortie = demande / OUTPUT
    _, cache = paths(case, root)
    lignes = read_spreadsheet(demande / SPREADSHEET)
    choisies = read_arbitrations(demande / ARBITRATIONS)
    if choisies:
        logger.info("%d arbitrage(s) lu(s) dans %s.", len(choisies), demande / ARBITRATIONS)
    logger.info("Tableur lu : %d ligne(s).", len(lignes))

    for ligne in lignes:
        ligne["code_demande"] = normalise_code(ligne["code_demande"])
        ligne["type_code_demande"] = code_kind(ligne["code_demande"])
        ligne["code_site"] = ligne["code_demande"][:8]

    genres = pd.Series([ligne["type_code_demande"] for ligne in lignes]).value_counts()
    logger.info("  dont %s.", ", ".join(f"{nombre} code(s) de {genre}"
                                        for genre, nombre in genres.items()))

    # Hub'Eau d'abord : il est rapide, et il dit quelles stations sonder.
    demandes = [ligne["code_demande"] for ligne in lignes
                if ligne["type_code_demande"] == "station"]
    records = api.station_records(demandes) if demandes else {}
    for ligne in lignes:
        connu = records.get(ligne["code_demande"], {})
        if connu.get("code_site"):
            ligne["code_site"] = connu["code_site"]

    sites = sorted({ligne["code_site"] for ligne in lignes if ligne["code_site"]})
    logger.info("Référentiel Hub'Eau : %d site(s) à résoudre.", len(sites))
    par_site = api.site_stations(sites)
    for site, rows in par_site.items():
        for row in rows:
            if row.get("code_station"):
                records.setdefault(row["code_station"], row)

    candidates = _candidates(lignes, records, par_site)
    # Une station arbitrée se sonde comme les autres, même si le référentiel ne
    # la rattache pas au site demandé : le choix humain n'a pas à se justifier
    # auprès du script, mais sa couverture doit figurer dans la table.
    a_sonder = sorted({code for liste in candidates.values() for code in liste}
                      | {code for code, _, _ in choisies.values() if code})
    logger.info("HydroPortail : %d station(s) candidates à sonder, "
                "une requête rapide chacune.", len(a_sonder))

    jours: dict[str, int] = {}
    etendues: dict[str, tuple[str, str, int]] = {}
    non_servies: dict[str, str] = {}
    for numero, code in enumerate(a_sonder, start=1):
        try:
            debut, fin, nombre = _extent(api.coverage_map(cache, code))
        except (api.UnservedStation, api.UnknownStation) as erreur:
            # Ou le service ignore ce code, ou il échoue dessus quelle que soit
            # la fenêtre. Une campagne de cinquante stations ne peut pas
            # s'arrêter là : on le note et on continue, et la table le dira.
            inconnue = isinstance(erreur, api.UnknownStation)
            non_servies[code] = "ne connaît pas" if inconnue else "ne sert pas"
            debut, fin, nombre = "", "", 0
            logger.warning("  [%d/%d] %s : HydroPortail %s cette station "
                           "(HTTP %s)", numero, len(a_sonder), code,
                           non_servies[code], "404" if inconnue else "500")
        else:
            logger.info("  [%d/%d] %s : %s", numero, len(a_sonder), code,
                        f"{nombre} jours, {debut} à {fin}" if nombre
                        else "aucun débit instantané")
        jours[code], etendues[code] = nombre, (debut, fin, nombre)

    for ligne in lignes:
        code = ligne["code_demande"]
        retenue, choix = _select(ligne, candidates[code], jours, records, non_servies)
        arbitre = code in choisies
        if arbitre:
            retenue, cas_arbitrage, motif = choisies[code]
            choix = f"arbitré à la main, {cas_arbitrage} : {motif}"
        record = records.get(retenue, {}) if retenue else {}
        debut, fin, nombre = etendues.get(retenue, ("", "", 0))
        ligne.update({
            "code_station": retenue,
            "libelle_station": record.get("libelle_station", ""),
            "cours_eau_station": record.get("libelle_cours_eau", ""),
            "en_service": record.get("en_service", ""),
            "stations_du_site": ";".join(candidates[code]),
            # Le nombre de jours accolé à chaque code : sans lui, l'arbitrage
            # entre deux stations d'un même site demanderait de tout resonder.
            "stations_avec_debit": ";".join(
                f"{c}:{jours[c]}" for c in candidates[code] if jours.get(c, 0) > 0),
            "date_debut_instantane": debut,
            "date_fin_instantane": fin,
            # Vide plutôt que zéro quand rien n'a été retenu : zéro voudrait
            # dire « mesuré à zéro », ce qui n'est pas la même chose.
            "jours_avec_donnees": nombre if retenue else "",
            "concordance_libelle": similarity(
                ligne["libelle_demande"], record.get("libelle_station", "")
            ) if retenue else "",
            "choix": choix,
        })
        ligne["alerte"] = _warnings(ligne, candidates[code], jours, non_servies, arbitre)

    table = pd.DataFrame(lignes, columns=COLUMNS)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(sortie, index=False, encoding="utf-8")
    logger.info("Écrit %s (%d lignes).", sortie, len(table))

    # Le contrat entre la demande et le téléchargement : un code par ligne, et
    # rien d'autre. Le téléchargeur n'a pas à savoir par quel chemin la liste
    # est arrivée.
    retenues = sorted({code for code in table["code_station"] if code})
    (demande / SELECTED).write_text("\n".join(retenues) + "\n", encoding="utf-8")
    logger.info("Écrit %s (%d stations).", demande / SELECTED, len(retenues))
    return table


def report(table: pd.DataFrame) -> None:
    """Ce qu'il faut regarder avant de se servir de la table."""
    retenues = table[table["code_station"] != ""]
    print(f"\n{len(table)} codes demandés, {retenues['code_station'].nunique()} "
          f"stations retenues, {len(table) - len(retenues)} sans débit instantané.")
    print("\nComment chaque station a été retenue :")
    for choix, nombre in table["choix"].str.split(" : ").str[0].value_counts().items():
        print(f"  {nombre:3d}  {choix}")
    alertes = table[table["alerte"] != ""]
    if alertes.empty:
        return
    print(f"\n{len(alertes)} ligne(s) à regarder :")
    for _, ligne in alertes.iterrows():
        print(f"  {ligne['code_demande']}  {ligne['libelle_demande'][:46]:46s} "
              f"-> {ligne['code_station'] or '(rien)':10s}  {ligne['alerte']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Met au propre la liste de stations reçue et la confronte au service.")
    parser.add_argument("--case", default=DEFAULT_CASE,
                        help=f"sous-dossier de {CASES} (défaut : {DEFAULT_CASE})")
    parser.add_argument("--root", default=DEFAULT_ROOT, metavar="CHEMIN",
                        help=f"racine des données (défaut : {DEFAULT_ROOT}), où "
                             "vit le cache des réponses partagé par les cas")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    try:
        table = prepare(args.case, args.root)
    except (ValueError, FileNotFoundError, api.APIError) as erreur:
        print(f"\nErreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu. Relancez : ce qui est déjà en cache ne sera pas "
              "redemandé.", file=sys.stderr)
        return 130
    report(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
