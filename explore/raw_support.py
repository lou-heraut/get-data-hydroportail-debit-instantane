# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Part des pas de chaque année que le brut porte, à 15, 30 et 60 minutes.

Un pas de durée D est porté quand aucun écart entre deux points bruts voisins
qui le chevauche ne dépasse D. C'est la mesure de docs/findings.md, section
« Ce que chaque pas de sortie garde du brut ».

    python explore/raw_support.py
"""

import numpy as np
import pandas as pd

from common import level, measurements, stations
from hydroportail.aggregate import aggregate


def main():
    rows = []
    for code in stations():
        raw = level(measurements(code), 4)
        if len(raw) < 2:
            continue
        for minutes in (15, 30, 60):
            bins = aggregate(raw.date_obs, raw.debit_m3s, minutes)
            year = bins.debut_pas.dt.year
            per_year = pd.Series(1, index=year).groupby(level=0).size()
            full = [pd.date_range(f"{y}-01-01", f"{y + 1}-01-01", freq=f"{minutes}min",
                                  inclusive="left", tz="UTC").size for y in per_year.index]
            kept = bins.mesure_suffisante.groupby(year).sum()
            for y, n in zip(per_year.index, full):
                rows.append(dict(code=code, pas=minutes, annee=y,
                                 part=round(100 * kept.get(y, 0) / n)))
    table = pd.DataFrame(rows)
    for minutes in (15, 30, 60):
        print(f"\nsortie à {minutes} min, % des pas de l'année portés par le brut")
        wide = table[table.pas == minutes].pivot(index="code", columns="annee", values="part")
        print(wide.to_string(na_rep=""))


if __name__ == "__main__":
    main()
