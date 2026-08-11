"""
Modell-Vorschläge für die Lese-Combobox (Scan-Stufe B, Issue #57).

OpenRouter live-gefiltert (bild-fähig) über MockTransport; OpenAI/Gemini
kuratiert; Fallback auf die kuratierte Liste, wenn der Live-Abruf ausfällt.
"""

import asyncio

import httpx

from app.services.scan import model_catalog


def _run(coro):
    return asyncio.run(coro)


def test_is_vision_filter():
    assert model_catalog._is_vision({"architecture": {"input_modalities": ["text", "image"]}}) is True
    assert model_catalog._is_vision({"architecture": {"input_modalities": ["text"]}}) is False
    assert model_catalog._is_vision({"architecture": {"modality": "text+image->text"}}) is True
    assert model_catalog._is_vision({}) is False


def test_curated_openai_und_gemini():
    r = _run(model_catalog.list_models("openai"))
    assert r["source"] == "curated"
    assert any(m["id"] == "gpt-4o-mini" for m in r["models"])
    r = _run(model_catalog.list_models("gemini"))
    assert r["source"] == "curated"
    assert any("gemini" in m["id"] for m in r["models"])


def test_unbekannter_provider_leer():
    assert _run(model_catalog.list_models("bogus")) == {"models": [], "source": "curated"}


def test_openrouter_live_filtert_und_sortiert():
    model_catalog._cache.clear()
    body = {"data": [
        {"id": "z/vision-b", "name": "B", "architecture": {"input_modalities": ["text", "image"]}},
        {"id": "a/vision-a", "name": "A", "architecture": {"input_modalities": ["text", "image"]}},
        {"id": "c/text-only", "name": "C", "architecture": {"input_modalities": ["text"]}},
    ]}

    def handler(request: httpx.Request):
        assert "openrouter.ai" in str(request.url)
        return httpx.Response(200, json=body)

    r = _run(model_catalog.list_models("openrouter", transport=httpx.MockTransport(handler)))
    assert r["source"] == "live"
    # nur bild-fähige, nach id sortiert (text-only fällt raus)
    assert [m["id"] for m in r["models"]] == ["a/vision-a", "z/vision-b"]


def test_openrouter_fehler_faellt_auf_kuratiert():
    model_catalog._cache.clear()

    def handler(request: httpx.Request):
        return httpx.Response(500, text="boom")

    r = _run(model_catalog.list_models("openrouter", transport=httpx.MockTransport(handler)))
    assert r["source"] == "curated"
    assert r["models"] == model_catalog._CURATED["openrouter"]
