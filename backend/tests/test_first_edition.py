"""
First Edition (#25): eigenes Ja/Nein-Feld `erste_edition` an der Karte.
- persistiert bei Anlage/Update, Default false
- eigener Query-Filter erste_edition greift (nur 1st-Edition-Karten)
"""


def _owned(client, name: str, **extra) -> int:
    """Besessene Karte OHNE Pokédex-Nr. — Delete räumt sie restlos ab
    (kein Platzhalter wird nachgelegt)."""
    r = client.post("/api/v1/cards", json={"kartenname": name, "besessen": True, **extra})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_erste_edition_defaults_false(client):
    cid = _owned(client, "Editionslos")
    try:
        assert client.get(f"/api/v1/cards/{cid}").json()["erste_edition"] is False
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def test_erste_edition_persistiert_und_togglet(client):
    cid = _owned(client, "Erstauflagemon", erste_edition=True)
    try:
        assert client.get(f"/api/v1/cards/{cid}").json()["erste_edition"] is True
        # zurücksetzen per Update
        r = client.put(f"/api/v1/cards/{cid}", json={"erste_edition": False})
        assert r.status_code == 200
        assert r.json()["erste_edition"] is False
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def test_filter_erste_edition(client):
    ja = _owned(client, "1stEd-Ja", erste_edition=True)
    nein = _owned(client, "1stEd-Nein", erste_edition=False)
    try:
        only = client.get("/api/v1/cards", params={"erste_edition": True, "limit": 5000})
        assert only.status_code == 200
        ids = {c["id"] for c in only.json()["items"]}
        assert ja in ids
        assert nein not in ids
        # Gegenprobe: erste_edition=false enthält die Nicht-1st-Karte, nicht die 1st
        rest = client.get("/api/v1/cards", params={"erste_edition": False, "limit": 5000})
        rest_ids = {c["id"] for c in rest.json()["items"]}
        assert nein in rest_ids
        assert ja not in rest_ids
    finally:
        client.delete(f"/api/v1/cards/{ja}")
        client.delete(f"/api/v1/cards/{nein}")
