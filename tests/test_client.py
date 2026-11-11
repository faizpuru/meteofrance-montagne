"""Tests for the client of the avalanche bulletins API."""

import aiohttp
import pytest

from meteofrance_montagne import (
    MeteoFranceMontagneApi,
    MeteoFranceMontagneApiError,
    MeteoFranceMontagneAuthError,
    MeteoFranceMontagneOffSeason,
)
from meteofrance_montagne.const import BASE_URL

from .conftest import TOKEN, load_resource

BULLETIN_URL = f"{BASE_URL}/massif/BRA?id-massif=72&format=xml"

GEOMETRY = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[6.8, 45.4], [7.1, 45.4], [7.1, 45.6], [6.8, 45.6], [6.8, 45.4]]]
    ],
}

# Answer of /liste-massifs, reduced to the properties read
MASSIFS = {
    "features": [
        {
            "properties": {
                "title": "Orlu St-Barthelemy",
                "code": 72,
                "Departement": "Ariege",
            },
        },
        {
            "properties": {
                "title": "Haute-Tarentaise",
                "code": 6,
                "Departement": "Savoie",
            },
            "geometry": GEOMETRY,
        },
        # On two departments
        {
            "properties": {
                "title": "Ubaye",
                "code": 21,
                "Departement": "Alpes-de-Haute-Provence",
                "Dep2": "Hautes-Alpes",
            },
        },
    ]
}


@pytest.fixture
def api(session):
    """Return a client with the test key."""
    return MeteoFranceMontagneApi(session, TOKEN)


async def test_bulletin(mock_http, api):
    """Fetch and parse the bulletin of a massif."""
    mock_http.get(BULLETIN_URL, body=load_resource("sample_bulletin.xml"))

    bulletin = await api.bulletin(72)
    assert bulletin.massif == "Orlu St-Barthelemy"
    assert bulletin.risque.risque_max == "3"


async def test_bulletin_off_season(mock_http, api):
    """Raise off season when the API answers a message instead of a bulletin."""
    mock_http.get(BULLETIN_URL, body=load_resource("offseason_bulletin.xml"))

    with pytest.raises(MeteoFranceMontagneOffSeason, match="la saison est terminée"):
        await api.bulletin(72)


async def test_bulletin_invalid_xml(mock_http, api):
    """Raise an API error on a malformed answer."""
    mock_http.get(BULLETIN_URL, body=b"<BULLETINS")

    with pytest.raises(MeteoFranceMontagneApiError, match="XML parsing error"):
        await api.bulletin(72)


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, MeteoFranceMontagneAuthError),
        (404, MeteoFranceMontagneOffSeason),
        (500, MeteoFranceMontagneApiError),
    ],
)
async def test_call_api_errors(mock_http, api, status, error):
    """Map the HTTP errors to the exceptions."""
    mock_http.get(BULLETIN_URL, status=status)

    with pytest.raises(error):
        await api.call_api(BULLETIN_URL)


@pytest.mark.parametrize("exception", [aiohttp.ClientConnectionError(), TimeoutError()])
async def test_call_api_unreachable(mock_http, api, exception):
    """Raise an API error when the API cannot be reached."""
    mock_http.get(BULLETIN_URL, exception=exception)

    with pytest.raises(MeteoFranceMontagneApiError):
        await api.call_api(BULLETIN_URL)


async def test_image(mock_http, api):
    """Return the image of a massif."""
    mock_http.get(f"{BASE_URL}/massif/image/rose-pentes?id-massif=72", body=b"PNG")

    assert await api.rose_pentes(72) == b"PNG"


async def test_image_not_published(mock_http, api):
    """Return no image when the API has none for the massif."""
    mock_http.get(
        f"{BASE_URL}/massif/image/sept-derniers-jours?id-massif=40",
        status=404,
        payload={"detail": "no matching blob"},
    )

    assert await api.sept_derniers_jours(40) is None


async def test_list_massif(mock_http, api):
    """Send the API key and organize the massifs by department."""
    mock_http.get(f"{BASE_URL}/liste-massifs", payload=MASSIFS)

    massifs = await api.list_massif()
    assert {
        department: [(massif.nom, massif.code) for massif in department_massifs]
        for department, department_massifs in massifs.items()
    } == {
        "Ariege": [("Orlu St-Barthelemy", 72)],
        "Savoie": [("Haute-Tarentaise", 6)],
        "Alpes-de-Haute-Provence": [("Ubaye", 21)],
        "Hautes-Alpes": [("Ubaye", 21)],
    }
    assert massifs["Savoie"][0].geometry == GEOMETRY
    assert massifs["Ariege"][0].geometry is None
    # The same massif in its two departments
    assert massifs["Hautes-Alpes"][0] is massifs["Alpes-de-Haute-Provence"][0]

    ((call,),) = mock_http.requests.values()
    assert call.kwargs["headers"]["apikey"] == TOKEN
