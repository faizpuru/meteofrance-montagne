"""Data of the avalanche bulletins and of the snow observations.

Texts are empty and numbers None when the bulletin does not give them. The
risk levels are kept as written in the bulletin: "1" to "5", empty without
risk.
"""

from dataclasses import dataclass
from typing import Any

# Orientations of the dangerous slopes
ORIENTATIONS = ("NE", "E", "SE", "S", "SW", "W", "NW", "N")


@dataclass(frozen=True, slots=True, kw_only=True)
class Massif:
    """Massif of the avalanche bulletins."""

    code: int
    nom: str
    # GeoJSON (Multi)Polygon in longitude/latitude
    geometry: dict[str, Any] | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ZoneRisque:
    """Risk of a part of the massif, below or above an altitude, or on a side."""

    valeur: str
    evolution: str
    # "E"/"O" or "S"/"N" when the massif is split by orientation
    localisation: str


@dataclass(frozen=True, slots=True, kw_only=True)
class EstimationJ2:
    """Risk estimated for the day after."""

    date: str
    risque_max: str
    description: str
    commentaire: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Pentes:
    """Dangerous slopes, keyed by orientation (see ORIENTATIONS)."""

    orientations: dict[str, bool | None]
    commentaire: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RisqueJour:
    """Highest risk of a past day."""

    date: str
    # Empty on the days without bulletin
    risque_max: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Risque:
    """Avalanche risk."""

    risque_max: str
    risque_1: ZoneRisque
    risque_2: ZoneRisque
    # Meters, between the zones 1 and 2 when the massif is split by altitude
    altitude_limite: int | None
    commentaire: str
    naturel: str
    accidentel: str
    resume: str
    # Empty, "fort risque d'avalanche" or "très fort risque d'avalanche"
    avis: str
    estimation_j2: EstimationJ2
    pentes: Pentes
    historique: tuple[RisqueJour, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Stabilite:
    """Stability of the snowpack."""

    # Codes "1" to "6" of the typical avalanche situations, the main one first
    situations_avalancheuses: tuple[str, ...]
    titre: str
    texte: str


@dataclass(frozen=True, slots=True, kw_only=True)
class NiveauEnneigement:
    """Snow depth at an altitude."""

    # Meters
    altitude: int | None
    # Centimeters
    nord: int | None
    sud: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class EnneigementJour:
    """Snow cover of a past day."""

    date: str
    # Meters, 0 without continuous snow cover
    limite_sud: int | None
    limite_nord: int | None
    niveaux: tuple[NiveauEnneigement, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Enneigement:
    """Snow cover."""

    date: str
    # Meters, -1 without continuous snow cover
    limite_sud: int | None
    limite_nord: int | None
    niveaux: tuple[NiveauEnneigement, ...]
    historique: tuple[EnneigementJour, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class NeigeFraicheJour:
    """Fresh snow over 24h, from 06 UTC on its date."""

    date: str
    # Centimeters
    min: int | None
    max: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NeigeFraiche:
    """Fresh snow."""

    # Meters, altitude of the measures
    altitude_ss: int | None
    # Analyses then forecasts
    mesures: tuple[NeigeFraicheJour, ...]
    historique: tuple[NeigeFraicheJour, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Vent:
    """Wind at the altitudes 1 and 2 of the forecast."""

    # km/h
    force_1: int | None
    direction_1: str
    force_2: int | None
    direction_2: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Echeance:
    """Weather at a forecast time, -1 when not applicable."""

    date: str
    vent: Vent
    # Meters
    iso_0: int | None
    pluie_neige: int | None
    # Weather condition code
    temps_sensible: int | None
    mer_nuages: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class Meteo:
    """Weather forecast."""

    # Meters
    altitude_vent_1: int | None
    altitude_vent_2: int | None
    commentaire: str
    echeances: tuple[Echeance, ...]
    echeances_historique: tuple[Echeance, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class Bulletin:
    """Avalanche bulletin of a massif.

    The dates are French local times, written without offset.
    """

    id: str
    massif: str
    date_bulletin: str
    date_echeance: str
    date_validite: str
    date_diffusion: str
    amendement: bool
    risque: Risque
    stabilite: Stabilite
    qualite: str
    enneigement: Enneigement
    neige_fraiche: NeigeFraiche
    meteo: Meteo
    partenaires: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Observation:
    """Last observation of a station of the nivo-meteorological network."""

    # WMO id
    id: str
    nom: str
    # Meters
    altitude: int | None
    latitude: float | None
    longitude: float | None
    # UTC, as "2026-02-12T12:02:00Z"
    date: str
    # Centimeters, the altitude ones estimated by the observer higher up
    hauteur_neige: int | None
    hauteur_neige_altitude: int | None
    neige_fraiche_24h: int | None
    neige_fraiche_altitude: int | None
    # WMO code of the present weather
    temps_present: int | None
    # Octas, 9 when the sky is hidden
    nebulosite: int | None
    # Millimeters
    precipitations_24h: float | None
    # Percent
    humidite: int | None
    # Degrees Celsius
    point_rosee: float | None
    temperature: float | None
    temperature_min_24h: float | None
    temperature_max_24h: float | None
    # At the surface of the snow
    temperature_neige: float | None
    # Degrees and m/s
    vent_direction: int | None
    vent_force: float | None
    vent_altitude_direction: int | None
    vent_altitude_force: float | None
    # Blowing snow code
    chasse_neige: int | None
    # Risk estimated by the observer, 1 to 5
    risque: int | None
    # Snow grain codes, at the surface and down to 10 cm
    grain_surface: int | None
    grain_sous_surface: int | None
    # kg/m³
    masse_volumique: float | None
