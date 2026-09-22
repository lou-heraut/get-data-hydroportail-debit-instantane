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
    xml_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    return ["".join(fragment.text or "" for fragment in item.iter(_XL + "t"))
            for item in xml_root]


def _cell_value(cell: ET.Element, strings: Sequence[str]) -> str:
    """Le contenu d'une cellule, en texte, quel que soit son mode de stockage."""
    if cell.get("t") == "inlineStr":
        return "".join(fragment.text or "" for fragment in cell.iter(_XL + "t"))
    element = cell.find(_XL + "v")
    if element is None or element.text is None:
        return ""
    if cell.get("t") == "s":
        position = int(element.text)
        return strings[position] if position < len(strings) else ""
    return element.text


def read_spreadsheet(path: Path) -> list[dict[str, str]]:
    """Le tableur reçu, lu avec la bibliothèque standard.

    Un .xlsx est un zip de XML, et openpyxl ne servirait ici qu'à lire ce
    fichier unique : la trentaine de lignes ci-dessus évite une dépendance de
    plus dans un dépôt qui n'en a que trois. La lecture est stricte, et une
    structure inattendue lève plutôt que de passer inaperçue.
    """
    with zipfile.ZipFile(path) as archive:
        strings = _shared_strings(archive)
        sheets = [name for name in archive.namelist()
                  if name.startswith("xl/worksheets/sheet")]
        if len(sheets) != 1:
            raise ValueError(f"{path} : {len(sheets)} feuilles, une seule attendue.")
        xml_root = ET.fromstring(archive.read(sheets[0]))

    raw_rows: list[tuple[int, dict[str, str]]] = []
    for xml_row in xml_root.iter(_XL + "row"):
        cells: dict[str, str] = {}
        for cell in xml_row.iter(_XL + "c"):
            column = "".join(c for c in cell.get("r", "") if c.isalpha())
            cells[column] = _cell_value(cell, strings).strip()
        raw_rows.append((int(xml_row.get("r", 0)), cells))

    if not raw_rows:
        raise ValueError(f"{path} : feuille vide.")
    _, header = raw_rows[0]
    names = {column: HEADERS[heading] for column, heading in header.items()
             if heading in HEADERS}
    missing = set(HEADERS.values()) - set(names.values())
    if missing:
        raise ValueError(f"{path} : colonnes absentes, {', '.join(sorted(missing))}.")

    entries = []
    for line_number, cells in raw_rows[1:]:
        entry = {name: cells.get(column, "") for column, name in names.items()}
        if not any(entry.values()):
            continue
        entry["ligne_source"] = line_number
        entries.append(entry)
    return entries


def read_arbitrations(path: Path) -> dict[str, tuple[str, str, str]]:
    """Les choix faits à la main, par code demandé, avec leur motif.

    Le script ne sait trancher qu'au libellé, et le libellé d'une liste désigne
    un site, pas un instrument : là où plusieurs stations d'un même site portent
    du débit, la décision revient à quelqu'un qui sait ce qu'il cherche. Elle
    vit ici plutôt que dans le CSV produit, qui se réécrit à chaque passage, et
    elle porte son motif pour que personne n'ait à refaire l'enquête.
    """
    if not path.exists():
        return {}
    table = pd.read_csv(path, dtype=str).fillna("")
    missing = {"code_demande", "code_station", "cas", "motif"} - set(table.columns)
    if missing:
        raise ValueError(f"{path} : colonnes absentes, {', '.join(sorted(missing))}.")
    unknown_values = sorted(set(table["cas"].str.strip()) - set(ARBITRATION_KINDS))
    if unknown_values:
        raise ValueError(f"{path} : cas inconnu(s), {', '.join(unknown_values)}. "
                         f"Le vocabulaire est {', '.join(ARBITRATION_KINDS)}.")
    return {entry.code_demande.strip(): (entry.code_station.strip(),
                                         entry.cas.strip(), entry.motif.strip())
            for entry in table.itertuples() if entry.code_demande.strip()}


# --------------------------------------------------------------------------
#  Normaliser
# --------------------------------------------------------------------------

_WHITESPACE = re.compile(r"\s+")
_SITE = re.compile(r"[A-Z][0-9A-Z]{7}")
_STATION = re.compile(r"[A-Z][0-9A-Z]{9}")


def normalise_code(raw_code: str) -> str:
    """Le code sans ses espaces internes ni sa casse.

    Trois codes du tableur en portent une, ``W103 0003`` par exemple, ce qui
    suffirait à les rendre introuvables.
    """
    return _WHITESPACE.sub("", (raw_code or "").replace(" ", " ")).upper()


def code_kind(code: str) -> str:
    """``site`` à huit caractères, ``station`` à dix, ``inconnu`` sinon."""
    if _SITE.fullmatch(code):
        return "site"
    if _STATION.fullmatch(code):
        return "station"
    return "inconnu"


def _comparable(raw_text: str) -> str:
    """Un libellé réduit à ce qui se compare : sans accent, ponctuation ni casse."""
    decomposed = unicodedata.normalize("NFD", raw_text or "")
    without_accent = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_accent.lower()).split())


def similarity(expected: str, actual: str) -> float:
    """Ressemblance de deux libellés, entre 0 et 1.

    Le tableur écrit ``L_Arc_a_Aiguebelle`` là où le référentiel écrit
    ``L'Arc à Aiguebelle`` : la comparaison sert à repérer le code qui désigne
    autre chose que ce que son libellé annonce, et à départager les stations
    d'un même site.
    """
    if not expected or not actual:
        return 0.0
    return round(difflib.SequenceMatcher(
        None, _comparable(expected), _comparable(actual)).ratio(), 3)


def _extent(points: Sequence[dict[str, Any]]) -> tuple[str, str, int]:
    """Premier jour, dernier jour, jours distincts portant de la donnée.

    Même règle que l'inventaire, jours distincts et non points, pour que les
    deux tables disent la même chose de la même station.
    """
    days_by_code = sorted({str(point.get("t", ""))[:10] for point in points
                    if len(str(point.get("t", ""))) >= 10})
    return (days_by_code[0], days_by_code[-1], len(days_by_code)) if days_by_code else ("", "", 0)


# --------------------------------------------------------------------------
#  Résoudre
# --------------------------------------------------------------------------

def _candidates(entries, records, by_site) -> dict[str, list[str]]:
    """Les stations à sonder pour chaque code demandé.

    Pour un code de site, les stations que Hub'Eau lui rattache. Pour un code de
    station, ce code et ses soeurs, parce qu'une liste fournie par un tiers peut
    désigner la station qui ne porte que la hauteur d'eau.
    """
    candidates = {}
    for entry in entries:
        code, kind = entry["code_demande"], entry["type_code_demande"]
        site = entry["code_site"]
        sisters = [row.get("code_station") for row in by_site.get(site, [])
                   if row.get("code_station")]
        if kind == "station":
            candidates[code] = sorted(set(sisters) | {code})
        else:
            candidates[code] = sorted(set(sisters))
    return candidates


def _select(entry, candidates, days_by_code, records, unserved):
    """La station retenue pour un code demandé, et la phrase qui dit pourquoi."""
    code, kind = entry["code_demande"], entry["type_code_demande"]
    carrying_codes = [c for c in candidates if days_by_code.get(c, 0) > 0]

    def rank(station: str) -> tuple[float, int]:
        label = (records.get(station) or {}).get("libelle_station", "")
        return (similarity(entry["libelle_demande"], label), days_by_code.get(station, 0))

    if not carrying_codes:
        if not candidates:
            return "", "aucune station rattachée à ce code"
        if set(candidates) <= set(unserved):
            return "", "HydroPortail ne sert aucune station de ce site"
        if any(code in unserved for code in candidates):
            # L'absence n'est pas établie : une station du site n'a pas pu être
            # sondée, et une station non sondée ne prouve rien.
            return "", ("aucune station sondable du site ne porte de débit, "
                        "une autre est refusée par le service")
        return "", "aucune station du site ne porte de débit instantané"
    if kind == "station" and code in carrying_codes:
        return code, "code de station fourni, il porte du débit"
    if kind == "station":
        return max(carrying_codes, key=rank), "station fournie sans débit, remplacée par une soeur du site"
    if len(carrying_codes) == 1:
        return carrying_codes[0], "seule station du site à porter du débit"
    return max(carrying_codes, key=rank), "plusieurs stations du site portent du débit, retenue par son libellé"


#: Au delà de ce rapport, une soeur mieux fournie que la station retenue mérite
#: un regard : le libellé a tranché, la donnée dit peut-être autre chose.
SIBLING_RATIO = 2.0


def _warnings(entry: dict[str, Any], candidates: Sequence[str],
              days_by_code: dict[str, int], unserved: dict[str, str],
              arbitrated: bool = False) -> str:
    """Ce qui demande un regard humain sur cette ligne, en clair.

    Une ligne arbitrée garde ce qui relève du service, qui reste vrai, et perd
    ce qui relevait du choix : il a été fait, et le motif est dans « choix ».
    """
    reasons = []
    for code in candidates:
        if code in unserved:
            reasons.append(f"HydroPortail {unserved[code]} {code}")
    selected = entry["code_station"]
    if selected and not arbitrated:
        sisters = [(days_by_code.get(code, 0), code) for code in candidates if code != selected]
        if sisters:
            best, code = max(sisters)
            if best >= SIBLING_RATIO * max(days_by_code.get(selected, 0), 1):
                reasons.append(f"{code} porte {best} jours contre "
                               f"{days_by_code.get(selected, 0)} à la station retenue")
    if entry["type_code_demande"] == "inconnu":
        reasons.append("code de forme inattendue")
    if not entry["stations_du_site"]:
        reasons.append("code inconnu du référentiel Hub'Eau")
    if not entry["code_station"]:
        # Le pourquoi est dans « choix », qui distingue l'absence établie de la
        # station que le service a refusé de sonder.
        reasons.append("aucune station retenue")
    if not arbitrated and len(str(entry["stations_avec_debit"]).split(";")) > 1:
        reasons.append("plusieurs stations du site portent du débit")
    if not arbitrated and entry["code_station"] and entry["concordance_libelle"] < 0.6:
        reasons.append("libellé éloigné de celui du référentiel")
    if entry["code_station"] and entry["type_code_demande"] == "station" \
            and entry["code_station"] != entry["code_demande"]:
        reasons.append("station demandée remplacée")
    return " ; ".join(reasons)


def prepare(case: str = DEFAULT_CASE, root: str = DEFAULT_ROOT) -> pd.DataFrame:
    """Du tableur reçu à la table de correspondance, en trois passes."""
    case_folder = CASES / case
    if not case_folder.is_dir():
        raise FileNotFoundError(f"{case_folder} : ce dossier de demande n'existe pas.")
    output = case_folder / OUTPUT
    _, cache = paths(case, root)
    entries = read_spreadsheet(case_folder / SPREADSHEET)
    chosen = read_arbitrations(case_folder / ARBITRATIONS)
    if chosen:
        logger.info("%d arbitrage(s) lu(s) dans %s.", len(chosen), case_folder / ARBITRATIONS)
    logger.info("Tableur lu : %d ligne(s).", len(entries))

    for entry in entries:
        entry["code_demande"] = normalise_code(entry["code_demande"])
        entry["type_code_demande"] = code_kind(entry["code_demande"])
        entry["code_site"] = entry["code_demande"][:8]

    kinds = pd.Series([entry["type_code_demande"] for entry in entries]).value_counts()
    logger.info("  dont %s.", ", ".join(f"{count} code(s) de {kind}"
                                        for kind, count in kinds.items()))

    # Hub'Eau d'abord : il est rapide, et il dit quelles stations sonder.
    requested = [entry["code_demande"] for entry in entries
                 if entry["type_code_demande"] == "station"]
    records = api.station_records(requested) if requested else {}
    for entry in entries:
        known = records.get(entry["code_demande"], {})
        if known.get("code_site"):
            entry["code_site"] = known["code_site"]

    sites = sorted({entry["code_site"] for entry in entries if entry["code_site"]})
    logger.info("Référentiel Hub'Eau : %d site(s) à résoudre.", len(sites))
    by_site = api.site_stations(sites)
    for site, rows in by_site.items():
        for row in rows:
            if row.get("code_station"):
                records.setdefault(row["code_station"], row)

    candidates = _candidates(entries, records, by_site)
    # Une station arbitrée se sonde comme les autres, même si le référentiel ne
    # la rattache pas au site demandé : le choix humain n'a pas à se justifier
    # auprès du script, mais sa couverture doit figurer dans la table.
    to_probe = sorted({code for listing in candidates.values() for code in listing}
                      | {code for code, _, _ in chosen.values() if code})
    logger.info("HydroPortail : %d station(s) candidates à sonder, "
                "une requête rapide chacune.", len(to_probe))

    days_by_code: dict[str, int] = {}
    extents: dict[str, tuple[str, str, int]] = {}
    unserved: dict[str, str] = {}
    for line_number, code in enumerate(to_probe, start=1):
        try:
            first_day, last_day, count = _extent(api.coverage_map(cache, code))
        except (api.UnservedStation, api.UnknownStation) as error:
            # Ou le service ignore ce code, ou il échoue dessus quelle que soit
            # la fenêtre. Une campagne de cinquante stations ne peut pas
            # s'arrêter là : on le note et on continue, et la table le dira.
            is_unknown = isinstance(error, api.UnknownStation)
            unserved[code] = "ne connaît pas" if is_unknown else "ne sert pas"
            first_day, last_day, count = "", "", 0
            logger.warning("  [%d/%d] %s : HydroPortail %s cette station "
                           "(HTTP %s)", line_number, len(to_probe), code,
                           unserved[code], "404" if is_unknown else "500")
        else:
            logger.info("  [%d/%d] %s : %s", line_number, len(to_probe), code,
                        f"{count} jours, {first_day} à {last_day}" if count
                        else "aucun débit instantané")
        days_by_code[code], extents[code] = count, (first_day, last_day, count)

    for entry in entries:
        code = entry["code_demande"]
        selected, choice = _select(entry, candidates[code], days_by_code, records, unserved)
        arbitrated = code in chosen
        if arbitrated:
            selected, arbitration_kind, reason = chosen[code]
            choice = f"arbitré à la main, {arbitration_kind} : {reason}"
        record = records.get(selected, {}) if selected else {}
        first_day, last_day, count = extents.get(selected, ("", "", 0))
        entry.update({
            "code_station": selected,
            "libelle_station": record.get("libelle_station", ""),
            "cours_eau_station": record.get("libelle_cours_eau", ""),
            "en_service": record.get("en_service", ""),
            "stations_du_site": ";".join(candidates[code]),
            # Le nombre de jours accolé à chaque code : sans lui, l'arbitrage
            # entre deux stations d'un même site demanderait de tout resonder.
            "stations_avec_debit": ";".join(
                f"{c}:{days_by_code[c]}" for c in candidates[code] if days_by_code.get(c, 0) > 0),
            "date_debut_instantane": first_day,
            "date_fin_instantane": last_day,
            # Vide plutôt que zéro quand rien n'a été retenu : zéro voudrait
            # dire « mesuré à zéro », ce qui n'est pas la même chose.
            "jours_avec_donnees": count if selected else "",
            "concordance_libelle": similarity(
                entry["libelle_demande"], record.get("libelle_station", "")
            ) if selected else "",
            "choix": choice,
        })
        entry["alerte"] = _warnings(entry, candidates[code], days_by_code, unserved, arbitrated)

    table = pd.DataFrame(entries, columns=COLUMNS)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False, encoding="utf-8")
    logger.info("Écrit %s (%d lignes).", output, len(table))

    # Le contrat entre la demande et le téléchargement : un code par ligne, et
    # rien d'autre. Le téléchargeur n'a pas à savoir par quel chemin la liste
    # est arrivée.
    selected_codes = sorted({code for code in table["code_station"] if code})
    (case_folder / SELECTED).write_text("\n".join(selected_codes) + "\n", encoding="utf-8")
    logger.info("Écrit %s (%d stations).", case_folder / SELECTED, len(selected_codes))
    return table


def report(table: pd.DataFrame) -> None:
    """Ce qu'il faut regarder avant de se servir de la table."""
    selected_codes = table[table["code_station"] != ""]
    print(f"\n{len(table)} codes demandés, {selected_codes['code_station'].nunique()} "
          f"stations retenues, {len(table) - len(selected_codes)} sans débit instantané.")
    print("\nComment chaque station a été retenue :")
    for choice, count in table["choix"].str.split(" : ").str[0].value_counts().items():
        print(f"  {count:3d}  {choice}")
    warnings = table[table["alerte"] != ""]
    if warnings.empty:
        return
    print(f"\n{len(warnings)} ligne(s) à regarder :")
    for _, entry in warnings.iterrows():
        print(f"  {entry['code_demande']}  {entry['libelle_demande'][:46]:46s} "
              f"-> {entry['code_station'] or '(rien)':10s}  {entry['alerte']}")


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
    except (ValueError, FileNotFoundError, api.APIError) as error:
        print(f"\nErreur : {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu. Relancez : ce qui est déjà en cache ne sera pas "
              "redemandé.", file=sys.stderr)
        return 130
    report(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
