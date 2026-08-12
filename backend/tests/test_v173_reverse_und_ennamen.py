"""
v1.7.3: €-Reverse-Preis (Cardmarket--holo-Kette), case-toleranter Katalog-
Lookup und EN-Namen-Übernahme aus dem Katalog (JP-Karten).

Empirischer Hintergrund (2026-08-12, me02-043 „Hokumil", normal+reverse ohne
Holo): avg30=0.02 aber avg30-holo=0.08 — die -holo-Felder sind bei solchen
Karten der Reverse-Preis.
"""

from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services.card_creation import create_owned_card
from app.services.catalog_lookup import catalog_row_for
from app.services.pricing import pick_cardmarket_price
from app.services.tcgdex import CardMarketPricing


# ── €-Reverse: -holo-Kette wenn keine echte Holo-Variante existiert ──────────

_CM = CardMarketPricing(**{"avg30": 0.02, "avg30-holo": 0.08,
                           "avg1": 0.01, "avg1-holo": 0.05})


def test_reverse_ohne_echtes_holo_nutzt_holo_kette():
    assert pick_cardmarket_price(_CM, "Reverse Holo",
                                 hat_echtes_holo=False) == Decimal("0.08")


def test_reverse_muster_varianten_ebenso():
    for f in ("Reverse Holo – Pokéball", "Reverse Holo – Masterball",
              "Reverse Holo – Sterne"):
        assert pick_cardmarket_price(_CM, f, hat_echtes_holo=False) == Decimal("0.08")


def test_reverse_mit_echtem_holo_bleibt_basis():
    """Existiert eine echte Holo-Variante, wäre -holo deren Preis — Reverse
    bleibt (mangels eigener Quelle) bei der Basis-Kette wie bisher."""
    assert pick_cardmarket_price(_CM, "Reverse Holo",
                                 hat_echtes_holo=True) == Decimal("0.02")


def test_default_bleibt_altverhalten():
    """Ohne hat_echtes_holo-Angabe (Bestandsaufrufer) ändert sich nichts."""
    assert pick_cardmarket_price(_CM, "Reverse Holo") == Decimal("0.02")
    assert pick_cardmarket_price(_CM, "Normal") == Decimal("0.02")
    assert pick_cardmarket_price(_CM, "Holo") == Decimal("0.08")


def test_reverse_daily_nutzt_avg1_holo():
    assert pick_cardmarket_price(_CM, "Reverse Holo", "daily",
                                 hat_echtes_holo=False) == Decimal("0.05")


def test_reverse_trend_only_faellt_auf_trend(  # Panel-MAJOR: kein Preisverlust
):
    """Karte mit NUR trend-Daten: die Holo-Kette muss auf trend enden — sonst
    bliebe eine Reverse-Karte preislos, die vorher 0,05 € bekam."""
    cm = CardMarketPricing(trend=0.05)
    assert pick_cardmarket_price(cm, "Reverse Holo",
                                 hat_echtes_holo=False) == Decimal("0.05")
    cm2 = CardMarketPricing(**{"trend-holo": 0.07})
    assert pick_cardmarket_price(cm2, "Reverse Holo",
                                 hat_echtes_holo=False) == Decimal("0.07")


def test_reverse_daily_ohne_avg1_holo_nimmt_foil_30d(  # Panel-MAJOR: daily-Pfad
):
    """daily OHNE Foil-Tagespreis: der Foil-30d-Wert (0.08) muss den Normal-
    Tagespreis (0.01) schlagen — sonst bestünde der Owner-Bug für daily fort."""
    cm = CardMarketPricing(**{"avg1": 0.01, "avg30-holo": 0.08})
    assert pick_cardmarket_price(cm, "Reverse Holo", "daily",
                                 hat_echtes_holo=False) == Decimal("0.08")


# ── TCGplayer-Produktname → sauberer Kartenname ──────────────────────────────

def test_clean_card_name():
    from app.services.tcgcsv import clean_card_name
    assert clean_card_name("Mega Manectric ex - 032/063") == "Mega Manectric ex"
    assert clean_card_name("Mew ex - 205/165 (151 Metal Card)") == "Mew ex"
    assert clean_card_name("Pikachu - 001/SV-P") == "Pikachu"
    assert clean_card_name("Team Aqua's Poochyena") == "Team Aqua's Poochyena"
    assert clean_card_name("Porygon-Z") == "Porygon-Z"     # Bindestrich ohne Nummer
    assert clean_card_name("  ") is None
    assert clean_card_name(None) is None


# ── Case-toleranter Katalog-Lookup + EN-Namen-Fill ───────────────────────────

@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == "JPName-Testkarte").delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("testv173%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def test_catalog_lookup_case_tolerant(db):
    """Scan-IDs sind klein („me03-029"), JP-Katalog groß — beides muss treffen."""
    db.add(TcgdexCatalog(card_id="TESTV173-029", region="ja", name_en="Dedenne"))
    db.commit()
    assert catalog_row_for(db, "TESTV173-029") is not None    # exakt
    assert catalog_row_for(db, "testv173-029") is not None    # case-tolerant
    assert catalog_row_for(db, "Testv173-029") is not None    # Gegenrichtung/Mix
    assert catalog_row_for(db, "testv173-999") is None
    assert catalog_row_for(db, None) is None


def test_catalog_lookup_kollision_deterministisch(db):
    """Zwei case-gleiche Zeilen (theoretisch): exakter Treffer gewinnt; der
    Fallback wählt stabil alphabetisch statt Planer-Zufall (Panel-Fund)."""
    db.add(TcgdexCatalog(card_id="TESTV173-D1", region="ja", name_en="Gross"))
    db.add(TcgdexCatalog(card_id="testv173-d1", region="west", name_en="Klein"))
    db.commit()
    assert catalog_row_for(db, "testv173-d1").name_en == "Klein"   # exakt
    assert catalog_row_for(db, "TESTV173-D1").name_en == "Gross"   # exakt
    # dritte Schreibweise → Fallback, deterministisch alphabetisch erste
    assert catalog_row_for(db, "TestV173-d1").name_en == "Gross"   # "TESTV.." < "testv.."


def test_usd_fallback_trifft_kleingeschriebene_scan_id(db, monkeypatch):
    """E2E-Symptom: scan-committete JP-Karte (ID klein) bekommt ihren $→€-Wert
    trotz großgeschriebener Katalog-Zeile (Panel-Testlücke)."""
    import asyncio
    from app.services import pricing

    async def kein_preis(db_, card, price_source="30d_avg"):
        return None, True
    monkeypatch.setattr(pricing, "_price_for_card", kein_preis)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db_, card: None)

    async def kurs():
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", kurs)

    from datetime import datetime, timezone
    db.add(TcgdexCatalog(card_id="TESTV173-USD", region="ja",
                         price_usd=Decimal("10.00"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    card = PokemonCard(kartenname="JPName-Testkarte", besessen=True,
                       sprache="JP", tcgdex_card_id="testv173-usd")  # klein!
    db.add(card)
    db.commit()

    asyncio.run(pricing.refresh_prices_for_cards(db, [card.id]))
    assert db.get(PokemonCard, card.id).wert_eur == Decimal("9.00")


def test_create_owned_card_fuellt_en_namen_aus_katalog(db):
    db.add(TcgdexCatalog(card_id="TESTV173-032", region="ja",
                         name_en="Mega Manectric ex"))
    db.commit()

    card = create_owned_card(db, {
        "kartenname": "JPName-Testkarte", "sprache": "JP",
        # klein geschrieben wie vom Scan-Resolver — Case-Toleranz inklusive
        "tcgdex_card_id": "testv173-032",
    })
    assert card.englischer_name == "Mega Manectric ex"


def test_create_owned_card_ueberschreibt_keinen_en_namen(db):
    db.add(TcgdexCatalog(card_id="TESTV173-033", region="ja",
                         name_en="Katalog-Name"))
    db.commit()

    card = create_owned_card(db, {
        "kartenname": "JPName-Testkarte", "sprache": "JP",
        "tcgdex_card_id": "TESTV173-033",
        "englischer_name": "Vom Nutzer gesetzt",
    })
    assert card.englischer_name == "Vom Nutzer gesetzt"
