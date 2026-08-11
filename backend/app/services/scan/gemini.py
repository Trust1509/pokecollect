"""
Scan-Variante B: Bilderkennung über Google Gemini (REST, kein SDK nötig).

Nur aktiv, wenn ein Gemini-Key gesetzt ist. Gemini liest aus einem Foto
(Einzelkarte ODER ganze Binderseite) die wesentlichen Felder pro Karte aus
und liefert sie als JSON-Liste. Die Auflösung gegen TCGdex passiert danach
serverseitig im Resolver (eine Quelle für alle Clients).

Prompt, JSON→Karten-Parsing und die Retry-Schleife sind provider-neutral und
liegen in `vlm.py` (DRY, seit Issue #57 von OpenAI/OpenRouter mitbenutzt); hier
bleibt nur das Gemini-spezifische: generateContent-Payload, `?key=`-Auth und die
Klassifikation der Gemini-Antwortform (candidates/usageMetadata).
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Optional

import httpx

from app.services.scan import vlm
from app.services.scan.vlm import ReaderResult as GeminiResult  # geteilte Ergebnisform

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Prompt + Backoff/Retry-Status stammen aus dem gemeinsamen Kern.
_PROMPT = vlm.PROMPT
_RETRY_STATUS = vlm.RETRY_STATUS
_BACKOFF_SEKUNDEN = vlm.BACKOFF
_post_mit_retry = vlm.post_with_retry

# Nach außen unterscheidbare Fehlerarten. Dienen zugleich als `hinweis_art` in
# der Scan-Response (schemas/scan.py). Key/Rate teilen die Werte mit dem
# generischen VLM-Pfad; der harte Gemini-Fehler behält seinen eigenen Wert,
# damit die UI-Meldung „Gemini nicht erreichbar" korrekt bleibt.
FEHLER_KEY = vlm.FEHLER_KEY       # 401/403 – dauerhaft, KEIN Retry
FEHLER_RATE = vlm.FEHLER_RATE     # 429 erschöpft – Limit erreicht
FEHLER_GEMINI = "gemini_fehler"   # 5xx/Timeout/Netz/sonstiges erschöpft


def is_enabled(api_key: Optional[str]) -> bool:
    return bool(api_key)


async def extract(
    image_bytes: bytes,
    api_key: str,
    model: Optional[str] = None,
    mime_type: str = "image/jpeg",
    *,
    sleep=asyncio.sleep,
) -> GeminiResult:
    """
    Schickt das Bild an Gemini und liefert ein `GeminiResult`.

    Transiente Fehler (429/5xx, httpx-Timeout/Netzfehler) werden mit
    exponentiellem Backoff wiederholt (Issue #21); dauerhafte Fehler (401/403 =
    ungültiger/fehlender Key) NICHT. `sleep` ist injizierbar, damit Tests den
    Backoff ohne reales Warten durchlaufen.
    """
    if not api_key:
        return GeminiResult(None, None, None)
    model = model or DEFAULT_MODEL

    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "contents": [{
            "parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": mime_type, "data": b64}},
            ]
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.0,
            # "Thinking" für diese reine Extraktionsaufgabe abschalten → deutlich
            # schneller. (Wird von älteren Modellen ignoriert.)
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    url = _ENDPOINT.format(model=model)

    async with httpx.AsyncClient(timeout=60.0) as client:
        async def do_post():
            return await client.post(url, params={"key": api_key}, json=payload)

        resp = await _post_mit_retry(do_post, sleep=sleep)

    return _klassifiziere(resp)


def _klassifiziere(resp) -> GeminiResult:
    """Ordnet die (finale) HTTP-Antwort einer Fehlerart zu bzw. parst sie."""
    if resp is None:
        return GeminiResult(None, None, FEHLER_GEMINI)
    sc = resp.status_code
    if sc in (401, 403):
        log.warning("Gemini-Key ungültig/fehlt (Status %s) – Fallback auf OCR.", sc)
        return GeminiResult(None, None, FEHLER_KEY)
    if sc == 429:
        log.warning("Gemini-Rate-Limit erreicht (Status 429) – Fallback auf OCR.")
        return GeminiResult(None, None, FEHLER_RATE)
    if sc != 200:
        log.warning("Gemini Status %s: %s", sc, (resp.text or "")[:300])
        return GeminiResult(None, None, FEHLER_GEMINI)
    return _parse_erfolg(resp)


def _parse_erfolg(resp) -> GeminiResult:
    """
    Parst eine erfolgreiche (200) Antwort in Karten + Tokenzahl. Ein unlesbarer
    Inhalt ist KEIN harter Fehler (fehler_art=None): der Call fand statt (Tokens
    ggf. gebucht), es gab nur keine verwertbaren Karten → stiller OCR-Fallback.
    """
    try:
        data = resp.json()
    except ValueError as exc:
        log.warning("Gemini-Antwort kein JSON: %s", exc)
        return GeminiResult(None, None, None)

    # Erfolgreicher (kontingentierter) Call → Tokens an den Aufrufer melden
    try:
        tokens = int(data.get("usageMetadata", {}).get("totalTokenCount", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        tokens = 0

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        log.warning("Gemini-Antwort nicht interpretierbar: %s", exc)
        return GeminiResult(None, tokens, None)

    reads = vlm.reads_from_json(vlm.loads_tolerant(text))
    return GeminiResult(reads, tokens, None)
