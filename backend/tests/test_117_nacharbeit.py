"""
#117, Nacharbeit 1: Das Panel fand dieselben drei Klassen von Server-Fehlern an
Stellen, die das Fuzzing nicht getroffen hatte, und Lücken in den Tests.
Jeder Fall hier lief vor der Nacharbeit auf 500 oder ließ einen Rückbau
unbemerkt (gemessen von Blind- und Gegenprüfer).
"""

import base64
import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy.exc import DataError

import app.api.v1.cards as cards_api
from app.config import settings

ZU_GROSS = 2**31


# --- Steuerzeichen im PFAD (bisher nur der Query getestet) ------------------


def test_steuerzeichen_im_pfad_wird_abgelehnt(client):
    r = client.get("/api/v1/catalog/abc%00x/detail")
    assert r.status_code == 422, r.text


# --- nicht kodierbarer Text in normalen Textfeldern -------------------------


@pytest.mark.parametrize(
    "pfad, methode, koerper",
    [
        ("/api/v1/cards", "post", rb'{"kartenname": "\ud800"}'),
        ("/api/v1/collections", "post", rb'{"name": "\udfff"}'),
    ],
)
def test_surrogat_in_textfeld_wird_abgelehnt(client, pfad, methode, koerper):
    r = getattr(client, methode)(pfad, content=koerper, headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text


def test_surrogat_in_notizen_beim_aendern_wird_abgelehnt(client):
    kid = client.post("/api/v1/cards", json={"kartenname": "Notiz #117"}).json()["id"]
    r = client.put(
        f"/api/v1/cards/{kid}",
        content=rb'{"notizen": "a\ud83db"}',
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 422, r.text


def test_echtes_emoji_bleibt_erlaubt(client):
    # Ein Paar aus zwei Surrogaten in JSON ist ein echtes Zeichen (hier ein
    # Emoji) und muss durchgehen — nur EINZELNE Surrogate sind ungültig.
    # Backslash über chr(92): Werkzeuge beim Schreiben dieser Datei machten aus
    # der Escape-Folge sonst das fertige Zeichen.
    bs = chr(92)
    koerper = ('{"kartenname": "Pika ' + bs + "ud83d" + bs + 'ude00"}').encode("ascii")
    r = client.post(
        "/api/v1/cards",
        content=koerper,
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["kartenname"] == "Pika \U0001F600"


# --- Ganzzahl-Geschwisterfelder ----------------------------------------------


def test_pokedex_nr_karte_ausserhalb_wird_abgelehnt(client):
    assert client.post("/api/v1/cards", json={"kartenname": "Dex #117", "pokedex_nr": ZU_GROSS}).status_code == 422
    kid = client.post("/api/v1/cards", json={"kartenname": "Dex #117"}).json()["id"]
    assert client.put(f"/api/v1/cards/{kid}", json={"pokedex_nr": -1}).status_code == 422


@pytest.mark.parametrize("feld, wert", [("pokedex_nr", ZU_GROSS), ("dex_id", ZU_GROSS), ("position", ZU_GROSS), ("position", -5)])
def test_scan_commit_ganzzahlen_ausserhalb_werden_abgelehnt(client, feld, wert):
    r = client.post("/api/v1/scan/commit", json={"target": "pokedex", "items": [{"kartenname": "Scan #117", feld: wert}]})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("wert", [ZU_GROSS, -5])
def test_soll_position_ausserhalb_wird_abgelehnt(client, wert):
    # Der Körper wird vor dem Handler geprüft — die IDs müssen nicht existieren.
    r = client.put("/api/v1/collections/1/soll/1", json={"position": wert})
    assert r.status_code == 422, r.text


@pytest.mark.parametrize("pfad", ["/api/v1/cards", "/api/v1/catalog"])
def test_seite_ausserhalb_wird_abgelehnt(client, pfad):
    r = client.get(pfad, params={"page": 10**21})
    assert r.status_code == 422, r.text


# --- Netz für den Rest der Klasse: DataError aus der Datenbank → 422 --------


def test_datenbank_wertfehler_wird_422_statt_500(client, monkeypatch):
    def _wirft(*args, **kwargs):
        raise DataError("SELECT 1", {}, Exception("integer out of range"))

    monkeypatch.setattr(cards_api, "select", _wirft)
    r = client.get("/api/v1/cards")
    assert r.status_code == 422, r.text
    assert "integer out of range" not in r.text  # keine Datenbank-Interna nach außen


# --- JWT: exp und sub sind Pflicht ------------------------------------------


def _b64(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def _token(nutzlast: dict) -> str:
    teil = _b64(json.dumps({"alg": settings.jwt_algorithm, "typ": "JWT"}).encode()) + "." + _b64(json.dumps(nutzlast).encode())
    sig = hmac.new(settings.jwt_secret.encode(), teil.encode(), hashlib.sha256).digest()
    return teil + "." + _b64(sig)


@pytest.mark.parametrize(
    "nutzlast",
    [
        {"sub": "admin"},                                  # ohne exp: liefe nie ab
        {"exp": 4_000_000_000},                            # ohne sub
    ],
)
def test_token_ohne_pflicht_claim_401(anon_client, nutzlast):
    r = anon_client.get("/api/v1/cards", headers={"Authorization": f"Bearer {_token(nutzlast)}"})
    assert r.status_code == 401, r.text


def test_token_mit_exp_und_sub_200(anon_client):
    t = _token({"sub": "admin", "exp": int(time.time()) + 600})
    assert anon_client.get("/api/v1/cards", headers={"Authorization": f"Bearer {t}"}).status_code == 200
