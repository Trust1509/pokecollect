"""
Katalog-Regionen (v1.6.4): nicht-westliche Karten (JP …) werden mit `region`
getaggt in den Katalog indiziert; der Regionsfilter trennt West/JP. Netzfrei:
tcgdex.get_sets/get_set gemockt.
"""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import tcgcsv
from app.services import tcgdex
from app.services.tcgdex import CardCount, TcgdexSetBrief


def _cleanup(db, *card_ids, set_codes=()):
    for cid in card_ids:
        r = db.get(TcgdexCatalog, cid)
        if r:
            db.delete(r)
    for c in set_codes:
        r = db.get(PokemonSet, c)
        if r:
            db.delete(r)
    db.commit()


def test_index_region_cards_tags_region(client, monkeypatch):
    async def fake_get_sets(region):
        return ([TcgdexSetBrief(id="ZZM3", name="ムニキスゼロ",
                                cardCount=CardCount(official=80, total=117))]
                if region == "ja" else [])

    async def fake_get_set(sid, lang):
        if sid == "ZZM3":
            return {"serie": {"id": "M"}, "cards": [
                {"id": "ZZM3-9", "name": "ビビヨン", "localId": "009",
                 "image": "https://assets.tcgdex.net/ja/M/ZZM3/9"},
            ]}
        return {}

    monkeypatch.setattr(tcgdex, "get_sets", fake_get_sets)
    monkeypatch.setattr(tcgdex, "get_set", fake_get_set)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZM3-9", set_codes=("ZZM3",))
        db.add(PokemonSet(code="ZZM3", set_id="ZZM3", name="Test M3"))
        db.commit()

        rc, _ = asyncio.run(catalog_svc._index_region_cards(db, "ja", {}))
        db.commit()

        row = db.get(TcgdexCatalog, "ZZM3-9")
        assert row is not None
        assert row.region == "ja"
        assert row.name == "ビビヨン"       # Regionssprache
        assert row.set_id == "ZZM3"
        assert row.set_code == "ZZM3"       # aus pokemon_sets
        assert row.local_id == "009"
        assert rc == 1
    finally:
        _cleanup(db, "ZZM3-9", set_codes=("ZZM3",))
        db.close()


def test_index_region_does_not_overwrite_shared_card(client, monkeypatch):
    """Sprachübergreifend geteiltes Set (gleiche card_id in West + JP, z. B. Neo):
    die bereits als „west" katalogisierte Karte darf beim JP-Index NICHT auf
    „ja" umgeschrieben werden — sonst ginge Name/Region der Westkarte verloren."""
    async def fake_get_sets(region):
        return ([TcgdexSetBrief(id="ZZNEO", name="Shared Neo",
                                cardCount=CardCount(official=10, total=10))]
                if region == "ja" else [])

    async def fake_get_set(sid, lang):
        if sid == "ZZNEO":
            return {"serie": {"id": "neo"},
                    "cards": [{"id": "ZZNEO-1", "name": "JA Name", "localId": "1"}]}
        return {}

    monkeypatch.setattr(tcgdex, "get_sets", fake_get_sets)
    monkeypatch.setattr(tcgdex, "get_set", fake_get_set)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZNEO-1", set_codes=("ZZNEO",))
        db.add(TcgdexCatalog(card_id="ZZNEO-1", region="west",
                             name="Western Original", set_id="ZZNEO"))
        db.commit()

        existing = {r.card_id: r for r in db.scalars(select(TcgdexCatalog)).all()}
        rc, _ = asyncio.run(catalog_svc._index_region_cards(db, "ja", existing))
        db.commit()

        row = db.get(TcgdexCatalog, "ZZNEO-1")
        assert row.region == "west", "geteilte Karte darf nicht auf ja überschrieben werden"
        assert row.name == "Western Original"
        assert rc == 0     # nichts neu angelegt
    finally:
        _cleanup(db, "ZZNEO-1", set_codes=("ZZNEO",))
        db.close()


def test_fill_region_image_fallback(client, monkeypatch):
    """JP-Bild-Fallback (Epic #41, Slice 1): bildlose JP-Karte bekommt die
    TCGplayer-CDN-URL + image_source; eine Karte MIT TCGdex-Bild bleibt
    unangetastet."""
    async def fake_groups(cat):
        return ([{"groupId": 999, "name": "ZZM3: Test Nihil"}]
                if cat == tcgcsv.CATEGORY_POKEMON_JP else [])

    async def fake_products(cat, gid):
        if gid == 999:
            return [{
                "productId": 111,
                "name": "Team Aqua's Poochyena",
                "extendedData": [{"name": "Number", "value": "009/080"}],
                "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/product/111_200w.jpg",
            }]
        return []

    async def fake_prices(cat, gid):
        return ([{"productId": 111, "subTypeName": "Normal", "marketPrice": 3.87}]
                if gid == 999 else [])

    monkeypatch.setattr(tcgcsv, "get_groups", fake_groups)
    monkeypatch.setattr(tcgcsv, "get_products", fake_products)
    monkeypatch.setattr(tcgcsv, "get_prices", fake_prices)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZM3-9-nofb", "ZZM3-9-has")
        db.add(TcgdexCatalog(card_id="ZZM3-9-nofb", region="ja", set_code="ZZM3",
                             local_id="009", name="Ohne Bild", image_url=None))
        db.add(TcgdexCatalog(card_id="ZZM3-9-has", region="ja", set_code="ZZM3",
                             local_id="009", name="Mit TCGdex-Bild",
                             image_url="https://assets.tcgdex.net/ja/M/M3/9/high.webp"))
        db.commit()

        res = asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "ja"))
        db.commit()

        nofb = db.get(TcgdexCatalog, "ZZM3-9-nofb")
        assert nofb.image_url == "https://tcgplayer-cdn.tcgplayer.com/product/111_in_1000x1000.jpg"
        assert nofb.image_source == "tcgplayer"
        assert nofb.name_en == "Team Aqua's Poochyena"   # EN-Name aus TCGplayer
        assert float(nofb.price_usd) == 3.87             # $-Preis aus TCGCSV
        assert nofb.price_usd_updated                    # Datenstand gesetzt

        has = db.get(TcgdexCatalog, "ZZM3-9-has")
        assert "assets.tcgdex.net" in has.image_url   # TCGdex-Bild unberührt
        assert has.image_source is None
        assert res["images"] >= 1 and res["prices"] >= 1
    finally:
        _cleanup(db, "ZZM3-9-nofb", "ZZM3-9-has")
        db.close()


def test_fill_region_image_fallback_ambiguous_code(client, monkeypatch):
    """Zwei TCGplayer-Gruppen mit demselben Set-Code sind mehrdeutig → es darf
    KEIN Bild gesetzt werden (lieber keins als eins aus dem falschen Set)."""
    async def fake_groups(cat):
        return ([{"groupId": 1, "name": "ZZDUP: Erste"},
                 {"groupId": 2, "name": "ZZDUP: Zweite"}]
                if cat == tcgcsv.CATEGORY_POKEMON_JP else [])

    async def fake_products(cat, gid):
        return [{
            "extendedData": [{"name": "Number", "value": "009/080"}],
            "imageUrl": "https://tcgplayer-cdn.tcgplayer.com/product/1_200w.jpg",
        }]

    async def fake_prices(cat, gid):
        return []

    monkeypatch.setattr(tcgcsv, "get_groups", fake_groups)
    monkeypatch.setattr(tcgcsv, "get_products", fake_products)
    monkeypatch.setattr(tcgcsv, "get_prices", fake_prices)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZDUP-9")
        db.add(TcgdexCatalog(card_id="ZZDUP-9", region="ja", set_code="ZZDUP",
                             local_id="009", name="Mehrdeutig", image_url=None))
        db.commit()

        res = asyncio.run(catalog_svc.fill_region_from_tcgplayer(db, "ja"))
        db.commit()

        row = db.get(TcgdexCatalog, "ZZDUP-9")
        assert row.image_url is None       # mehrdeutig → kein Bild
        assert row.image_source is None
        assert res["images"] == 0 and res["prices"] == 0
    finally:
        _cleanup(db, "ZZDUP-9")
        db.close()


def test_index_region_clears_stale_tcgplayer_source(client, monkeypatch):
    """Cross-Run (Panel-Fund Blind-Erststimme): Karte hatte einen TCGplayer-
    Fallback (image_source='tcgplayer', TCGdex-Basisbild image=NULL). Liefert
    TCGdex später ein Bild, wird image_url auf TCGdex umgestellt UND das stale
    'tcgplayer'-Label geräumt — sonst zeigt die Provenienz (Slice 6) falsch."""
    async def fake_get_sets(region):
        return ([TcgdexSetBrief(id="ZZTP", name="TP Set",
                                cardCount=CardCount(official=10, total=10))]
                if region == "ja" else [])

    async def fake_get_set(sid, lang):
        if sid == "ZZTP":
            return {"serie": {"id": "M"}, "cards": [
                {"id": "ZZTP-9", "name": "JA Name", "localId": "009",
                 "image": "https://assets.tcgdex.net/ja/M/ZZTP/9"},
            ]}
        return {}

    monkeypatch.setattr(tcgdex, "get_sets", fake_get_sets)
    monkeypatch.setattr(tcgdex, "get_set", fake_get_set)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZTP-9", set_codes=("ZZTP",))
        db.add(PokemonSet(code="ZZTP", set_id="ZZTP", name="TP Set"))
        db.add(TcgdexCatalog(
            card_id="ZZTP-9", region="ja", set_id="ZZTP", image=None,
            image_url="https://tcgplayer-cdn.tcgplayer.com/product/1_in_1000x1000.jpg",
            image_source="tcgplayer"))
        db.commit()

        existing = {r.card_id: r for r in db.scalars(select(TcgdexCatalog)).all()}
        asyncio.run(catalog_svc._index_region_cards(db, "ja", existing))
        db.commit()

        row = db.get(TcgdexCatalog, "ZZTP-9")
        assert "assets.tcgdex.net" in row.image_url   # TCGdex übernimmt
        assert row.image_source is None               # stale 'tcgplayer' geräumt
    finally:
        _cleanup(db, "ZZTP-9", set_codes=("ZZTP",))
        db.close()


def test_catalog_region_filter(client):
    db = SessionLocal()
    try:
        _cleanup(db, "ZZW-1", "ZZJ-1")
        db.add(TcgdexCatalog(card_id="ZZW-1", region="west", name="West Card", set_id="zzw"))
        db.add(TcgdexCatalog(card_id="ZZJ-1", region="ja", name="JP Card", set_id="ZZJ"))
        db.commit()

        def _ids(region):
            r = client.get("/api/v1/catalog", params={"region": region, "limit": 500})
            assert r.status_code == 200
            return r.json()["items"]

        ja = _ids("ja")
        ja_ids = {i["card_id"] for i in ja}
        assert "ZZJ-1" in ja_ids and "ZZW-1" not in ja_ids
        assert next(i for i in ja if i["card_id"] == "ZZJ-1")["region"] == "ja"

        west_ids = {i["card_id"] for i in _ids("west")}
        assert "ZZW-1" in west_ids and "ZZJ-1" not in west_ids
    finally:
        _cleanup(db, "ZZW-1", "ZZJ-1")
        db.close()
