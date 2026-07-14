"""
Settings-Maskierung (Issue #1): Secrets verlassen das Backend nie im Klartext.
Die Response liefert je Secret nur <key>_set (bool) + <key>_masked
("•••• " + letzte 4 Zeichen, leer wenn nicht gesetzt); PUT bleibt Klartext.
"""

SECRET_KEYS = (
    "cardmarket_app_token",
    "cardmarket_app_secret",
    "cardmarket_access_token",
    "cardmarket_access_secret",
    "gemini_api_key",
)


def test_settings_response_ohne_klartext_secrets(client):
    body = client.get("/api/v1/settings").json()
    for key in SECRET_KEYS:
        assert key not in body, f"Klartext-Feld {key} darf nicht mehr ausgeliefert werden"
        assert f"{key}_set" in body
        assert f"{key}_masked" in body


def test_secret_setzen_liefert_maske_statt_klartext(client):
    secret = "sk-test-1234-ABCD"
    r = client.put("/api/v1/settings", json={"gemini_api_key": secret})
    assert r.status_code == 200
    body = r.json()
    assert body["gemini_api_key_set"] is True
    assert body["gemini_api_key_masked"] == "•••• ABCD"
    assert secret not in r.text, "Klartext-Secret in der Response gefunden"

    # GET zeigt denselben maskierten Stand
    body = client.get("/api/v1/settings").json()
    assert body["gemini_api_key_set"] is True
    assert body["gemini_api_key_masked"] == "•••• ABCD"

    # Aufräumen: Secret wieder leeren → Flag aus, Maske leer
    body = client.put("/api/v1/settings", json={"gemini_api_key": ""}).json()
    assert body["gemini_api_key_set"] is False
    assert body["gemini_api_key_masked"] == ""


def test_nicht_gesetzte_secrets_sind_leer_maskiert(client):
    body = client.get("/api/v1/settings").json()
    for key in ("cardmarket_app_token", "cardmarket_app_secret"):
        assert body[f"{key}_set"] is False
        assert body[f"{key}_masked"] == ""
