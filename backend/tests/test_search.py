"""
Kurzcode-Suche „PFL 001" (Issue #19): Parser (pur) + Katalog-/Kartensuche.
"""

import pytest

from app.database import SessionLocal
from app.domain.search import parse_kurzcode
from app.models.card import PokemonCard
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog


# ── Parser (pur, ohne DB) ────────────────────────────────────────────────────

def test_parse_kurzcode_basis():
    assert parse_kurzcode("PFL 001") == ("PFL", "1")
    assert parse_kurzcode("obf 125") == ("OBF", "125")
    assert parse_kurzcode("  mew   151  ") == ("MEW", "151")


def test_parse_kurzcode_mit_gesamtnummer():
    assert parse_kurzcode("OBF 125/197") == ("OBF", "125")


def test_parse_kurzcode_kein_treffer():
    assert parse_kurzcode("Pikachu") is None
    assert parse_kurzcode("151") is None
    assert parse_kurzcode("") is None
    assert parse_kurzcode(None) is None
    assert parse_kurzcode("Charizard ex") is None  # ex ist kein Nummernteil


# ── Endpoints (mit DB) ───────────────────────────────────────────────────────

SET_ID = "ksv01"
SET_CODE = "KSV"


@pytest.fixture()
def kurzcode_set(client):
    db = SessionLocal()
    try:
        db.add(PokemonSet(code=SET_CODE, name="Kurzcode-Set", max_card_nr=2,
                          set_id=SET_ID, card_count_official=2))
        for nr in ("1", "2"):
            db.add(TcgdexCatalog(
                card_id=f"{SET_ID}-{nr}", set_id=SET_ID, set_code=SET_CODE,
                set_name="Kurzcode-Set", local_id=nr, local_id_num=int(nr),
                name=f"Codemon {nr}", name_en=f"Codemon {nr}",
            ))
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(PokemonCard).filter(PokemonCard.set_edition.ilike(f"%{SET_CODE}%")).delete(
            synchronize_session=False)
        db.query(TcgdexCatalog).filter(TcgdexCatalog.set_id == SET_ID).delete(
            synchronize_session=False)
        db.query(PokemonSet).filter(PokemonSet.code == SET_CODE).delete(
            synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_catalog_kurzcode_trifft_genau(client, kurzcode_set):
    r = client.get("/api/v1/catalog", params={"q": "KSV 001"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["card_id"] == f"{SET_ID}-1"


def test_catalog_unbekanntes_kuerzel_faellt_auf_volltext(client, kurzcode_set):
    # "ZZZ 1" ist kein Set → Volltextsuche nach "ZZZ 1" → keine Treffer,
    # aber KEIN 500 und nicht fälschlich das Kurzcode-Ergebnis.
    r = client.get("/api/v1/catalog", params={"q": "ZZZ 1"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_cards_kurzcode_trifft(client, kurzcode_set):
    created = client.post("/api/v1/cards", json={
        "kartenname": "Codemon 1", "besessen": True,
        "set_edition": f"Kurzcode-Set ({SET_CODE})", "karten_nr": "001/002",
    })
    assert created.status_code == 201
    cid = created.json()["id"]
    r = client.get("/api/v1/cards", params={"search": "KSV 1"})
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()["items"]]
    assert cid in ids
    client.delete(f"/api/v1/cards/{cid}")
