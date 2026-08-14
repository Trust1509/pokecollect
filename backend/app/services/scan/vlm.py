"""
Gemeinsamer Kern der Bild-Lese-Provider (Scan-Stufe B) + der OpenAI-kompatible
Provider für OpenAI **und** OpenRouter.

Die Erkennung „welche Karte ist das?" (Name/Nummer/Set aus einem Foto) ist ab
Issue #57 pluggbar: der Nutzer wählt in den Einstellungen das Lese-Modell
(Gemini · OpenAI · OpenRouter · lokale OCR). Gemini spricht seine eigene
generateContent-REST-API (siehe `gemini.py`); OpenAI und OpenRouter sprechen
DIESELBE OpenAI-kompatible `chat/completions`-API — sie unterscheiden sich nur
in der `base_url`, dem Modellnamen und dem Key. Deshalb genügt EINE
Implementierung (`extract`) für beide.

Provider-neutral (und deshalb hier, nicht im Gemini-Modul):
- `PROMPT`          – der identische Lese-Auftrag für jedes VLM.
- `ReaderResult`    – das Ergebnis eines Leseversuchs.
- `reads_from_json` – JSON-Antwort → `ScanRawRead`-Liste (beide Provider liefern
                      dasselbe von PROMPT vorgegebene Schema).
- `post_with_retry` – Backoff-Schleife für transiente HTTP-/Netzfehler.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from app.schemas._validators import strip_control_chars
from app.schemas.scan import ScanRawRead

log = logging.getLogger(__name__)

# ── Lese-Auftrag (identisch für jedes VLM) ───────────────────────────────────
PROMPT = """Du bist ein Experte für Pokémon-Sammelkarten (TCG).
Analysiere das Bild. Es zeigt entweder EINE Karte (ggf. mit angeschnittenen
Nachbarkarten am Rand) oder MEHRERE Karten (z.B. eine ganze Binder-/
Sammelmappen-Seite mit einem Raster aus Kartenfächern).

WICHTIG — welche Karten du auswertest:
- Werte NUR vollständig (oder nahezu vollständig) sichtbare Karten aus. Ist eine
  Karte klar der Bildmittelpunkt bzw. die deutlich größte, ist SIE die Zielkarte.
- IGNORIERE nur teilweise sichtbare Nachbarkarten, die am oberen, unteren oder
  seitlichen Bildrand angeschnitten sind — sie gehören NICHT zur Zielkarte.
- IGNORIERE Register-, Trenn- und Beschriftungsstreifen (Tab-Labels) der
  Sammelmappe; das sind KEINE Karten.

Der ZUVERLÄSSIGE Schlüssel einer Karte ist die aufgedruckte Sammelnummer plus das
Set-Kürzel/-Symbol — NICHT der Name. Lies daher Nummer und Set besonders sorgfältig.

Gib für JEDE so ausgewählte Pokémon-Karte ein Objekt zurück mit:
- "name": AUSSCHLIESSLICH der Kartenname aus der Titelzeile OBEN auf der Karte
  (z.B. "Glurak ex", "Pikachu"). Übernimm NIEMALS Text aus Attacken, Fähigkeiten,
  Evolutions-Hinweisen, Sammelmappen-Labels oder sonstigem Fließtext als Namen.
  Wenn der Titel nicht sicher lesbar ist, setze null — rate NICHT.
- "number": die aufgedruckte Sammelnummer GENAU wie sie (meist unten) auf der
  Karte steht, im Format "NNN/NNN" (z.B. "113/217", "068/172") bzw. wie gedruckt;
  null wenn unlesbar. Zusammen mit dem Set der eindeutige Schlüssel.
- "set_code": das kleine aufgedruckte Set-Kürzel bzw. Set-Symbol unten (z.B.
  "PAF", "OBF", "MEW", "151"); null wenn unlesbar. Ebenfalls Teil des Schlüssels.
- "language": Sprache der Karte als Kürzel: "DE", "EN", "JP", "CN", "FR", "ES", "IT"; null wenn unklar
- "position": die Position im Raster, von links nach rechts und oben nach unten gezählt, beginnend bei 0; bei Einzelkarte 0
- "box_2d": die Bounding-Box NUR dieser einen Karte als [ymin, xmin, ymax, xmax],
  jeweils ganzzahlig von 0 bis 1000 (auf Bildhöhe/-breite normiert), möglichst eng
  um die Karte — OHNE angeschnittene Nachbarn oder Register-Labels
- "corners": die VIER Eckpunkte der Karte als [[x,y],[x,y],[x,y],[x,y]] in der
  Reihenfolge oben-links, oben-rechts, unten-rechts, unten-links; x,y ganzzahlig
  0–1000. Für perspektivische Entzerrung – exakt an den Kartenecken, auch wenn die Karte schräg liegt.
- "confidence": deine Sicherheit 0.0–1.0, wie zuverlässig du NUMMER UND Name gelesen hast

Leere Fächer sowie angeschnittene Rand-Karten NICHT ausgeben.
Antworte AUSSCHLIESSLICH mit einem JSON-Array von Objekten, ohne Erklärungstext."""


# ── Fehlerarten (maschinenlesbar, zugleich `hinweis_art` in schemas/scan.py) ──
# Key/Rate teilen dieselben Werte wie der Gemini-Pfad, damit das UI beide Provider
# gleich behandeln kann; der generische Server-/Netzfehler bekommt einen eigenen
# Wert („reader_fehler"), damit die UI-Meldung nicht fälschlich „Gemini" sagt.
FEHLER_KEY = "key_ungueltig"   # 401/403 – dauerhaft, KEIN Retry
FEHLER_RATE = "rate_limit"     # 429 erschöpft – Limit erreicht
FEHLER_VLM = "reader_fehler"   # 5xx/Timeout/Netz/sonstiges erschöpft


@dataclass
class ReaderResult:
    """
    Ergebnis eines Leseversuchs eines beliebigen VLM-Providers.

    - reads:      erkannte Karten; None = kein verwertbares Ergebnis
                  (Aufrufer weicht auf lokale OCR aus).
    - tokens:     Tokenverbrauch eines ZÄHLBAREN Calls; None = kein
                  abrechenbarer Call (Fehler vor/ohne gültige Antwort).
    - fehler_art: None = ok bzw. kein harter Fehler; sonst FEHLER_* als
                  maschinenlesbarer Fallback-Grund.
    """
    reads: Optional[list[ScanRawRead]]
    tokens: Optional[int]
    fehler_art: Optional[str] = None


# ── Retry-/Backoff-Infrastruktur (transiente Fehler) ─────────────────────────
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
BACKOFF: tuple[float, ...] = (0.5, 1.0, 2.0)


async def post_with_retry(do_post, *, sleep, backoffs=BACKOFF):
    """
    Pure, testbare Retry-Schleife (provider-neutral). Ruft `do_post()` auf und
    wiederholt bei transienten Fehlern (Status in `RETRY_STATUS` sowie
    httpx-Netz-/Timeout-Fehlern) mit exponentiellem Backoff; dauerhafte Fehler
    (z. B. 401/403) kehren sofort zurück (kein Retry).

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
                log.info("VLM-Netzfehler (%s) – Retry in %ss", exc, backoffs[i])
                await sleep(backoffs[i])
                continue
            log.warning("VLM-Request nach %d Versuchen fehlgeschlagen: %s", i + 1, exc)
            return None
        if resp.status_code in RETRY_STATUS and i < len(backoffs):
            log.info("VLM Status %s – Retry in %ss", resp.status_code, backoffs[i])
            await sleep(backoffs[i])
            continue
        return resp
    return None


# ── JSON-Antwort → ScanRawRead (beide Provider, gleiches PROMPT-Schema) ───────

def loads_tolerant(text: Any) -> Any:
    """
    Robustes JSON-Parsen der Modell-Antwort. VLMs verpacken JSON gern in
    ```json …```-Fences oder umrahmen es mit Fließtext. Toleriert beides;
    liefert das geparste Objekt oder None.
    """
    if not isinstance(text, str):
        return text
    s = text.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z0-9]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        pass
    # Fallback: das erste vollständige Array/Objekt aus umgebendem Text schneiden.
    for open_c, close_c in (("[", "]"), ("{", "}")):
        i, j = s.find(open_c), s.rfind(close_c)
        if 0 <= i < j:
            try:
                return json.loads(s[i:j + 1])
            except (ValueError, TypeError):
                continue
    return None


def reads_from_json(parsed: Any) -> Optional[list[ScanRawRead]]:
    """
    Wandelt die (bereits geparste) VLM-Antwort in `ScanRawRead`-Objekte um.
    None = kein verwertbares Schema → der Aufrufer weicht auf OCR aus.
    """
    items = _as_item_list(parsed)
    if items is None:
        return None
    out: list[ScanRawRead] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        out.append(ScanRawRead(
            name=_str(item.get("name")),
            set_code=_str(item.get("set_code")),
            number=_str(item.get("number")),
            language=_norm_lang(item.get("language")),
            position=_int(item.get("position"), default=idx),
            confidence=_float(item.get("confidence")),
            bbox=_bbox(item),
            quad=_quad(item),
        ))
    return out


# Bekannte Wrapper-Schlüssel, unter denen Modelle im json_object-Modus die
# Kartenliste ablegen. Bevorzugt vor „irgendeiner Liste", damit z. B.
# {"positions": [...], "cards": [...]} korrekt „cards" wählt.
_WRAPPER_KEYS = ("cards", "results", "items", "data", "karten")


def _as_item_list(parsed: Any) -> Optional[list]:
    """
    Normalisiert auf eine Liste von Karten-Objekten. Akzeptiert:
    - ein JSON-Array (der Regelfall aus PROMPT),
    - ein einzelnes Karten-Objekt (→ Liste mit einem Element),
    - ein Wrapper-Objekt wie {"cards": [...]} (manche Modelle im json_object-Modus).
    """
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        if _looks_like_card(parsed):
            return [parsed]
        for key in _WRAPPER_KEYS:
            if isinstance(parsed.get(key), list):
                return parsed[key]
        # Sonst die erste Liste, deren Elemente Objekte (Karten) sind — NICHT
        # irgendeine Skalar-Liste (z. B. eine Positions-/Index-Liste).
        for value in parsed.values():
            if isinstance(value, list) and (not value or isinstance(value[0], dict)):
                return value
        return [parsed]
    return None


def _looks_like_card(d: dict) -> bool:
    return any(k in d for k in
               ("name", "number", "set_code", "box_2d", "corners", "bbox", "quad"))


def _str(v) -> Optional[str]:
    if v is None:
        return None
    # Steuerzeichen aus der Modell-Antwort ENTFERNEN (#55): ScanRawRead lehnt
    # sie als Client-Eingabe ab — aus einem LLM-JSON („") wäre das ein
    # Absturz mitten im Scan statt eines sauberen OCR-Rückfalls.
    s = strip_control_chars(str(v)).strip()
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
    Wandelt die Bounding-Box in [x, y, w, h] als Anteil 0..1 um.
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


# ── OpenAI-kompatibler Provider (OpenAI + OpenRouter) ─────────────────────────

def is_enabled(api_key: Optional[str]) -> bool:
    return bool(api_key)


async def extract(
    image_bytes: bytes,
    *,
    base_url: str,
    api_key: str,
    model: str,
    mime_type: str = "image/jpeg",
    referer: Optional[str] = None,
    title: Optional[str] = None,
    sleep=asyncio.sleep,
    transport=None,
) -> ReaderResult:
    """
    Schickt das Bild an einen OpenAI-kompatiblen `chat/completions`-Endpunkt
    (OpenAI oder OpenRouter) und liefert ein `ReaderResult`.

    `base_url` ist der API-Stamm ohne Pfad, z. B. "https://api.openai.com/v1"
    oder "https://openrouter.ai/api/v1". `referer`/`title` sind optionale
    OpenRouter-Etikette-Header (werden von OpenAI ignoriert). `transport` ist ein
    optionaler httpx-Transport für Tests.

    Wirft NIE: jeder Fehler (auch beim Request-Bau) wird zu einem `ReaderResult`
    mit `FEHLER_VLM`, damit der Scan-Handler sauber auf lokale OCR ausweichen
    kann statt mit 500 abzustürzen.
    """
    if not api_key:
        return ReaderResult(None, None, None)

    b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": model,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": PROMPT},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
            ],
        }],
        "temperature": 0.0,
        "max_tokens": 4096,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    # HTTP-Header sind ASCII/latin-1: ein non-ASCII-Wert (z. B. „é") ließe httpx
    # schon beim Request-Bau werfen. Optionale Etikette-Header nur setzen, wenn
    # rein ASCII — sonst weglassen (sie sind unkritisch).
    if referer and referer.isascii():
        headers["HTTP-Referer"] = referer
    if title and title.isascii():
        headers["X-Title"] = title
    url = base_url.rstrip("/") + "/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=60.0, transport=transport) as client:
            async def do_post():
                return await client.post(url, headers=headers, json=payload)

            resp = await post_with_retry(do_post, sleep=sleep)
    except Exception as exc:  # Adapter darf NIE in den Handler werfen (→ 500)
        log.warning("VLM-Request unerwartet fehlgeschlagen: %s", type(exc).__name__)
        return ReaderResult(None, None, FEHLER_VLM)

    return classify(resp)


def classify(resp) -> ReaderResult:
    """Ordnet die (finale) HTTP-Antwort einer Fehlerart zu bzw. parst sie."""
    if resp is None:
        return ReaderResult(None, None, FEHLER_VLM)
    sc = resp.status_code
    if sc in (401, 403):
        log.warning("VLM-Key ungültig/fehlt (Status %s) – Fallback auf OCR.", sc)
        return ReaderResult(None, None, FEHLER_KEY)
    if sc == 429:
        log.warning("VLM-Rate-Limit erreicht (Status 429) – Fallback auf OCR.")
        return ReaderResult(None, None, FEHLER_RATE)
    if sc != 200:
        log.warning("VLM Status %s: %s", sc, (getattr(resp, "text", "") or "")[:300])
        return ReaderResult(None, None, FEHLER_VLM)
    return _parse_success(resp)


def _parse_success(resp) -> ReaderResult:
    """
    Parst eine erfolgreiche (200) OpenAI-kompatible Antwort. Ein unlesbarer
    Inhalt ist KEIN harter Fehler (fehler_art=None): der Call fand statt, es gab
    nur keine verwertbaren Karten → stiller OCR-Fallback.
    """
    try:
        data = resp.json()
    except ValueError as exc:
        log.warning("VLM-Antwort kein JSON: %s", exc)
        return ReaderResult(None, None, None)

    try:
        tokens = int((data.get("usage") or {}).get("total_tokens", 0) or 0)
    except (TypeError, ValueError, AttributeError):
        tokens = 0

    # Manche OpenAI-kompatiblen Anbieter (v. a. OpenRouter) melden einen HARTEN
    # Fehler als 200 mit Top-Level-"error" (z. B. Guthaben leer, Modell gesperrt)
    # statt mit 4xx/5xx. Das ist KEINE unlesbare Karte → als harten Reader-Fehler
    # behandeln, damit das UI eine Ursache zeigt statt still auf OCR zu wechseln.
    if isinstance(data, dict) and data.get("error") and not data.get("choices"):
        detail = data["error"].get("message") if isinstance(data["error"], dict) else data["error"]
        log.warning("VLM 200 mit Fehlerobjekt – Fallback auf OCR: %s", str(detail)[:200])
        return ReaderResult(None, tokens, FEHLER_VLM)

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        log.warning("VLM-Antwort ohne choices/content – Fallback auf OCR.")
        return ReaderResult(None, tokens, None)

    reads = reads_from_json(loads_tolerant(text))
    return ReaderResult(reads, tokens, None)
