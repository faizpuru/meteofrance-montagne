"""Parser of the XML avalanche bulletins (BRA)."""

import xml.etree.ElementTree as ET

from .models import (
    ORIENTATIONS,
    Bulletin,
    Echeance,
    Enneigement,
    EnneigementJour,
    EstimationJ2,
    Meteo,
    NeigeFraiche,
    NeigeFraicheJour,
    NiveauEnneigement,
    Pentes,
    Risque,
    RisqueJour,
    Stabilite,
    Vent,
    ZoneRisque,
)


def _attr(element: ET.Element | None, name: str) -> str:
    """Return an attribute, empty when missing."""
    return (element.get(name) or "") if element is not None else ""


def _int(element: ET.Element | None, name: str) -> int | None:
    """Return an integer attribute, None when missing or invalid."""
    try:
        return int(_attr(element, name))
    except ValueError:
        return None


def _bool(element: ET.Element | None, name: str) -> bool | None:
    """Return a "true"/"false" attribute, None when missing."""
    return {"true": True, "false": False}.get(_attr(element, name).lower())


def _text(element: ET.Element | None, path: str) -> str:
    """Return the text of a child, empty when missing."""
    child = element.find(path) if element is not None else None
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _children(element: ET.Element | None, tag: str) -> list[ET.Element]:
    """Return the children with a tag, none when the element is missing."""
    return element.findall(tag) if element is not None else []


def _niveau(niveau: ET.Element) -> NiveauEnneigement:
    """Parse the snow depth at an altitude."""
    return NiveauEnneigement(
        altitude=_int(niveau, "ALTI"),
        nord=_int(niveau, "N"),
        sud=_int(niveau, "S"),
    )


def _neige24h(neige24h: ET.Element) -> NeigeFraicheJour:
    """Parse the fresh snow of a day."""
    return NeigeFraicheJour(
        date=_attr(neige24h, "DATE"),
        min=_int(neige24h, "SS24Min"),
        max=_int(neige24h, "SS24Max"),
    )


def _echeance(echeance: ET.Element) -> Echeance:
    """Parse the weather of a forecast time."""
    return Echeance(
        date=_attr(echeance, "DATE"),
        vent=Vent(
            force_1=_int(echeance, "FF1"),
            direction_1=_attr(echeance, "DD1"),
            force_2=_int(echeance, "FF2"),
            direction_2=_attr(echeance, "DD2"),
        ),
        iso_0=_int(echeance, "ISO0"),
        pluie_neige=_int(echeance, "PLUIENEIGE"),
        temps_sensible=_int(echeance, "TEMPSSENSIBLE"),
        mer_nuages=_int(echeance, "MERNUAGES"),
    )


def _risque(root: ET.Element, bsh: ET.Element | None) -> Risque:
    """Parse the avalanche risk and its history."""
    cartouche = root.find("CARTOUCHERISQUE")
    risque = cartouche.find("RISQUE") if cartouche is not None else None
    pente = cartouche.find("PENTE") if cartouche is not None else None
    historique = bsh.find("RISQUES") if bsh is not None else None

    return Risque(
        risque_max=_attr(risque, "RISQUEMAXI"),
        risque_1=ZoneRisque(
            valeur=_attr(risque, "RISQUE1"),
            evolution=_attr(risque, "EVOLURISQUE1"),
            localisation=_attr(risque, "LOC1"),
        ),
        risque_2=ZoneRisque(
            valeur=_attr(risque, "RISQUE2"),
            evolution=_attr(risque, "EVOLURISQUE2"),
            localisation=_attr(risque, "LOC2"),
        ),
        altitude_limite=_int(risque, "ALTITUDE"),
        commentaire=_attr(risque, "COMMENTAIRE"),
        naturel=_text(cartouche, "NATUREL"),
        accidentel=_text(cartouche, "ACCIDENTEL"),
        resume=_text(cartouche, "RESUME"),
        avis=_text(cartouche, "AVIS"),
        estimation_j2=EstimationJ2(
            date=_attr(risque, "DATE_RISQUE_J2"),
            risque_max=_attr(risque, "RISQUEMAXIJ2"),
            description=_text(cartouche, "RisqueJ2"),
            commentaire=_text(cartouche, "CommentaireRisqueJ2"),
        ),
        pentes=Pentes(
            orientations={
                orientation: _bool(pente, orientation) for orientation in ORIENTATIONS
            },
            commentaire=_attr(pente, "COMMENTAIRE"),
        ),
        historique=tuple(
            RisqueJour(date=_attr(jour, "DATE"), risque_max=_attr(jour, "RISQUEMAXI"))
            for jour in _children(historique, "RISQUE")
        ),
    )


def _stabilite(root: ET.Element) -> Stabilite:
    """Parse the stability of the snowpack."""
    stabilite = root.find("STABILITE")
    sitaval = stabilite.find("SitAvalTyp") if stabilite is not None else None
    return Stabilite(
        situations_avalancheuses=tuple(
            sat for name in ("SAT1", "SAT2") if (sat := _attr(sitaval, name))
        ),
        titre=_text(stabilite, "TITRE"),
        # TEXTE repeats the title, TEXTESANSTITRE does not
        texte=_text(stabilite, "TEXTESANSTITRE") or _text(stabilite, "TEXTE"),
    )


def _enneigement(root: ET.Element, bsh: ET.Element | None) -> Enneigement:
    """Parse the snow cover and its history."""
    enneigement = root.find("ENNEIGEMENT")
    historique = bsh.find("ENNEIGEMENTS") if bsh is not None else None
    return Enneigement(
        date=_attr(enneigement, "DATE"),
        limite_sud=_int(enneigement, "LimiteSud"),
        limite_nord=_int(enneigement, "LimiteNord"),
        niveaux=tuple(_niveau(niveau) for niveau in _children(enneigement, "NIVEAU")),
        historique=tuple(
            EnneigementJour(
                date=_attr(jour, "DATE"),
                limite_sud=_int(jour, "LimiteSud"),
                limite_nord=_int(jour, "LimiteNord"),
                niveaux=tuple(_niveau(niveau) for niveau in _children(jour, "NIVEAU")),
            )
            for jour in _children(historique, "ENNEIGEMENT")
        ),
    )


def _neige_fraiche(root: ET.Element, bsh: ET.Element | None) -> NeigeFraiche:
    """Parse the fresh snow and its history."""
    neige_fraiche = root.find("NEIGEFRAICHE")
    historique = bsh.find("NEIGEFRAICHE") if bsh is not None else None
    return NeigeFraiche(
        altitude_ss=_int(neige_fraiche, "ALTITUDESS"),
        mesures=tuple(_neige24h(n) for n in _children(neige_fraiche, "NEIGE24H")),
        historique=tuple(_neige24h(n) for n in _children(historique, "NEIGE24H")),
    )


def _meteo(root: ET.Element, bsh: ET.Element | None) -> Meteo:
    """Parse the weather forecast and its history."""
    meteo = root.find("METEO")
    historique = bsh.find("METEO") if bsh is not None else None
    return Meteo(
        altitude_vent_1=_int(meteo, "ALTITUDEVENT1"),
        altitude_vent_2=_int(meteo, "ALTITUDEVENT2"),
        commentaire=_text(meteo, "COMMENTAIRE"),
        echeances=tuple(_echeance(e) for e in _children(meteo, "ECHEANCE")),
        echeances_historique=tuple(
            _echeance(e) for e in _children(historique, "ECHEANCE")
        ),
    )


def parse_bulletin_xml(root: ET.Element) -> Bulletin:
    """Parse an XML bulletin."""
    # Bilan de Saison Hivernal: the history of the last days
    bsh = root.find("BSH")
    return Bulletin(
        id=_attr(root, "ID"),
        massif=_attr(root, "MASSIF"),
        date_bulletin=_attr(root, "DATEBULLETIN"),
        date_echeance=_attr(root, "DATEECHEANCE"),
        date_validite=_attr(root, "DATEVALIDITE"),
        date_diffusion=_attr(root, "DATEDIFFUSION"),
        amendement=root.get("AMENDEMENT") == "true",
        risque=_risque(root, bsh),
        stabilite=_stabilite(root),
        qualite=_text(root.find("QUALITE"), "TEXTE"),
        enneigement=_enneigement(root, bsh),
        neige_fraiche=_neige_fraiche(root, bsh),
        meteo=_meteo(root, bsh),
        partenaires=_text(root, "TexteMeta/Partenaires"),
    )
