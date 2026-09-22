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

from hydroportail import chemins, download, inventory, summary
from hydroportail.api import APIError
from hydroportail.download import DEFAULT_ROOT

#: Où vivent les demandes. Un cas porte le même nom des deux côtés : sa liste
#: de stations ici, ses tables sous donnees_hydroportail/.
RESSOURCES = Path("ressources")

EXEMPLES = """\
exemples :
  # ce que contient un cas, sans rien telecharger de lourd
  python download_hydroportail.py --cas 2026-09_jeu-de-test --inventaire

  # telecharger ses chroniques, les deux passes
  python download_hydroportail.py --cas 2026-09_jeu-de-test

  # la chronique arbitree par le producteur seule, dix fois plus legere
  python download_hydroportail.py --cas 2026-09_eclusees-rmc --statuts most_valid

  # quelques stations hors de tout cas, pour regarder
  python download_hydroportail.py --cas bac-a-sable --inventaire \\
      --stations V720001002 W011001001 X031001001
"""


def lire_codes(chemin: str | Path) -> list[str]:
    """Un code par ligne. Les lignes vides et celles commençant par # sont ignorées."""
    lignes = Path(chemin).read_text(encoding="utf-8").splitlines()
    return [ligne.strip() for ligne in lignes
            if ligne.strip() and not ligne.strip().startswith("#")]


def codes_du_cas(cas: str) -> list[str]:
    """Les stations que ce cas demande, dans `ressources/<cas>/stations.txt`.

    C'est le seul contrat entre une demande et le téléchargement. Peu importe
    par quel chemin la liste est arrivée, tableur traduit ou dix codes écrits à
    la main : ici, c'est un code par ligne.
    """
    chemin = RESSOURCES / cas / "stations.txt"
    if not chemin.exists():
        raise FileNotFoundError(
            f"{chemin} : ce cas n'a pas de liste de stations. Donnez-en une avec "
            "--stations ou --fichier, ou écrivez ce fichier.")
    return lire_codes(chemin)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Télécharge les débits instantanés depuis HydroPortail.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXEMPLES,
    )
    parser.add_argument("--cas", required=True, metavar="NOM",
                        help="nom du cas, ex. 2026-09_eclusees-rmc. Ses stations "
                             f"sont lues dans {RESSOURCES}/<cas>/stations.txt et "
                             "ses tables écrites sous <racine>/<cas>/")
    parser.add_argument("--racine", default=DEFAULT_ROOT, metavar="CHEMIN",
                        help=f"racine des données (défaut : {DEFAULT_ROOT}). Le "
                             "cache des réponses y est partagé par tous les cas")

    groupe = parser.add_argument_group("quelles stations")
    groupe.add_argument("--stations", nargs="+", metavar="CODE",
                        help="codes Sandre de station, au lieu de ceux du cas")
    groupe.add_argument("--fichier", metavar="CHEMIN",
                        help="fichier de codes, un par ligne, au lieu de ceux du cas")

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
        codes = codes_du_cas(args.cas)
    passes = {"les-deux": ("raw", "most_valid"),
              "raw": ("raw",), "most_valid": ("most_valid",)}[args.statuts]

    try:
        if args.inventaire:
            inventory(args.cas, args.racine, codes=codes)
        else:
            download(args.cas, args.racine, codes=codes, statuts=passes)
        if not args.silencieux:
            summary(chemins(args.cas, args.racine)[0])
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
