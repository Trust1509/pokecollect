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
