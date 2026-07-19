"""
Reine Retry-/Backoff-Logik + Fehlerklassifikation für Gemini (Issue #21).

Kein echter API-Call, kein reales Warten: `do_post` liefert vorgefertigte
Antworten (oder wirft), `sleep` wird als Fake injiziert (protokolliert nur die
Wartezeiten). Async-Tests laufen ohne pytest-asyncio über asyncio.run().
"""

import asyncio

import httpx

from app.services.scan import gemini


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


def _seq(outcomes):
    """do_post, das nacheinander die vorgegebenen Antworten liefert/wirft."""
    it = iter(outcomes)

    async def do_post():
        item = next(it)
        if isinstance(item, Exception):
            raise item
        return item

    return do_post


def _run_retry(outcomes, backoffs=gemini._BACKOFF_SEKUNDEN):
    """Führt _post_mit_retry + _klassifiziere aus; gibt (Result, Wartezeiten)."""
    slept: list[float] = []

    async def sleep(seconds):
        slept.append(seconds)

    async def go():
        resp = await gemini._post_mit_retry(_seq(outcomes), sleep=sleep, backoffs=backoffs)
        return gemini._klassifiziere(resp)

    return asyncio.run(go()), slept


_OK_JSON = {
    "usageMetadata": {"totalTokenCount": 5},
    "candidates": [{"content": {"parts": [{"text": '[{"name": "Pikachu"}]'}]}}],
}


def test_429_dann_erfolg_genau_ein_retry():
    """429 → einmal warten (0.5s) → 200 mit Treffer; kein harter Fehler."""
    result, slept = _run_retry([FakeResp(429, text="rate"), FakeResp(200, _OK_JSON)])
    assert slept == [0.5]
    assert result.fehler_art is None
    assert result.reads and result.reads[0].name == "Pikachu"
    assert result.tokens == 5


def test_401_kein_retry_distinktes_signal():
    """401 ist dauerhaft → sofort zurück, KEIN Retry, distinkte Fehlerart."""
    result, slept = _run_retry([FakeResp(401, text="bad key")])
    assert slept == []
    assert result.fehler_art == gemini.FEHLER_KEY
    assert result.reads is None
    assert result.tokens is None


def test_403_kein_retry_key_signal():
    result, slept = _run_retry([FakeResp(403, text="forbidden")])
    assert slept == []
    assert result.fehler_art == gemini.FEHLER_KEY


def test_5xx_erschoepft_gemini_fehler():
    """Dauerhafte 5xx → Backoff 0.5→1→2, danach aufgeben (gemini_fehler)."""
    result, slept = _run_retry([FakeResp(503)] * 4)
    assert slept == [0.5, 1.0, 2.0]
    assert result.fehler_art == gemini.FEHLER_GEMINI
    assert result.reads is None


def test_429_erschoepft_ist_rate_limit():
    """Dauerhaftes 429 → nach erschöpften Retries als Rate-Limit gemeldet."""
    result, slept = _run_retry([FakeResp(429)] * 4)
    assert slept == [0.5, 1.0, 2.0]
    assert result.fehler_art == gemini.FEHLER_RATE


def test_netzfehler_wird_wiederholt_und_erschoepft():
    """httpx-Netz-/Timeout-Fehler sind transient → Retry, dann gemini_fehler."""
    result, slept = _run_retry([httpx.ConnectError("boom")] * 4)
    assert slept == [0.5, 1.0, 2.0]
    assert result.fehler_art == gemini.FEHLER_GEMINI


def test_netzfehler_dann_erfolg():
    """Erst Timeout, dann Treffer → ein Retry, kein Fehler."""
    result, slept = _run_retry([httpx.ReadTimeout("slow"), FakeResp(200, _OK_JSON)])
    assert slept == [0.5]
    assert result.fehler_art is None
    assert result.reads and result.reads[0].name == "Pikachu"


def test_200_unlesbar_ist_kein_harter_fehler():
    """200 ohne verwertbaren Inhalt → stiller OCR-Fallback (fehler_art None)."""
    result, slept = _run_retry([FakeResp(200, {"candidates": []})])
    assert slept == []
    assert result.fehler_art is None
    assert result.reads is None
    # Call fand statt (Tokens gebucht), auch wenn 0 Karten
    assert result.tokens == 0


def test_400_ohne_retry_als_gemini_fehler():
    """Andere 4xx (z. B. 400) sind dauerhaft → kein Retry, gemini_fehler."""
    result, slept = _run_retry([FakeResp(400, text="bad request")])
    assert slept == []
    assert result.fehler_art == gemini.FEHLER_GEMINI
