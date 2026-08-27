"""
#47: dezente Herkunfts-Zeile in der Kartendetailansicht („Daten: … · Bild:
… · Preis: …"). Preis-Herkunft existiert bereits (wert_quelle, v1.8.2) und
wird hier nur mitgeprüft; Daten-/Bild-Herkunft sind neu (app/services/
provenance.py), rein abgeleitet aus vorhandenen Feldern, keine Migration.
"""

from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard, PreisHistorie
from app.services.provenance import _HOST_QUELLE, bild_quelle, daten_quelle
from app.services.tcgdex import ALLOWED_IMAGE_HOSTS

_TESTNAME = "test47-Provenienzkarte"

# Erfundene Pfade auf den ECHTEN erlaubten Bild-Hosts (tcgdex.py
# ALLOWED_IMAGE_HOSTS) — keine Karten/Namen aus diesem Baugespräch.
_TCGDEX_URL = "https://assets.tcgdex.net/de/xx/test47/high.webp"
_TCGPLAYER_URL = "https://tcgplayer-cdn.tcgplayer.com/product/test47/high.webp"
_FREMDER_HOST_URL = "https://example.com/test47/high.webp"
# Manuell gesetzte Bild-URL (Glied 2 der Kette, bild_pokedex_url) — bewusst
# EIN Host außerhalb der erlaubten Liste: dieses Feld ist Nutzereingabe ohne
# Host-Deutung, jeder Host ist hier gültig.
_MANUELLE_BILD_URL = "https://i.example-photos.test/test47-manuell.jpg"
# Adversarial: der erlaubte Hostname taucht als TEILSTRING auf, ist aber NICHT
# der tatsächliche Host (Panel-Nacharbeit, WICHTIG 2) — eine naive
# Teilstring-Prüfung würde beide fälschlich als "tcgdex" durchlassen.
_HOST_ALS_PFAD_TEILSTRING_URL = "https://evil.example/assets.tcgdex.net/high.webp"
_HOST_ALS_DOMAIN_PRAEFIX_URL = "https://assets.tcgdex.net.evil.example/x"


# ── bild_quelle: reine Ableitung, keine DB nötig ─────────────────────────────

def test_bild_quelle_foto_schlaegt_alles():
    """Eigenes Foto hat Vorrang – auch wenn GLEICHZEITIG eine manuelle
    Bild-URL UND eine gültige TCGdex-URL gesetzt sind (Panel-Nacharbeit:
    verschärft gegenüber der ursprünglichen Fassung, die nur zwei von drei
    Feldern gleichzeitig prüfte)."""
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_pfad="fotos/test47.jpg",
                        bild_pokedex_url=_MANUELLE_BILD_URL,
                        bild_karte_url=_TCGDEX_URL)
    assert bild_quelle(card) == "foto"


def test_bild_quelle_pokedex_url_schlaegt_karte_url():
    """Glied 2 vor Glied 3 (Panel-Nacharbeit, BLOCKER 1): PhotoPanel setzt
    beim Speichern einer Bild-URL NUR bild_pokedex_url und löscht
    bild_karte_url NICHT – die Anzeige zeigt dann trotzdem die manuelle URL,
    nicht das liegen gebliebene TCGdex-Bild."""
    card = PokemonCard(kartenname=_TESTNAME, bild_pokedex_url=_MANUELLE_BILD_URL,
                        bild_karte_url=_TCGDEX_URL)
    assert bild_quelle(card) == "url"


def test_bild_quelle_nur_pokedex_url():
    card = PokemonCard(kartenname=_TESTNAME, bild_pokedex_url=_MANUELLE_BILD_URL)
    assert bild_quelle(card) == "url"


def test_bild_quelle_tcgdex_url():
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_url=_TCGDEX_URL)
    assert bild_quelle(card) == "tcgdex"


def test_bild_quelle_tcgplayer_url():
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_url=_TCGPLAYER_URL)
    assert bild_quelle(card) == "tcgplayer"


def test_bild_quelle_fremder_host_ist_none():
    """Kein Raten bei einem nicht erlaubten Host – lieber nichts als ein
    falsches Label."""
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_url=_FREMDER_HOST_URL)
    assert bild_quelle(card) is None


def test_bild_quelle_erlaubter_host_als_teilstring_im_pfad_ist_none():
    """Panel-Nacharbeit WICHTIG 2: der erlaubte Host taucht im PFAD auf,
    ist aber nicht der tatsächliche Host (evil.example). Eine naive
    Teilstring-Prüfung würde das durchlassen – die echte Prüfung
    (is_allowed_image_url → urlparse().hostname) nicht."""
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_url=_HOST_ALS_PFAD_TEILSTRING_URL)
    assert bild_quelle(card) is None


def test_bild_quelle_erlaubter_host_als_domain_praefix_ist_none():
    """Wie oben, aber der erlaubte Host ist Präfix einer FREMDEN Domain
    (assets.tcgdex.net.evil.example) statt eines Pfad-Segments."""
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_url=_HOST_ALS_DOMAIN_PRAEFIX_URL)
    assert bild_quelle(card) is None


def test_bild_quelle_ohne_bild_ist_none():
    """Weder Foto noch URL gesetzt → Platzhalter, keine Herkunft."""
    card = PokemonCard(kartenname=_TESTNAME, bild_karte_pfad=None,
                        bild_pokedex_url=None, bild_karte_url=None)
    assert bild_quelle(card) is None


def test_host_quelle_bleibt_synchron_zu_erlaubten_bild_hosts():
    """Ersetzt den früheren Import-Assert (Panel-Nacharbeit KLEIN 4): die
    Synchronität zwischen dem Label-Wörterbuch und der echten Bild-Allowlist
    ist ein GATE-Befund, kein App-Start-Abbruch (ein Label-Wörterbuch darf
    kein Veto über die Bild-Allowlist haben) und übersteht `python -O`
    (das einen Assert wortlos entfernen würde)."""
    assert set(_HOST_QUELLE) == ALLOWED_IMAGE_HOSTS


# ── daten_quelle: reine Ableitung, keine DB nötig ────────────────────────────

def test_daten_quelle_mit_tcgdex_id():
    card = PokemonCard(kartenname=_TESTNAME, tcgdex_card_id="test47-01")
    assert daten_quelle(card) == "tcgdex"


def test_daten_quelle_ohne_tcgdex_id():
    card = PokemonCard(kartenname=_TESTNAME, tcgdex_card_id=None)
    assert daten_quelle(card) == "manuell"


# ── API: Felder in der Einzelantwort, NICHT in der Liste ────────────────────

@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == _TESTNAME).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def test_detail_liefert_bild_und_daten_quelle(db, client):
    card = PokemonCard(kartenname=_TESTNAME, besessen=True,
                        tcgdex_card_id="test47-02", bild_karte_url=_TCGDEX_URL)
    db.add(card)
    db.commit()
    cid = card.id

    body = client.get(f"/api/v1/cards/{cid}").json()
    assert body["daten_quelle"] == "tcgdex"
    assert body["bild_quelle"] == "tcgdex"


def test_detail_kombiniert_alle_drei_herkuenfte(db, client):
    """Deckt die volle Zeile ab: Daten manuell, Bild = eigenes Foto (schlägt
    die gesetzte URL), Preis aus dem jüngsten Verlaufseintrag."""
    card = PokemonCard(kartenname=_TESTNAME, besessen=True,
                        tcgdex_card_id=None,
                        bild_karte_pfad="fotos/test47-kombi.jpg",
                        bild_karte_url=_TCGPLAYER_URL,
                        wert_eur=Decimal("1.23"))
    db.add(card)
    db.flush()
    cid = card.id
    db.add(PreisHistorie(karte_id=cid, wert_eur=Decimal("1.23"),
                          quelle="tcgdex-cardmarket"))
    db.commit()

    body = client.get(f"/api/v1/cards/{cid}").json()
    assert body["daten_quelle"] == "manuell"
    assert body["bild_quelle"] == "foto"
    assert body["wert_quelle"] == "tcgdex-cardmarket"


def test_liste_enthaelt_provenienz_felder_nicht(db, client):
    """Muster wie katalog_preis_usd (v1.7.3): Listen-Items laufen NICHT durch
    _card_response, die neuen Felder bleiben dort None."""
    card = PokemonCard(kartenname=_TESTNAME, besessen=True,
                        tcgdex_card_id="test47-03", bild_karte_url=_TCGDEX_URL)
    db.add(card)
    db.commit()
    cid = card.id

    # Einzelantwort: gefüllt (Gegenprobe, dass wir dieselbe Karte treffen)
    solo = client.get(f"/api/v1/cards/{cid}").json()
    assert solo["daten_quelle"] == "tcgdex"
    assert solo["bild_quelle"] == "tcgdex"

    # Liste, per search auf genau diese Testkarte eingeschränkt
    liste = client.get("/api/v1/cards", params={"search": _TESTNAME}).json()
    treffer = [c for c in liste["items"] if c["id"] == cid]
    assert len(treffer) == 1
    assert treffer[0]["daten_quelle"] is None
    assert treffer[0]["bild_quelle"] is None
