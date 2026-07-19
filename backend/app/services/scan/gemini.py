"""
Scan-Variante B: Bilderkennung über Google Gemini (REST, kein SDK nötig).

Nur aktiv, wenn GEMINI_API_KEY gesetzt ist. Gemini liest aus einem Foto
(Einzelkarte ODER ganze Binderseite) die wesentlichen Felder pro Karte aus
und liefert sie als JSON-Liste. Die Auflösung gegen TCGdex passiert danach
serverseitig im Resolver (eine Quelle für alle Clients).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.schemas.scan import ScanRawRead

log = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_PROMPT = """Du bist ein Experte für Pokémon-Sammelkarten (TCG).
Analysiere das Bild. Es zeigt entweder EINE Karte oder MEHRERE Karten
(z.B. eine ganze Binder-/Sammelmappen-Seite mit einem Raster aus Kartenfächern).

Gib für JEDE eindeutig erkennbare Pokémon-Karte ein Objekt zurück mit:
- "name": der auf der Karte gedruckte Kartenname (z.B. "Glurak ex", "Pikachu")
- "set_code": das kleine aufgedruckte Set-Kürzel unten (z.B. "PAF", "OBF", "MEW", "151"); null wenn unlesbar
- "number": die aufgedruckte Kartennummer wie sie dasteht (z.B. "007/091", "201/091"); null wenn unlesbar
- "language": Sprache der Karte als Kürzel: "DE", "EN", "JP", "CN", "FR", "ES", "IT"; null wenn unklar
- "position": die Position im Raster, von links nach rechts und oben nach unten gezählt, beginnend bei 0; bei Einzelkarte 0
- "box_2d": die Bounding-Box der Karte als [ymin, xmin, ymax, xmax], jeweils
  ganzzahlig von 0 bis 1000 (auf Bildhöhe/-breite normiert), möglichst eng um die Karte
- "corners": die VIER Eckpunkte der Karte als [[x,y],[x,y],[x,y],[x,y]] in der
  Reihenfolge oben-links, oben-rechts, unten-rechts, unten-links; x,y ganzzahlig
  0–1000. Für perspektivische Entzerrung – exakt an den Kartenecken, auch wenn die Karte schräg liegt.
- "confidence": deine Sicherheit 0.0–1.0, wie zuverlässig du Name UND Nummer gelesen hast

Leere/keine Karte enthaltende Fächer NICHT ausgeben.
Antworte AUSSCHLIESSLICH mit einem JSON-Array von Objekten, ohne Erklärungstext."""


# ── Retry-/Fehler-Klassifikation (Issue #21) ─────────────────────────────────

# Transiente HTTP-Status → erneut versuchen (Rate-Limit + Server-Fehler).
_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})

# Exponentieller Backoff: Wartezeit VOR jeder Wiederholung. Länge = maximale
# Anzahl Wiederholungen (also bis zu len+1 Versuche insgesamt): 0.5s → 1s → 2s.
_BACKOFF_SEKUNDEN: tuple[float, ...] = (0.5, 1.0, 2.0)

# Nach außen unterscheidbare Fehlerarten. Dienen zugleich als `hinweis_art` in
# der Scan-Response (schemas/scan.py), damit das UI „Rate-Limit erreicht" von
# „Gemini-Key ungültig" trennen kann.
FEHLER_KEY = "key_ungueltig"     # 401/403 – dauerhaft, KEIN Retry
FEHLER_RATE = "rate_limit"       # 429 erschöpft – Limit erreicht
FEHLER_GEMINI = "gemini_fehler"  # 5xx/Timeout/Netz/sonstiges erschöpft


@dataclass
class GeminiResult:
    """
    Ergebnis eines Gemini-Extraktionsversuchs.

    - reads:      erkannte Karten; None = kein verwertbares Ergebnis
                  (Aufrufer weicht auf lokale OCR aus).
    - tokens:     Tokenverbrauch eines ZÄHLBAREN Calls; None = kein
                  abrechenbarer Call (Fehler vor/ohne gültige Antwort) → der
                  Aufrufer bucht die Nutzung dann nicht (Issue #9).
    - fehler_art: None = ok bzw. kein harter Fehler; sonst FEHLER_* als
                  maschinenlesbarer Fallback-Grund.
    """
    reads: Optional[list[ScanRawRead]]
    tokens: Optional[int]
    fehler_art: Optional[str] = None


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


async def _post_mit_retry(do_post, *, sleep, backoffs=_BACKOFF_SEKUNDEN):
    """
    Pure, testbare Retry-Schleife. Ruft `do_post()` auf und wiederholt bei
    transienten Fehlern (Status in `_RETRY_STATUS` sowie httpx-Netz-/Timeout-
    Fehlern) mit exponentiellem Backoff; dauerhafte Fehler (z. B. 401/403)
    kehren sofort zurück (kein Retry).

    - do_post: async Callable → Response-artiges Objekt (`.status_code`,
      `.json()`, `.text`) ODER wirft `httpx.HTTPError`.
    - sleep:   async Callable(seconds) — im Test mockbar (kein echtes Warten).

    Rückgabe: die (letzte) Antwort, oder None bei erschöpften Netz-/Timeout-
    Fehlern (kein HTTP-Status verfügbar).
    """
    for i in range(len(backoffs) + 1):
        try:
            resp = await do_post()
        except httpx.HTTPError as exc:
            if i < len(backoffs):
                log.info("Gemini-Netzfehler (%s) – Retry in %ss", exc, backoffs[i])
                await sleep(backoffs[i])
                continue
            log.warning("Gemini-Request nach %d Versuchen fehlgeschlagen: %s", i + 1, exc)
            return None
        if resp.status_code in _RETRY_STATUS and i < len(backoffs):
            log.info("Gemini Status %s – Retry in %ss", resp.status_code, backoffs[i])
            await sleep(backoffs[i])
            continue
        return resp
    return None


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
    except (TypeError, ValueError):
        tokens = 0

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        log.warning("Gemini-Antwort nicht interpretierbar: %s", exc)
        return GeminiResult(None, tokens, None)

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return GeminiResult(None, tokens, None)

    out: list[ScanRawRead] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            continue
        read = ScanRawRead(
            name=_str(item.get("name")),
            set_code=_str(item.get("set_code")),
            number=_str(item.get("number")),
            language=_norm_lang(item.get("language")),
            position=_int(item.get("position"), default=idx),
            confidence=_float(item.get("confidence")),
            bbox=_bbox(item),
            quad=_quad(item),
        )
        out.append(read)
    return GeminiResult(out, tokens, None)


def _str(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _int(v, default=None) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _float(v) -> Optional[float]:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bbox(item: dict) -> Optional[list[float]]:
    """
    Wandelt Geminis Bounding-Box in [x, y, w, h] als Anteil 0..1 um.
    Bevorzugt das native box_2d-Format [ymin, xmin, ymax, xmax] (0..1000);
    akzeptiert als Fallback auch [x, y, w, h].
    """
    raw = item.get("box_2d")
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        try:
            ymin, xmin, ymax, xmax = (float(v) for v in raw)
        except (TypeError, ValueError):
            return None
        scale = 1000.0 if max(ymin, xmin, ymax, xmax) > 1.5 else 1.0
        x, y = xmin / scale, ymin / scale
        w, h = (xmax - xmin) / scale, (ymax - ymin) / scale
        if w <= 0 or h <= 0:
            return None
        return [x, y, w, h]

    raw = item.get("bbox")
    if isinstance(raw, (list, tuple)) and len(raw) == 4:
        try:
            box = [float(v) for v in raw]
        except (TypeError, ValueError):
            return None
        if any(v > 1.5 for v in box):
            box = [v / 100.0 for v in box]
        return box
    return None


def _quad(item: dict) -> Optional[list[list[float]]]:
    """Vier Eckpunkte [[x,y]…] (TL,TR,BR,BL) als Anteile 0..1; sonst None."""
    raw = item.get("corners") or item.get("quad")
    if not isinstance(raw, (list, tuple)) or len(raw) != 4:
        return None
    pts: list[list[float]] = []
    for p in raw:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            return None
        try:
            pts.append([float(p[0]), float(p[1])])
        except (TypeError, ValueError):
            return None
    scale = 1000.0 if max(max(p) for p in pts) > 1.5 else 1.0
    return [[p[0] / scale, p[1] / scale] for p in pts]


def _norm_lang(v) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    s = s.upper()
    mapping = {"DE": "DE", "GER": "DE", "EN": "EN", "ENG": "EN",
               "JP": "JP", "JA": "JP", "JPN": "JP",
               "CN": "CN", "ZH": "CN", "FR": "FR", "ES": "ES", "IT": "IT"}
    return mapping.get(s, s[:2])
