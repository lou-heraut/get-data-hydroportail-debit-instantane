# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Les longs écarts de la série validée : trous ou segments certifiés ?

Deux lectures confrontées. Le code de continuité c du point qui suit l'écart,
qui devrait marquer une discontinuité et ne le fait pas ; et la carte QIXnJ,
dont les jours intérieurs sont tous présents quand le producteur certifie le
segment, tous absents quand c'est un trou. C'est la mesure de
docs/findings.md, section « Le code c ne marque pas les trous, la carte QIXnJ
si ».

    python explore/validated_gaps.py
"""

import numpy as np
import pandas as pd

from common import coverage_days, level, measurements, stations


def main():
    for code in stations():
        valid = level(measurements(code), 16)
        if len(valid) < 2:
            continue
        present = set(coverage_days(code).jour)
        t = valid.date_obs.to_numpy()
        gaps = np.diff(t) / np.timedelta64(1, "D")
        after_day = pd.Series(valid.continuite.to_numpy()[1:][gaps > 1]).value_counts()
        kinds = {"certifié": 0, "trou": 0, "en partie": 0}
        for i in np.nonzero(gaps > 2)[0]:
            first = pd.Timestamp(t[i]).floor("D") + pd.Timedelta(days=1)
            inner = pd.date_range(first, pd.Timestamp(t[i + 1]).floor("D"), inclusive="left")
            if len(inner) == 0:
                continue
            share = np.mean([d in present for d in inner])
            kinds["certifié" if share == 1 else "trou" if share == 0 else "en partie"] += 1
        print(f"{code}  c après un écart > 1 j : {after_day.to_dict()}")
        print(f"            écarts > 2 j selon QIXnJ : {kinds}")


if __name__ == "__main__":
    main()
