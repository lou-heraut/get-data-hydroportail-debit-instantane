#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Interface en ligne de commande.

À ce stade, seul l'inventaire existe : il dit ce que des codes de station
contiennent réellement, sans télécharger de chronique. Le téléchargement des
mesures vient ensuite.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from hydroportail import download, inventory, summary
from hydroportail.api import APIError

EXEMPLES = """\
exemples :
  # ce que contiennent trois stations, sans rien telecharger de lourd
  python download_hydroportail.py --inventaire --stations V720001002 W011001001 X031001001

  # la meme chose depuis un fichier, un code par ligne
  python download_hydroportail.py --inventaire --fichier stations_rmc.txt

  # telecharger les chroniques, les deux passes
  python download_hydroportail.py --stations V720001002

  # la chronique arbitree par le producteur seule, dix fois plus legere
  python download_hydroportail.py --fichier stations_rmc.txt --statuts most_valid
"""


def lire_codes(chemin: str) -> list[str]:
    """Un code par ligne. Les lignes vides et celles commençant par # sont ignorées."""
    lignes = Path(chemin).read_text(encoding="utf-8").splitlines()
    return [ligne.strip() for ligne in lignes
            if ligne.strip() and not ligne.strip().startswith("#")]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Télécharge les débits instantanés depuis HydroPortail.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXEMPLES,
    )
    parser.add_argument(
        "dossier", nargs="?", default="donnees_hydroportail",
        help="dossier de destination (défaut : donnees_hydroportail)")

    groupe = parser.add_argument_group("quelles stations")
    groupe.add_argument("--stations", nargs="+", metavar="CODE",
                        help="codes Sandre de station, ex. --stations V720001002")
    groupe.add_argument("--fichier", metavar="CHEMIN",
                        help="fichier de codes, un par ligne")

    groupe = parser.add_argument_group("comment")
    groupe.add_argument("--inventaire", action="store_true",
                        help="afficher et écrire ce qui existe, sans télécharger "
                             "de chronique (une requête rapide par station)")
    groupe.add_argument("--statuts", default="les-deux",
                        choices=["les-deux", "raw", "most_valid"],
                        help="quelles passes télécharger (défaut : les-deux). "
                             "most_valid est la chronique arbitrée par le "
                             "producteur, raw le signal brut non corrigé")
    groupe.add_argument("--silencieux", action="store_true",
                        help="n'afficher que les erreurs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.silencieux else logging.INFO,
        format="%(message)s", stream=sys.stderr,
    )

    codes = list(args.stations or [])
    if args.fichier:
        codes += lire_codes(args.fichier)
    if not codes:
        parser.error("indiquez des stations avec --stations ou --fichier")
    passes = {"les-deux": ("raw", "most_valid"),
              "raw": ("raw",), "most_valid": ("most_valid",)}[args.statuts]

    try:
        if args.inventaire:
            inventory(folder=args.dossier, codes=codes)
        else:
            download(folder=args.dossier, codes=codes, statuts=passes)
        if not args.silencieux:
            summary(args.dossier)
        return 0
    except (APIError, ValueError, FileNotFoundError) as erreur:
        print(f"\nErreur : {erreur}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu. Relancez la commande : ce qui est déjà en cache "
              "ne sera pas redemandé.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
