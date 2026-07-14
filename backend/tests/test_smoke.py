"""
Smoke-Suite: deckt die Kern-API ab (Health, Seed, Karten-CRUD inkl.
Platzhalter-Logik, Settings, Auth, Enums). Absichtlich schlank — sie ist das
Gate, das jede Änderung vor Push/Release passieren muss.
"""


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["version"]


def test_sets_seeded(client):
    r = client.get("/api/v1/sets")
    assert r.status_code == 200
    codes = {s["code"] for s in r.json()}
    # Stichproben aus allen Generationen des Seeds
    assert {"SVI", "MEW", "SSH", "SUM", "EVO"} <= codes


def test_card_crud_roundtrip(client):
    created = client.post(
        "/api/v1/cards",
        json={
            "kartenname": "Smoke-Testmon",
            "englischer_name": "Smoke Testmon",
            "sprache": "DE",
            "besessen": True,
            "seltenheit": "Common",
        },
    )
    assert created.status_code == 201, created.text
    card = created.json()
    card_id = card["id"]
    assert card["kartenname"] == "Smoke-Testmon"

    r = client.get(f"/api/v1/cards/{card_id}")
    assert r.status_code == 200
    assert r.json()["besessen"] is True

    r = client.put(f"/api/v1/cards/{card_id}", json={"notizen": "geändert"})
    assert r.status_code == 200
    assert r.json()["notizen"] == "geändert"

    r = client.get("/api/v1/cards", params={"search": "Smoke-Testmon"})
    assert r.status_code == 200
    assert any(c["id"] == card_id for c in r.json()["items"])

    assert client.delete(f"/api/v1/cards/{card_id}").status_code == 204
    assert client.get(f"/api/v1/cards/{card_id}").status_code == 404


def test_placeholder_not_deletable(client):
    created = client.post(
        "/api/v1/cards",
        json={"kartenname": "Platzhaltermon", "besessen": False},
    )
    assert created.status_code == 201
    card_id = created.json()["id"]
    r = client.delete(f"/api/v1/cards/{card_id}")
    assert r.status_code == 400


def test_owned_card_adopts_placeholder(client):
    """Kern-Invariante: besessene Karte übernimmt den Pokédex-Platzhalter."""
    ph = client.post(
        "/api/v1/cards",
        json={"kartenname": "Adoptmon", "pokedex_nr": 9999, "besessen": False},
    )
    assert ph.status_code == 201
    ph_id = ph.json()["id"]

    owned = client.post(
        "/api/v1/cards",
        json={"kartenname": "Adoptmon", "pokedex_nr": 9999, "besessen": True},
    )
    assert owned.status_code == 201
    body = owned.json()
    assert body["id"] == ph_id, "Platzhalter muss übernommen werden, kein Duplikat"
    assert body["im_pokedex"] is True

    # Aufräumen: Delete legt den Platzhalter wieder an → den auch entfernen
    client.delete(f"/api/v1/cards/{ph_id}")


def test_list_pagination_shape(client):
    r = client.get("/api/v1/cards", params={"page": 1, "limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"items", "total", "page", "limit", "pages"}
    assert body["limit"] == 5


def test_enums_endpoint(client):
    r = client.get("/api/v1/cards/meta/enums")
    assert r.status_code == 200
    body = r.json()
    assert "Common" in body["seltenheit"]
    assert "DE" in body["sprache"]


def test_settings_defaults(client):
    r = client.get("/api/v1/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["cards_per_page"] > 0
    assert body["default_language"] in ("DE", "EN")


def test_settings_update_roundtrip(client):
    r = client.put("/api/v1/settings", json={"cards_per_page": 24})
    assert r.status_code == 200
    assert r.json()["cards_per_page"] == 24
    r = client.get("/api/v1/settings")
    assert r.json()["cards_per_page"] == 24


def test_login_rejects_wrong_password(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "definitiv-falsch"},
    )
    assert r.status_code == 401


def test_login_accepts_default_credentials(client):
    """Default-Hash ('secret') gilt, solange kein eigener Hash gesetzt ist."""
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "secret"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["expires_in"] > 0


def test_stats_endpoint(client):
    r = client.get("/api/v1/cards/meta/stats")
    assert r.status_code == 200
