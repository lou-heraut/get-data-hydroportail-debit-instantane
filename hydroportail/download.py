# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Orchestration: what to ask for, how to shape it, where to write it.

Nothing here knows how HydroPortail behaves; that lives in
``hydroportail.api``. Nothing here decides what is good data either: the
columns come out as the producer published them, and the reader decides.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from . import api, schema

logger = logging.getLogger("hydroportail")

DEFAULT_FOLDER = "donnees_hydroportail"


# --------------------------------------------------------------------------
#  Reading the coverage map
# --------------------------------------------------------------------------

def _days_by_year_and_status(points: Sequence[dict[str, Any]]) -> dict[tuple[int, int], int]:
    """Days carrying data, per year and per status code.

    The map holds one point per day, so counting days is counting points. Days
    are counted as distinct on purpose: a duplicate would otherwise inflate a
    coverage figure that people will trust.
    """
    seen: dict[tuple[int, int], set[str]] = defaultdict(set)
    for point in points:
        day = str(point.get("t", ""))[:10]
        if len(day) == 10:
            seen[(int(day[:4]), int(point.get("s") or 0))].add(day)
    return {key: len(days) for key, days in seen.items()}


def _extent(points: Sequence[dict[str, Any]]) -> tuple[str, str, int]:
    """First day, last day, and how many distinct days carry data."""
    days = sorted({str(point.get("t", ""))[:10] for point in points
                   if len(str(point.get("t", ""))) >= 10})
    if not days:
        return "", "", 0
    return days[0], days[-1], len(days)


def _coverage_rate(first: str, last: str, days: int) -> float | None:
    if not first or not last:
        return None
    span = (date.fromisoformat(last) - date.fromisoformat(first)).days + 1
    return round(days / span, 4) if span > 0 else None


# --------------------------------------------------------------------------
#  Inventory
# --------------------------------------------------------------------------

def inventory(
    folder: str | Path = DEFAULT_FOLDER,
    codes: Sequence[str] = (),
    write: bool = True,
) -> dict[str, pd.DataFrame]:
    """What exists, before downloading anything heavy.

    One coverage map request per station, under two seconds each, gives the
    real extent of the instantaneous series, which days carry data and in what
    state of validation. Hub'Eau adds the identity. Nothing of the series
    itself is fetched.

    A code that carries no discharge at all gets its site looked up, so that
    the answer is not merely "nothing here" but "the discharge of this site is
    on that station". A third party list cannot be trusted on this point: the
    obvious station of a site may hold water level only.
    """
    folder = Path(folder)
    cache = folder / ".sources"
    codes = [str(code).strip() for code in codes if str(code).strip()]
    if not codes:
        raise ValueError("Aucun code de station demandé.")

    logger.info("Inventaire de %d station(s), sans télécharger de chronique.", len(codes))

    maps: dict[str, list[dict[str, Any]]] = {}
    for number, code in enumerate(codes, start=1):
        points = api.coverage_map(cache, code)
        maps[code] = points
        first, last, days = _extent(points)
        logger.info("  [%d/%d] %s : %s",
                    number, len(codes), code,
                    f"{days} jours, {first} à {last}" if days else "aucun débit instantané")

    records = api.station_records(codes)
    missing = [code for code in codes if code not in records]
    if missing:
        logger.warning("  %d code(s) absent(s) du référentiel Hub'Eau : %s",
                       len(missing), ", ".join(missing))

    siblings, replacements = _resolve_sites(cache, codes, maps, records)
    stations = _stations_table(codes, maps, records, siblings, replacements)
    couverture = _couverture_table(codes, maps)
    ref_codes = pd.DataFrame(schema.ref_codes_rows(), columns=schema.columns("ref_codes"))

    tables = {"stations": stations, "couverture": couverture, "ref_codes": ref_codes}
    if write:
        folder.mkdir(parents=True, exist_ok=True)
        for name, frame in tables.items():
            path = _write_csv(frame, folder, name)
            logger.info("  écrit %s (%d lignes)", path.name, len(frame))
    return tables


def _resolve_sites(cache: Path, codes: Sequence[str], maps, records):
    """Sister stations of each code, and a replacement for those without data.

    Hub'Eau is asked for the whole site of every code, which is cheap. Only the
    stations of a site whose requested code carries nothing are then looked up
    on HydroPortail, because that is the single case where the answer changes
    what the user should ask for: the obvious station of a site may hold water
    level only, and its neighbour the discharge.
    """
    sites = {(records.get(code) or {}).get("code_site") for code in codes}
    sites.discard(None)
    by_site = api.site_stations(sites)

    siblings: dict[str, str] = {}
    replacements: dict[str, str] = {}
    for code in codes:
        site = (records.get(code) or {}).get("code_site")
        others = [row.get("code_station") for row in by_site.get(site, [])
                  if row.get("code_station") and row.get("code_station") != code]
        siblings[code] = ";".join(sorted(others))
        if maps[code] or not others:
            continue
        for other in sorted(others):
            if api.coverage_map(cache, other):
                replacements[code] = other
                logger.info("  %s ne porte pas de débit ; %s, du même site, en porte",
                            code, other)
                break
    return siblings, replacements


def _stations_table(codes, maps, records, siblings, replacements) -> pd.DataFrame:
    rows = []
    for code in codes:
        record = records.get(code, {})
        points = maps[code]
        first, last, days = _extent(points)
        rows.append({
            "code_station": code,
            "libelle_station": record.get("libelle_station"),
            "libelle_cours_eau": record.get("libelle_cours_eau"),
            "code_site": record.get("code_site"),
            "stations_soeurs": siblings.get(code, ""),
            "station_debit_du_site": replacements.get(code, ""),
            "descriptif_station": record.get("descriptif_station"),
            "type_station": record.get("type_station"),
            "influence_locale_station": record.get("influence_locale_station"),
            "en_service": record.get("en_service"),
            "code_commune_station": record.get("code_commune_station"),
            "libelle_commune": record.get("libelle_commune"),
            "code_departement": record.get("code_departement"),
            "latitude_station": record.get("latitude_station"),
            "longitude_station": record.get("longitude_station"),
            "altitude_ref_alti_station": record.get("altitude_ref_alti_station"),
            "date_ouverture_station": str(record.get("date_ouverture_station") or "")[:10],
            "date_fermeture_station": str(record.get("date_fermeture_station") or "")[:10],
            "porte_debit": bool(points),
            "date_debut_instantane": first,
            "date_fin_instantane": last,
            "jours_avec_donnees": days,
            "taux_couverture": _coverage_rate(first, last, days),
        })
    frame = pd.DataFrame(rows, columns=schema.columns("stations"))
    return frame.sort_values("code_station").reset_index(drop=True)


def _couverture_table(codes, maps) -> pd.DataFrame:
    rows = []
    for code in codes:
        for (year, status), days in sorted(_days_by_year_and_status(maps[code]).items()):
            rows.append({
                "code_station": code,
                "annee": year,
                "statut": status,
                "jours_avec_donnees": days,
                # Left empty on purpose: empty means "not measured yet", never
                # "measured as zero". A run that only did the inventory shows
                # exactly that, which is the true state of affairs.
                "nb_points": pd.NA,
                "intervalle_median_min": pd.NA,
                "intervalle_p90_min": pd.NA,
            })
    frame = pd.DataFrame(rows, columns=schema.columns("couverture"))
    for column in ("nb_points",):
        frame[column] = frame[column].astype("Int64")
    return frame.sort_values(["code_station", "annee", "statut"]).reset_index(drop=True)


# --------------------------------------------------------------------------
#  Disk
# --------------------------------------------------------------------------

def _write_csv(frame: pd.DataFrame, folder: Path, table: str) -> Path:
    path = folder / f"{table}.csv"
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path


def read_tables(folder: str | Path = DEFAULT_FOLDER) -> dict[str, pd.DataFrame]:
    """The reference tables, with the commune and department codes kept as text."""
    folder = Path(folder)
    tables = {}
    for table in schema.TABLES:
        path = folder / f"{table}.csv"
        if path.exists():
            tables[table] = pd.read_csv(path, dtype={
                "code_station": "string", "code_site": "string",
                "code_commune_station": "string", "code_departement": "string",
            })
    return tables


# --------------------------------------------------------------------------
#  Telling the user what came out
# --------------------------------------------------------------------------

def summary(folder: str | Path = DEFAULT_FOLDER) -> pd.DataFrame:
    """A readable digest of the inventory, printed after a run."""
    tables = read_tables(folder)
    stations = tables.get("stations")
    if stations is None or stations.empty:
        logger.info("Aucun inventaire dans %s.", folder)
        return pd.DataFrame()

    carries = stations["porte_debit"].fillna(False).astype(bool)
    logger.info("")
    logger.info("%d station(s), dont %d portant un débit instantané.",
                len(stations), int(carries.sum()))

    for _, row in stations.iterrows():
        if row["porte_debit"]:
            logger.info("  %-11s %-38s %s à %s  %5d j  %4.0f %%",
                        row["code_station"], str(row["libelle_station"])[:38],
                        row["date_debut_instantane"], row["date_fin_instantane"],
                        row["jours_avec_donnees"], 100 * (row["taux_couverture"] or 0))
        else:
            replacement = row["station_debit_du_site"]
            logger.info("  %-11s %-38s aucun débit instantané%s",
                        row["code_station"], str(row["libelle_station"])[:38],
                        f", voir {replacement}" if isinstance(replacement, str) and replacement else "")

    couverture = tables.get("couverture")
    if couverture is not None and not couverture.empty:
        statuses = Counter(couverture["statut"])
        logger.info("")
        logger.info("Couverture : %d lignes, statuts rencontrés %s.",
                    len(couverture), dict(sorted(statuses.items())))
        if couverture["nb_points"].isna().all():
            logger.info("Les colonnes de résolution restent vides tant que les "
                        "chroniques n'ont pas été téléchargées.")
        else:
            manquantes = int(couverture["nb_points"].isna().sum())
            if manquantes:
                logger.info("%d ligne(s) sans résolution : station non "
                            "téléchargée.", manquantes)
    return stations


# --------------------------------------------------------------------------
#  The fact table
# --------------------------------------------------------------------------

def _to_frame(code: str, points: Sequence[dict[str, Any]], most_valid: bool) -> pd.DataFrame:
    """Points as published, one row each, nothing dropped and nothing judged."""
    if not points:
        return pd.DataFrame(columns=schema.columns("mesures"))
    frame = pd.DataFrame(points, columns=["t", "v", "s", "q", "m", "c"])
    out = pd.DataFrame({
        "code_station": code,
        "date_obs": pd.to_datetime(frame["t"], utc=True, format="ISO8601"),
        # The source serves litres per second, which series.unit confirms on
        # every response; unitQ claims m3 and would be wrong by a factor 1000.
        "debit_m3s": frame["v"].astype("float64") / 1000.0,
        "statut": frame["s"].fillna(0).astype("int8"),
        "qualification": frame["q"].fillna(0).astype("int8"),
        "methode": frame["m"].fillna(0).astype("int8"),
        "continuite": frame["c"].fillna(0).astype("int8"),
        "most_valid": most_valid,
    })
    return out


def _merge_passes(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Union of the passes, deduplicated on the whole row.

    The two passes overlap: on recent periods most_valid returns the very same
    raw points. Deduplicating on the whole row rather than on
    (station, date, statut) assumes nothing: two levels always carry two
    different `statut`, but a single raw series already mixes two
    `qualification`, so the narrower key would have to be argued for. The wider
    one costs nothing.

    ``most_valid`` is true as soon as either pass returned the row, which is
    what makes ``mesures[most_valid]`` exactly the producer's own chronicle.
    """
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return pd.DataFrame(columns=schema.columns("mesures"))
    joined = pd.concat(frames, ignore_index=True)
    keys = [column for column in schema.columns("mesures") if column != "most_valid"]
    merged = joined.groupby(keys, as_index=False, sort=False)["most_valid"].max()
    return merged.sort_values(["code_station", "date_obs", "statut"]).reset_index(drop=True)


def _resolution(frame: pd.DataFrame) -> pd.DataFrame:
    """Points, median and ninth decile of the gaps, per station, year and status.

    The median alone lies at both ends of a chronicle: it climbs back to 72
    minutes at Moûtiers in 2015 between two years at 15 and 12, and it says
    nothing of a year whose third is missing. Read with the p90 and with the
    days count, it says what it means.
    """
    if frame.empty:
        return pd.DataFrame(columns=["code_station", "annee", "statut",
                                     "jours_avec_donnees", "nb_points",
                                     "intervalle_median_min", "intervalle_p90_min"])
    work = frame[["code_station", "date_obs", "statut"]].copy()
    work["annee"] = work["date_obs"].dt.year
    rows = []
    for (code, year, status), group in work.groupby(
            ["code_station", "annee", "statut"], sort=True):
        stamps = group["date_obs"].sort_values()
        gaps = stamps.diff().dropna().dt.total_seconds() / 60.0
        rows.append({
            "code_station": code,
            "annee": int(year),
            "statut": int(status),
            "jours_avec_donnees": stamps.dt.date.nunique(),
            "nb_points": len(stamps),
            # A single point in a year gives no gap at all, and an invented
            # zero would read as "perfect resolution". Left empty.
            "intervalle_median_min": round(float(gaps.median()), 1) if len(gaps) else None,
            "intervalle_p90_min": round(float(gaps.quantile(0.9)), 1) if len(gaps) else None,
        })
    return pd.DataFrame(rows)


def download(
    folder: str | Path = DEFAULT_FOLDER,
    codes: Sequence[str] = (),
    statuts: Sequence[str] = api.STATUSES,
    write: bool = True,
) -> dict[str, pd.DataFrame]:
    """Download the series themselves, one parquet file per station.

    The inventory runs first, because it says over which period each station
    has anything at all, and which carry no discharge and can be skipped. The
    raw pass is asked over that whole period even where only validated data is
    expected: raw does live underneath validated periods, and the windows
    accelerate through the empty years by themselves.
    """
    folder = Path(folder)
    cache = folder / ".sources"
    mesures = folder / "mesures"
    unknown = {kind: set() for kind in ("s", "q", "m", "c")}

    tables = inventory(folder, codes, write=False)
    stations = tables["stations"]
    working = stations[stations["porte_debit"].astype(bool)]
    logger.info("")
    logger.info("Téléchargement de %d station(s), passes %s.",
                len(working), " et ".join(statuts))

    resolutions = []
    for number, row in enumerate(working.itertuples(), start=1):
        code = row.code_station
        begin = date.fromisoformat(row.date_debut_instantane)
        finish = date.fromisoformat(row.date_fin_instantane)
        logger.info("  [%d/%d] %s, %s à %s", number, len(working), code, begin, finish)

        frames = []
        for status in statuts:
            points = api.fetch_series(
                cache, code, status, begin, finish,
                on_progress=lambda a, b, n, total, s=status: logger.info(
                    "      %s %s -> %s : %s pts (total %s)", s, a, b,
                    f"{n:,}".replace(",", " "), f"{total:,}".replace(",", " ")))
            for point in points:
                for kind, key in (("s", "s"), ("q", "q"), ("m", "m"), ("c", "c")):
                    unknown[kind].add(int(point.get(key) or 0))
            frames.append(_to_frame(code, points, most_valid=(status == "most_valid")))
            del points

        merged = _merge_passes(frames)
        del frames
        logger.info("      %s lignes après fusion",
                    f"{len(merged):,}".replace(",", " "))
        if write and not merged.empty:
            mesures.mkdir(parents=True, exist_ok=True)
            path = mesures / f"{code}.parquet"
            merged.to_parquet(path, compression="zstd", index=False)
            logger.info("      %s : %.2f Mo", path.name, path.stat().st_size / 1e6)
        resolutions.append(_resolution(merged))
        del merged

    tables["couverture"] = _fill_resolution(tables["couverture"], resolutions)

    strays = schema.unknown_codes(unknown)
    if strays:
        logger.warning("  codes absents de ref_codes.csv, la nomenclature a bougé : %s",
                       strays)

    if write:
        folder.mkdir(parents=True, exist_ok=True)
        for name, frame in tables.items():
            _write_csv(frame, folder, name)
    return tables


def _fill_resolution(couverture: pd.DataFrame,
                     resolutions: Sequence[pd.DataFrame]) -> pd.DataFrame:
    """Put the measured columns next to the ones the inventory already filled.

    An outer join, because the two sources need not agree exactly: the coverage
    map carries the status of each daily maximum, the series carries the status
    of each point, and a year may hold a status the daily maximum never shows.
    Losing such a row would hide real data.
    """
    measured = [frame for frame in resolutions if not frame.empty]
    if not measured:
        return couverture
    measured = pd.concat(measured, ignore_index=True)
    keys = ["code_station", "annee", "statut"]
    merged = couverture.drop(columns=["nb_points", "intervalle_median_min",
                                      "intervalle_p90_min"]).merge(
        measured, on=keys, how="outer", suffixes=("_carte", ""))
    # The map labels a day by the status of its daily maximum, so a day holding
    # both raw and validated points is only counted once, under one of them.
    # Once the series is here the true count is known, and it replaces the
    # estimate; the estimate stays for whatever was not downloaded.
    merged["jours_avec_donnees"] = (merged["jours_avec_donnees"]
                                    .fillna(merged["jours_avec_donnees_carte"])
                                    .astype("Int64"))
    merged["nb_points"] = merged["nb_points"].astype("Int64")
    return merged[schema.columns("couverture")].sort_values(keys).reset_index(drop=True)


def read(folder: str | Path = DEFAULT_FOLDER) -> pd.DataFrame:
    """The fact table, every station at once."""
    mesures = Path(folder) / "mesures"
    if not mesures.exists():
        raise FileNotFoundError(
            f"Aucune mesure dans {mesures}. Lancez d'abord le téléchargement.")
    return pd.read_parquet(mesures)
