"""
Herkunfts-Ableitung für die Kartendetail-Anzeige (#47): reine Lese-Ableitung
aus vorhandenen Feldern, KEINE Persistierung und KEINE neue Berechnung. Die
Preis-Herkunft existiert bereits (wert_quelle, siehe api/v1/cards.py –
_card_response füllt sie aus PreisHistorie); dieses Modul liefert die zwei
fehlenden Bausteine Bild- und Daten-Herkunft für die Zeile
„Daten: … · Bild: … · Preis: …" in der Detailansicht.

bild_quelle() spiegelt die BESTEHENDE Bild-Prioritätskette (dieselbe Kette,
keine eigene Fassung – DRY): `web/src/lib/utils.ts::cardImageSrc` entscheidet
client-seitig, was angezeigt wird; `card_image_service.py` (Kopfkommentar)
benennt sie so:
  1. bild_karte_pfad  – eigenes Foto (Upload), immer bevorzugt
  2. bild_pokedex_url – manuell gesetzte URL
  3. bild_karte_url   – auto von TCGdex/TCGplayer
  4. Platzhalter

Werte sind klein/ASCII ("foto"/"url"/"tcgdex"/"tcgplayer", "tcgdex"/"manuell")
— die Beschriftung übernimmt ausschließlich das Frontend über Label-Maps
(Hausregel: interne ASCII-Werte nie roh ins UI).

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from app.models.card import PokemonCard
from app.services.tcgdex import is_allowed_image_url

# Host → Bild-Herkunfts-Kürzel für Glied 3 der Kette (bild_karte_url). NUR ein
# Beschriftungs-Wörterbuch für die Anzeige — die eigentliche Zulassung bleibt
# allein bei tcgdex.is_allowed_image_url/ALLOWED_IMAGE_HOSTS (Panel-Nacharbeit:
# ein Import-Assert hier würde bei einem künftigen dritten erlaubten Host die
# GANZE App am Start hindern – ein Label-Wörterbuch darf kein Veto über die
# Bild-Allowlist haben, Kopplungsrichtung verkehrt; zudem entfernt `python -O`
# einen Assert wortlos). Die Synchronität wird stattdessen als TEST geprüft
# (test_47_provenienz.py) – Drift wird im Gate rot, nicht beim App-Start.
_HOST_QUELLE = {
    "assets.tcgdex.net": "tcgdex",
    "tcgplayer-cdn.tcgplayer.com": "tcgplayer",
}


def bild_quelle(card: PokemonCard) -> Optional[str]:
    """
    Herkunft des angezeigten Kartenbilds – spiegelt cardImageSrc (utils.ts),
    Glied für Glied:
    - "foto": eigenes Foto hochgeladen (Glied 1) – schlägt ALLES andere.
    - "url": manuell gesetzte bild_pokedex_url (Glied 2) – KEINE Host-Deutung,
      das ist Nutzereingabe, nicht TCGdex/TCGplayer. Ohne dieses Glied würde
      eine liegen gebliebene bild_karte_url (PhotoPanel setzt beim
      URL-Speichern NUR bild_pokedex_url, löscht bild_karte_url nicht) fälschlich
      als "tcgdex"/"tcgplayer" etikettiert – dieselbe Fehlerklasse wie das
      Preis-Label in v1.8.2.
    - "tcgdex" / "tcgplayer": Host der bild_karte_url (Glied 3) – geprüft über
      denselben Türsteher wie beim Einlass (is_allowed_image_url), kein
      eigenes, zweites Urteil über was ein „erlaubter" Host ist. Ein erlaubter
      Host ohne Label-Eintrag (Drift, s. o.) liefert None statt eines
      Ersatz-Labels – unterbehauptet, statt abzustürzen.
    - None: kein Bild (Glied 4, Platzhalter) ODER ein nicht erkannter/fremder
      Host – beide Fälle raten NICHT, sie zeigen nichts statt eines
      Ersatz-Labels.
    """
    if card.bild_karte_pfad:
        return "foto"
    if card.bild_pokedex_url:
        return "url"
    if not is_allowed_image_url(card.bild_karte_url):
        return None
    return _HOST_QUELLE.get(urlparse(card.bild_karte_url).hostname)


def daten_quelle(card: PokemonCard) -> str:
    """
    Herkunft der Kartendaten: "tcgdex" wenn TCGdex-verknüpft, sonst "manuell".
    ACHTUNG (Panel-Nacharbeit #47): "manuell" behauptet NUR die Abwesenheit
    einer TCGdex-Verknüpfung, NICHT dass ein Mensch die Zeile erfasst hat –
    der Server legt beim Löschen einer letzten Karte einen Pokédex-Platzhalter
    OHNE tcgdex_card_id neu an (cards.py::delete_card), ohne dass je jemand
    etwas "erfasst" hätte. Der ASCII-Wert bleibt bewusst "manuell" (kein
    API-Bruch, Panel-Auflage) – nur das Frontend-Label wurde entsprechend
    zurückhaltend formuliert ("ohne TCGdex-Verknüpfung" statt "manuell
    erfasst").
    """
    return "tcgdex" if card.tcgdex_card_id else "manuell"
