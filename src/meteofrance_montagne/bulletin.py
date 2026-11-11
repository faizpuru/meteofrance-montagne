"""Parser of the XML avalanche bulletins (BRA)."""

import xml.etree.ElementTree as ET
from typing import Any


def _get_attr(element: ET.Element, attr: str, default: str = "") -> str:
    """Get attribute value or default."""
    value = element.get(attr, default)
    return value if value else default


def _get_text(element: ET.Element | None, default: str = "") -> str:
    """Get element text or default."""
    if element is not None and element.text:
        return element.text.strip()
    return default


def _to_int_or_null(value: str) -> int | None:
    """Convert to int or None."""
    if value and value != "":
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _to_bool_or_null(value: str) -> bool | None:
    """Convert "true"/"false" to a boolean or None."""
    return {"true": True, "false": False}.get(value.lower()) if value else None


def _niveau(niveau: ET.Element) -> dict[str, Any]:
    """Parse the snow depth at an altitude."""
    return {
        "altitude": _to_int_or_null(_get_attr(niveau, "ALTI")),
        "nord": _to_int_or_null(_get_attr(niveau, "N")),
        "sud": _to_int_or_null(_get_attr(niveau, "S")),
    }


def _neige24h(neige24h: ET.Element) -> dict[str, Any]:
    """Parse the fresh snow of a day."""
    return {
        "date": _get_attr(neige24h, "DATE"),
        "min": _to_int_or_null(_get_attr(neige24h, "SS24Min")),
        "max": _to_int_or_null(_get_attr(neige24h, "SS24Max")),
    }


def _echeance(echeance: ET.Element) -> dict[str, Any]:
    """Parse the weather of a forecast time."""
    return {
        "date": _get_attr(echeance, "DATE"),
        "vent": {
            "force_1": _to_int_or_null(_get_attr(echeance, "FF1")),
            "direction_1": _get_attr(echeance, "DD1"),
            "force_2": _to_int_or_null(_get_attr(echeance, "FF2")),
            "direction_2": _get_attr(echeance, "DD2"),
        },
        "iso_0": _to_int_or_null(_get_attr(echeance, "ISO0")),
        "pluie_neige": _to_int_or_null(_get_attr(echeance, "PLUIENEIGE")),
        "temps_sensible": _to_int_or_null(_get_attr(echeance, "TEMPSSENSIBLE")),
        "mer_nuages": _to_int_or_null(_get_attr(echeance, "MERNUAGES")),
    }


def parse_bulletin_xml(root: ET.Element) -> dict[str, Any]:
    """Parse XML bulletin and convert to JSON structure."""
    # Parse CARTOUCHERISQUE
    cartouche = root.find("CARTOUCHERISQUE")
    risque_elem = cartouche.find("RISQUE") if cartouche is not None else None
    pente_elem = cartouche.find("PENTE") if cartouche is not None else None

    def risque_attr(attr: str) -> str:
        return _get_attr(risque_elem, attr) if risque_elem is not None else ""

    def cartouche_text(tag: str) -> str:
        return _get_text(cartouche.find(tag)) if cartouche is not None else ""

    def pente(attr: str) -> bool | None:
        if pente_elem is None:
            return None
        return _to_bool_or_null(_get_attr(pente_elem, attr))

    risque: dict[str, Any] = {
        "risque_max": risque_attr("RISQUEMAXI"),
        "risque_1": {
            "valeur": risque_attr("RISQUE1"),
            "evolution": risque_attr("EVOLURISQUE1"),
            "localisation": risque_attr("LOC1"),
        },
        "risque_2": {
            "valeur": risque_attr("RISQUE2"),
            "evolution": risque_attr("EVOLURISQUE2"),
            "localisation": risque_attr("LOC2"),
        },
        "altitude_limite": _to_int_or_null(risque_attr("ALTITUDE"))
        if risque_elem is not None
        else None,
        "commentaire": risque_attr("COMMENTAIRE"),
        "naturel": cartouche_text("NATUREL"),
        "accidentel": cartouche_text("ACCIDENTEL"),
        "resume": cartouche_text("RESUME"),
        # Empty, "fort risque d'avalanche" or "très fort risque d'avalanche"
        "avis": cartouche_text("AVIS"),
        "estimation_j2": {
            "date": risque_attr("DATE_RISQUE_J2"),
            "risque_max": risque_attr("RISQUEMAXIJ2"),
            "description": cartouche_text("RisqueJ2"),
            "commentaire": cartouche_text("CommentaireRisqueJ2"),
        },
        "pentes_particulieres": {
            **{
                orientation: pente(orientation)
                for orientation in ("NE", "E", "SE", "S", "SW", "W", "NW", "N")
            },
            "commentaire": _get_attr(pente_elem, "COMMENTAIRE")
            if pente_elem is not None
            else "",
        },
    }

    # Parse STABILITE
    stabilite_elem = root.find("STABILITE")
    situations_avalancheuses = []
    if stabilite_elem is not None:
        sitaval = stabilite_elem.find("SitAvalTyp")
        if sitaval is not None:
            for attr in ("SAT1", "SAT2"):
                if sat := _get_attr(sitaval, attr):
                    situations_avalancheuses.append({"type": sat})

    stabilite = {
        "situations_avalancheuses": situations_avalancheuses,
        "titre": _get_text(stabilite_elem.find("TITRE"))
        if stabilite_elem is not None
        else "",
        # TEXTE repeats the title, TEXTESANSTITRE does not
        "texte": (
            _get_text(stabilite_elem.find("TEXTESANSTITRE"))
            or _get_text(stabilite_elem.find("TEXTE"))
        )
        if stabilite_elem is not None
        else "",
    }

    # Parse QUALITE
    qualite_elem = root.find("QUALITE")
    qualite = _get_text(qualite_elem.find("TEXTE")) if qualite_elem is not None else ""

    # Parse ENNEIGEMENT
    enneigement_elem = root.find("ENNEIGEMENT")
    enneigement: dict[str, Any] = {
        "date": _get_attr(enneigement_elem, "DATE")
        if enneigement_elem is not None
        else "",
        "limite_sud": _to_int_or_null(_get_attr(enneigement_elem, "LimiteSud"))
        if enneigement_elem is not None
        else None,
        "limite_nord": _to_int_or_null(_get_attr(enneigement_elem, "LimiteNord"))
        if enneigement_elem is not None
        else None,
        "niveaux": [_niveau(niveau) for niveau in enneigement_elem.findall("NIVEAU")]
        if enneigement_elem is not None
        else [],
        "historique": [],  # Filled below from BSH
    }

    # Parse NEIGEFRAICHE
    neige_fraiche_elem = root.find("NEIGEFRAICHE")
    neige_fraiche: dict[str, Any] = {
        "altitude_ss": _to_int_or_null(_get_attr(neige_fraiche_elem, "ALTITUDESS"))
        if neige_fraiche_elem is not None
        else None,
        "mesures": [_neige24h(n) for n in neige_fraiche_elem.findall("NEIGE24H")]
        if neige_fraiche_elem is not None
        else [],
        "historique": [],  # Filled below from BSH
    }

    # Parse METEO (prévisions)
    meteo_elem = root.find("METEO")
    echeances = (
        [_echeance(echeance) for echeance in meteo_elem.findall("ECHEANCE")]
        if meteo_elem is not None
        else []
    )

    # Parse BSH (Bilan de Saison Hivernal - Historique)
    bsh_elem = root.find("BSH")

    def bsh_section(tag: str) -> ET.Element | None:
        return bsh_elem.find(tag) if bsh_elem is not None else None

    # Parse METEO historique
    echeances_historique = []
    if (bsh_meteo_elem := bsh_section("METEO")) is not None:
        echeances_historique = [
            _echeance(echeance) for echeance in bsh_meteo_elem.findall("ECHEANCE")
        ]

    # Parse RISQUES historique
    risques_historique = []
    if (risques_elem := bsh_section("RISQUES")) is not None:
        risques_historique = [
            {
                "date": _get_attr(risque_jour, "DATE"),
                "risque_max": _get_attr(risque_jour, "RISQUEMAXI"),
            }
            for risque_jour in risques_elem.findall("RISQUE")
        ]

    # Parse ENNEIGEMENTS historique
    enneigements_historique = []
    if (enneigements_elem := bsh_section("ENNEIGEMENTS")) is not None:
        enneigements_historique = [
            {
                "date": _get_attr(enneigement_jour, "DATE"),
                "limite_sud": _to_int_or_null(_get_attr(enneigement_jour, "LimiteSud")),
                "limite_nord": _to_int_or_null(
                    _get_attr(enneigement_jour, "LimiteNord")
                ),
                "niveaux": [
                    _niveau(niveau) for niveau in enneigement_jour.findall("NIVEAU")
                ],
            }
            for enneigement_jour in enneigements_elem.findall("ENNEIGEMENT")
        ]

    # Parse NEIGEFRAICHE historique
    neige_fraiche_historique = []
    if (neige_fraiche_hist_elem := bsh_section("NEIGEFRAICHE")) is not None:
        neige_fraiche_historique = [
            _neige24h(neige24h)
            for neige24h in neige_fraiche_hist_elem.findall("NEIGE24H")
        ]

    meteo = {
        "altitude_vent_1": _to_int_or_null(_get_attr(meteo_elem, "ALTITUDEVENT1"))
        if meteo_elem is not None
        else None,
        "altitude_vent_2": _to_int_or_null(_get_attr(meteo_elem, "ALTITUDEVENT2"))
        if meteo_elem is not None
        else None,
        "commentaire": _get_text(meteo_elem.find("COMMENTAIRE"))
        if meteo_elem is not None
        else "",
        "echeances": echeances,
        "echeances_historique": echeances_historique,
    }

    # Add historical data to their respective sections
    risque["historique"] = risques_historique
    enneigement["historique"] = enneigements_historique
    neige_fraiche["historique"] = neige_fraiche_historique

    return {
        "type": "bulletins_neige_avalanche",
        "id": _get_attr(root, "ID"),
        "massif": _get_attr(root, "MASSIF"),
        "dateBulletin": _get_attr(root, "DATEBULLETIN"),
        "dateEcheance": _get_attr(root, "DATEECHEANCE"),
        "dateValidite": _get_attr(root, "DATEVALIDITE"),
        "dateDiffusion": _get_attr(root, "DATEDIFFUSION"),
        "amendement": root.get("AMENDEMENT") == "true",
        "risque": risque,
        "stabilite": stabilite,
        "qualite": qualite,
        "enneigement": enneigement,
        "neige_fraiche": neige_fraiche,
        "meteo": meteo,
        "partenaires": _get_text(root.find("TexteMeta/Partenaires")),
    }
