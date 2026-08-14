"""
v1.8.2: Anzeige zeigt die WAHRE Preisquelle.

Owner-Fund: die Detailansicht behauptete pauschal „Wert (Cardmarket 30-Tage-Ø)"
und zeigte den TCGplayer-BASISpreis ($0.25) — obwohl der Wert (0,52 €) aus dem
Pokéball-PRODUKT ($0.60) stammte. Jetzt liefert die API die tatsächlich
bepreiste Variante + die Herkunft des letzten Werts.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard, PreisHistorie
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services.pricing import variant_usd

_TESTNAME = "Variante-Testkarte"


class _Row:
    """Katalogzeilen-Double für die pure Variantenwahl."""
    def __init__(self, **kw):
        for k in ("price_usd", "price_usd_holo", "price_usd_reverse",
                  "price_usd_pokeball", "price_usd_masterball"):
            setattr(self, k, kw.get(k))


# ── variant_usd: eine Routine für Bewertung UND Anzeige ──────────────────────

def test_variant_usd_waehlt_musterprodukt():
    row = _Row(price_usd=Decimal("0.25"), price_usd_reverse=Decimal("0.26"),
               price_usd_pokeball=Decimal("0.60"), price_usd_masterball=Decimal("12.78"))
    assert variant_usd(row, "Reverse Holo", "Pokéball") == (Decimal("0.60"), "pokeball")
    assert variant_usd(row, "Reverse Holo", "Masterball") == (Decimal("12.78"), "masterball")


def test_variant_usd_ohne_muster_und_holo():
    row = _Row(price_usd=Decimal("0.25"), price_usd_holo=Decimal("0.22"),
               price_usd_reverse=Decimal("0.26"))
    assert variant_usd(row, "Reverse Holo", None) == (Decimal("0.26"), "reverse")
    assert variant_usd(row, "Holo", None) == (Decimal("0.22"), "holo")
    assert variant_usd(row, "Normal", None) == (Decimal("0.25"), "normal")


def test_variant_usd_stale_muster_an_normal_karte_ignoriert():
    row = _Row(price_usd=Decimal("0.25"), price_usd_masterball=Decimal("12.78"))
    assert variant_usd(row, "Normal", "Masterball") == (Decimal("0.25"), "normal")


def test_variant_usd_reverse_ohne_reverse_spalte_naehert_normal():
    row = _Row(price_usd=Decimal("0.25"))
    assert variant_usd(row, "Reverse Holo", None) == (Decimal("0.25"), "normal")


def test_variant_usd_holo_ohne_holo_spalte_bleibt_leer():
    """Kein Fallback auf Normal — falsche Variante wäre schlimmer als kein Preis."""
    row = _Row(price_usd=Decimal("0.25"))
    assert variant_usd(row, "Holo", None) == (None, "holo")


# ── API: Variante + Wertquelle in der Einzelkarten-Antwort ───────────────────

@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == _TESTNAME).delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.like("test182%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def test_detail_liefert_variante_und_wertquelle(db, client):
    db.add(TcgdexCatalog(card_id="test182-43", region="west",
                         price_usd=Decimal("0.25"),
                         price_usd_reverse=Decimal("0.26"),
                         price_usd_pokeball=Decimal("0.60"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    card = PokemonCard(kartenname=_TESTNAME, besessen=True, sprache="DE",
                       folierung="Reverse Holo", muster="Pokéball",
                       tcgdex_card_id="test182-43", wert_eur=Decimal("0.52"))
    db.add(card)
    db.flush()
    cid = card.id
    db.add(PreisHistorie(karte_id=cid, wert_eur=Decimal("0.52"),
                         quelle="tcgplayer-usd@0.867"))
    db.commit()

    body = client.get(f"/api/v1/cards/{cid}").json()
    # $-Zeile zeigt das PATTERN-Produkt, nicht den Basispreis
    assert body["katalog_preis_usd"] == "0.60"
    assert body["katalog_preis_usd_variante"] == "pokeball"
    # Wert-Label bekommt die echte Herkunft inkl. Kurs
    assert body["wert_quelle"] == "tcgplayer-usd@0.867"


def test_detail_ohne_verlauf_hat_keine_wertquelle(db, client):
    db.add(TcgdexCatalog(card_id="test182-99", region="west",
                         price_usd=Decimal("1.00"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    card = PokemonCard(kartenname=_TESTNAME, besessen=True, folierung="Normal",
                       tcgdex_card_id="test182-99", wert_eur=Decimal("0.87"))
    db.add(card)
    db.flush()
    cid = card.id
    db.commit()

    body = client.get(f"/api/v1/cards/{cid}").json()
    # Kein Verlauf → keine Quelle; das UI beschriftet dann neutral „Wert"
    # statt „Cardmarket" zu behaupten (Panel-Fund).
    assert body["wert_quelle"] is None
    assert body["katalog_preis_usd_variante"] == "normal"


def test_detail_zeigt_keinen_fremden_variantenpreis(db, client):
    """Panel-MAJOR: Holo-Karte OHNE Holo-Preis darf NICHT den Basispreis als
    „normal" anzeigen — die Bewertung nähme ihn nie, das Label löge sonst."""
    db.add(TcgdexCatalog(card_id="test182-holo", region="west",
                         price_usd=Decimal("0.25"),          # nur Basispreis
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    card = PokemonCard(kartenname=_TESTNAME, besessen=True, folierung="Holo",
                       tcgdex_card_id="test182-holo", wert_eur=Decimal("1.00"))
    db.add(card)
    db.flush()
    cid = card.id
    db.commit()

    body = client.get(f"/api/v1/cards/{cid}").json()
    assert body["katalog_preis_usd"] is None            # lieber keiner als ein fremder
    assert body["katalog_preis_usd_variante"] is None


def test_detail_zeigt_juengste_quelle(db, client):
    card = PokemonCard(kartenname=_TESTNAME, besessen=True, wert_eur=Decimal("1.00"))
    db.add(card)
    db.flush()
    cid = card.id
    from datetime import timedelta
    alt = datetime.utcnow() - timedelta(days=3)
    db.add(PreisHistorie(karte_id=cid, wert_eur=Decimal("0.90"),
                         quelle="tcgdex-cardmarket", erfasst_am=alt))
    db.add(PreisHistorie(karte_id=cid, wert_eur=Decimal("1.00"),
                         quelle="tcgplayer-usd@0.87"))
    db.commit()

    assert client.get(f"/api/v1/cards/{cid}").json()["wert_quelle"] == "tcgplayer-usd@0.87"
