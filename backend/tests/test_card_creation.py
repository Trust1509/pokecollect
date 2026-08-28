"""
Domain-Service create_owned_card (Issue #4): Platzhalter-Adoption und
im_pokedex-Exklusivität über die vereinheitlichten Anlege-Pfade
scan/commit und Katalog-Übernahme.
"""

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog

# Mehrfachlauf-Fixture (#79): Alle Tests in dieser Datei legen Karten mit
# einer festen `pokedex_nr` aus dem 99xx-Bereich per POST an, ohne
# aufzuräumen. Ohne dieses Aufräumen trifft die Platzhalter-Adoption in
# create_owned_card beim zweiten Suite-Lauf auf mehr als eine offene Zeile
# derselben Nummer, und len(cards)==1-Zusicherungen scheitern an der
# Dublette aus dem Erstlauf. Die Nummern sind ausschließlich in dieser Datei
# verwendet (grep über backend/tests bestätigt keine Kollision mit anderen
# Testdateien).
_TEST_POKEDEX_NRS = (9901, 9902, 9903)


@pytest.fixture(autouse=True)
def _pokedex_platzhalter_aufraeumen():
    """Räumt nach jedem Test alle Karten der o.g. Nummern weg — auch den
    Platzhalter, den der Server selbst beim Löschen der letzten Karte einer
    Art neu anlegt (cards.py::delete_card): Der Filter auf `pokedex_nr`
    erfasst beide Formen unabhängig vom `besessen`-Stand."""
    yield
    db = SessionLocal()
    try:
        db.query(PokemonCard).filter(
            PokemonCard.pokedex_nr.in_(_TEST_POKEDEX_NRS)
        ).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def _placeholder(client, name: str, nr: int) -> int:
    r = client.post(
        "/api/v1/cards",
        json={"kartenname": name, "pokedex_nr": nr, "besessen": False},
    )
    assert r.status_code == 201
    return r.json()["id"]


def _cards_for_nr(client, nr: int) -> list[dict]:
    r = client.get("/api/v1/cards", params={"pokedex_nr": nr, "limit": 100})
    assert r.status_code == 200
    return r.json()["items"]


def test_scan_commit_adopts_placeholder(client):
    """scan/commit übernimmt den Platzhalter statt ein Duplikat zu erzeugen."""
    ph_id = _placeholder(client, "Scanmon", 9901)

    r = client.post(
        "/api/v1/scan/commit",
        json={"target": "pokedex", "items": [{"kartenname": "Scanmon", "pokedex_nr": 9901}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["created"] == 1
    assert body["card_ids"] == [ph_id], "Platzhalter muss adoptiert werden"

    cards = _cards_for_nr(client, 9901)
    assert len(cards) == 1
    assert cards[0]["besessen"] is True
    assert cards[0]["im_pokedex"] is True


def test_scan_commit_pokedex_exclusivity_in_batch(client):
    """Zwei Karten derselben Nr. im Batch → genau ein Pokédex-Vertreter."""
    r = client.post(
        "/api/v1/scan/commit",
        json={
            "target": "pokedex",
            "items": [
                {"kartenname": "Batchmon A", "pokedex_nr": 9902},
                {"kartenname": "Batchmon B", "pokedex_nr": 9902},
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["created"] == 2

    cards = _cards_for_nr(client, 9902)
    flagged = [c for c in cards if c["im_pokedex"]]
    assert len(flagged) == 1, "im_pokedex muss exklusiv je Pokédex-Nr. sein"


@pytest.fixture()
def catalog_rows():
    """Zwei angereicherte Katalog-Einträge derselben Spezies (kein Netz-Fetch)."""
    ids = ["test-9903-1", "test-9903-2"]
    db = SessionLocal()
    try:
        for i, cid in enumerate(ids, start=1):
            db.add(TcgdexCatalog(
                card_id=cid,
                set_id="sv03",
                set_code="OBF",
                set_name="Obsidianflammen",
                local_id=str(40 + i),
                name="Katalogmon",
                name_en="Catalogmon",
                dex_id=9903,
                rarity="Common",
                enriched=True,
            ))
        db.commit()
    finally:
        db.close()

    yield ids

    db = SessionLocal()
    try:
        for cid in ids:
            row = db.get(TcgdexCatalog, cid)
            if row:
                db.delete(row)
        db.commit()
    finally:
        db.close()


def test_catalog_to_collection_adopts_and_flags(client, catalog_rows):
    """Katalog-Übernahme adoptiert den Platzhalter + wahrt die Exklusivität."""
    ph_id = _placeholder(client, "Katalogmon", 9903)

    coll = client.post("/api/v1/collections", json={"name": "Adoptions-Binder"})
    assert coll.status_code == 201
    coll_id = coll.json()["id"]

    r = client.post(f"/api/v1/catalog/{catalog_rows[0]}/collection", params={"collection_id": coll_id})
    assert r.status_code == 200, r.text
    first_id = r.json()["card_id"]
    assert first_id == ph_id, "Platzhalter muss adoptiert werden"

    cards = _cards_for_nr(client, 9903)
    assert len(cards) == 1
    assert cards[0]["besessen"] is True
    assert cards[0]["im_pokedex"] is True

    # Zweite Karte derselben Spezies: kein Platzhalter mehr da → neue Zeile,
    # aber der Pokédex-Vertreter bleibt exklusiv bei der ersten.
    r = client.post(f"/api/v1/catalog/{catalog_rows[1]}/collection", params={"collection_id": coll_id})
    assert r.status_code == 200, r.text
    second_id = r.json()["card_id"]
    assert second_id != first_id

    cards = _cards_for_nr(client, 9903)
    assert len(cards) == 2
    flagged = [c for c in cards if c["im_pokedex"]]
    assert [c["id"] for c in flagged] == [first_id]

    client.delete(f"/api/v1/collections/{coll_id}")
