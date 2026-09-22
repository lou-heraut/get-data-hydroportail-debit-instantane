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

from hydroportail import download, inventory, paths, summary
from hydroportail.api import APIError
from hydroportail.download import DEFAULT_ROOT

#: Où vivent les demandes. Un cas porte le même nom des deux côtés : sa liste
#: de stations ici, ses tables sous donnees_hydroportail/.
CASES = Path("cases")

EXAMPLES = """\
exemples :
  # ce que contient un cas, sans rien telecharger de lourd
  python download_hydroportail.py --case 2026-09_test-set --inventory

  # telecharger ses chroniques, les deux passes
  python download_hydroportail.py --case 2026-09_test-set

  # la chronique arbitree par le producteur seule, dix fois plus legere
  python download_hydroportail.py --case 2026-09_eclusees-rmc --statuses most_valid

  # quelques stations hors de tout cas, pour regarder
  python download_hydroportail.py --case bac-a-sable --inventory \\
      --stations V720001002 W011001001 X031001001
"""


def read_codes(path: str | Path) -> list[str]:
    """Un code par ligne. Les lignes vides et celles commençant par # sont ignorées."""
    rows = Path(path).read_text(encoding="utf-8").splitlines()
    return [row.strip() for row in rows
            if row.strip() and not row.strip().startswith("#")]


def case_codes(case: str) -> list[str]:
    """Les stations que ce cas demande, dans `cases/<case>/stations.txt`.

    C'est le seul contrat entre une demande et le téléchargement. Peu importe
    par quel chemin la liste est arrivée, tableur traduit ou dix codes écrits à
    la main : ici, c'est un code par ligne.
    """
    path = CASES / case / "stations.txt"
    if not path.exists():
        raise FileNotFoundError(
            f"{path} : ce cas n'a pas de liste de stations. Donnez-en une avec "
            "--stations ou --file, ou écrivez ce fichier.")
    return read_codes(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Télécharge les débits instantanés depuis HydroPortail.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    parser.add_argument("--case", required=True, metavar="NOM",
                        help="nom du cas, ex. 2026-09_eclusees-rmc. Ses stations "
                             f"sont lues dans {CASES}/<case>/stations.txt et "
                             "ses tables écrites sous <root>/<case>/")
    parser.add_argument("--root", default=DEFAULT_ROOT, metavar="CHEMIN",
                        help=f"racine des données (défaut : {DEFAULT_ROOT}). Le "
                             "cache des réponses y est partagé par tous les cas")

    group = parser.add_argument_group("quelles stations")
    group.add_argument("--stations", nargs="+", metavar="CODE",
                       help="codes Sandre de station, au lieu de ceux du cas")
    group.add_argument("--file", metavar="CHEMIN",
                       help="fichier de codes, un par ligne, au lieu de ceux du cas")

    group = parser.add_argument_group("comment")
    group.add_argument("--inventory", action="store_true",
                       help="afficher et écrire ce qui existe, sans télécharger "
                             "de chronique (une requête rapide par station)")
    group.add_argument("--statuses", default="both",
                       choices=["both", "raw", "most_valid"],
                       help="quelles passes télécharger (défaut : both). "
                             "most_valid est la chronique arbitrée par le "
                             "producteur, raw le signal brut non corrigé")
    group.add_argument("--quiet", action="store_true",
                       help="n'afficher que les erreurs")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s", stream=sys.stderr,
    )

    codes = list(args.stations or [])
    if args.file:
        codes += read_codes(args.file)
    if not codes:
        codes = case_codes(args.case)
    passes = {"both": ("raw", "most_valid"),
              "raw": ("raw",), "most_valid": ("most_valid",)}[args.statuses]

    try:
        if args.inventory:
            inventory(args.case, args.root, codes=codes)
        else:
            download(args.case, args.root, codes=codes, statuses=passes)
        if not args.quiet:
            summary(paths(args.case, args.root)[0])
        return 0
    except (APIError, ValueError, FileNotFoundError) as error:
        print(f"\nErreur : {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrompu. Relancez la commande : ce qui est déjà en cache "
              "ne sera pas redemandé.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
