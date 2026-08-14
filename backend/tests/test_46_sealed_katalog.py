"""
#46: Sealed-Produkt-Katalog aus TCGplayer — Fill, Picker-API, Verknüpfung,
Auto-Wert für verknüpfte Produkte.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.models.sealed import SealedCatalog, SealedProduct
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import pricing, tcgcsv


@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(SealedProduct).filter(
            SealedProduct.name.like("Sealed46%")).delete(synchronize_session=False)
        session.query(SealedCatalog).filter(
            SealedCatalog.product_id >= 4600000).delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.like("test46%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def test_fill_upsertet_sealed_produkte(db, monkeypatch):
    """Produkte OHNE Nummer landen im Sealed-Katalog (Bild + Marktpreis)."""
    db.add(TcgdexCatalog(card_id="test46-1", region="west", set_id="zsv12",
                         set_code="ZQW", local_id="1"))
    db.commit()

    async def groups(category, **kw):
        return [{"groupId": 5, "abbreviation": "Q", "name": "ZSV12: Testset"}]

    async def products(category, gid, **kw):
        return [
            {"productId": 4600001, "name": "Testset Elite Trainer Box",
             "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/etb_200w.jpg"},
            {"productId": 4600002, "name": "Karte X",
             "extendedData": [{"name": "Number", "value": "001/100"}]},
        ]

    async def prices(category, gid, **kw):
        return [
            {"productId": 4600001, "subTypeName": "Normal", "marketPrice": 156.41},
            {"productId": 4600002, "subTypeName": "Normal", "marketPrice": 1.00},
        ]

    monkeypatch.setattr(tcgcsv, "get_groups", groups)
    monkeypatch.setattr(tcgcsv, "get_products", products)
    monkeypatch.setattr(tcgcsv, "get_prices", prices)

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    row = db.get(SealedCatalog, 4600001)
    assert row is not None
    assert row.name == "Testset Elite Trainer Box"
    assert row.region == "west"
    assert row.image_url == "https://tcgplayer-cdn.tcgplayer.com/etb_in_1000x1000.jpg"
    assert row.price_usd == Decimal("156.41")
    assert row.price_usd_updated is not None
    # Karten-Produkt landet NICHT im Sealed-Katalog
    assert db.get(SealedCatalog, 4600002) is None


def test_sealed_katalog_suche_und_verknuepfung(db, client):
    db.add(SealedCatalog(product_id=4600010, region="west", set_code="ZQW",
                         name="Sealed46 Booster Bundle",
                         image_url="https://tcgplayer-cdn.tcgplayer.com/x_in_1000x1000.jpg",
                         price_usd=Decimal("87.79"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    db.commit()

    # Suche (Picker-Quelle)
    r = client.get("/api/v1/sealed/catalog", params={"search": "Sealed46 Booster"})
    assert r.status_code == 200
    hits = r.json()
    assert any(h["product_id"] == 4600010 for h in hits)

    # Anlage mit Verknüpfung: Bild kommt aus dem Katalog
    r = client.post("/api/v1/sealed", json={
        "name": "Sealed46 Mein Bundle", "typ": "Bundle",
        "tcgplayer_product_id": 4600010,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["tcgplayer_product_id"] == 4600010
    assert body["bild_url"] == "https://tcgplayer-cdn.tcgplayer.com/x_in_1000x1000.jpg"

    # Unbekannte Verknüpfung → 404
    r = client.post("/api/v1/sealed", json={
        "name": "Sealed46 Kaputt", "tcgplayer_product_id": 999999999})
    assert r.status_code == 404

    # Verknüpfung lösen (Sonderwert 0)
    r = client.put(f"/api/v1/sealed/{body['id']}", json={"tcgplayer_product_id": 0})
    assert r.status_code == 200
    assert r.json()["tcgplayer_product_id"] is None
    assert r.json()["bild_url"] is None


def test_null_loest_verknuepfung_vollstaendig(db, client):
    """Panel-MAJOR: explizites null löst die Verknüpfung UND räumt Bild/Stand —
    sonst fiele das Produkt still aus dem Auto-Wert-Lauf, sähe aber gepflegt aus."""
    db.add(SealedCatalog(product_id=4600040, region="west", name="Sealed46 Null",
                         image_url="https://tcgplayer-cdn.tcgplayer.com/n_in_1000x1000.jpg",
                         price_usd=Decimal("10.00"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    db.commit()
    created = client.post("/api/v1/sealed", json={
        "name": "Sealed46 Null-Test", "tcgplayer_product_id": 4600040}).json()

    # Feld WEGGELASSEN → Verknüpfung unverändert
    r = client.put(f"/api/v1/sealed/{created['id']}", json={"name": "Sealed46 Null-Test 2"})
    assert r.json()["tcgplayer_product_id"] == 4600040
    assert r.json()["bild_url"]

    # Explizit null → gelöst, Bild geräumt
    r = client.put(f"/api/v1/sealed/{created['id']}", json={"tcgplayer_product_id": None})
    assert r.status_code == 200
    assert r.json()["tcgplayer_product_id"] is None
    assert r.json()["bild_url"] is None
    assert r.json()["wert_aktualisiert"] is None


def test_verwaister_link_blockiert_edits_nicht(db, client):
    """Panel-MINOR: zeigt ein Bestands-Link auf eine fehlende Katalogzeile,
    darf eine reine Namensänderung nicht mit 404 scheitern."""
    p = SealedProduct(name="Sealed46 verwaist", tcgplayer_product_id=999999998)
    db.add(p)
    db.flush()
    pid = p.id
    db.commit()

    r = client.put(f"/api/v1/sealed/{pid}", json={
        "name": "Sealed46 verwaist neu", "tcgplayer_product_id": 999999998})
    assert r.status_code == 200
    assert r.json()["name"] == "Sealed46 verwaist neu"
    assert r.json()["tcgplayer_product_id"] is None   # still gelöst


def test_karte_mit_nicht_numerischer_nummer_ist_kein_sealed(db, monkeypatch):
    """Panel-MAJOR: „TG01/TG30"/„SVP001" sind KARTEN — sie dürfen nicht im
    Sealed-Katalog (und damit im Picker) landen."""
    db.add(TcgdexCatalog(card_id="test46-tg", region="west", set_id="zsv13",
                         set_code="ZQE", local_id="1"))
    db.commit()

    async def groups(category, **kw):
        return [{"groupId": 6, "abbreviation": "E", "name": "ZSV13: Testset"}]

    async def products(category, gid, **kw):
        return [
            {"productId": 4600050, "name": "Trainer Gallery Karte",
             "extendedData": [{"name": "Number", "value": "TG01/TG30"}]},
            {"productId": 4600051, "name": "Promo Karte",
             "extendedData": [{"name": "Number", "value": "SVP001"}]},
            {"productId": 4600052, "name": "Echtes Display"},   # kein Number-Feld
        ]

    async def prices(category, gid, **kw):
        return [{"productId": 4600052, "subTypeName": "Normal", "marketPrice": 99.0}]

    monkeypatch.setattr(tcgcsv, "get_groups", groups)
    monkeypatch.setattr(tcgcsv, "get_products", products)
    monkeypatch.setattr(tcgcsv, "get_prices", prices)

    asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "west"))

    db.expire_all()
    assert db.get(SealedCatalog, 4600050) is None   # TG-Karte
    assert db.get(SealedCatalog, 4600051) is None   # Promo-Karte
    assert db.get(SealedCatalog, 4600052) is not None   # echtes Sealed


def test_katalogsuche_behandelt_wildcards_literal(db, client):
    """Panel-MINOR: %/_ im Suchbegriff sind LITERALE, keine LIKE-Wildcards."""
    db.add(SealedCatalog(product_id=4600060, region="west", name="Sealed46 100% Bundle"))
    db.add(SealedCatalog(product_id=4600061, region="west", name="Sealed46 100x Bundle"))
    db.commit()

    hits = client.get("/api/v1/sealed/catalog", params={"search": "100%"}).json()
    ids = {h["product_id"] for h in hits}
    assert 4600060 in ids and 4600061 not in ids

    # Nacktes % darf nicht den ganzen Katalog liefern
    hits = client.get("/api/v1/sealed/catalog", params={"search": "%"}).json()
    assert all("%" in h["name"] for h in hits)


def test_auto_wert_nur_fuer_verknuepfte(db, monkeypatch):
    async def rate():
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", rate)

    db.add(SealedCatalog(product_id=4600020, region="west", name="Sealed46 ETB",
                         price_usd=Decimal("100.00"),
                         price_usd_updated=datetime.now(timezone.utc).isoformat()))
    linked = SealedProduct(name="Sealed46 verknüpft", tcgplayer_product_id=4600020,
                           wert_eur=Decimal("5.00"))
    manuell = SealedProduct(name="Sealed46 manuell", wert_eur=Decimal("42.00"))
    db.add_all([linked, manuell])
    db.flush()
    lid, mid = linked.id, manuell.id
    db.commit()

    asyncio.run(pricing.refresh_sealed_prices(db))

    db.expire_all()
    assert db.get(SealedProduct, lid).wert_eur == Decimal("90.00")   # 100 × 0.90
    assert db.get(SealedProduct, lid).wert_aktualisiert is not None
    assert db.get(SealedProduct, mid).wert_eur == Decimal("42.00")   # manuell unangetastet


def test_auto_wert_respektiert_frische_guard(db, monkeypatch):
    async def rate():
        return Decimal("0.90")
    monkeypatch.setattr(pricing.fx, "usd_eur_rate", rate)

    db.add(SealedCatalog(product_id=4600030, region="west", name="Sealed46 Alt",
                         price_usd=Decimal("100.00"),
                         price_usd_updated="2020-01-01T00:00:00+00:00"))
    p = SealedProduct(name="Sealed46 stale", tcgplayer_product_id=4600030,
                      wert_eur=Decimal("7.77"))
    db.add(p)
    db.flush()
    pid = p.id
    db.commit()

    asyncio.run(pricing.refresh_sealed_prices(db))

    db.expire_all()
    assert db.get(SealedProduct, pid).wert_eur == Decimal("7.77")   # Stand zu alt → unverändert
