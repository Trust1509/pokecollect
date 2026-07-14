"""
Issue #12 — Admin-Endpoints & wirkungslose Settings:
- Cardmarket-OAuth-Fallback liest DB-Settings VOR der ENV
- price_source kommt aus der DB (Default 30d_avg)
- entfernte Endpoints (/sets/sync, /catalog/enrich, /catalog/enrich-all) sind weg
- verdrahtete Endpoints (/prices/refresh, /catalog/sync) antworten
"""

import pytest

from app.config import settings as env_settings
from app.database import SessionLocal
from app.models.setting import AppSetting
from app.services.pricing import (
    CARDMARKET_CREDENTIAL_KEYS,
    get_cardmarket_credentials,
    get_price_source,
)


@pytest.fixture()
def db(client):
    """Frische Session; angelegte Settings-Rows werden wieder entfernt."""
    session = SessionLocal()
    try:
        yield session
        for key in (*CARDMARKET_CREDENTIAL_KEYS, "price_source"):
            row = session.get(AppSetting, key)
            if row:
                session.delete(row)
        session.commit()
    finally:
        session.close()


def _set(db, key: str, value: str):
    row = db.get(AppSetting, key)
    if row:
        row.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


# ── Cardmarket-Credentials: DB vor ENV ───────────────────────────────────────

def test_cardmarket_credentials_db_wins_over_env(db, monkeypatch):
    for key in CARDMARKET_CREDENTIAL_KEYS:
        monkeypatch.setattr(env_settings, key, f"env-{key}")
        _set(db, key, f"db-{key}")
    creds = get_cardmarket_credentials(db)
    assert creds is not None
    assert creds.app_token == "db-cardmarket_app_token"
    assert creds.access_secret == "db-cardmarket_access_secret"


def test_cardmarket_credentials_env_fallback(db, monkeypatch):
    for key in CARDMARKET_CREDENTIAL_KEYS:
        monkeypatch.setattr(env_settings, key, f"env-{key}")
    creds = get_cardmarket_credentials(db)
    assert creds is not None
    assert creds.app_token == "env-cardmarket_app_token"


def test_cardmarket_credentials_mixed_per_field(db, monkeypatch):
    """Leere DB-Rows (Settings-Seite speichert '') fallen je Feld auf ENV zurück."""
    for key in CARDMARKET_CREDENTIAL_KEYS:
        monkeypatch.setattr(env_settings, key, f"env-{key}")
        _set(db, key, "")
    _set(db, "cardmarket_app_token", "db-token")
    creds = get_cardmarket_credentials(db)
    assert creds is not None
    assert creds.app_token == "db-token"
    assert creds.app_secret == "env-cardmarket_app_secret"


def test_cardmarket_credentials_incomplete_is_none(db, monkeypatch):
    for key in CARDMARKET_CREDENTIAL_KEYS:
        monkeypatch.setattr(env_settings, key, "")
    _set(db, "cardmarket_app_token", "nur-eins")
    assert get_cardmarket_credentials(db) is None


# ── price_source aus der DB ──────────────────────────────────────────────────

def test_price_source_default_without_row(db):
    assert get_price_source(db) == "30d_avg"


def test_price_source_daily_from_db(db):
    _set(db, "price_source", "daily")
    assert get_price_source(db) == "daily"


def test_price_source_legacy_current_from_db(db):
    _set(db, "price_source", "current")
    assert get_price_source(db) == "daily"


# ── Entfernte Endpoints sind weg, verdrahtete antworten ─────────────────────

def test_removed_endpoints_are_gone(client):
    assert client.post("/api/v1/sets/sync").status_code == 404
    assert client.post("/api/v1/catalog/enrich").status_code == 404
    assert client.post("/api/v1/catalog/enrich-all").status_code == 404


def test_prices_refresh_endpoint_answers(client, monkeypatch):
    import app.api.v1.prices as prices_api

    async def _noop(db, ids):
        return None

    monkeypatch.setattr(prices_api, "refresh_prices_for_cards", _noop)
    resp = client.post("/api/v1/prices/refresh")
    assert resp.status_code == 200
    assert "Preisupdate" in resp.json()["message"]


def test_catalog_sync_endpoint_answers(client, monkeypatch):
    import app.api.v1.catalog as catalog_api

    async def _noop_sets():
        return {}

    async def _noop_catalog(db):
        return {}

    monkeypatch.setattr(catalog_api, "sync_sets", _noop_sets)
    monkeypatch.setattr(catalog_api.catalog_svc, "sync_catalog", _noop_catalog)
    resp = client.post("/api/v1/catalog/sync")
    assert resp.status_code == 200
    assert "Katalog-Sync" in resp.json()["detail"]
