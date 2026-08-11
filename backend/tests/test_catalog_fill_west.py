"""
West-$-Tagesrefresh über TCGCSV Kat. 3 (#64) — zweistufiges Set-Matching.

Panel-BLOCKER-Regression: TCGplayers `abbreviation` ist ein ANDERES Vokabular
als unsere PTCGO-Codes („TR" = Team Rocket 1999 vs. Team Rocket Returns 2004).
Ein PTCGO-Code-Match (Stufe 2) wird deshalb nur nach Nenner-Verifikation
übernommen; set_id-Schlüssel (Stufe 1, TCGplayers eigenes Schema) sind vertraut.

Hermetisch: tcgcsv-Netzfunktionen gemockt; Zeilen in der echten Test-DB,
danach entfernt.
"""

import asyncio
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import tcgcsv


@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.like("test-west%")).delete(synchronize_session=False)
        session.query(PokemonSet).filter(
            PokemonSet.code == "XQZ").delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _mock_tcgcsv(monkeypatch, *, groups, products_by_gid, prices_by_gid):
    async def _groups(category, **kw):
        return groups

    async def _products(category, gid, **kw):
        return products_by_gid.get(gid, [])

    async def _prices(category, gid, **kw):
        return prices_by_gid.get(gid, [])

    monkeypatch.setattr(tcgcsv, "get_groups", _groups)
    monkeypatch.setattr(tcgcsv, "get_products", _products)
    monkeypatch.setattr(tcgcsv, "get_prices", _prices)


def test_west_fill_frischt_preis_auf(db, monkeypatch):
    """Stufe 1 (set_id ↔ Namens-Präfix „SV04"): Preis wird täglich aufgefrischt."""
    db.add(TcgdexCatalog(
        card_id="test-west-1", region="west", set_id="sv04", set_code="PAR",
        local_id="136", name="Testkarte", name_en="Test Card",
        image_url="https://assets.tcgdex.net/x/high.webp",
        price_usd=Decimal("1.11"), price_usd_updated="2020-01-01T00:00:00+00:00",
    ))
    db.commit()
    _mock_tcgcsv(
        monkeypatch,
        groups=[{"groupId": 77, "abbreviation": "PAR", "name": "SV04: Paradox Rift"}],
        products_by_gid={77: [{"productId": 900, "name": "Roaring Moon ex",
                               "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/x_200w.jpg",
                               "extendedData": [{"name": "Number", "value": "136/182"}]}]},
        prices_by_gid={77: [{"productId": 900, "subTypeName": "Normal", "marketPrice": 4.20}]},
    )

    result = asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    row = db.get(TcgdexCatalog, "test-west-1")
    assert result["prices"] >= 1
    assert row.price_usd == Decimal("4.20")                    # täglich frisch
    assert row.price_usd_updated > "2025"                      # neuer Stand
    assert row.name_en == "Test Card"                          # COALESCE: nicht überschrieben
    assert row.image_url == "https://assets.tcgdex.net/x/high.webp"  # Bild bleibt TCGdex
    assert row.image_source is None


def test_swsh_einstellig_matcht_gepolstert(db, monkeypatch):
    """SWSH-Ära einstellig: unsere set_id „swsh5" ↔ TCGplayer „SWSH05" (Polsterung)."""
    db.add(TcgdexCatalog(card_id="test-west-2", region="west", set_id="swsh5",
                         set_code="BST", local_id="25"))
    db.commit()
    _mock_tcgcsv(
        monkeypatch,
        groups=[
            {"groupId": 50, "abbreviation": "SWSH05", "name": "SWSH05: Battle Styles"},
            # Fremd-Vokabular-Falle: TCGplayer „BST" = EX Battle Stadium (2005)!
            {"groupId": 66, "abbreviation": "BST", "name": "EX Battle Stadium"},
        ],
        products_by_gid={
            50: [{"productId": 901, "name": "X",
                  "extendedData": [{"name": "Number", "value": "025/163"}]}],
            66: [{"productId": 999, "name": "Falsch",
                  "extendedData": [{"name": "Number", "value": "025/100"}]}],
        },
        prices_by_gid={
            50: [{"productId": 901, "subTypeName": "Normal", "marketPrice": 2.50}],
            66: [{"productId": 999, "subTypeName": "Normal", "marketPrice": 399.99}],
        },
    )

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    # Stufe 1 (SWSH05) gewinnt VOR dem Fremd-Vokabular-Treffer (BST → 2005er-Set)
    assert db.get(TcgdexCatalog, "test-west-2").price_usd == Decimal("2.50")


def test_fremdvokabular_ohne_nenner_beleg_wird_verworfen(db, monkeypatch):
    """Panel-BLOCKER: PTCGO-Code trifft eine FREMDE TCGplayer-Gruppe (anderes
    Vokabular) → Nenner passt nicht zur offiziellen Set-Größe → kein Preis."""
    db.add(PokemonSet(code="XQZ", name="Fiktives Set", set_id="zz9",
                      card_count_official=109))
    db.add(TcgdexCatalog(card_id="test-west-3", region="west", set_id="zz9",
                         set_code="XQZ", local_id="4"))
    db.commit()
    _mock_tcgcsv(
        monkeypatch,
        # Gruppe heißt anders (kein Namens-Präfix-Schlüssel), abbreviation
        # kollidiert zufällig mit unserem Code — Nenner /82 ≠ offiziell 109.
        groups=[{"groupId": 13, "abbreviation": "XQZ", "name": "Team Rocket"}],
        products_by_gid={13: [
            {"productId": 1, "name": "Dark Charizard",
             "extendedData": [{"name": "Number", "value": "4/82"}]},
            {"productId": 2, "name": "Dark Blastoise",
             "extendedData": [{"name": "Number", "value": "3/82"}]},
            {"productId": 3, "name": "Dark Dragonite",
             "extendedData": [{"name": "Number", "value": "5/82"}]},
        ]},
        prices_by_gid={13: [{"productId": 1, "subTypeName": "Normal", "marketPrice": 399.37}]},
    )

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    assert db.get(TcgdexCatalog, "test-west-3").price_usd is None  # NICHT $399


def test_ptcgo_match_mit_passendem_nenner_wird_uebernommen(db, monkeypatch):
    """Stufe 2 positiv: Code-Match + Nenner == offizielle Größe → Preis kommt."""
    db.add(PokemonSet(code="XQZ", name="Fiktives Set", set_id="zz9",
                      card_count_official=82))
    db.add(TcgdexCatalog(card_id="test-west-4", region="west", set_id="zz9",
                         set_code="XQZ", local_id="4"))
    db.commit()
    _mock_tcgcsv(
        monkeypatch,
        groups=[{"groupId": 13, "abbreviation": "XQZ", "name": "Irgendein Set"}],
        products_by_gid={13: [
            {"productId": 1, "name": "A", "extendedData": [{"name": "Number", "value": "4/82"}]},
            {"productId": 2, "name": "B", "extendedData": [{"name": "Number", "value": "3/82"}]},
            {"productId": 3, "name": "C", "extendedData": [{"name": "Number", "value": "5/82"}]},
        ]},
        prices_by_gid={13: [{"productId": 1, "subTypeName": "Normal", "marketPrice": 7.00}]},
    )

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    assert db.get(TcgdexCatalog, "test-west-4").price_usd == Decimal("7.00")


def test_nummern_dublette_bevorzugt_grundform(db, monkeypatch):
    """„Mew ex - 205/165 (Metal Card)" verliert gegen die Grundform (Panel-Fund)."""
    db.add(TcgdexCatalog(card_id="test-west-5", region="west", set_id="sv03.5",
                         set_code="MEW", local_id="205"))
    db.commit()
    _mock_tcgcsv(
        monkeypatch,
        groups=[{"groupId": 88, "abbreviation": "MEW", "name": "SV: Scarlet and Violet 151"}],
        products_by_gid={88: [
            {"productId": 11, "name": "Mew ex - 205/165 (151 Metal Card)",
             "extendedData": [{"name": "Number", "value": "205/165"}]},
            {"productId": 12, "name": "Mew ex - 205/165",
             "extendedData": [{"name": "Number", "value": "205/165"}]},
            {"productId": 13, "name": "Pikachu",
             "extendedData": [{"name": "Number", "value": "025/165"}]},
            {"productId": 14, "name": "Bulbasaur",
             "extendedData": [{"name": "Number", "value": "001/165"}]},
        ]},
        prices_by_gid={88: [
            {"productId": 11, "subTypeName": "Normal", "marketPrice": 99.99},
            {"productId": 12, "subTypeName": "Normal", "marketPrice": 30.00},
        ]},
    )
    # Stufe 2 (Code MEW): Nenner /165 — offizielle Größe aus pokemon_sets nötig.
    # Der echte Seed führt MEW bereits; falls nicht, Verifikation via set_id-Weg
    # unnötig machen: Namens-Präfix „SV" wäre mehrdeutig — darum sichern wir die
    # offizielle Größe explizit ab (merge: Bestand aktualisieren statt doppeln).
    ps = db.get(PokemonSet, "MEW")
    if ps is None:
        db.add(PokemonSet(code="MEW", name="151", set_id="sv03.5", card_count_official=165))
    else:
        ps.card_count_official = ps.card_count_official or 165
    db.commit()

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    assert db.get(TcgdexCatalog, "test-west-5").price_usd == Decimal("30.00")  # Grundform


def test_unbekannte_region_bleibt_noop(db):
    result = asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "ko"))
    assert result == {"images": 0, "prices": 0, "sets": 0}
