"""Fixtures for the meteofrance-montagne tests."""

import gzip
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

RESOURCES = Path(__file__).parent / "resources"

TOKEN = "api-key"


def load_resource(name: str) -> bytes:
    """Return the content of a file of tests/resources."""
    return (RESOURCES / name).read_bytes()


def nivo_file() -> bytes:
    """Return the sample nivo file, compressed as published."""
    return gzip.compress(load_resource("nivo_sample.csv"))


@pytest.fixture
def mock_http():
    """Mock aiohttp requests."""
    with aioresponses() as m:
        yield m


@pytest.fixture
async def session():
    """Return an aiohttp session."""
    async with aiohttp.ClientSession() as s:
        yield s
