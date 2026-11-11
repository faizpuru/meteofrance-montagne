"""Tests for the parser of the XML bulletins."""

import re
import xml.etree.ElementTree as ET

import pytest

from meteofrance_montagne import parse_bulletin_xml

from .conftest import load_resource


def parse(xml: bytes) -> dict:
    """Parse a bulletin."""
    return parse_bulletin_xml(ET.fromstring(xml))


@pytest.fixture
def bulletin() -> dict:
    """Return the parsed sample bulletin."""
    return parse(load_resource("sample_bulletin.xml"))


def test_parse_header(bulletin):
    """Parse the bulletin identification and dates."""
    assert bulletin["type"] == "bulletins_neige_avalanche"
    assert bulletin["id"] == "72"
    assert bulletin["massif"] == "Orlu St-Barthelemy"
    assert bulletin["dateBulletin"] == "2025-11-21T16:00:00"
    assert bulletin["dateEcheance"] == "2025-11-22T18:00:00"
    assert bulletin["dateValidite"] == "2025-11-22T18:00:00"
    assert bulletin["dateDiffusion"] == "2025-11-21T16:25:00"
    assert bulletin["amendement"] is False
    assert bulletin["partenaires"].startswith("Rédigé par Météo-France")


def test_parse_risque(bulletin):
    """Parse the avalanche risk."""
    risque = bulletin["risque"]
    assert risque["risque_max"] == "3"
    assert risque["risque_1"] == {"valeur": "3", "evolution": "", "localisation": ""}
    assert risque["risque_2"]["valeur"] == ""
    assert risque["altitude_limite"] is None
    assert risque["commentaire"] == "Indice de risque marqué."
    assert risque["naturel"] == "Nombreux départs pendant les chutes puis au soleil"
    assert (
        risque["accidentel"] == "Nombreuses plaques friables facilement déclenchables"
    )
    assert "Départs spontanés" in risque["resume"]
    assert risque["avis"] == ""

    assert risque["estimation_j2"] == {
        "date": "2025-11-23T00:00:00",
        "risque_max": "3",
        "description": "Indice de risque marqué",
        "commentaire": "Stabilisation progressive du manteau neigeux.",
    }

    assert len(risque["historique"]) == 7
    assert risque["historique"][-1] == {
        "date": "2025-11-21T00:00:00",
        "risque_max": "2",
    }


def test_parse_pentes(bulletin):
    """Convert the dangerous slopes to booleans."""
    assert bulletin["risque"]["pentes_particulieres"] == {
        "NE": False,
        "E": True,
        "SE": True,
        "S": True,
        "SW": True,
        "W": True,
        "NW": False,
        "N": False,
        "commentaire": "",
    }


def test_parse_stabilite_qualite(bulletin):
    """Parse the snowpack stability and the snow quality."""
    stabilite = bulletin["stabilite"]
    assert stabilite["situations_avalancheuses"] == [{"type": "1"}, {"type": "2"}]
    assert stabilite["titre"] == "Manteau neigeux récent encore instable"
    assert stabilite["texte"].startswith("Déclenchements provoqués")
    assert "Le jour se lève samedi" in bulletin["qualite"]


def test_parse_stabilite_without_texte_sans_titre():
    """Fall back on the text with the title when the text alone is missing."""
    xml = re.sub(
        rb"<TEXTESANSTITRE>.*?</TEXTESANSTITRE>",
        b"",
        load_resource("sample_bulletin.xml"),
        flags=re.DOTALL,
    )
    texte = parse(xml)["stabilite"]["texte"]
    assert texte.startswith("Manteau neigeux récent encore instable")


def test_parse_enneigement(bulletin):
    """Parse the snow cover and its history."""
    enneigement = bulletin["enneigement"]
    assert enneigement["date"] == "2025-11-21T00:00:00"
    assert enneigement["limite_sud"] == 600
    assert enneigement["limite_nord"] == 600
    assert len(enneigement["niveaux"]) == 3
    assert enneigement["niveaux"][0] == {"altitude": 1500, "nord": 25, "sud": 25}
    assert enneigement["niveaux"][2]["altitude"] == 2500
    assert enneigement["niveaux"][2]["nord"] == 50

    assert enneigement["historique"]
    assert set(enneigement["historique"][0]) == {
        "date",
        "limite_sud",
        "limite_nord",
        "niveaux",
    }


def test_parse_neige_fraiche(bulletin):
    """Parse the fresh snow measures and their history."""
    neige = bulletin["neige_fraiche"]
    assert neige["altitude_ss"] == 1800
    assert len(neige["mesures"]) == 6
    assert neige["mesures"][0] == {"date": "2025-11-17T00:00:00", "min": 0, "max": 3}
    assert neige["mesures"][3] == {"date": "2025-11-20T00:00:00", "min": 20, "max": 40}

    assert neige["historique"]
    assert set(neige["historique"][0]) == {"date", "min", "max"}


def test_parse_meteo(bulletin):
    """Parse the weather forecast and its history."""
    meteo = bulletin["meteo"]
    assert meteo["altitude_vent_1"] == 2000
    assert meteo["altitude_vent_2"] == 3000
    assert (
        meteo["commentaire"] == "Températures très froides le matin malgré le soleil !"
    )
    assert len(meteo["echeances"]) == 4

    assert meteo["echeances"][0] == {
        "date": "2025-11-22T06:00:00",
        "vent": {
            "force_1": 45,
            "direction_1": "NO",
            "force_2": 85,
            "direction_2": "NO",
        },
        "iso_0": 500,
        "pluie_neige": 300,
        "temps_sensible": 61,
        "mer_nuages": -1,
    }
    assert meteo["echeances"][3]["date"] == "2025-11-23T00:00:00"
    assert meteo["echeances"][3]["pluie_neige"] == -1

    assert meteo["echeances_historique"]
    assert set(meteo["echeances_historique"][0]) == {
        "date",
        "vent",
        "iso_0",
        "pluie_neige",
        "temps_sensible",
        "mer_nuages",
    }


def test_parse_zones_by_orientation():
    """Keep the second risk of a massif split east/west, without altitude limit."""
    xml = (
        load_resource("sample_bulletin.xml")
        .replace(
            b'RISQUE1="3" EVOLURISQUE1="" LOC1="" ALTITUDE="" RISQUE2=""',
            b'RISQUE1="3" EVOLURISQUE1="" LOC1="E" ALTITUDE="" RISQUE2="2"',
        )
        .replace(b'LOC2=""', b'LOC2="O"')
    )
    risque = parse(xml)["risque"]
    assert risque["altitude_limite"] is None
    assert risque["risque_1"]["localisation"] == "E"
    assert risque["risque_2"] == {"valeur": "2", "evolution": "", "localisation": "O"}


def test_parse_avis():
    """Read the high risk warning."""
    xml = load_resource("sample_bulletin.xml").replace(
        b"<AVIS/>", b"<AVIS>fort risque d'avalanche</AVIS>"
    )
    assert parse(xml)["risque"]["avis"] == "fort risque d'avalanche"
