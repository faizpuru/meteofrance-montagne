# meteofrance-montagne

Async Python client for the Météo-France mountain data, built on `aiohttp`:

- the avalanche bulletins (BRA) of the massifs, with their images, from the [Données Publiques BRA](https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesBRA) API;
- the observations of the nivo-meteorological network, published without key.

It powers the [Météo-France Montagne integration](https://github.com/faizpuru/ha-meteofrance-montagne) for Home Assistant, but does not depend on it.

## Installation

```bash
pip install meteofrance-montagne
```

## Usage

The bulletins need a free API key: subscribe to **Données Publiques BRA** on [portail-api.meteofrance.fr](https://portail-api.meteofrance.fr/web/fr/api/DonneesPubliquesBRA) and generate an API key (not an OAuth2 token, which expires after an hour).

```python
import asyncio

import aiohttp

from meteofrance_montagne import MeteoFranceMontagneApi, MeteoFranceNivoApi, in_massif


async def main() -> None:
    async with aiohttp.ClientSession() as session:
        api = MeteoFranceMontagneApi(session, "your-api-key")

        # Massifs by department, with their geometry
        departments = await api.list_massif()
        haute_tarentaise = next(
            massif for massif in departments["Savoie"] if massif.code == 6
        )

        bulletin = await api.bulletin(6)
        print(bulletin.risque.risque_max, bulletin.risque.resume)

        # PNG bytes, None when not published
        rose = await api.rose_pentes(6)

        # Last observation of each station, keyed by WMO id
        nivo = MeteoFranceNivoApi(session)
        stations = await nivo.stations(2026)
        for station in stations.values():
            if in_massif(
                station.longitude, station.latitude, haute_tarentaise.geometry
            ):
                print(station.nom, station.hauteur_neige, "cm")


asyncio.run(main())
```

The data are frozen dataclasses (`Bulletin`, `Massif`, `Observation`…), with French names as in the bulletins. The caller owns the `aiohttp.ClientSession`. The bulletins are only published from early November to late May.

| Exception | Meaning |
|---|---|
| `MeteoFranceMontagneApiError` | The API cannot be reached or answered an error |
| `MeteoFranceMontagneAuthError` | The API key was rejected (subclass of `MeteoFranceMontagneApiError`) |
| `MeteoFranceMontagneOffSeason` | No bulletin is published for the massif outside the season |

## Development

```bash
uv run --group dev pytest
uv run --group dev ruff check .
uv run --group dev ruff format .
```

Releases are published to PyPI by publishing a GitHub release, after bumping the version in `pyproject.toml`.
