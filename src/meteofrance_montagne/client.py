"""Client of the avalanche bulletins API (BRA)."""

import json
import logging
import xml.etree.ElementTree as ET
from typing import Any

import aiohttp

from .bulletin import parse_bulletin_xml
from .const import BASE_URL, TIMEOUT
from .exceptions import (
    MeteoFranceMontagneApiError,
    MeteoFranceMontagneAuthError,
    MeteoFranceMontagneOffSeason,
)
from .massifs import organize_by_department

_LOGGER = logging.getLogger(__name__)


class MeteoFranceMontagneApi:
    """Avalanche bulletins of the massifs, behind an API key."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        """Initialize the API."""
        self.session = session
        self.token = token

    async def list_massif(self) -> dict[str, list[dict]]:
        """Get list of massifs organized by department."""
        response = await self.call_api(f"{BASE_URL}/liste-massifs")
        return organize_by_department(json.loads(response))

    async def bulletin(self, massif: int | str) -> dict[str, Any]:
        """Get avalanche bulletin for a massif."""
        response = await self.call_api(
            f"{BASE_URL}/massif/BRA?id-massif={massif}&format=xml"
        )
        try:
            xml_doc = ET.fromstring(response)
        except ET.ParseError as e:
            raise MeteoFranceMontagneApiError(f"XML parsing error: {e}") from e

        # Outside the season the API answers a single <message> instead of a bulletin
        if xml_doc.tag == "message":
            raise MeteoFranceMontagneOffSeason((xml_doc.text or "").strip())

        return parse_bulletin_xml(xml_doc)

    async def image(self, image_type: str, massif: int | str) -> bytes | None:
        """Get image for a massif, None when it is not published."""
        url = f"{BASE_URL}/massif/image/{image_type}?id-massif={massif}"
        try:
            return await self.call_api(url)
        except MeteoFranceMontagneOffSeason:
            # Some massifs lack an image during the season, e.g. the last
            # seven days in Corsica
            _LOGGER.debug("No %s image for massif %s", image_type, massif)
            return None

    async def rose_pentes(self, massif: int | str) -> bytes | None:
        """Get the dangerous slopes of a massif."""
        return await self.image("rose-pentes", massif)

    async def montagne_risques(self, massif: int | str) -> bytes | None:
        """Get the risk by altitude of a massif."""
        return await self.image("montagne-risques", massif)

    async def montagne_enneigement(self, massif: int | str) -> bytes | None:
        """Get the snow depth by altitude of a massif."""
        return await self.image("montagne-enneigement", massif)

    async def graphe_neige_fraiche(self, massif: int | str) -> bytes | None:
        """Get the fresh snow graph of a massif."""
        return await self.image("graphe-neige-fraiche", massif)

    async def apercu_meteo(self, massif: int | str) -> bytes | None:
        """Get the weather overview of a massif."""
        return await self.image("apercu-meteo", massif)

    async def sept_derniers_jours(self, massif: int | str) -> bytes | None:
        """Get the last seven days of a massif."""
        return await self.image("sept-derniers-jours", massif)

    async def call_api(self, url: str) -> bytes:
        """Fetch data from a given URL."""
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        _LOGGER.debug("Executing URL fetch: %s", url)
        headers = {"accept": "*/*", "apikey": self.token}
        try:
            async with self.session.get(
                url, timeout=timeout, headers=headers
            ) as response:
                if response.status == 401:
                    raise MeteoFranceMontagneAuthError(
                        "Invalid API token (401 Unauthorized)"
                    )
                if response.status == 404:
                    # Documented answer for a dataset unavailable outside the season
                    raise MeteoFranceMontagneOffSeason(await response.text())
                if response.status != 200:
                    raise MeteoFranceMontagneApiError(
                        f"HTTP {response.status} error for url: {url}"
                    )
                return await response.read()

        except aiohttp.ClientError as e:
            raise MeteoFranceMontagneApiError(
                f"Client error for url: {url}: {e}"
            ) from e
        except TimeoutError as e:
            raise MeteoFranceMontagneApiError(f"Timeout fetching url: {url}") from e
