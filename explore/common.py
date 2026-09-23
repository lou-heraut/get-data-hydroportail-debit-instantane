# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ce que les scripts d'exploration se partagent : lire un niveau de statut, et
la carte de couverture QIXnJ déjà en cache, sans aucune requête."""

import gzip
import json
from pathlib import Path

import pandas as pd

CASE = "2026-09_test-set"
ROOT = Path("data")


def measurements(code: str, case: str = CASE) -> pd.DataFrame:
    return pd.read_parquet(ROOT / case / "measurements" / f"{code}.parquet")


def stations(case: str = CASE) -> list[str]:
    return sorted(p.stem for p in (ROOT / case / "measurements").glob("*.parquet"))


def level(frame: pd.DataFrame, statut: int) -> pd.DataFrame:
    """One status level, sorted and without duplicate timestamps."""
    part = frame[frame.statut == statut]
    return part.sort_values("date_obs").drop_duplicates("date_obs")


def coverage_days(code: str) -> pd.DataFrame:
    """Days of the QIXnJ coverage map with their status, from the newest cache file.

    The map is the daily maximum of the most_valid instantaneous series: a day
    is in it exactly when the producer has a series that day, and its status
    says which level. See docs/findings.md.
    """
    files = sorted((ROOT / ".cache" / code).glob("19000101_*_QIXnJ_most_valid.json.gz"))
    if not files:
        raise FileNotFoundError(f"pas de carte QIXnJ en cache pour {code} : "
                                "lancer l'inventaire du cas d'abord")
    content = json.load(gzip.open(files[-1]))
    data = content["series"]["data"] if isinstance(content, dict) else content
    days = pd.DataFrame(data)
    days["jour"] = pd.to_datetime(days.t, utc=True).dt.floor("D")
    return days[["jour", "s"]]
