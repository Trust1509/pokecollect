"""
#63: Folierung/Muster-Umbau + Varianten-$-Preise.

- Light-Migration teilt Alt-Werte („Reverse Holo – Pokéball") in Grundform +
  Muster (idempotent).
- Der Fill cached Varianten-Preise (Holofoil-/Reverse-Subtyp + Pokéball-/
  Masterball-PRODUKTE).
- Die Preis-Kette wählt die Spalte je (Folierung, Muster); Muster-Produktpreis
  hat Vorrang vor Cardmarket-Basis-€ ($12.78 vs 0,08 €).
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.main import _run_light_migrations
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import pricing, tcgcsv

_TESTNAME = "Muster-Testkarte"


@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == _TESTNAME).delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("test63%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


# ── Migration: Alt-Folierungen aufteilen ─────────────────────────────────────

def test_migration_teilt_alt_folierungen(db):
    alt = {
        "Reverse Holo – Pokéball": ("Reverse Holo", "Pokéball"),
        "Reverse Holo – Masterball": ("Reverse Holo", "Masterball"),
        "Reverse Holo – Muster": ("Reverse Holo", "Sonstiges"),
        "Cosmos Holo": ("Holo", "Cosmos"),
        "Etched Holo": ("Holo", "Etched"),
    }
    ids = {}
    for old in alt:
        card = PokemonCard(kartenname=_TESTNAME, besessen=True, folierung=old)
        db.add(card)
        db.flush()
        ids[old] = card.id     # VOR dem Commit lesen — ein Zugriff danach
    db.commit()                # öffnete still eine neue Tx (idle in transaction)
    db.rollback()              # und blockierte die ALTERs der Migration (Lehre!)

    _run_light_migrations()   # idempotent, läuft sonst beim App-Start

    db.expire_all()
    for old, (grundform, muster) in alt.items():
        card = db.get(PokemonCard, ids[old])
        assert card.folierung == grundform, old
        assert card.muster == muster, old

    # Zweiter Lauf ändert nichts (Idempotenz) und überschreibt kein Muster.
    card = db.get(PokemonCard, ids["Cosmos Holo"])
    card.muster = "Sonstiges"
    db.commit()
    _run_light_migrations()
    db.expire_all()
    assert db.get(PokemonCard, ids["Cosmos Holo"]).muster == "Sonstiges"


# ── Fill: Varianten-Spalten ──────────────────────────────────────────────────

def test_fill_cached_varianten_preise(db, monkeypatch):
    db.add(TcgdexCatalog(card_id="test63-43", region="west", set_id="zsv10",
                         set_code="WHT", local_id="43"))
    db.commit()

    async def groups(category, **kw):
        return [{"groupId": 9, "abbreviation": "X", "name": "ZSV10: White Flare"}]

    async def products(category, gid, **kw):
        return [
            {"productId": 1, "name": "Gothitelle",
             "extendedData": [{"name": "Number", "value": "043/086"}]},
            {"productId": 2, "name": "Gothitelle (Poke Ball Pattern)",
             "extendedData": [{"name": "Number", "value": "043/086"}]},
            {"productId": 3, "name": "Gothitelle (Master Ball Pattern)",
             "extendedData": [{"name": "Number", "value": "043/086"}]},
        ]

    async def prices(category, gid, **kw):
        return [
            {"productId": 1, "subTypeName": "Holofoil", "marketPrice": 0.22},
            {"productId": 1, "subTypeName": "Reverse Holofoil", "marketPrice": 0.26},
            {"productId": 2, "subTypeName": "Holofoil", "marketPrice": 0.60},
            {"productId": 3, "subTypeName": "Holofoil", "marketPrice": 12.78},
        ]

    monkeypatch.setattr(tcgcsv, "get_groups", groups)
    monkeypatch.setattr(tcgcsv, "get_products", products)
    monkeypatch.setattr(tcgcsv, "get_prices", prices)

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    row = db.get(TcgdexCatalog, "test63-43")
    assert row.price_usd_holo == Decimal("0.22")
    assert row.price_usd_reverse == Decimal("0.26")
    assert row.price_usd_pokeball == Decimal("0.60")
    assert row.price_usd_masterball == Decimal("12.78")
    assert row.price_usd_updated is not None     # Stand gilt für alle $-Spalten
    # kein Normal-Subtyp → market_usd_for fällt auf den ersten Preissatz zurück
    # (etablierte Semantik: bei holo-only-Karten IST Holofoil die Grundform;
    # JP-Produkte kennen oft nur „1st Edition")
    assert row.price_usd == Decimal("0.22")


# ── Preis-Kette: Varianten-Wahl + Muster-Vorrang ─────────────────────────────

def _katalog_zeile(db, cid, **preise):
    db.add(TcgdexCatalog(card_id=cid, region="west",
                         price_usd_updated=datetime.now(timezone.utc).isoformat(),
                         **preise))


def _karte(db, cid, folierung=None, muster=None) -> int:
    card = PokemonCard(kartenname=_TESTNAME, besessen=True,
                       tcgdex_card_id=cid, folierung=folierung, muster=muster)
    db.add(card)
    db.commit()
    return card.id


@pytest.fixture()
def fester_kurs(monkeypatch):
    async def rate():
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", rate)


@pytest.fixture()
def keine_eur_quelle(monkeypatch):
    async def kein_preis(db_, card, price_source="30d_avg"):
        return None, True
    monkeypatch.setattr(pricing, "_price_for_card", kein_preis)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db_, card: None)


def test_holo_karte_nutzt_holofoil_spalte(db, keine_eur_quelle, fester_kurs):
    _katalog_zeile(db, "test63-h1", price_usd=Decimal("1.00"),
                   price_usd_holo=Decimal("5.00"))
    cid = _karte(db, "test63-h1", folierung="Holo")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    assert db.get(PokemonCard, cid).wert_eur == Decimal("4.50")   # 5.00 × 0.90


def test_holo_ohne_holofoil_spalte_bleibt_unbepreist(db, keine_eur_quelle, fester_kurs):
    _katalog_zeile(db, "test63-h2", price_usd=Decimal("1.00"))    # nur Normal-$
    cid = _karte(db, "test63-h2", folierung="Holo")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    assert db.get(PokemonCard, cid).wert_eur is None              # keine falsche Variante


def test_reverse_bevorzugt_reverse_spalte(db, keine_eur_quelle, fester_kurs):
    _katalog_zeile(db, "test63-r1", price_usd=Decimal("1.00"),
                   price_usd_reverse=Decimal("3.00"))
    cid = _karte(db, "test63-r1", folierung="Reverse Holo")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    assert db.get(PokemonCard, cid).wert_eur == Decimal("2.70")   # 3.00 × 0.90


def test_muster_produkt_hat_vorrang_vor_cardmarket(db, fester_kurs, monkeypatch):
    """Masterball-Karte: Pattern-$ ($12.78) schlägt den Basis-€ (0,08 €)."""
    async def basis_eur(db_, card, price_source="30d_avg"):
        return Decimal("0.08"), True     # Cardmarket kennt nur die Basis-Reverse
    monkeypatch.setattr(pricing, "_price_for_card", basis_eur)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db_, card: None)

    _katalog_zeile(db, "test63-m1", price_usd_masterball=Decimal("12.78"))
    cid = _karte(db, "test63-m1", folierung="Reverse Holo", muster="Masterball")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    card = db.get(PokemonCard, cid)
    assert card.wert_eur == Decimal("11.50")                      # 12.78 × 0.90
    assert card.preis_historie[0].quelle.startswith("tcgplayer-usd@")


def test_stale_muster_an_normal_karte_wird_ignoriert(db, keine_eur_quelle, fester_kurs):
    """Panel-MAJOR: Normal-Karte mit zurückgelassenem Masterball-Muster darf
    NICHT den Muster-Preis (12.78) bekommen, sondern den Normalpreis."""
    _katalog_zeile(db, "test63-m3", price_usd=Decimal("0.10"),
                   price_usd_masterball=Decimal("12.78"))
    cid = _karte(db, "test63-m3", folierung="Normal", muster="Masterball")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    assert db.get(PokemonCard, cid).wert_eur == Decimal("0.09")   # 0.10 × 0.90


def test_muster_preis_greift_auch_bei_eur_ausfall(db, fester_kurs, monkeypatch):
    """Bewusstes Verhalten locken: Muster-$ ist Primärquelle — er greift auch,
    wenn TCGdex gerade ausgefallen ist (eur_geprueft=False)."""
    async def tcgdex_down(db_, card, price_source="30d_avg"):
        return None, False
    monkeypatch.setattr(pricing, "_price_for_card", tcgdex_down)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db_, card: None)

    _katalog_zeile(db, "test63-m4", price_usd_pokeball=Decimal("0.60"))
    cid = _karte(db, "test63-m4", folierung="Reverse Holo", muster="Pokéball")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    assert db.get(PokemonCard, cid).wert_eur == Decimal("0.54")   # 0.60 × 0.90


def test_migration_normalisiert_sammelziele(db):
    """Panel-MAJOR: ziel_folierung/soll_folierung tragen die Alt-Semantik und
    vergleichen exakt — sie werden auf die Grundform normalisiert."""
    from app.models.collection import Collection, CollectionSoll
    coll = Collection(name="Muster-Migrationsziel", typ="set_ziel",
                      ziel_folierung="Reverse Holo – Pokéball")
    db.add(coll)
    db.flush()
    soll = CollectionSoll(collection_id=coll.id, tcgdex_card_id="test63-soll",
                          soll_folierung="Cosmos Holo")
    db.add(soll)
    db.flush()                      # IDs VOR dem Commit lesen (Session-Lehre)
    cid, sid = coll.id, soll.id
    db.commit()
    db.rollback()   # nichts offen lassen — Migration braucht exklusive Locks

    _run_light_migrations()

    db.expire_all()
    try:
        assert db.get(Collection, cid).ziel_folierung == "Reverse Holo"
        assert db.get(CollectionSoll, sid).soll_folierung == "Holo"
    finally:
        db.delete(db.get(CollectionSoll, sid))
        db.delete(db.get(Collection, cid))
        db.commit()


def test_product_pattern_schreibvarianten():
    from app.services.tcgcsv import product_pattern
    assert product_pattern({"name": "Gothitelle (Poke Ball Pattern)"}) == "pokeball"
    assert product_pattern({"name": "Gothitelle (Poké Ball Pattern)"}) == "pokeball"
    assert product_pattern({"name": "X (Pokeball Pattern)"}) == "pokeball"
    assert product_pattern({"name": "X (Master Ball Pattern)"}) == "masterball"
    assert product_pattern({"name": "X (Masterball Pattern)"}) == "masterball"
    assert product_pattern({"name": "Gothitelle"}) is None
    assert product_pattern({}) is None


def test_fill_muster_only_nummer_setzt_keine_basisdaten(db, monkeypatch):
    """Panel-MAJOR: existiert für eine Nummer NUR das Muster-Produkt, dürfen
    Bild/Name/Basispreis NICHT vom Muster-Produkt stammen."""
    db.add(TcgdexCatalog(card_id="test63-only", region="west", set_id="zsv11",
                         set_code="ZZQ", local_id="99"))
    db.commit()

    async def groups(category, **kw):
        return [{"groupId": 8, "abbreviation": "Y", "name": "ZSV11: Testset"}]

    async def products(category, gid, **kw):
        return [{"productId": 7, "name": "Solo (Poke Ball Pattern)",
                 "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/x_200w.jpg",
                 "extendedData": [{"name": "Number", "value": "099/100"}]}]

    async def prices(category, gid, **kw):
        return [{"productId": 7, "subTypeName": "Holofoil", "marketPrice": 5.55}]

    monkeypatch.setattr(tcgcsv, "get_groups", groups)
    monkeypatch.setattr(tcgcsv, "get_products", products)
    monkeypatch.setattr(tcgcsv, "get_prices", prices)

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    row = db.get(TcgdexCatalog, "test63-only")
    assert row.image_url is None                       # kein Muster-Bild als Kartenbild
    assert row.name_en is None                         # kein Muster-Name
    assert row.price_usd is None                       # kein Muster-$ als Basispreis
    assert row.price_usd_pokeball == Decimal("5.55")   # aber die Muster-Spalte


def test_muster_ohne_pattern_preis_faellt_auf_eur(db, fester_kurs, monkeypatch):
    """Pokéball-Karte ohne gecachten Pattern-$ → Cardmarket-€ als Näherung."""
    async def basis_eur(db_, card, price_source="30d_avg"):
        return Decimal("0.08"), True
    monkeypatch.setattr(pricing, "_price_for_card", basis_eur)
    monkeypatch.setattr(pricing, "_cardmarket_oauth_fallback", lambda db_, card: None)

    _katalog_zeile(db, "test63-m2", price_usd=Decimal("1.00"))   # kein Pattern-$
    cid = _karte(db, "test63-m2", folierung="Reverse Holo", muster="Pokéball")
    asyncio.run(pricing.refresh_prices_for_cards(db, [cid]))
    card = db.get(PokemonCard, cid)
    assert card.wert_eur == Decimal("0.08")
    assert card.preis_historie[0].quelle == "tcgdex-cardmarket"
