"""
Set-Sammlungen / Sammelziele (Issue #16): Prefill aus dem Katalog,
Fortschritts-Matching (Folierung/Sprache/Fallback), Kuratieren und
Wunschlisten-Übergabe. Kein Netz — Katalog-Zeilen werden per ORM geseedet.
"""

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.collection import Collection, CollectionSoll
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog

SET_ID = "tsg01"
SET_CODE = "TSG"

# (card_id, local_id, reverse-fähig, holo-fähig) — Nr. 3 ist die "Secret Rare"
_CATALOG = [
    ("tsg01-1", "1", True, False),
    ("tsg01-2", "2", False, True),
    ("tsg01-3", "3", False, True),
]


@pytest.fixture()
def goal_set(client):
    """Test-Set (offiziell 2 Karten, total 3) + Katalog-Zeilen, ohne Netz."""
    db = SessionLocal()
    try:
        db.add(PokemonSet(
            code=SET_CODE, name="Test-Sammelziel", max_card_nr=2,
            set_id=SET_ID, card_count_official=2, card_count_total=3,
        ))
        for cid, local_id, rev, holo in _CATALOG:
            db.add(TcgdexCatalog(
                card_id=cid, set_id=SET_ID, set_code=SET_CODE,
                set_name="Test-Sammelziel", local_id=local_id,
                local_id_num=int(local_id), name=f"Zielmon {local_id}",
                name_en=f"Goalmon {local_id}", rarity="Common",
                image_url=f"https://assets.tcgdex.net/{SET_ID}/{local_id}/high.webp",
                variants_normal=True, variants_reverse=rev, variants_holo=holo,
                enriched=True,
            ))
        db.commit()
    finally:
        db.close()

    yield

    db = SessionLocal()
    try:
        # Reihenfolge: Karten/Soll-Slots zuerst, dann Katalog + Set
        db.query(PokemonCard).filter(
            (PokemonCard.set_id == SET_ID)
            | PokemonCard.tcgdex_card_id.in_([c[0] for c in _CATALOG])
            | PokemonCard.kartenname.ilike("Zielmon%")
        ).delete(synchronize_session=False)
        colls = db.query(Collection).filter(Collection.ziel_set_id == SET_ID).all()
        for coll in colls:
            db.query(CollectionSoll).filter(CollectionSoll.collection_id == coll.id).delete(
                synchronize_session=False
            )
            db.delete(coll)
        db.query(TcgdexCatalog).filter(TcgdexCatalog.set_id == SET_ID).delete(
            synchronize_session=False
        )
        row = db.get(PokemonSet, SET_CODE)
        if row:
            db.delete(row)
        db.commit()
    finally:
        db.close()


def _create_goal(client, **overrides) -> dict:
    payload = {"name": "TSG-Ziel", "typ": "set_ziel", "ziel_set_id": SET_ID}
    payload.update(overrides)
    r = client.post("/api/v1/collections", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def _soll(client, coll_id: int) -> list[dict]:
    r = client.get(f"/api/v1/collections/{coll_id}/soll")
    assert r.status_code == 200, r.text
    return r.json()


def _add_owned(db, **fields) -> int:
    card = PokemonCard(kartenname="Zielmon", besessen=True, **fields)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card.id


# ── Prefill ──────────────────────────────────────────────────────────────────

def test_prefill_official_vs_master(client, goal_set):
    """Standard: bis zur offiziellen Nummer; Master-Set: alle Katalog-Karten."""
    official = _create_goal(client)
    slots = _soll(client, official["id"])
    assert [s["tcgdex_card_id"] for s in slots] == ["tsg01-1", "tsg01-2"]
    assert official["fortschritt"] == {"erfuellt": 0, "soll": 2}
    # Katalog-Bild als Platzhalter für fehlende Slots
    assert all(s["image_url"] for s in slots)
    assert all(s["erfuellt"] is False for s in slots)

    master = _create_goal(client, name="TSG-Master", ziel_master_set=True)
    assert [s["tcgdex_card_id"] for s in _soll(client, master["id"])] == [
        "tsg01-1", "tsg01-2", "tsg01-3",
    ]


def test_prefill_folierung_vorschlag(client, goal_set):
    """Folierungs-Regel filtert den Startvorschlag über die variants_*-Flags."""
    reverse = _create_goal(client, name="TSG-Reverse", ziel_folierung="Reverse Holo")
    assert [s["tcgdex_card_id"] for s in _soll(client, reverse["id"])] == ["tsg01-1"]

    holo = _create_goal(client, name="TSG-Holo", ziel_folierung="Holo", ziel_master_set=True)
    assert [s["tcgdex_card_id"] for s in _soll(client, holo["id"])] == ["tsg01-2", "tsg01-3"]


def test_set_ziel_braucht_set_id(client, goal_set):
    r = client.post("/api/v1/collections", json={"name": "kaputt", "typ": "set_ziel"})
    assert r.status_code == 400


# ── Fortschritt / Matching ───────────────────────────────────────────────────

def test_progress_matching_folierung_sprache(client, goal_set):
    coll = _create_goal(client, name="TSG-RH", ziel_folierung="Reverse Holo", ziel_sprache="DE",
                        ziel_master_set=True)
    # Regel filtert Prefill auf tsg01-1; zweiten Slot manuell dazu kuratieren
    r = client.post(f"/api/v1/collections/{coll['id']}/soll",
                    json={"tcgdex_card_id": "tsg01-2"})
    assert r.status_code == 201, r.text

    db = SessionLocal()
    try:
        # Falsche Folierung → zählt nicht
        _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Holo", sprache="DE")
        r = client.get(f"/api/v1/collections/{coll['id']}/progress")
        assert r.json() == {"erfuellt": 0, "soll": 2}

        # Passende Folierung, falsche Sprache → zählt nicht
        wrong_lang = _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Reverse Holo", sprache="EN")
        assert client.get(f"/api/v1/collections/{coll['id']}/progress").json()["erfuellt"] == 0

        # Passende Folierung + Sprache → erfüllt
        match_id = _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Reverse Holo", sprache="DE")
        slots = _soll(client, coll["id"])
        slot1 = next(s for s in slots if s["tcgdex_card_id"] == "tsg01-1")
        assert slot1["erfuellt"] is True
        assert slot1["karte_id"] == match_id
        assert slot1["karte"]["id"] == match_id
        assert wrong_lang != match_id
        assert client.get(f"/api/v1/collections/{coll['id']}/progress").json() == {
            "erfuellt": 1, "soll": 2,
        }
    finally:
        db.close()


def test_progress_null_ist_egal(client, goal_set):
    """Ohne Folierungs-/Sprach-Regel zählt jede besessene Karte der Nummer."""
    coll = _create_goal(client, name="TSG-Egal")
    db = SessionLocal()
    try:
        _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Bubble Holo", sprache="JP")
        assert client.get(f"/api/v1/collections/{coll['id']}/progress").json() == {
            "erfuellt": 1, "soll": 2,
        }
    finally:
        db.close()


def test_progress_soll_folierung_override(client, goal_set):
    """Slot-Folierung übersteuert die Ziel-Regel (NULL am Slot = Regel gilt)."""
    coll = _create_goal(client, name="TSG-Override")
    slots = _soll(client, coll["id"])
    slot1 = next(s for s in slots if s["tcgdex_card_id"] == "tsg01-1")
    r = client.put(
        f"/api/v1/collections/{coll['id']}/soll/{slot1['id']}",
        json={"soll_folierung": "Holo"},
    )
    assert r.status_code == 200, r.text
    db = SessionLocal()
    try:
        _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Normal")
        slots = _soll(client, coll["id"])
        assert next(s for s in slots if s["tcgdex_card_id"] == "tsg01-1")["erfuellt"] is False
        _add_owned(db, tcgdex_card_id="tsg01-1", folierung="Holo")
        slots = _soll(client, coll["id"])
        assert next(s for s in slots if s["tcgdex_card_id"] == "tsg01-1")["erfuellt"] is True
    finally:
        db.close()


def test_progress_fallback_set_und_nummer(client, goal_set):
    """Karten ohne tcgdex_card_id matchen über set_id bzw. Set-Kürzel + Kartennummer."""
    coll = _create_goal(client, name="TSG-Fallback")
    db = SessionLocal()
    try:
        # Fallback über stabile set_id + "NNN/NNN"-Nummer
        _add_owned(db, set_id=SET_ID, karten_nr="001/002")
        # Fallback über Set-Kürzel im set_edition-Feld + nackte Nummer
        _add_owned(db, set_edition=f"Test-Sammelziel ({SET_CODE})", karten_nr="2")
        assert client.get(f"/api/v1/collections/{coll['id']}/progress").json() == {
            "erfuellt": 2, "soll": 2,
        }
    finally:
        db.close()


def test_mehrfach_zaehlung_ueber_ziele(client, goal_set):
    """Eine Karte erfüllt mehrere Ziele gleichzeitig — keine Exklusiv-Zuordnung."""
    a = _create_goal(client, name="TSG-A")
    b = _create_goal(client, name="TSG-B")
    db = SessionLocal()
    try:
        _add_owned(db, tcgdex_card_id="tsg01-1")
        for coll in (a, b):
            assert client.get(f"/api/v1/collections/{coll['id']}/progress").json()["erfuellt"] == 1
    finally:
        db.close()


# ── Kuratieren ───────────────────────────────────────────────────────────────

def test_kuratieren_add_update_remove(client, goal_set):
    coll = _create_goal(client)
    assert len(_soll(client, coll["id"])) == 2

    # Secret Rare mit Slot-Folierung dazu kuratieren
    r = client.post(
        f"/api/v1/collections/{coll['id']}/soll",
        json={"tcgdex_card_id": "tsg01-3", "soll_folierung": "Holo"},
    )
    assert r.status_code == 201, r.text
    new_slot = r.json()
    assert new_slot["soll_folierung"] == "Holo"
    assert new_slot["position"] == 2  # ans Ende
    assert len(_soll(client, coll["id"])) == 3

    # Unbekannte Katalog-Karte → 404
    r = client.post(f"/api/v1/collections/{coll['id']}/soll",
                    json={"tcgdex_card_id": "gibtsnicht-99"})
    assert r.status_code == 404

    # Folierung zurück auf Regel (null) + Position ändern
    r = client.put(
        f"/api/v1/collections/{coll['id']}/soll/{new_slot['id']}",
        json={"soll_folierung": None, "position": 10},
    )
    assert r.status_code == 200, r.text
    assert r.json()["soll_folierung"] is None
    assert r.json()["position"] == 10

    # Slot entfernen
    r = client.delete(f"/api/v1/collections/{coll['id']}/soll/{new_slot['id']}")
    assert r.status_code == 204
    assert len(_soll(client, coll["id"])) == 2

    # Fremder/unbekannter Slot → 404
    r = client.delete(f"/api/v1/collections/{coll['id']}/soll/{new_slot['id']}")
    assert r.status_code == 404


def test_soll_zur_wunschliste(client, goal_set):
    """Fehlender Slot → Wunschliste über den bestehenden Katalog-Pfad."""
    coll = _create_goal(client)
    slot = _soll(client, coll["id"])[0]
    r = client.post(f"/api/v1/collections/{coll['id']}/soll/{slot['id']}/wishlist")
    assert r.status_code == 200, r.text
    card_id = r.json()["card_id"]

    r = client.get(f"/api/v1/cards/{card_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["wunschliste"] is True
    assert body["besessen"] is False
    assert body["tcgdex_card_id"] == slot["tcgdex_card_id"]


def test_freie_sammlung_unveraendert(client):
    """Freie Sammlungen bleiben unverändert: typ-Default, kein Fortschritt."""
    r = client.post("/api/v1/collections", json={"name": "Freier Binder"})
    assert r.status_code == 201
    body = r.json()
    assert body["typ"] == "frei"
    assert body["fortschritt"] is None
    client.delete(f"/api/v1/collections/{body['id']}")
