"""
#117: python-jose wird durch PyJWT ersetzt (python-jose zieht ecdsa mit, für
das es keine Korrektur gibt). Diese Tests halten fest, was die Anmeldegrenze
leisten muss, unabhängig von der Bibliothek: Die Tokens werden hier VON HAND
gebaut (hmac + base64), nicht mit der Bibliothek, die geprüft wird — sonst
prüfte das Orakel dieselbe Annahme mit wie der Code.
"""

import base64
import hashlib
import hmac
import json
import time

from app.config import settings

GESCHUETZT = "/api/v1/cards"


def _b64(daten: bytes) -> str:
    return base64.urlsafe_b64encode(daten).rstrip(b"=").decode()


def _token(kopf: dict, nutzlast: dict, schluessel: str | None, algo=hashlib.sha256) -> str:
    teil = _b64(json.dumps(kopf).encode()) + "." + _b64(json.dumps(nutzlast).encode())
    if schluessel is None:
        return teil + "."
    sig = hmac.new(schluessel.encode(), teil.encode(), algo).digest()
    return teil + "." + _b64(sig)


def _get(anon_client, token: str):
    return anon_client.get(GESCHUETZT, headers={"Authorization": f"Bearer {token}"})


def _gueltige_nutzlast() -> dict:
    return {"sub": "admin", "exp": int(time.time()) + 600}


def test_von_hand_gebautes_gueltiges_token_wird_angenommen(anon_client):
    # Gegenprobe: ohne sie bewiesen die Ablehnungen unten nichts.
    t = _token({"alg": settings.jwt_algorithm, "typ": "JWT"}, _gueltige_nutzlast(), settings.jwt_secret)
    assert _get(anon_client, t).status_code == 200


def test_falscher_schluessel_401(anon_client):
    t = _token({"alg": settings.jwt_algorithm, "typ": "JWT"}, _gueltige_nutzlast(), "falscher-schluessel")
    assert _get(anon_client, t).status_code == 401


def test_abgelaufenes_token_401(anon_client):
    nutzlast = {"sub": "admin", "exp": int(time.time()) - 60}
    t = _token({"alg": settings.jwt_algorithm, "typ": "JWT"}, nutzlast, settings.jwt_secret)
    assert _get(anon_client, t).status_code == 401


def test_alg_none_401(anon_client):
    t = _token({"alg": "none", "typ": "JWT"}, _gueltige_nutzlast(), None)
    assert _get(anon_client, t).status_code == 401


def test_anderer_algorithmus_mit_richtigem_schluessel_401(anon_client):
    # Nur der konfigurierte Algorithmus zählt (algorithms=[...] beim Prüfen).
    t = _token({"alg": "HS512", "typ": "JWT"}, _gueltige_nutzlast(), settings.jwt_secret, hashlib.sha512)
    assert _get(anon_client, t).status_code == 401


def test_login_token_wird_angenommen_und_traegt_exp(anon_client, test_password):
    r = anon_client.post("/api/v1/auth/login", json={"username": "admin", "password": test_password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    assert isinstance(token, str)
    nutzlast = json.loads(base64.urlsafe_b64decode(token.split(".")[1] + "=="))
    assert nutzlast["sub"] == "admin"
    assert nutzlast["exp"] > time.time()
    assert _get(anon_client, token).status_code == 200
