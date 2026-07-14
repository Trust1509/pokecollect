"""
Gemini-Tageslimit durchsetzen + Content-Type-Validierung am Scan (Issue #3).
Gemini wird gemockt — kein echter API-Call.
"""

from datetime import datetime, timezone

import pytest

from app.database import SessionLocal
from app.models.gemini_usage import GeminiUsage
from app.services.scan import gemini


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@pytest.fixture()
def gemini_calls(monkeypatch):
    """Gemini als aktiviert simulieren; Aufrufe zählen statt echter API-Calls."""
    calls: list[str] = []

    async def fake_extract(data, api_key, model=None, mime_type="image/jpeg"):
        calls.append(mime_type)
        return [], 7  # keine Karten erkannt, 7 Tokens verbraucht

    monkeypatch.setattr(gemini, "is_enabled", lambda key: True)
    monkeypatch.setattr(gemini, "extract", fake_extract)
    return calls


@pytest.fixture()
def daily_limit_reached(client):
    """Limit 1 setzen + heutigen Zähler auf 1 → Limit erreicht; danach zurücksetzen."""
    r = client.put("/api/v1/settings", json={"gemini_daily_limit": 1})
    assert r.status_code == 200
    db = SessionLocal()
    try:
        row = db.get(GeminiUsage, _today())
        prev = (row.requests, row.tokens) if row else None
        if row:
            row.requests = 1
        else:
            db.add(GeminiUsage(day=_today(), requests=1, tokens=0))
        db.commit()
    finally:
        db.close()

    yield

    client.put("/api/v1/settings", json={"gemini_daily_limit": 0})
    db = SessionLocal()
    try:
        row = db.get(GeminiUsage, _today())
        if row:
            if prev is not None:
                row.requests, row.tokens = prev
            else:
                db.delete(row)
        db.commit()
    finally:
        db.close()


def test_scan_limit_falls_back_to_ocr(client, gemini_calls, daily_limit_reached, png_bytes):
    """Limit erreicht → Gemini wird NICHT gerufen, OCR-Fallback + Hinweis."""
    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert gemini_calls == [], "Gemini darf bei erreichtem Limit nicht gerufen werden"
    assert body["engine"] == "ocr"
    assert body["limit_erreicht"] is True
    assert body["hinweis"]


def test_scan_below_limit_uses_gemini(client, gemini_calls, png_bytes):
    """Ohne Limit (0 = unbegrenzt) läuft der Scan über Gemini + Usage-Buchung."""
    usage_before = client.get("/api/v1/scan/usage").json()["today"]

    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert gemini_calls == ["image/png"]
    assert body["engine"] == "gemini"
    assert body["limit_erreicht"] is False
    assert body["hinweis"] is None

    # _record_usage wurde vom Aufrufer gebucht (Issue #9: aus gemini.py gehoben)
    usage_after = client.get("/api/v1/scan/usage").json()["today"]
    assert usage_after["requests"] == usage_before["requests"] + 1
    assert usage_after["tokens"] == usage_before["tokens"] + 7


def test_scan_rejects_non_image_content_type(client, png_bytes):
    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.txt", png_bytes, "text/plain")},
    )
    assert r.status_code == 400
