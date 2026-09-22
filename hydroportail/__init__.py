# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Download instantaneous discharge series from HydroPortail.

Source: the AJAX route of the HydroPortail station page, the public channel of
        the form the site displays. https://hydro.eaufrance.fr/

Hub'Eau cannot serve this data: its real time endpoint only goes back one
rolling month, and its historical endpoint stops at the daily time step. See
SOURCE.md for the measurements behind every choice made here.

Typical use, once the download layer exists:

    from hydroportail import download, read

    download("2026-09_test-set", codes=["V720001002"])
    df = read("data/2026-09_test-set")
"""

from .download import paths, download, inventory, read, read_tables, summary
from .schema import SCRIPT_VERSION as __version__

__all__ = ["paths", "download", "inventory", "read", "read_tables", "summary",
           "__version__"]
