# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ce que le validé garde du brut, une fois les deux agrégés sur les mêmes pas.

Pour chaque journée où le brut porte tous les pas sans point douteux, et que la
carte QIXnJ certifie validée : pic de la moyenne, plus grand saut entre deux
moyennes consécutives, qui tient lieu de gradient, et écart relatif entre les
moyennes. Rangé par nombre de points validés dans la journée. C'est la mesure
de docs/findings.md, section « Agrégé, le validé garde les pics, et les
gradients selon sa densité ».

    python explore/compare_valid_raw.py --minutes 15
"""

import argparse

import numpy as np
import pandas as pd

from common import coverage_days, level, measurements, stations
from hydroportail.aggregate import aggregate

DOUBTFUL = 12
DENSITY = [-1, 10, 25, 50, 100, 10_000]


def days_of(code, minutes):
    frame = measurements(code)
    raw, valid = level(frame, 4), level(frame, 16)
    if len(raw) < 2 or len(valid) < 2:
        return []
    certified = set(coverage_days(code).query("s == 16").jour)
    doubtful = set(raw[raw.qualification == DOUBTFUL].date_obs.dt.floor("D"))
    per_day = valid.date_obs.dt.floor("D").value_counts()
    both = (aggregate(raw.date_obs, raw.debit_m3s, minutes).set_index("debut_pas")
            .join(aggregate(valid.date_obs, valid.debit_m3s, minutes).set_index("debut_pas"),
                  lsuffix="_b", rsuffix="_v", how="inner"))
    rows = []
    for day, g in both.groupby(both.index.floor("D")):
        if (len(g) < 1440 // minutes or not g.mesure_suffisante_b.all()
                or day in doubtful or day not in certified):
            continue
        b, v = g.debit_moyen_m3s_b.to_numpy(), g.debit_moyen_m3s_v.to_numpy()
        gap = np.abs(v - b) / b
        rows.append(dict(code=code, jour=day, points_valides=per_day.get(day, 0),
                         pic=v.max() / b.max(),
                         gradient=np.abs(np.diff(v)).max() / np.abs(np.diff(b)).max(),
                         forte_variation=(b.max() - b.min()) / b.max() > 0.3,
                         a_5_pct=np.mean(gap <= 0.05), ecart_median=np.median(gap),
                         pire_ecart=gap.max()))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args()
    days = pd.DataFrame([r for code in stations() for r in days_of(code, args.minutes)])
    days["densite"] = pd.cut(days.points_valides, DENSITY)
    print(f"{len(days)} journées certifiées comparables, "
          f"{days.forte_variation.sum()} à forte variation")
    strong = days[days.forte_variation]
    print("\nforte variation, par points validés par jour : pic et gradient gardés")
    print(strong.groupby("densite", observed=True).agg(
        jours=("pic", "size"), pic=("pic", "median"), gradient=("gradient", "median"),
        gradient_p10=("gradient", lambda x: x.quantile(0.1)),
        sous_moitie=("gradient", lambda x: (x < 0.5).mean())).round(2).to_string())
    print("\ntoutes journées, par points validés par jour : écart en valeur")
    print(days.groupby("densite", observed=True).agg(
        jours=("pic", "size"), a_5_pct=("a_5_pct", "mean"),
        ecart_median=("ecart_median", "median"), pire_median=("pire_ecart", "median"),
        pire_p90=("pire_ecart", lambda x: x.quantile(0.9))).round(4).to_string())


if __name__ == "__main__":
    main()
