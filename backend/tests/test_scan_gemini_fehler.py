"""
Getrennte Gemini-Fehlersignale am Scan-Endpunkt (Issue #21).

Gemini wird gemockt und liefert je Fall ein GeminiResult mit gesetzter
fehler_art. Erwartet: OCR-Fallback + passende hinweis_art/hinweis in der
Scan-Response, damit das UI Rate-Limit vs. ungültigen Key trennen kann.
"""

import pytest

from app.services.scan import gemini
from app.services.scan.gemini import GeminiResult


@pytest.fixture()
def gemini_fehler(monkeypatch):
    """Installiert einen Gemini-Mock, der die gewünschte Fehlerart zurückgibt."""

    def _install(fehler_art):
        async def fake_extract(data, api_key, model=None, mime_type="image/jpeg"):
            return GeminiResult(None, None, fehler_art)

        monkeypatch.setattr(gemini, "is_enabled", lambda key: True)
        monkeypatch.setattr(gemini, "extract", fake_extract)

    return _install


def _scan(client, png_bytes):
    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_key_ungueltig_ist_distinktes_signal(client, gemini_fehler, png_bytes):
    gemini_fehler("key_ungueltig")
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "key_ungueltig"
    assert body["limit_erreicht"] is False   # kein Limit, sondern Key-Problem
    assert body["hinweis"]


def test_rate_limit_setzt_limit_erreicht(client, gemini_fehler, png_bytes):
    gemini_fehler("rate_limit")
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "rate_limit"
    assert body["limit_erreicht"] is True    # erreichtes Kontingent
    assert body["hinweis"]


def test_gemini_fehler_fallback_mit_hinweis(client, gemini_fehler, png_bytes):
    gemini_fehler("gemini_fehler")
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "gemini_fehler"
    assert body["limit_erreicht"] is False
    assert body["hinweis"]
