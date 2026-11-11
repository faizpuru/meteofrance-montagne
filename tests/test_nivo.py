"""Tests for the observations of the nivo-meteorological network."""

import gzip

import pytest

from meteofrance_montagne import (
    MeteoFranceMontagneApiError,
    MeteoFranceNivoApi,
    parse_nivo_observations,
    station_name,
)
from meteofrance_montagne.const import NIVO_URL

from .conftest import load_resource, nivo_file

STATION_ID = "7498"
ETAG = '"nivo-2026"'


@pytest.fixture
def api(session):
    """Return a client of the observations."""
    return MeteoFranceNivoApi(session)


def test_parse_two_observations_a_day():
    """Complete the midday observation with the morning one."""
    observation = parse_nivo_observations(nivo_file())[STATION_ID]

    assert observation.nom == "Val d'Isère (Joseray)"
    assert observation.altitude == 1854
    assert observation.latitude == 45.445
    assert observation.longitude == 6.978167
    # Midday observation
    assert observation.date == "2026-02-12T12:02:00Z"
    assert observation.hauteur_neige == 151
    assert observation.temperature == -1.7
    assert observation.grain_sous_surface == 9
    # Only measured in the morning
    assert observation.temperature_min_24h == -6.6
    assert observation.temperature_max_24h == 0.9
    # The morning board over 24h, not the midday one over 5h
    assert observation.neige_fraiche_24h == 31
    # Not observed over the last 24h
    assert observation.chasse_neige is None
    assert observation.temps_present == 73
    assert observation.nebulosite == 8
    assert observation.humidite == 95
    assert observation.point_rosee == -2.4
    # Over 24h, measured in the morning
    assert observation.precipitations_24h == 24.0


def test_parse_ignores_older_days():
    """Leave out the values not measured over the last 24h."""
    observation = parse_nivo_observations(nivo_file())["7393"]

    assert observation.date == "2026-02-12T06:45:00Z"
    assert observation.hauteur_neige == 120
    # Measured two days before only
    assert observation.neige_fraiche_24h is None
    assert observation.risque is None


@pytest.mark.parametrize(
    ("station_id", "name", "expected"),
    [
        ("7931", "CEILLAC_NIVO", "Ceillac"),
        ("7916", "ST FRANCOIS LONG", "Saint-François-Longchamp"),
        # Unknown stations
        ("1", "SUPER DEVOLUY_NIVO2", "Super Devoluy 2"),
        ("2", "LA FOUX D ALLOS_NIVO", "La Foux d'Allos"),
        ("3", "L Alpe d Huez 2350", "L'Alpe d'Huez 2350"),
        ("4", "SERRE CHE-CHANTEMERLE_NIVO", "Serre Che-Chantemerle"),
        ("5", "Les Gets", "Les Gets"),
    ],
)
def test_station_name(station_id, name, expected):
    """Give the usual name of a station, readable when unknown."""
    assert station_name(station_id, name) == expected


async def test_observations_unchanged(mock_http, api):
    """Ask for the file only if it changed, and keep the observations."""
    url = NIVO_URL.format(year=2026)
    mock_http.get(url, body=nivo_file(), headers={"ETag": ETAG})
    mock_http.get(url, status=304)

    observations = await api.observations(2026)
    assert observations[STATION_ID].hauteur_neige == 151
    assert await api.observations(2026) is observations

    _, call = next(iter(mock_http.requests.values()))
    assert call.kwargs["headers"] == {"If-None-Match": ETAG}


@pytest.mark.parametrize("status", [403, 404])
async def test_observations_not_published(mock_http, api, status):
    """Return no observation while the file of the year is not created."""
    mock_http.get(NIVO_URL.format(year=2027), status=status)

    assert await api.observations(2027) == {}


async def test_observations_error(mock_http, api):
    """Raise an API error when the file cannot be downloaded."""
    mock_http.get(NIVO_URL.format(year=2026), status=500)

    with pytest.raises(MeteoFranceMontagneApiError, match="HTTP 500"):
        await api.observations(2026)


@pytest.mark.parametrize(
    "content",
    [
        b"not gzip",
        gzip.compress(b"\xff\xfe"),
        gzip.compress(b"geo_id_wmo;validity_time\n1;x\n"),
    ],
    ids=["not_gzip", "not_utf8", "invalid_date"],
)
async def test_observations_invalid_file(mock_http, api, content):
    """Raise an API error on a file that cannot be parsed."""
    mock_http.get(NIVO_URL.format(year=2026), body=content)

    with pytest.raises(MeteoFranceMontagneApiError, match="Invalid nivo file"):
        await api.observations(2026)


async def test_stations(mock_http, api):
    """List the stations of the year and of the previous one."""
    previous = load_resource("nivo_sample.csv").replace(b"2026-02-", b"2025-12-")
    mock_http.get(NIVO_URL.format(year=2025), body=gzip.compress(previous))
    mock_http.get(NIVO_URL.format(year=2026), body=nivo_file())

    stations = await api.stations(2026)
    assert set(stations) == {"7393", STATION_ID}
    # The current year wins
    assert stations[STATION_ID].date == "2026-02-12T12:02:00Z"
