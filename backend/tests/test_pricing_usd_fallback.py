"""
$-Preis-Fallback für Karten ohne Cardmarket-€ (Epic #41, Owner-Entscheid
2026-08-11): TCGplayer-$ aus dem Katalog-Cache × EZB-Kurs → wert_eur +
Preisverlauf (Quelle "tcgplayer-usd@<kurs>"). Betrifft v. a. japanische Karten.

Panel-gehärtete Garantien (2026-08-11):
- Ein TCGdex-AUSFALL (€-Quelle nicht prüfbar) löst KEINEN $-Fallback aus —
  sonst würde ein transienter Ausfall die Sammlung still auf $-Basis umbewerten.
- 0/negativ-$ und Werte außerhalb Numeric(8,2) werden übersprungen (nie 0
  schreiben; ein Ausreißer darf nicht den ganzen Lauf zurückrollen).
- Echte Holo-Karten überspringen den Fallback (gecachter $ = Normal-Variante).
- Veralteter $-Datenstand (> 30 Tage) wird nicht verwendet.

Hermetisch: €-Quelle und fx.usd_eur_rate sind gemockt; Karten-/Katalog-Zeilen
liegen in der echten Test-DB (Postgres) und werden nach jedem Test entfernt.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import pricing
from app.services.pricing import convert_usd_eur, refresh_prices_for_cards

_TESTNAME = "JP-Preistestkarte"


def _frisch() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_convert_usd_eur_rundet_kaufmaennisch():
    assert convert_usd_eur(Decimal("10.00"), Decimal("0.8666")) == Decimal("8.67")
    assert convert_usd_eur(Decimal("0.05"), Decimal("0.8666")) == Decimal("0.04")
    assert convert_usd_eur(Decimal("1.00"), Decimal("0.865")) == Decimal("0.87")  # HALF_UP
    # float-Durchreicher wird über str() exakt behandelt (Panel-Fund)
    assert convert_usd_eur(2.675, 1) == Decimal("2.68")


@pytest.fixture()
def db(client):
    """Echte Session gegen die Test-DB; räumt angelegte Zeilen wieder ab."""
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == _TESTNAME).delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.like("test-usd%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def keine_eur_quelle(monkeypatch):
    """€-Quellen abklemmen: Cardmarket GEPRÜFT, aber ohne Preis (JP-Fall)."""
    async def kein_preis(db, card, price_source="30d_avg"):
        return None, True
    monkeypatch.setattr(pricing, "_price_for_card", kein_preis)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db, card: None)


@pytest.fixture()
def fester_kurs(monkeypatch):
    async def rate():
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", rate)


def _mach_karte(db, tcgdex_card_id, mit_katalog_usd=None, *, stand=None,
                folierung=None, set_id=None) -> int:
    """Besessene Karte + (optional) Katalog-Zeile mit $-Preis anlegen."""
    if mit_katalog_usd is not None:
        if db.get(TcgdexCatalog, tcgdex_card_id) is None:
            db.add(TcgdexCatalog(card_id=tcgdex_card_id, region="ja",
                                 price_usd=Decimal(mit_katalog_usd),
                                 price_usd_updated=stand or _frisch()))
    card = PokemonCard(kartenname=_TESTNAME, besessen=True, sprache="JP",
                       tcgdex_card_id=tcgdex_card_id, folierung=folierung,
                       set_id=set_id)
    db.add(card)
    db.commit()
    return card.id


def test_usd_fallback_schreibt_wert_und_verlauf(db, keine_eur_quelle, fester_kurs):
    card_id = _mach_karte(db, "test-usd-1", mit_katalog_usd="10.00")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur == Decimal("9.00")          # 10.00 $ × 0.90
    assert card.wert_aktualisiert is not None
    hist = list(card.preis_historie)
    assert len(hist) == 1
    assert hist[0].wert_eur == Decimal("9.00")
    # Herkunft inkl. Kurs UND Variante auditierbar markiert (Panel-Funde;
    # die Variante kam in v1.8.2 dazu, damit das Label nicht die spätere
    # Formular-Einstellung behauptet).
    assert hist[0].quelle == "tcgplayer-usd@0.90/normal"


def test_ohne_katalog_preis_bleibt_karte_unveraendert(db, keine_eur_quelle, fester_kurs):
    card_id = _mach_karte(db, "test-usd-2", mit_katalog_usd=None)  # keine Katalog-Zeile

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur is None                      # kein 0-Wert, unverändert
    assert card.preis_historie == []


def test_ohne_kurs_bleibt_karte_unveraendert(db, keine_eur_quelle, monkeypatch):
    async def kein_kurs():
        return None
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", kein_kurs)
    card_id = _mach_karte(db, "test-usd-3", mit_katalog_usd="5.00")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur is None
    assert card.preis_historie == []


def test_eur_ausfall_loest_keinen_usd_fallback_aus(db, fester_kurs, monkeypatch):
    """TCGdex down (€ nicht prüfbar) → Karte bleibt unangetastet, KEINE stille
    Umbasierung der Sammlung auf $-Basis (Panel-MAJOR)."""
    async def tcgdex_down(set_id, karten_nr, sprache):
        return None
    monkeypatch.setattr(pricing, "fetch_tcgdex_card", tcgdex_down)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db, card: None)
    # set_id gesetzt → die €-Prüfung erreicht den (ausgefallenen) Fetch
    card_id = _mach_karte(db, "test-usd-9", mit_katalog_usd="10.00", set_id="m1s")
    card = db.get(PokemonCard, card_id)
    card.wert_eur = Decimal("55.00")   # bestehender €-Wert
    db.commit()

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur == Decimal("55.00")          # unangetastet
    assert card.preis_historie == []


def test_holo_karte_ueberspringt_usd_fallback(db, keine_eur_quelle, fester_kurs):
    """Gecachter $ ist der Normal-Varianten-Preis → echte Holo nicht bepreisen."""
    card_id = _mach_karte(db, "test-usd-10", mit_katalog_usd="10.00", folierung="Holo")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    assert db.get(PokemonCard, card_id).wert_eur is None


def test_reverse_holo_zaehlt_wie_normal(db, keine_eur_quelle, fester_kurs):
    """Reverse nutzt wie im €-Pfad den Normal-Preis → Fallback greift."""
    card_id = _mach_karte(db, "test-usd-11", mit_katalog_usd="4.00", folierung="Reverse Holo")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    assert db.get(PokemonCard, card_id).wert_eur == Decimal("3.60")


def test_alter_datenstand_wird_ignoriert(db, keine_eur_quelle, fester_kurs):
    """$-Preis mit Stand > 30 Tage (z. B. West-Einmal-Enrich) → kein Fallback."""
    alt = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    card_id = _mach_karte(db, "test-usd-12", mit_katalog_usd="10.00", stand=alt)

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    assert db.get(PokemonCard, card_id).wert_eur is None


def test_null_dollar_ueberschreibt_nie(db, keine_eur_quelle, fester_kurs):
    """0-$-Katalogpreis = Datenfehler → bestehender Wert bleibt stehen (nie 0)."""
    card_id = _mach_karte(db, "test-usd-6", mit_katalog_usd="0.00")
    card = db.get(PokemonCard, card_id)
    card.wert_eur = Decimal("123.45")
    db.commit()

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur == Decimal("123.45")   # unverändert
    assert card.preis_historie == []


def test_ueberlauf_karte_killt_nicht_den_lauf(db, keine_eur_quelle, fester_kurs):
    """Ein $-Ausreißer über Numeric(8,2) wird übersprungen; andere Karten des
    Laufs werden trotzdem aktualisiert (kein Kollektiv-Rollback)."""
    ausreisser = _mach_karte(db, "test-usd-7", mit_katalog_usd="99999999.99")
    normal = _mach_karte(db, "test-usd-8", mit_katalog_usd="10.00")

    asyncio.run(refresh_prices_for_cards(db, [ausreisser, normal]))

    assert db.get(PokemonCard, ausreisser).wert_eur is None      # übersprungen
    assert db.get(PokemonCard, normal).wert_eur == Decimal("9.00")  # gerettet


def test_kurs_wird_nur_einmal_je_lauf_geholt(db, keine_eur_quelle, monkeypatch):
    calls = {"n": 0}

    async def zaehlender_kurs():
        calls["n"] += 1
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", zaehlender_kurs)

    ids = [_mach_karte(db, f"test-usd-batch-{i}", mit_katalog_usd="2.00") for i in range(3)]
    asyncio.run(refresh_prices_for_cards(db, ids))

    assert calls["n"] == 1
    assert all(db.get(PokemonCard, i).wert_eur == Decimal("1.80") for i in ids)


def test_eur_quelle_hat_vorrang_vor_usd(db, fester_kurs, monkeypatch):
    """Liefert Cardmarket €, wird NICHT umgerechnet (Kette: € zuerst)."""
    async def eur_preis(db, card, price_source="30d_avg"):
        return Decimal("12.34"), True
    monkeypatch.setattr(pricing, "_price_for_card", eur_preis)
    card_id = _mach_karte(db, "test-usd-4", mit_katalog_usd="99.99")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur == Decimal("12.34")
    assert card.preis_historie[0].quelle == "tcgdex-cardmarket"


def test_oauth_fallback_bekommt_eigene_quelle(db, fester_kurs, monkeypatch):
    """OAuth-Preis wird als cardmarket-oauth etikettiert (Panel-Fund)."""
    async def kein_preis(db, card, price_source="30d_avg"):
        return None, True
    monkeypatch.setattr(pricing, "_price_for_card", kein_preis)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback",
                        lambda db, card: Decimal("7.77"))
    card_id = _mach_karte(db, "test-usd-13")

    asyncio.run(refresh_prices_for_cards(db, [card_id]))

    card = db.get(PokemonCard, card_id)
    assert card.wert_eur == Decimal("7.77")
    assert card.preis_historie[0].quelle == "cardmarket-oauth"


def test_detail_endpunkt_liefert_katalog_usd(db, client):
    """GET /cards/{id} legt den Original-$ aus dem Katalog-Cache bei."""
    stand = _frisch()
    card_id = _mach_karte(db, "test-usd-5", mit_katalog_usd="7.50", stand=stand)
    body = client.get(f"/api/v1/cards/{card_id}").json()
    assert body["katalog_preis_usd"] == "7.50"
    assert body["katalog_preis_usd_stand"] == stand


def test_detail_endpunkt_ohne_katalogzeile_null(db, client):
    card_id = _mach_karte(db, "test-usd-14", mit_katalog_usd=None)
    body = client.get(f"/api/v1/cards/{card_id}").json()
    assert body["katalog_preis_usd"] is None
    assert body["katalog_preis_usd_stand"] is None
