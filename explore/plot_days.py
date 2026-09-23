# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quelques journées de brut, et ce qu'en gardent les moyennes à 15 et 60 min.

Exploration, pas un produit : la figure sert à voir ce que l'agrégation garde
et perd d'une éclusée. Elle se refait sur le jeu de test téléchargé :

    pip install -e ".[explore]"
    python explore/plot_days.py

et s'écrit dans data/_exploration/, en PNG et en PDF.
"""

from pathlib import Path

import matplotlib
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from hydroportail.aggregate import aggregate  # noqa: E402

MEASUREMENTS = Path("data/2026-09_test-set/measurements")
OUT = Path("data/_exploration")

INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
RAW, SERIES = "#8a8984", "#2a78d6"

#: Code, name, start of the 24 hours shown, what the day illustrates.
DAYS = [
    ("V271201001", "L'Ain à Pont-d'Ain", "2026-09-01 12:00", "brut à 5 min"),
    ("W011001001", "L'Isère à Moûtiers", "2026-02-17", "brut à 5 min"),
    ("X031001001", "La Durance à Embrun", "2023-10-19", "brut à 15 min"),
    ("W283201001", "W283201001", "2024-11-27", "brut à 5 min, pic isolé"),
]
STEPS = (15, 60)


def raw_around(code, start, end):
    frame = pd.read_parquet(MEASUREMENTS / f"{code}.parquet")
    margin = pd.Timedelta(hours=2)
    raw = frame[(frame.statut == 4) & (frame.date_obs >= start - margin)
                & (frame.date_obs < end + margin)]
    return raw.sort_values("date_obs").drop_duplicates("date_obs")


def panel(ax, raw, start, end, minutes, title):
    bins = aggregate(raw.date_obs, raw.debit_m3s, minutes)
    bins = bins[(bins.debut_pas >= start) & (bins.debut_pas < end)]
    x = list(bins.debut_pas) + [end]
    close = lambda col: list(bins[col]) + [bins[col].iloc[-1]]  # noqa: E731
    shown = raw[(raw.date_obs >= start) & (raw.date_obs <= end)]

    ax.fill_between(x, close("debit_min_m3s"), close("debit_max_m3s"), step="post",
                    color=SERIES, alpha=0.16, lw=0, label="min et max dans le pas")
    ax.plot(shown.date_obs, shown.debit_m3s, color=RAW, lw=1, marker="o", ms=2.2,
            label="brut, points servis")
    ax.step(x, close("debit_moyen_m3s"), where="post", color=SERIES, lw=2,
            label="moyenne sur le pas (intégrale)")

    elapsed = (shown.date_obs - start).dt.total_seconds().to_numpy() / 60
    values = shown.debit_m3s.to_numpy()
    ramp_raw = np.max(np.abs(np.diff(values) / np.diff(elapsed)))
    ramp_mean = np.max(np.abs(np.diff(bins.debit_moyen_m3s))) / minutes
    ax.text(0, 1.0,
            f"pic : brut {values.max():.1f}   moyenne {bins.debit_moyen_m3s.max():.1f}"
            f"   max du pas {bins.debit_max_m3s.max():.1f} m³/s\n"
            f"gradient max : brut {ramp_raw:.2f}   moyenne {ramp_mean:.2f} m³/s par min",
            transform=ax.transAxes, ha="left", va="bottom", fontsize=8, color=INK2)
    ax.set_title(title, loc="left", fontsize=10, color=INK, pad=26)
    ax.set_facecolor(SURFACE)
    ax.set_xlim(start, end)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz="UTC"))
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 3)))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(len(DAYS), len(STEPS), facecolor=SURFACE,
                             figsize=(13, 3.8 * len(DAYS)))
    for row, (code, name, day, note) in enumerate(DAYS):
        start = pd.Timestamp(day, tz="UTC")
        end = start + pd.Timedelta(days=1)
        raw = raw_around(code, start, end)
        for col, minutes in enumerate(STEPS):
            ax = axes[row, col]
            panel(ax, raw, start, end, minutes,
                  f"{name}, {day} ({note}) : pas de {minutes} min")
            if col == 0:
                ax.set_ylabel("m³/s", color=INK2, fontsize=9)
            if row == 0:
                ax.legend(loc="center left", fontsize=8, frameon=False)
    fig.text(0.01, 0.004, "Heures en UTC. Gradient de la moyenne : plus grand saut "
             "entre deux pas consécutifs, divisé par la durée du pas.",
             fontsize=8, color=INK2)
    fig.tight_layout(rect=(0, 0.012, 1, 1))
    for suffix in ("png", "pdf"):
        fig.savefig(OUT / f"journees.{suffix}", dpi=110, facecolor=SURFACE)
    print(f"écrit dans {OUT}/journees.png et .pdf")


if __name__ == "__main__":
    main()
