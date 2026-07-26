"""
Issue #30: Binder-Positionen sind Slot-Indizes (0-basiert, Lücken erlaubt).
Neue Karten füllen den nächsten WIRKLICH freien Slot, ohne bestehende Karten
zu verschieben — beim Hinzufügen wird NICHT kompaktiert.
"""

from app.database import SessionLocal
from app.services.collection_slots import next_free_position


def _owned(client, name: str) -> int:
    r = client.post("/api/v1/cards", json={"kartenname": name, "besessen": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _positions(client, cid: int) -> dict[int, object]:
    r = client.get(f"/api/v1/collections/{cid}/cards")
    assert r.status_code == 200, r.text
    return {c["id"]: c["position"] for c in r.json()}


def test_add_card_does_not_shift_existing_binder_slots(client):
    """Zwei Karten in Slot 0 zweier Seiten; Hinzufügen darf sie nicht verschieben."""
    coll = client.post("/api/v1/collections", json={"name": "Binder #30"})
    assert coll.status_code == 201
    cid = coll.json()["id"]

    a = _owned(client, "Slot0-Seite1")
    b = _owned(client, "Slot0-Seite2")

    assert client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": a}).status_code == 201
    assert client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": b}).status_code == 201
    # B gezielt auf Slot 9 legen (Seite 2, Slot 0 bei 3x3)
    assert client.put(f"/api/v1/collections/{cid}/cards/{b}/slot", json={"slot": 9}).status_code == 204

    before = _positions(client, cid)
    assert before[a] == 0 and before[b] == 9, "Ausgangslage: A@0, B@9"

    # Neue Karte hinzufügen
    c = _owned(client, "Neuzugang")
    assert client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": c}).status_code == 201

    after = _positions(client, cid)
    assert after[a] == 0, "Karte auf Seite 1 darf sich nicht bewegen"
    assert after[b] == 9, "Karte auf Seite 2 darf nicht nach Seite 1 rutschen (#30)"
    # Neue Karte im nächsten wirklich freien Slot (erste Lücke = 1), nie None
    assert after[c] == 1

    client.delete(f"/api/v1/collections/{cid}")


def test_next_free_position_fills_first_gap(client):
    """next_free_position gibt den kleinsten freien Slot (füllt Lücken vorne)."""
    coll = client.post("/api/v1/collections", json={"name": "Lueckentest"})
    cid = coll.json()["id"]
    a = _owned(client, "L-A")
    b = _owned(client, "L-B")
    # A@0, B@2 → Slot 1 bleibt frei
    client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": a})
    client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": b})
    client.put(f"/api/v1/collections/{cid}/cards/{b}/slot", json={"slot": 2})

    db = SessionLocal()
    try:
        assert next_free_position(db, cid) == 1
    finally:
        db.close()

    client.delete(f"/api/v1/collections/{cid}")
