"""Async client for the Météo-France avalanche bulletins and snow observations."""

from .bulletin import parse_bulletin_xml
from .client import MeteoFranceMontagneApi
from .exceptions import (
    MeteoFranceMontagneApiError,
    MeteoFranceMontagneAuthError,
    MeteoFranceMontagneOffSeason,
)
from .massifs import in_massif, organize_by_department
from .nivo import MeteoFranceNivoApi, parse_nivo_observations
from .stations import station_name

__all__ = [
    "MeteoFranceMontagneApi",
    "MeteoFranceMontagneApiError",
    "MeteoFranceMontagneAuthError",
    "MeteoFranceMontagneOffSeason",
    "MeteoFranceNivoApi",
    "in_massif",
    "organize_by_department",
    "parse_bulletin_xml",
    "parse_nivo_observations",
    "station_name",
]
