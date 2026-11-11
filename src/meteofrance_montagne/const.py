"""Constants of the Météo-France APIs."""

# Avalanche bulletins (BRA), behind an API key of portail-api.meteofrance.fr
BASE_URL = "https://public-api.meteofrance.fr/public/DPBRA/v1"
TIMEOUT = 5

# Observations of the nivo-meteorological network, one file per year rebuilt
# every morning, published without key
NIVO_URL = (
    "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/OBS/NIVOSE/nivo_{year}.csv.gz"
)
NIVO_TIMEOUT = 30
