"""
#117: Das API-Fuzzing (Schemathesis, Wochen-Scan) fand drei Server-Fehler (500)
mit absurd großen Ganzzahlen. Die Werte landen in Spalten vom Typ `integer`
(Postgres, 32 Bit) bzw. in einem LIMIT — ohne Grenze im Schema scheitert erst
die Datenbank. Erwartet ist eine Ablehnung der Eingabe (422), kein 500.

Die Grenze kommt aus dem Spaltentyp (lehren.md: Integer-Grenzen nur auf PG
messen), nicht aus einer geschätzten Fachobergrenze.
"""

import pytest

PG_INT_MAX = 2**31 - 1
ZU_GROSS = PG_INT_MAX + 1


def _sammlung(client) -> int:
    r = client.post("/api/v1/collections", json={"name": "Grenzen #117"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _karte(client) -> int:
    r = client.post("/api/v1/cards", json={"kartenname": "Grenzen-Karte #117", "besessen": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# --- die drei Fälle aus dem Fuzzing-Lauf ---------------------------------


@pytest.mark.parametrize("limit", [-59235849993543614464, -1, ZU_GROSS])
def test_preis_historie_limit_ausserhalb_wird_abgelehnt(client, limit):
    kid = _karte(client)
    r = client.get(f"/api/v1/prices/history/{kid}", params={"limit": limit})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("slots", [-35184372088832, -1, ZU_GROSS])
def test_binder_slots_ausserhalb_wird_abgelehnt(client, slots):
    cid = _sammlung(client)
    r = client.put(f"/api/v1/collections/{cid}", json={"binder_slots": slots})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    "eintrag",
    [
        {"card_id": 1, "position": ZU_GROSS},
        {"card_id": 1, "position": -1},
        {"card_id": ZU_GROSS, "position": 0},
    ],
)
def test_positionen_ausserhalb_werden_abgelehnt(client, eintrag):
    cid = _sammlung(client)
    r = client.put(f"/api/v1/collections/{cid}/cards/positions", json={"positions": [eintrag]})
    assert r.status_code == 422, r.text


# --- Geschwister im selben Schema: dieselbe Spalte, derselbe Fehler -------


def test_slot_ausserhalb_wird_abgelehnt(client):
    cid = _sammlung(client)
    kid = _karte(client)
    assert client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": kid}).status_code == 201
    r = client.put(f"/api/v1/collections/{cid}/cards/{kid}/slot", json={"slot": ZU_GROSS})
    assert r.status_code == 422, r.text


# --- Grenzwerte, die gelten müssen ------------------------------------------


def test_grenzwerte_innerhalb_gehen_durch(client):
    cid = _sammlung(client)
    kid = _karte(client)
    assert client.post(f"/api/v1/collections/{cid}/cards", json={"card_id": kid}).status_code == 201

    assert client.get(f"/api/v1/prices/history/{kid}", params={"limit": 0}).status_code == 200
    assert client.get(f"/api/v1/prices/history/{kid}", params={"limit": PG_INT_MAX}).status_code == 200
    assert client.put(f"/api/v1/collections/{cid}", json={"binder_slots": PG_INT_MAX}).status_code == 200
    assert client.put(f"/api/v1/collections/{cid}", json={"binder_slots": None}).status_code == 200
    r = client.put(
        f"/api/v1/collections/{cid}/cards/positions",
        json={"positions": [{"card_id": kid, "position": PG_INT_MAX}]},
    )
    assert r.status_code == 204, r.text


# --- zweite Klasse (lokales Fuzzing mit 50 Beispielen): NUL im Query-String --
# Postgres-Text kann kein NUL-Byte (0x00) — ein Suchparameter damit scheiterte
# erst in der Datenbank (500). Für Körper prüft das schon reject_control_chars.


@pytest.mark.parametrize(
    "pfad",
    [
        "/api/v1/cards?set=%00x",
        "/api/v1/catalog?region=a%00b",
        "/api/v1/sealed/catalog?search=%00",
        "/api/v1/cards?seltenheit=%14",
    ],
)
def test_steuerzeichen_im_query_werden_abgelehnt(client, pfad):
    r = client.get(pfad)
    assert r.status_code == 422, r.text


def test_normaler_query_mit_umlaut_geht_durch(client):
    assert client.get("/api/v1/cards", params={"set": "Paldeas Schicksale", "seltenheit": "Selten ä"}).status_code == 200


# --- Geldfelder der Karte: Spalte Numeric(8, 2) wie bei Sealed --------------


@pytest.mark.parametrize("feld", ["kaufpreis_eur", "wert_eur"])
@pytest.mark.parametrize("wert", [-3.3353633731416612e16, -0.01, 1_000_000])
def test_geldfeld_karte_ausserhalb_wird_abgelehnt(client, feld, wert):
    r = client.post("/api/v1/cards", json={"kartenname": "Geld #117", feld: wert})
    assert r.status_code == 422, r.text
    kid = _karte(client)
    r = client.put(f"/api/v1/cards/{kid}", json={feld: wert})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("feld", ["kaufpreis_eur", "wert_eur"])
def test_geldfeld_karte_grenzwert_geht_durch(client, feld):
    r = client.post("/api/v1/cards", json={"kartenname": "Geld-Grenze #117", feld: "999999.99"})
    assert r.status_code == 201, r.text
    assert r.json()[feld] == "999999.99"
    r = client.put(f"/api/v1/cards/{r.json()['id']}", json={feld: 0})
    assert r.status_code == 200, r.text


# --- dritte Klasse (zweiter Fuzzing-Lauf): nicht kodierbares Passwort -------
# Ein einzelnes Surrogat ist in JSON gültig ("\ud800"), lässt sich aber nicht
# als UTF-8 kodieren — bcrypt scheiterte daran mit 500. Ein solches Passwort
# kann es nicht geben (das gespeicherte ist ein Hash aus UTF-8-Bytes), also ist
# es eine ungültige Eingabe.

# Als Bytes mit der JSON-Schreibweise \ud800 (sechs ASCII-Zeichen): Erst der
# JSON-Parser der API macht daraus das Surrogat — wie bei einem echten Client.
_SURROGAT = rb'{"current_password": "\ud800", "new_password": "neu-neu-neu"}'


def test_passwortwechsel_mit_surrogat_kein_500(client):
    r = client.post(
        "/api/v1/settings/change-password",
        content=_SURROGAT,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (400, 422), r.text


def test_login_mit_surrogat_kein_500(anon_client):
    r = anon_client.post(
        "/api/v1/auth/login",
        content=rb'{"username": "admin", "password": "\ud800"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code in (401, 422), r.text


def test_422_spiegelt_abgelehnte_eingabe_nicht_zurueck(anon_client):
    # Ohne eigenen Handler schreibt FastAPI den abgelehnten Wert als "input" in
    # die 422 — bei einem Passwortfeld also das Passwort im Klartext, und ein
    # nicht kodierbarer Wert machte daraus wieder einen 500 (#117).
    geheim = "geheim-117-nicht-zurueck"
    r = anon_client.post("/api/v1/auth/login", json={"username": "admin", "password": [geheim]})
    assert r.status_code == 422, r.text
    assert geheim not in r.text
    assert r.json()["detail"][0]["loc"] == ["body", "password"]
