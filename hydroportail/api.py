# SPDX-FileCopyrightText: 2026 Louis Héraut <louis.heraut@inrae.fr>
# SPDX-License-Identifier: GPL-3.0-or-later
"""Talking to HydroPortail, and to the Hub'Eau referential.

This module is the only place that knows how the source behaves. Everything it
does is grounded in a measurement written down in SOURCE.md; the comments below
say which one, because several of these rules look wrong until you know why.

It returns lists of dictionaries. All the shaping happens in
``hydroportail.download``.
"""

from __future__ import annotations

import gzip
import json
import logging
import math
import os
import random
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence

import requests

logger = logging.getLogger("hydroportail")

BASE_URL = "https://hydro.eaufrance.fr"

#: Hub'Eau, used only for the station referential: identity, position, site.
HUBEAU_STATIONS = "https://hubeau.eaufrance.fr/api/v2/hydrometrie/referentiel/stations"

#: Says which software is calling and where to find it, never who is behind the
#: keyboard. HYDROPORTAIL_CONTACT may add a contact, and nothing is ever
#: collected automatically from the machine.
USER_AGENT = (
    "get-data-hydroportail/{version} "
    "(+https://github.com/lou-heraut/get-data-hydroportail-debit-instantane)"
)

REQUEST_TIMEOUT = 600  # seconds

#: What we aim for in a single response. A station-year of 5 minute raw data is
#: about 105 000 points, 5 seconds and 570 Ko on the wire. The cliff measured on
#: the service sits between 420 000 and 630 000 points returned, so this leaves
#: a factor of four of margin.
TARGET_POINTS = 100_000

#: The quota the service enforces: duration in minutes divided by step must stay
#: below this. It is NOT a real guard, it lets through requests the server then
#: fails to produce, which is why the window is sized from TARGET_POINTS and the
#: step is merely set to whatever makes that window acceptable.
QUOTA_MAX = 500_000

#: The form refuses anything outside 1..30 minutes: "Le pas de temps doit être
#: compris entre 1 et 30." Since the step is what buys quota, this caps how
#: wide a single window can be, whatever its density.
MAX_STEP = 30

FIRST_WINDOW_DAYS = 365
MIN_WINDOW_DAYS = 1
#: 30 x 500 000 minutes, about 28 years and a half.
MAX_WINDOW_DAYS = MAX_STEP * QUOTA_MAX // 1440

#: Statuses worth downloading. `pre_validated_and_validated` is a subset of
#: `most_valid`, verified on eight cases, and is only ever requested by the
#: control step that checks that inclusion still holds.
STATUSES = ("raw", "most_valid")

#: The three families of variables the form offers. Missing this was what made
#: the coverage map invisible at first.
FAMILIES = {
    "simple": ("simple_and_interpolated_and_hourly_variable",
               "hydro_series[simpleAndInterpolatedAndHourlyVariable]"),
    "daily": ("daily_variable", "hydro_series[dailyVariable]"),
    "monthly": ("monthly_variable", "hydro_series[monthlyVariable]"),
}


class APIError(RuntimeError):
    """A request failed for good, and retrying would not help."""


class TooManyPoints(RuntimeError):
    """The window is too wide for the server to build a response for it.

    Raised on HTTP 500. This is not a server failure: the same request fails
    the same way every time, and the cure is a smaller window, never a retry.
    """


class UnknownStation(APIError):
    """HydroPortail does not know this station code, and answers 404.

    Hub'Eau lists stations that the series route ignores, W107403002 for one,
    so a code can be perfectly valid in the referential and absent here. Like
    UnservedStation, this ends one station and not the campaign.
    """


class UnservedStation(APIError):
    """HydroPortail answers 500 for this station whatever is asked of it.

    Measured on V126002001, the Rhone at Ruffieux: 500 on a whole year as on a
    single day, on QIXnJ as on Q, while the station's own page answers 200 and
    an unknown station code answers 404. The 500 therefore says neither "too
    wide" nor "does not exist", and no window is small enough to get around it.
    See SOURCE.md.
    """


# --------------------------------------------------------------------------
#  Session and pacing
# --------------------------------------------------------------------------

_session: requests.Session | None = None

#: How long the previous response took. The delay before the next request is
#: exactly this, which keeps our duty cycle at half the server's time whatever
#: the size of the requests and whatever its load. Calibration found no rate at
#: which the service slows down, so rather than invent a constant we index on
#: its own behaviour. See SOURCE.md.
_last_elapsed = 1.0


def session() -> requests.Session:
    """Shared HTTP session. gzip is mandatory: it divides traffic by 55."""
    global _session
    if _session is None:
        from .schema import SCRIPT_VERSION

        agent = USER_AGENT.format(version=SCRIPT_VERSION)
        contact = os.environ.get("HYDROPORTAIL_CONTACT", "").strip()
        if contact:
            agent = f"{agent} contact: {contact}"
        new = requests.Session()
        new.headers.update({"User-Agent": agent, "Accept-Encoding": "gzip"})
        _session = new
    return _session


def _pace() -> None:
    """Wait as long as the previous response took, give or take 20 %."""
    time.sleep(_last_elapsed * random.uniform(0.9, 1.1))


# --------------------------------------------------------------------------
#  One request
# --------------------------------------------------------------------------

def _step_for(days: int, family: str = "simple") -> int:
    """The value to send as ``step`` for a window of ``days``.

    **It does not mean the same thing in the two families, and confusing them
    is silent.** For an instantaneous variable it is a pure quota knob: it
    never subsamples, `step` 1 and 20 return the same points, so it is raised
    to whatever buys the window. For a daily variable it is the ``n`` of the
    name, the length of the aggregation: `QIXnJ` with `step` 20 returns maxima
    over twenty days, that is a twentieth of the rows, and nothing in the
    response says so. It must stay at 1, and the quota does not bind there
    anyway, a request over 126 years being served without complaint.

    The step never subsamples anything, neither raw nor validated series: it
    only feeds the quota counter. So it is set from the window, never the other
    way round. Deducing the window from the quota instead would let 19 years of
    raw data through, which the server cannot build.

    It cannot go above :data:`MAX_STEP`, which is what caps
    :data:`MAX_WINDOW_DAYS`; callers keep their windows below that.
    """
    if family != "simple":
        return 1
    step = max(1, math.ceil(days * 1440 / QUOTA_MAX))
    if step > MAX_STEP:
        raise APIError(
            f"Fenêtre de {days} jours trop large : elle demanderait un pas de "
            f"{step} minutes, or HydroPortail n'accepte que 1 à {MAX_STEP}."
        )
    return step


def _request(code: str, variable: str, family: str, status: str,
             start: date, end: date, entity: str = "stationhydro") -> list[dict[str, Any]]:
    """One HTTP call, one list of points. Paces itself before leaving."""
    global _last_elapsed

    variable_type, variable_field = FAMILIES[family]
    params = {
        "hydro_series[variableType]": variable_type,
        variable_field: variable,
        "hydro_series[statusData]": status,
        "hydro_series[step]": _step_for((end - start).days + 1, family),
        "hydro_series[startAt]": start.strftime("%d/%m/%Y"),
        "hydro_series[endAt]": end.strftime("%d/%m/%Y"),
    }
    url = f"{BASE_URL}/{entity}/ajax/{code}/series"

    delay = 2.0
    for attempt in range(5):
        _pace()
        started = time.time()
        try:
            response = session().get(url, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as err:
            raise APIError(
                f"Échec de la requête HydroPortail pour {code} : {err}\n"
                "Vérifiez votre connexion ou votre proxy, puis relancez : "
                "le téléchargement reprendra là où il s'est arrêté."
            ) from err
        _last_elapsed = max(0.2, time.time() - started)

        if response.status_code == 500:
            # Measured and reproducible: too wide a window, not a sick server.
            raise TooManyPoints(f"{code} {status} {start}..{end}")
        if response.status_code in (429, 503, 504):
            logger.warning("    %s : HTTP %d, nouvelle tentative dans %.0f s",
                           code, response.status_code, delay)
            time.sleep(delay)
            delay *= 2
            continue
        if response.status_code == 400:
            raise APIError(
                f"Requête refusée pour {code} ({start} à {end}) : "
                f"{response.text[:200]}"
            )
        if response.status_code == 404:
            raise UnknownStation(
                f"{code} : HydroPortail ne connaît pas ce code (404). Il peut "
                "pourtant figurer au référentiel Hub'Eau, qui liste des "
                "stations que ce service n'expose pas."
            )
        if response.status_code != 200:
            raise APIError(f"HTTP {response.status_code} pour {code} ({start} à {end})")

        payload = response.json()
        series = payload.get("series") or {}
        unit = series.get("unit")
        if series.get("data") and unit != "l":
            # unitQ says "m3" while the values are litres per second; only
            # series.unit tells the truth. Refuse rather than be wrong by 1000.
            raise APIError(
                f"Unité inattendue « {unit} » pour {code} : le code suppose des "
                "litres par seconde. Vérifiez la source avant d'aller plus loin."
            )
        return series.get("data") or []

    # Out of patience. A gateway that keeps timing out is usually choking on
    # the size of the answer, so hand the caller the one remedy that helps.
    raise TooManyPoints(f"{code} {status} {start}..{end} après plusieurs tentatives")


# --------------------------------------------------------------------------
#  Cache
#
#  One file per window actually fetched. A window the server refuses is stored
#  as the split it was resolved into, so that resuming a run never replays a
#  request that is known to fail.
# --------------------------------------------------------------------------

def _cache_file(cache: Path, code: str, status: str, start: date, end: date,
                variable: str = "Q") -> Path:
    """One file per window actually fetched.

    The variable belongs in the name: without it a Q request and a QIXnJ
    request over the same window and status would overwrite each other. It does
    not happen today because the coverage map uses a window of its own, but
    relying on that would be a trap for whoever adds a variable.
    """
    return cache / code / f"{start:%Y%m%d}_{end:%Y%m%d}_{variable}_{status}.json.gz"


def _cache_read(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        logger.warning("    cache illisible, ignoré : %s", path.name)
        return None


def _cache_write(path: Path, content: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(content, handle)


def _fetch_window(cache: Path, code: str, status: str, start: date, end: date,
                  variable: str, family: str) -> list[dict[str, Any]]:
    """Points for one window, splitting it as often as the server requires.

    The cache holds either the points of a window, or the record that this
    window had to be split and into which halves. Replaying a run therefore
    costs no request at all, not even the one that is known to fail.
    """
    path = _cache_file(cache, code, status, start, end, variable)
    cached = _cache_read(path)
    if isinstance(cached, list):
        return cached
    if isinstance(cached, dict) and "split" in cached:
        points: list[dict[str, Any]] = []
        for left, right in cached["split"]:
            points.extend(_fetch_window(
                cache, code, status, date.fromisoformat(left),
                date.fromisoformat(right), variable, family))
        return points

    try:
        points = _request(code, variable, family, status, start, end)
    except TooManyPoints:
        days = (end - start).days + 1
        if family == "daily":
            # A daily window cannot be too wide: the whole life of a station is
            # about 46 000 points, two orders of magnitude below the cliff
            # measured on the service, and the quota does not bind on this
            # family. Splitting here would only repeat the same failure fifteen
            # times, which is what it did before this branch existed.
            raise UnservedStation(
                f"{code} : HydroPortail échoue sur cette station quelle que "
                f"soit la fenêtre demandée ({start} à {end}). Sa fiche répond "
                "pourtant, donc le code est bon : c'est le service qui ne sait "
                "pas produire sa série. Si l'échec ne dure pas, réessayer plus "
                "tard le confirmera."
            )
        if days <= MIN_WINDOW_DAYS:
            raise APIError(
                f"{code} : HydroPortail échoue même sur une seule journée "
                f"({start}). La station porte peut-être un volume anormal."
            )
        halves = [[a.isoformat(), b.isoformat()] for a, b in split_window(start, end)]
        logger.info("    fenêtre trop large (%d j), coupée en deux", days)
        _cache_write(path, {"split": halves})
        return _fetch_window(cache, code, status, start, end, variable, family)

    _cache_write(path, points)
    return points


# --------------------------------------------------------------------------
#  Walking a whole period
# --------------------------------------------------------------------------

def split_window(start: date, end: date) -> list[tuple[date, date]]:
    """Cut a window in two halves that cover it exactly.

    Pulled out so the arithmetic can be checked on its own: losing or repeating
    the pivot day here would silently drop or duplicate a day of data, in the
    one code path that only runs when the server is already unhappy.
    """
    days = (end - start).days + 1
    middle = start + timedelta(days=days // 2 - 1)
    return [(start, middle), (middle + timedelta(days=1), end)]


def walk(start: date, end: date, fetch, on_progress=None,
         first_span: int = FIRST_WINDOW_DAYS) -> list[dict[str, Any]]:
    """Cover ``start``..``end`` window after window, calling ``fetch`` on each.

    The whole tiling logic lives here, with no knowledge of HTTP or of the
    cache, so that the property that matters can be checked on synthetic input:
    **the windows must cover the period exactly**, with no gap of a single day
    and no overlap that would count points twice.

    The width of the next window follows the density just observed, which is
    what makes one rule fit both shapes of series. At Tarascon the raw series
    holds 105 209 points a year and stays on one year windows, while the
    most_valid series holds 6 077 and jumps to sixteen years. Without the growth
    the lightest data would cost the most requests, which is absurd.
    """
    points: list[dict[str, Any]] = []
    cursor = start
    span = min(first_span, MAX_WINDOW_DAYS)

    while cursor <= end:
        stop = min(end, cursor + timedelta(days=span - 1))
        got = fetch(cursor, stop)
        points.extend(got)
        if on_progress:
            on_progress(cursor, stop, len(got), len(points))

        days = (stop - cursor).days + 1
        if got:
            span = span_for(len(got) / days)
        else:
            # Nothing here: move on faster rather than crawl through a gap.
            span = min(MAX_WINDOW_DAYS, span * 4)
        cursor = stop + timedelta(days=1)

    return points


def span_for(points_per_day: float) -> int:
    """Window width that should return about :data:`TARGET_POINTS` points."""
    if points_per_day <= 0:
        return MAX_WINDOW_DAYS
    span = int(TARGET_POINTS / points_per_day)
    return max(MIN_WINDOW_DAYS, min(MAX_WINDOW_DAYS, span))


def fetch_series(cache: Path, code: str, status: str, start: date, end: date,
                 variable: str = "Q", family: str = "simple",
                 on_progress=None,
                 first_span: int = FIRST_WINDOW_DAYS) -> list[dict[str, Any]]:
    """Every point of a status over a period.

    Windows are replanned from scratch on a resumed run, which reproduces the
    same tiling because the densities that drive it come back from the cache.
    """
    def fetch(begin: date, finish: date) -> list[dict[str, Any]]:
        return _fetch_window(cache, code, status, begin, finish, variable, family)

    return walk(start, end, fetch, on_progress, first_span)


# --------------------------------------------------------------------------
#  The coverage map
# --------------------------------------------------------------------------

def coverage_map(cache: Path, code: str, first_year: int = 1900,
                 today: date | None = None) -> list[dict[str, Any]]:
    """One point per day on which an instantaneous series exists.

    QIXnJ is the daily maximum *of the instantaneous series*, so it exists
    exactly on the days that series exists. Asking for it reads the table of
    contents instead of the book: a whole station life comes back in under two
    seconds and a few thousand points, against millions for the series itself.

    Ask for it in ``most_valid``: in ``raw`` the daily summaries are only kept
    for about two months.

    It says which days exist, never how finely. A day present may hold 288
    points or 8, which is why the resolution columns of couverture.csv can only
    be filled once the series itself has been downloaded.
    """
    today = today or date.today()
    # One request for the whole life of the station: the daily family keeps its
    # step at 1 and the quota does not bind on it.
    return _fetch_window(cache, code, "most_valid", date(first_year, 1, 1),
                         today, "QIXnJ", "daily")


# --------------------------------------------------------------------------
#  Hub'Eau station referential
#
#  A second service, queried only for identity and the site a station belongs
#  to. A failure here degrades the referential, it never stops a download.
# --------------------------------------------------------------------------

#: Asking for the whole record on purpose. On the sites endpoint of the same
#: API, naming the coordinate fields explicitly returns them null; the habit of
#: not trimming `fields` is cheap insurance.
_HUBEAU_BATCH = 40


def station_records(codes: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Hub'Eau referential records, keyed by station code.

    Codes unknown to the referential are simply absent from the result, which
    is itself worth reporting: a code that HydroPortail serves but Hub'Eau
    ignores deserves a look.
    """
    wanted = [c for c in dict.fromkeys(str(c).strip() for c in codes) if c]
    found: dict[str, dict[str, Any]] = {}
    for start in range(0, len(wanted), _HUBEAU_BATCH):
        batch = wanted[start:start + _HUBEAU_BATCH]
        for row in _hubeau(code_station=",".join(batch), size=len(batch)):
            if row.get("code_station"):
                found[row["code_station"]] = row
    return found


def site_stations(site_codes: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
    """Every station of the given sites, keyed by site code.

    Used to answer the only question a third party list cannot be trusted on:
    given this code, which station of its site actually carries the discharge.
    """
    wanted = [c for c in dict.fromkeys(str(c).strip() for c in site_codes) if c]
    found: dict[str, list[dict[str, Any]]] = {}
    for code in wanted:
        rows = _hubeau(code_site=code, size=100)
        if rows:
            found[code] = rows
    return found


def _hubeau(**params: Any) -> list[dict[str, Any]]:
    try:
        response = session().get(
            HUBEAU_STATIONS, params=dict(params, format="json"), timeout=120)
        if response.status_code not in (200, 206):
            logger.warning("    référentiel Hub'Eau : HTTP %d", response.status_code)
            return []
        return response.json().get("data") or []
    except (requests.RequestException, ValueError) as err:
        logger.warning("    référentiel Hub'Eau injoignable (%s) : "
                       "les colonnes d'identité resteront vides.", err)
        return []
