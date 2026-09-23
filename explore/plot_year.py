# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Une station, une année, à parcourir : brut, validé, et leurs moyennes.

Exploration, pas un produit. La page HTML se zoome et se déplace, ce qu'une
figure fixe ne permet pas sur une année de points à cinq minutes. Elle met côte
à côte ce que la question du statut oppose : le brut, dense mais non corrigé,
et la série validée, corrigée et débarrassée des artefacts mais élaguée, avec
la moyenne que chacun donne sur le même pas. Les pas que la mesure ne porte
pas restent vides, et les points bruts marqués douteux sont signalés.

    pip install -e ".[explore]"
    python explore/plot_year.py W011001001 2024 --minutes 15

La page s'écrit dans data/_exploration/ et charge plotly depuis son CDN.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from hydroportail.aggregate import aggregate

MEASUREMENTS = Path("data/2026-09_test-set/measurements")
OUT = Path("data/_exploration")

INK2, GRID, SURFACE = "#52514e", "#e4e3df", "#fcfcfb"
RAW, RAW_MEAN, VALID, VALID_MEAN = "#8a8984", "#2a78d6", "#eb6834", "#1baf7a"
DOUBTFUL = 12


def level(frame, statut, start, end):
    """One status level of one station, sorted and without duplicates."""
    part = frame[(frame.statut == statut) & (frame.date_obs >= start)
                 & (frame.date_obs < end)]
    return part.sort_values("date_obs").drop_duplicates("date_obs")


def steps(series, minutes):
    """Bins as a step line, with the bins the measurement does not support blank."""
    bins = aggregate(series.date_obs, series.debit_m3s, minutes)
    blank = ~bins.mesure_suffisante
    for col in ("debit_moyen_m3s", "debit_min_m3s", "debit_max_m3s"):
        bins.loc[blank, col] = np.nan
    return bins


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("code")
    parser.add_argument("year", type=int)
    parser.add_argument("--minutes", type=int, default=15)
    args = parser.parse_args()

    frame = pd.read_parquet(MEASUREMENTS / f"{args.code}.parquet")
    start = pd.Timestamp(f"{args.year}-01-01", tz="UTC")
    end = pd.Timestamp(f"{args.year + 1}-01-01", tz="UTC")
    raw = level(frame, 4, start, end)
    valid = level(frame, 16, start, end)
    m = args.minutes

    fig = go.Figure()
    if len(raw) > 1:
        bins = steps(raw, m)
        fig.add_trace(go.Scattergl(x=bins.debut_pas, y=bins.debit_min_m3s, mode="lines",
                                   line=dict(width=0, shape="hv"), hoverinfo="skip",
                                   showlegend=False, connectgaps=False))
        fig.add_trace(go.Scattergl(x=bins.debut_pas, y=bins.debit_max_m3s, mode="lines",
                                   line=dict(width=0, shape="hv"), fill="tonexty",
                                   fillcolor="rgba(42,120,214,0.16)",
                                   name=f"min et max du brut sur {m} min",
                                   hoverinfo="skip", connectgaps=False))
        fig.add_trace(go.Scattergl(x=raw.date_obs, y=raw.debit_m3s, mode="lines+markers",
                                   line=dict(color=RAW, width=1), marker=dict(size=3),
                                   name=f"brut ({len(raw):,} points)".replace(",", " ")))
        fig.add_trace(go.Scattergl(x=bins.debut_pas, y=bins.debit_moyen_m3s, mode="lines",
                                   line=dict(color=RAW_MEAN, width=2, shape="hv"),
                                   name=f"moyenne du brut sur {m} min", connectgaps=False))
        doubtful = raw[raw.qualification == DOUBTFUL]
        fig.add_trace(go.Scattergl(x=doubtful.date_obs, y=doubtful.debit_m3s, mode="markers",
                                   marker=dict(symbol="x", size=7, color="#0b0b0b"),
                                   name=f"brut marqué douteux ({len(doubtful):,})".replace(",", " "),
                                   visible="legendonly"))
    if len(valid) > 1:
        fig.add_trace(go.Scattergl(x=valid.date_obs, y=valid.debit_m3s, mode="lines+markers",
                                   line=dict(color=VALID, width=1), marker=dict(size=4),
                                   name=f"validé ({len(valid):,} points)".replace(",", " ")))
        vbins = aggregate(valid.date_obs, valid.debit_m3s, m)
        fig.add_trace(go.Scattergl(x=vbins.debut_pas, y=vbins.debit_moyen_m3s, mode="lines",
                                   line=dict(color=VALID_MEAN, width=2, shape="hv"),
                                   name=f"moyenne du validé sur {m} min",
                                   visible="legendonly"))

    name = frame.code_station.iloc[0]
    fig.update_layout(
        title=dict(text=f"{name}, {args.year} : brut, validé et moyennes sur {m} min "
                   "(heures UTC, pas non portés par le brut laissés vides)", x=0.01,
                   font=dict(size=15)),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, hovermode="x unified",
        font=dict(color=INK2), legend=dict(orientation="h", y=-0.18),
        yaxis=dict(title="m³/s", gridcolor=GRID, zeroline=False),
        xaxis=dict(gridcolor=GRID, rangeslider=dict(visible=True),
                   rangeselector=dict(buttons=[
                       dict(count=1, label="1 j", step="day", stepmode="backward"),
                       dict(count=7, label="7 j", step="day", stepmode="backward"),
                       dict(count=1, label="1 mois", step="month", stepmode="backward"),
                       dict(step="all", label="tout")])),
        margin=dict(l=60, r=20, t=60, b=40), height=720)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"annee_{args.code}_{args.year}_{m}min.html"
    fig.write_html(path, include_plotlyjs="cdn")
    print(f"écrit dans {path}")


if __name__ == "__main__":
    main()
