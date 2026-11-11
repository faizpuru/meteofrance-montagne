"""Exceptions of the Météo-France APIs."""


class MeteoFranceMontagneApiError(Exception):
    """Error while communicating with the Météo-France API."""


class MeteoFranceMontagneAuthError(MeteoFranceMontagneApiError):
    """The API token was rejected."""


class MeteoFranceMontagneOffSeason(Exception):
    """No bulletin is published for the massif outside the season."""
