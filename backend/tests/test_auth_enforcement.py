"""
Auth-Zwang (Issue #1): Alle Fach-Router verlangen ein gültiges JWT.
Auth-frei bleiben nur /auth/login, /health und der /images-StaticFiles-Mount.
Dazu: Start-Guard — ohne konfiguriertes Passwort verweigert die App den Start.
"""

import pytest


def test_geschuetzte_endpoints_ohne_token_401(anon_client):
    for path in (
        "/api/v1/cards",
        "/api/v1/catalog",
        "/api/v1/collections",
        "/api/v1/settings",
        "/api/v1/sets",
        "/api/v1/scan/status",
        "/api/v1/cards/meta/stats",
    ):
        r = anon_client.get(path)
        assert r.status_code == 401, f"{path} muss ohne Token 401 liefern, war {r.status_code}"


def test_geschuetzter_endpoint_mit_kaputtem_token_401(anon_client):
    r = anon_client.get(
        "/api/v1/cards",
        headers={"Authorization": "Bearer kein-echtes-jwt"},
    )
    assert r.status_code == 401


def test_geschuetzte_endpoints_mit_token_200(client):
    assert client.get("/api/v1/cards").status_code == 200
    assert client.get("/api/v1/settings").status_code == 200


def test_health_ohne_token_erreichbar(anon_client):
    r = anon_client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_ohne_token_erreichbar_und_falsches_passwort_401(anon_client):
    r = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "definitiv-falsch"},
    )
    # 401 (nicht 403/404) → Endpoint ist ohne Token erreichbar, lehnt nur ab
    assert r.status_code == 401


def test_login_ohne_token_liefert_token(anon_client, test_password):
    r = anon_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": test_password},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_start_guard_verweigert_ohne_passwort(client, monkeypatch):
    """Leerer APP_PASSWORD_HASH + kein DB-Hash → App verweigert den Start."""
    from app import main
    from app.database import SessionLocal
    from app.models.setting import AppSetting

    # Sicherstellen, dass auch kein DB-Hash liegt (kein Test setzt ihn bisher)
    db = SessionLocal()
    try:
        assert db.get(AppSetting, "app_password_hash") is None
    finally:
        db.close()

    monkeypatch.setenv("APP_PASSWORD_HASH", "")
    with pytest.raises(RuntimeError, match="APP_PASSWORD_HASH"):
        main._ensure_password_configured()


def test_start_guard_akzeptiert_env_hash(client):
    """Mit gesetztem Env-Hash (conftest) läuft der Guard durch."""
    from app import main

    main._ensure_password_configured()
