"""
Gemeinsamer VLM-Kern + OpenAI-kompatibler Provider (Scan-Stufe B, Issue #57).

Rein, ohne Netz: `classify`/`_parse_success` bekommen ein Response-Double, die
JSON-Helfer werden direkt geprüft. Die Retry-Schleife ist bereits über
test_gemini_retry.py abgedeckt (gemeinsamer Code `vlm.post_with_retry`).
"""

import asyncio

import httpx

from app.services.scan import vlm


class FakeResp:
    """Minimales Response-Double: status_code, json(), text."""

    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("kein JSON")
        return self._json


def _openai_body(content, tokens=42):
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"total_tokens": tokens},
    }


# ── loads_tolerant ───────────────────────────────────────────────────────────

def test_loads_tolerant_plain_array():
    assert vlm.loads_tolerant('[{"name": "Pikachu"}]') == [{"name": "Pikachu"}]


def test_loads_tolerant_json_fence():
    text = '```json\n[{"name": "Glurak"}]\n```'
    assert vlm.loads_tolerant(text) == [{"name": "Glurak"}]


def test_loads_tolerant_surrounding_text():
    text = 'Hier die Karten:\n[{"name": "Relaxo"}]\nViel Erfolg!'
    assert vlm.loads_tolerant(text) == [{"name": "Relaxo"}]


def test_loads_tolerant_garbage_is_none():
    assert vlm.loads_tolerant("kein json hier") is None


def test_loads_tolerant_passes_through_non_str():
    assert vlm.loads_tolerant([{"a": 1}]) == [{"a": 1}]


# ── reads_from_json ──────────────────────────────────────────────────────────

def test_reads_from_json_list():
    reads = vlm.reads_from_json([
        {"name": "Pikachu", "number": "025/165", "set_code": "MEW"},
        {"name": "Glurak", "number": "006/165", "set_code": "MEW"},
    ])
    assert reads is not None and len(reads) == 2
    assert reads[0].name == "Pikachu" and reads[0].number == "025/165"
    assert reads[0].position == 0 and reads[1].position == 1


def test_reads_from_json_single_dict_is_wrapped():
    reads = vlm.reads_from_json({"name": "Pikachu", "number": "025/165"})
    assert reads is not None and len(reads) == 1
    assert reads[0].name == "Pikachu"


def test_reads_from_json_wrapper_object():
    """Manche Modelle im json_object-Modus umrahmen die Liste ({'cards': […]})."""
    reads = vlm.reads_from_json({"cards": [{"name": "Enton"}, {"name": "Entei"}]})
    assert reads is not None and [r.name for r in reads] == ["Enton", "Entei"]


def test_reads_from_json_box_2d_to_bbox():
    reads = vlm.reads_from_json([{"name": "X", "box_2d": [100, 200, 300, 400]}])
    assert reads and reads[0].bbox == [0.2, 0.1, 0.2, 0.2]


def test_reads_from_json_none_and_scalar():
    assert vlm.reads_from_json(None) is None
    assert vlm.reads_from_json("nope") is None


# ── classify / _parse_success (OpenAI-kompatible Antwortform) ─────────────────

def test_classify_200_liefert_reads():
    body = _openai_body('[{"name": "Pikachu", "confidence": 0.9}]', tokens=7)
    res = vlm.classify(FakeResp(200, body))
    assert res.fehler_art is None
    assert res.tokens == 7
    assert res.reads and res.reads[0].name == "Pikachu"


def test_classify_401_ist_key_fehler():
    res = vlm.classify(FakeResp(401, text="unauthorized"))
    assert res.fehler_art == vlm.FEHLER_KEY
    assert res.reads is None and res.tokens is None


def test_classify_429_ist_rate_limit():
    res = vlm.classify(FakeResp(429, text="slow down"))
    assert res.fehler_art == vlm.FEHLER_RATE


def test_classify_500_ist_reader_fehler():
    res = vlm.classify(FakeResp(500, text="boom"))
    assert res.fehler_art == vlm.FEHLER_VLM


def test_classify_none_ist_reader_fehler():
    """Erschöpfte Netz-/Timeout-Retries (kein HTTP-Status) → harter Reader-Fehler."""
    res = vlm.classify(None)
    assert res.fehler_art == vlm.FEHLER_VLM


def test_classify_200_ohne_choices_ist_weicher_fallback():
    """200 ohne choices UND ohne error (nur usage) → stiller OCR-Fallback."""
    res = vlm.classify(FakeResp(200, {"usage": {"total_tokens": 0}}))
    assert res.fehler_art is None
    assert res.reads is None


def test_classify_200_error_body_ist_harter_fehler():
    """200 mit Top-Level-error (z. B. OpenRouter 'kein Guthaben') → harter Fehler."""
    res = vlm.classify(FakeResp(200, {"error": {"message": "insufficient credits"}}))
    assert res.fehler_art == vlm.FEHLER_VLM   # UI zeigt Ursache statt still OCR
    assert res.reads is None


def test_classify_200_unlesbarer_inhalt_ist_weich():
    body = _openai_body("Ich kann das Bild leider nicht lesen.", tokens=3)
    res = vlm.classify(FakeResp(200, body))
    assert res.fehler_art is None
    assert res.reads is None      # kein JSON → keine Karten
    assert res.tokens == 3        # Call fand statt


def test_is_enabled():
    assert vlm.is_enabled("sk-abc") is True
    assert vlm.is_enabled("") is False
    assert vlm.is_enabled(None) is False


# ── _as_item_list-Härtung (Panel: bevorzugter Wrapper-Schlüssel) ──────────────

def test_wrapper_prefers_cards_over_scalar_list():
    """{'positions':[…], 'cards':[…]} → 'cards' gewinnt, nicht die Skalar-Liste."""
    reads = vlm.reads_from_json({"positions": [0, 1], "cards": [{"name": "A"}, {"name": "B"}]})
    assert reads and [r.name for r in reads] == ["A", "B"]


def test_wrapper_ignores_pure_scalar_list():
    """Ein Dict, dessen einzige Liste skalar ist, wird als EIN (leeres) Objekt gelesen."""
    reads = vlm.reads_from_json({"positions": [0, 1, 2]})
    assert reads is not None and len(reads) == 1  # als einzelnes Objekt, nicht die 3 Zahlen


# ── Echter extract()-Pfad via MockTransport (schließt die Mock-Lücke) ─────────

def _run(coro):
    return asyncio.run(coro)


def test_extract_real_path_parses_and_builds_headers():
    """Baut echten httpx-Request (Header!) + parst 200 — der bisher ungetestete Pfad."""
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers.get("Authorization")
        seen["title"] = request.headers.get("X-Title")
        return httpx.Response(200, json=_openai_body('[{"name":"Pikachu","number":"025/165"}]', tokens=11))

    res = _run(vlm.extract(
        b"\x89PNG-bytes", base_url="https://api.openai.com/v1",
        api_key="sk-test", model="gpt-4o-mini", title="PokeCollect",
        transport=httpx.MockTransport(handler)))
    assert seen["auth"] == "Bearer sk-test"
    assert seen["title"] == "PokeCollect"       # ASCII-Titel gesetzt
    assert res.fehler_art is None
    assert res.reads and res.reads[0].name == "Pikachu"
    assert res.tokens == 11


def test_extract_non_ascii_title_baut_und_crasht_nicht():
    """B1-Regression: ein non-ASCII X-Title darf den Request-Bau NICHT sprengen."""
    def handler(request: httpx.Request):
        assert "X-Title" not in request.headers   # non-ASCII wurde verworfen
        return httpx.Response(200, json=_openai_body("[]", tokens=1))

    res = _run(vlm.extract(
        b"x", base_url="https://openrouter.ai/api/v1", api_key="sk-or",
        model="m", title="PokéCollect", referer="http://köln.example",
        transport=httpx.MockTransport(handler)))
    assert res.fehler_art is None      # kein Crash
    assert res.reads == []             # leere, aber gültige Liste


def test_extract_200_error_body_ist_harter_fehler():
    """OpenRouter meldet 'kein Guthaben' als 200+error → FEHLER_VLM (nicht still)."""
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"error": {"message": "insufficient credits"}})

    res = _run(vlm.extract(
        b"x", base_url="https://openrouter.ai/api/v1", api_key="sk-or",
        model="m", transport=httpx.MockTransport(handler)))
    assert res.fehler_art == vlm.FEHLER_VLM


def test_extract_ohne_key_ist_stiller_noop():
    res = _run(vlm.extract(b"x", base_url="https://api.openai.com/v1",
                           api_key="", model="m"))
    assert res.reads is None and res.tokens is None and res.fehler_art is None
