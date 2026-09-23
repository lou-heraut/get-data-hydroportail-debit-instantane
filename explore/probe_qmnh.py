# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Le QmnH d'HydroPortail comparé à notre propre agrégation au pas horaire.

**Interroge le service** : une requête par station, à ne pas lancer pendant un
téléchargement, une requête à la fois étant la règle. Pour QmnH, step est le
« n » de la durée et non un bouton de quota, il reste donc à 1. C'est la
mesure de docs/findings.md, section « QmnH est l'intégrale de la courbe, sur
l'heure qui suit l'horodatage ».

    python explore/probe_qmnh.py V720001002 01/03/2024 07/03/2024
"""

import argparse

import pandas as pd

from common import measurements
from hydroportail.aggregate import aggregate
from hydroportail.api import BASE_URL, session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("code")
    parser.add_argument("start", help="jj/mm/aaaa")
    parser.add_argument("end", help="jj/mm/aaaa")
    args = parser.parse_args()
    params = {
        "hydro_series[variableType]": "simple_and_interpolated_and_hourly_variable",
        "hydro_series[simpleAndInterpolatedAndHourlyVariable]": "QmnH",
        "hydro_series[statusData]": "most_valid",
        "hydro_series[step]": 1,
        "hydro_series[startAt]": args.start,
        "hydro_series[endAt]": args.end,
    }
    response = session().get(f"{BASE_URL}/stationhydro/ajax/{args.code}/series",
                             params=params, timeout=600)
    response.raise_for_status()
    series = response.json()["series"]
    print(series["title"])
    served = pd.DataFrame(series["data"])
    served["debut_pas"] = pd.to_datetime(served.t, utc=True).astype("datetime64[ns, UTC]")
    served["qmnh_m3s"] = served.v / 1000

    frame = measurements(args.code)
    ours = frame[frame.most_valid].sort_values("date_obs").drop_duplicates("date_obs")
    bins = aggregate(ours.date_obs, ours.debit_m3s, 60)
    bins["debut_pas"] = bins.debut_pas.astype("datetime64[ns, UTC]")
    both = served.merge(bins, on="debut_pas")
    gap = ((both.debit_moyen_m3s - both.qmnh_m3s) / both.qmnh_m3s).abs() * 100
    print(f"{len(both)} heures comparées : écart relatif médian {gap.median():.3f} %, "
          f"maximal {gap.max():.3f} %")


if __name__ == "__main__":
    main()
