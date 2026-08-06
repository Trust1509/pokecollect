"""
Katalog-Detail-Endpoint (angereichertes Popup, Epic #41): GET
/catalog/{card_id}/detail merged die gespeicherte Zeile mit einem LIVE-Abruf bei
TCGdex (fehlende Felder auffüllen + Preise €/$). Netzfrei: tcgdex.get_card gemockt.
"""

from app.database import SessionLocal
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import tcgdex
from app.services.tcgdex import CardMarketPricing, Pricing, TcgdexCard, Variants


def _cleanup(db, *ids):
    for cid in ids:
        r = db.get(TcgdexCatalog, cid)
        if r:
            db.delete(r)
    db.commit()


def test_catalog_prices_helper():
    pr = Pricing(
        cardmarket=CardMarketPricing(avg=1.18, low=0.7, trend=1.5, updated="2026-08-06"),
        tcgplayer={"unit": "USD", "normal": {"marketPrice": 0.5},
                   "reverse-holofoil": {"marketPrice": 2.0}},
    )
    out = catalog_svc.catalog_prices(pr)
    assert out["eur"] == 1.18 and out["eur_low"] == 0.7 and out["eur_trend"] == 1.5
    assert out["usd"] == 0.5   # bevorzugt die Normal-Variante
    # tcgplayer nur reverse-holofoil → dessen Marktpreis
    only_rev = Pricing(tcgplayer={"reverse-holofoil": {"marketPrice": 2.0}})
    assert catalog_svc.catalog_prices(only_rev)["usd"] == 2.0
    # leeres/fehlendes tcgplayer bzw. pricing → None (JP-Karten)
    assert catalog_svc.catalog_prices(Pricing(tcgplayer={}))["usd"] is None
    assert catalog_svc.catalog_prices(None)["eur"] is None
    # Holo-only-Karte: avg/low/trend leer, nur Holo-Felder → Fallback (Panel-Fund Codex)
    holo = Pricing(cardmarket=CardMarketPricing.model_validate(
        {"avg-holo": 9.5, "low-holo": 6.0, "trend-holo": 11.0}))
    out_holo = catalog_svc.catalog_prices(holo)
    assert out_holo["eur"] == 9.5 and out_holo["eur_low"] == 6.0 and out_holo["eur_trend"] == 11.0


def test_catalog_detail_merges_live(client, monkeypatch):
    async def fake_get_card(card_id, lang="en"):
        return TcgdexCard(
            id=card_id, name="X", rarity="Common", illustrator="Kouki Saitou",
            category="Pokemon", dexId=[261],
            variants=Variants(normal=True, reverse=False, holo=False, firstEdition=False),
            pricing=Pricing(
                cardmarket=CardMarketPricing(avg=1.18, low=0.7, trend=1.5, updated="2026-08-06"),
                tcgplayer={},   # JP-Karte: $ leer
            ),
        )
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    db = SessionLocal()
    try:
        _cleanup(db, "CP1-016")
        db.add(TcgdexCatalog(card_id="CP1-016", region="ja", set_code="CP1",
                             set_name="Double Crisis", local_id="016",
                             name="アクア団のポチエナ", dex_id=None, rarity=None,
                             illustrator=None, enriched=False))
        db.commit()

        r = client.get("/api/v1/catalog/CP1-016/detail")
        assert r.status_code == 200
        j = r.json()
        assert j["dex_id"] == 261                 # aus Live-Abruf aufgefüllt
        assert j["rarity"] == "Common"
        assert j["illustrator"] == "Kouki Saitou"
        assert j["category"] == "Pokemon"
        assert j["variants_normal"] is True
        assert j["price_eur"] == 1.18
        assert j["price_usd"] is None             # JP: $ leer, sauber weggelassen
    finally:
        _cleanup(db, "CP1-016")
        db.close()


def test_catalog_detail_404(client):
    assert client.get("/api/v1/catalog/DOES-NOT-EXIST/detail").status_code == 404


def test_catalog_detail_survives_tcgdex_failure(client, monkeypatch):
    async def boom(card_id, lang="en"):
        raise RuntimeError("TCGdex down")
    monkeypatch.setattr(tcgdex, "get_card", boom)

    db = SessionLocal()
    try:
        _cleanup(db, "ZZF-1")
        db.add(TcgdexCatalog(card_id="ZZF-1", region="ja", set_code="ZZF",
                             local_id="1", name="Test", enriched=False))
        db.commit()

        r = client.get("/api/v1/catalog/ZZF-1/detail")
        assert r.status_code == 200               # externe Quelle darf das Popup nicht kippen
        j = r.json()
        assert j["card_id"] == "ZZF-1"
        assert j["price_eur"] is None             # kein Live-Abruf → keine Preise
    finally:
        _cleanup(db, "ZZF-1")
        db.close()
