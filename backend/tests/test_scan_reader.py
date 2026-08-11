"""
Pluggbares Lese-Modell am Scan-Endpunkt (Scan-Stufe B, Issue #57).

Provider wird auf OpenAI gestellt, `vlm.extract` gemockt; erwartet: das gewählte
Modell setzt die Engine, harte Fehler fallen sauber auf lokale OCR zurück und
melden ihre Ursache. Der Resolver ist gemockt (hermetisch, kein Netz).
"""

import pytest

import app.api.v1.scan as scan_module
from app.schemas.scan import ScanCandidate, ScanRawRead
from app.services.scan import vlm
from app.services.scan.vlm import ReaderResult


@pytest.fixture()
def reader_openai(client, monkeypatch):
    """Provider=OpenAI + Test-Key; Resolver hermetisch; setzt danach zurück."""
    client.put("/api/v1/settings", json={
        "scan_reader_provider": "openai",
        "openai_api_key": "sk-test-123",
        "openai_model": "gpt-4o-mini",
    })

    async def fake_resolve(db, reads, default_lang="DE"):
        return [
            ScanCandidate(position=r.position or 0, confidence=0.9, raw=r,
                          suggested={"kartenname": r.name or ""})
            for r in reads
        ]
    monkeypatch.setattr(scan_module, "resolve_reads", fake_resolve)

    def _install(result):
        async def fake_extract(data, *, base_url, api_key, model,
                               mime_type="image/jpeg", referer=None, title=None):
            return result
        monkeypatch.setattr(vlm, "extract", fake_extract)

    yield _install

    # Zustand für nachfolgende (Gemini-Default-)Tests zurücksetzen.
    client.put("/api/v1/settings",
               json={"scan_reader_provider": "gemini", "openai_api_key": ""})


def _scan(client, png_bytes):
    r = client.post("/api/v1/scan",
                    files={"file": ("scan.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    return r.json()


def test_openai_reads_setzen_engine(client, reader_openai, png_bytes):
    reader_openai(ReaderResult(
        [ScanRawRead(name="Pikachu", number="025/165", set_code="MEW", position=0)],
        42, None))
    body = _scan(client, png_bytes)
    assert body["engine"] == "openai"
    assert body["candidates"] and body["candidates"][0]["raw"]["name"] == "Pikachu"
    assert body["hinweis_art"] is None


def test_openai_key_fehler_faellt_auf_ocr(client, reader_openai, png_bytes):
    reader_openai(ReaderResult(None, None, vlm.FEHLER_KEY))
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "key_ungueltig"
    assert body["limit_erreicht"] is False   # Key-Problem, kein Limit
    assert body["hinweis"]


def test_openai_rate_limit_setzt_limit_erreicht(client, reader_openai, png_bytes):
    reader_openai(ReaderResult(None, None, vlm.FEHLER_RATE))
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "rate_limit"
    assert body["limit_erreicht"] is True    # erreichtes Kontingent


def test_openai_reader_fehler_hat_eigenen_hinweis(client, reader_openai, png_bytes):
    """Harter Reader-Fehler bekommt 'reader_fehler' – NICHT 'gemini_fehler'."""
    reader_openai(ReaderResult(None, None, vlm.FEHLER_VLM))
    body = _scan(client, png_bytes)
    assert body["engine"] == "ocr"
    assert body["hinweis_art"] == "reader_fehler"
    assert body["limit_erreicht"] is False
    assert body["hinweis"]


def test_status_spiegelt_provider(client, reader_openai):
    reader_openai(ReaderResult(None, None, None))
    st = client.get("/api/v1/scan/status").json()
    assert st["provider"] == "openai"
    assert st["model"] == "gpt-4o-mini"
    assert st["active"] == "openai"    # Key gesetzt → Modell aktiv
    assert st["gemini"] is False       # nicht der Gemini-Pfad


def test_settings_reader_secret_bleibt_maskiert(client):
    """Neue Provider-Keys verlassen das Backend nur maskiert (Issue #1)."""
    client.put("/api/v1/settings", json={
        "scan_reader_provider": "openrouter",
        "openrouter_api_key": "sk-or-secret-9999",
        "openrouter_model": "google/gemini-2.5-flash",
    })
    s = client.get("/api/v1/settings").json()
    assert s["scan_reader_provider"] == "openrouter"
    assert s["openrouter_model"] == "google/gemini-2.5-flash"
    assert s["openrouter_api_key_set"] is True
    assert s["openrouter_api_key_masked"].endswith("9999")
    assert "sk-or-secret" not in s["openrouter_api_key_masked"]
    assert "openrouter_api_key" not in s   # Klartext nie in der Response
    # zurücksetzen (Session-DB wird von Folge-Tests geteilt)
    client.put("/api/v1/settings",
               json={"scan_reader_provider": "gemini", "openrouter_api_key": ""})
