"""
Katalog-Übernahme mit Formularfeldern (#28) + Einstellungs-Defaults statt
hart „DE" (#27).

- Mitgegebene Felder (Zustand/Sprache/Folierung/1st Edition) persistieren auf
  beiden Pfaden (Wunschliste + Sammlung/create_owned_card).
- Ohne Felder greifen die Einstellungs-Defaults (default_language/
  default_condition) — auch auf dem body-losen Schnell-/Bulk-Pfad (#23).
"""

import pytest

from app.database import SessionLocal
from app.models.tcgdex_catalog import TcgdexCatalog


@pytest.fixture()
def catalog_card():
    """Angereicherter Katalog-Eintrag OHNE Pokédex-Nr. (keine Adoption, kein
    Netz-Fetch): jede Übernahme legt eine frische Karte an."""
    cid = "test-add-0001"
    db = SessionLocal()
    try:
        db.add(TcgdexCatalog(
            card_id=cid,
            set_id="sv03",
            set_code="OBF",
            set_name="Obsidianflammen",
            local_id="7",
            name="Feldmon",
            name_en="Fieldmon",
            rarity="Common",
            enriched=True,
        ))
        db.commit()
    finally:
        db.close()
    yield cid
    db = SessionLocal()
    try:
        row = db.get(TcgdexCatalog, cid)
        if row:
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _get_card(client, card_id: int) -> dict:
    r = client.get(f"/api/v1/cards/{card_id}")
    assert r.status_code == 200, r.text
    return r.json()


def test_wishlist_add_persists_fields(client, catalog_card):
    """#28: mitgegebene Felder landen an der Wunschlisten-Karte."""
    r = client.post(
        f"/api/v1/catalog/{catalog_card}/wishlist",
        json={"sprache": "EN", "zustand": "Near Mint", "folierung": "Holo", "erste_edition": True},
    )
    assert r.status_code == 200, r.text
    cid = r.json()["card_id"]
    try:
        card = _get_card(client, cid)
        assert card["sprache"] == "EN"
        assert card["zustand"] == "Near Mint"
        assert card["folierung"] == "Holo"
        assert card["erste_edition"] is True
        assert card["wunschliste"] is True
        assert card["besessen"] is False
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def test_collection_add_persists_fields(client, catalog_card):
    """#28: Felder greifen auch beim Sammlung-Add (create_owned_card-Pfad)."""
    coll = client.post("/api/v1/collections", json={"name": "Feld-Binder"})
    assert coll.status_code == 201
    coll_id = coll.json()["id"]
    r = client.post(
        f"/api/v1/catalog/{catalog_card}/collection",
        params={"collection_id": coll_id},
        json={"sprache": "JP", "zustand": "Mint", "folierung": "Reverse Holo", "erste_edition": True},
    )
    assert r.status_code == 200, r.text
    cid = r.json()["card_id"]
    try:
        card = _get_card(client, cid)
        assert card["sprache"] == "JP"
        assert card["zustand"] == "Mint"
        assert card["folierung"] == "Reverse Holo"
        assert card["erste_edition"] is True
        assert card["besessen"] is True
    finally:
        client.delete(f"/api/v1/cards/{cid}")
        client.delete(f"/api/v1/collections/{coll_id}")


def test_defaults_apply_when_fields_missing(client, catalog_card):
    """#27: ohne Felder greifen die Einstellungs-Defaults, nicht hart „DE"."""
    r = client.put("/api/v1/settings", json={"default_language": "EN", "default_condition": "Near Mint"})
    assert r.status_code == 200
    try:
        r = client.post(f"/api/v1/catalog/{catalog_card}/wishlist", json={})
        assert r.status_code == 200, r.text
        cid = r.json()["card_id"]
        try:
            card = _get_card(client, cid)
            assert card["sprache"] == "EN", "Default-Sprache muss greifen (nicht hart DE)"
            assert card["zustand"] == "Near Mint", "Default-Zustand muss greifen"
        finally:
            client.delete(f"/api/v1/cards/{cid}")
    finally:
        # Defaults zurücksetzen, damit andere Tests nicht betroffen sind.
        client.put("/api/v1/settings", json={"default_language": "DE", "default_condition": ""})


def test_defaults_apply_for_bodyless_bulk_add(client, catalog_card):
    """#27 auch für den Schnell-/Bulk-Add (#23) ohne Body — serverseitige Defaults."""
    r = client.put("/api/v1/settings", json={"default_language": "FR"})
    assert r.status_code == 200
    try:
        # Ganz ohne Body — genau wie der Schnell-Add es aufruft.
        r = client.post(f"/api/v1/catalog/{catalog_card}/wishlist")
        assert r.status_code == 200, r.text
        cid = r.json()["card_id"]
        try:
            assert _get_card(client, cid)["sprache"] == "FR"
        finally:
            client.delete(f"/api/v1/cards/{cid}")
    finally:
        client.put("/api/v1/settings", json={"default_language": "DE"})
