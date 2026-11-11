"""Observations of the nivo-meteorological network."""

import asyncio
import csv
import gzip
import io
import logging
from datetime import datetime, timedelta

import aiohttp

from .const import NIVO_TIMEOUT, NIVO_URL
from .exceptions import MeteoFranceMontagneApiError
from .models import Observation
from .stations import station_name

_LOGGER = logging.getLogger(__name__)


def _nivo_float(value: str | None) -> float | None:
    """Convert a value of the nivo file to float, None when missing."""
    if not value:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nivo_int(value: str | None) -> int | None:
    """Convert a code of the nivo file to int, None when missing or unknown ("/")."""
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nivo_cm(value: str | None) -> int | None:
    """Convert a snow depth in meters to centimeters."""
    meters = _nivo_float(value)
    return None if meters is None else round(meters * 100)


def _nivo_celsius(value: str | None) -> float | None:
    """Convert a temperature in kelvins to degrees Celsius."""
    kelvins = _nivo_float(value)
    return None if kelvins is None else round(kelvins - 273.15, 1)


def _nivo_time(row: dict[str, str]) -> datetime:
    """Return the time of an observation."""
    return datetime.fromisoformat(row["validity_time"].replace("Z", "+00:00"))


def parse_nivo_observations(content: bytes) -> dict[str, Observation]:
    """Parse a yearly nivo file into the last observation of each station."""
    text = gzip.decompress(content).decode("utf-8")
    rows_by_station: dict[str, list[dict[str, str]]] = {}
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        if row.get("geo_id_wmo") and row.get("validity_time"):
            rows_by_station.setdefault(row["geo_id_wmo"], []).append(row)

    observations = {}
    for station_id, rows in rows_by_station.items():
        rows.sort(key=_nivo_time, reverse=True)
        last = rows[0]
        # Some stations observe again at midday, without measuring everything:
        # complete with the morning observation
        recent = [
            row
            for row in rows
            if _nivo_time(row) > _nivo_time(last) - timedelta(hours=24)
        ]

        def value(column: str, rows: list[dict[str, str]] = recent) -> str:
            """Return the most recent value of a column, '' when not measured."""
            return next((row[column] for row in rows if row.get(column)), "")

        observations[station_id] = Observation(
            id=station_id,
            nom=station_name(station_id, last["name"]),
            altitude=_nivo_int(last["Altitude"]),
            latitude=_nivo_float(last["lat"]),
            longitude=_nivo_float(last["lon"]),
            date=last["validity_time"],
            hauteur_neige=_nivo_cm(value("ht_neige")),
            hauteur_neige_altitude=_nivo_cm(value("ht_neige_alti")),
            # Measured on a board cleared at each observation: over 24h in the
            # morning (-99), over a few hours at midday (-50)
            neige_fraiche_24h=_nivo_cm(
                value(
                    "ssfrai", [row for row in recent if row.get("perssfrai") == "-99"]
                )
            ),
            neige_fraiche_altitude=_nivo_cm(value("neige_fraiche")),
            temps_present=_nivo_int(value("ww")),
            nebulosite=_nivo_int(value("n")),
            precipitations_24h=_nivo_float(value("rr24")),
            humidite=_nivo_int(value("u")),
            point_rosee=_nivo_celsius(value("td")),
            temperature=_nivo_celsius(value("t")),
            temperature_min_24h=_nivo_celsius(value("tn24")),
            temperature_max_24h=_nivo_celsius(value("tx24")),
            temperature_neige=_nivo_celsius(value("t_neige")),
            vent_direction=_nivo_int(value("dd")),
            vent_force=_nivo_float(value("ff")),
            vent_altitude_direction=_nivo_int(value("dd_alti")),
            vent_altitude_force=_nivo_float(value("ff_alti")),
            chasse_neige=_nivo_int(value("chasse_neige")),
            risque=_nivo_int(value("aval_risque")),
            grain_surface=_nivo_int(value("grain_predom")),
            grain_sous_surface=_nivo_int(value("grain_nombre")),
            masse_volumique=_nivo_float(value("m_vol_neige")),
        )

    return observations


class MeteoFranceNivoApi:
    """Observations of the nivo-meteorological network, downloaded without key."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        """Initialize the API."""
        self.session = session
        # ETag and parsed observations of each downloaded file
        self._cache: dict[str, tuple[str, dict[str, Observation]]] = {}

    async def observations(self, year: int) -> dict[str, Observation]:
        """Return the last observation of each station during a year.

        Empty when the file of the year is not published yet.
        """
        url = NIVO_URL.format(year=year)
        headers = {}
        if cached := self._cache.get(url):
            headers["If-None-Match"] = cached[0]

        timeout = aiohttp.ClientTimeout(total=NIVO_TIMEOUT)
        _LOGGER.debug("Executing URL fetch: %s", url)
        try:
            async with self.session.get(
                url, timeout=timeout, headers=headers
            ) as response:
                if response.status == 304 and cached:
                    return cached[1]
                if response.status in (403, 404):
                    # S3 answers 403 or 404 for a file not created yet
                    return {}
                if response.status != 200:
                    raise MeteoFranceMontagneApiError(
                        f"HTTP {response.status} error for url: {url}"
                    )
                content = await response.read()
                etag = response.headers.get("ETag")
        except aiohttp.ClientError as e:
            raise MeteoFranceMontagneApiError(
                f"Client error for url: {url}: {e}"
            ) from e
        except TimeoutError as e:
            raise MeteoFranceMontagneApiError(f"Timeout fetching url: {url}") from e

        try:
            # Several MB to decompress and parse: off the event loop
            observations = await asyncio.get_running_loop().run_in_executor(
                None, parse_nivo_observations, content
            )
        except (
            OSError,
            EOFError,
            UnicodeDecodeError,
            csv.Error,
            KeyError,
            ValueError,
        ) as e:
            raise MeteoFranceMontagneApiError(f"Invalid nivo file {url}: {e}") from e

        if etag:
            self._cache[url] = (etag, observations)
        return observations

    async def stations(self, year: int) -> dict[str, Observation]:
        """Return the stations observing this year or the previous one."""
        previous, current = await asyncio.gather(
            self.observations(year - 1), self.observations(year)
        )
        return {**previous, **current}
