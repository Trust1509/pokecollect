"""
Herkunfts-Ableitung für die Kartendetail-Anzeige (#47): reine Lese-Ableitung
aus vorhandenen Feldern, KEINE Persistierung und KEINE neue Berechnung. Die
Preis-Herkunft existiert bereits (wert_quelle, siehe api/v1/cards.py –
_card_response füllt sie aus PreisHistorie); dieses Modul liefert die zwei
fehlenden Bausteine Bild- und Daten-Herkunft für die Zeile
„Daten: … · Bild: … · Preis: …" in der Detailansicht.

Werte sind klein/ASCII ("foto"/"tcgdex"/"tcgplayer", "tcgdex"/"manuell") —
die Beschriftung übernimmt ausschließlich das Frontend über Label-Maps
(Hausregel: interne ASCII-Werte nie roh ins UI).

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from app.models.card import PokemonCard
from app.services.tcgdex import ALLOWED_IMAGE_HOSTS, is_allowed_image_url

# Host → Bild-Herkunfts-Kürzel. Dieselbe Hostliste wie beim Bild-EINLASS
# (tcgdex.py) – der Assert hält beide Stellen synchron: käme dort je ein
# dritter erlaubter Host dazu, ohne dass hier jemand daran denkt, bricht der
# Import statt eine Karte mit diesem Host still ohne Herkunfts-Label zu lassen.
_HOST_QUELLE = {
    "assets.tcgdex.net": "tcgdex",
    "tcgplayer-cdn.tcgplayer.com": "tcgplayer",
}
assert set(_HOST_QUELLE) == ALLOWED_IMAGE_HOSTS, (
    "provenance._HOST_QUELLE ist von tcgdex.ALLOWED_IMAGE_HOSTS abgedriftet"
)


def bild_quelle(card: PokemonCard) -> Optional[str]:
    """
    Herkunft des angezeigten Kartenbilds:
    - "foto": eigenes Foto hochgeladen – schlägt IMMER eine evtl. GLEICHZEITIG
      gesetzte bild_karte_url (die Anzeige zeigt bei vorhandenem Foto nie
      die URL).
    - "tcgdex" / "tcgplayer": Host der bild_karte_url – geprüft über denselben
      Türsteher wie beim Einlass (is_allowed_image_url), kein eigenes,
      zweites Urteil über was ein „erlaubter" Host ist.
    - None: kein Bild (Platzhalter) ODER ein nicht erkannter/fremder Host –
      beide Fälle raten NICHT, sie zeigen nichts statt eines Ersatz-Labels.
    """
    if card.bild_karte_pfad:
        return "foto"
    if not is_allowed_image_url(card.bild_karte_url):
        return None
    # is_allowed_image_url war True → hostname ist garantiert in
    # ALLOWED_IMAGE_HOSTS und damit (siehe Assert oben) ein Schlüssel hier.
    return _HOST_QUELLE[urlparse(card.bild_karte_url).hostname]


def daten_quelle(card: PokemonCard) -> str:
    """Herkunft der Kartendaten: TCGdex-verknüpft oder von Hand erfasst."""
    return "tcgdex" if card.tcgdex_card_id else "manuell"
