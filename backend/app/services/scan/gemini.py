"""
Scan-Variante B: Bilderkennung über Google Gemini (REST, kein SDK nötig).

Nur aktiv, wenn GEMINI_API_KEY gesetzt ist. Gemini liest aus einem Foto
(Einzelkarte ODER ganze Binderseite) die wesentlichen Felder pro Karte aus
und liefert sie als JSON-Liste. Die Auflösung gegen TCGdex passiert danach
serverseitig im Resolver (eine Quelle für Web UND Android).
"""

from __future__ import annotations

import base64
import json
import logging
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
- "confidence": deine Sicherheit 0.0–1.0, wie zuverlässig du Name UND Nummer gelesen hast

Leere/keine Karte enthaltende Fächer NICHT ausgeben.
Antworte AUSSCHLIESSLICH mit einem JSON-Array von Objekten, ohne Erklärungstext."""


def is_enabled(api_key: Optional[str]) -> bool:
    return bool(api_key)


async def extract(
    image_bytes: bytes,
    api_key: str,
    model: Optional[str] = None,
    mime_type: str = "image/jpeg",
) -> Optional[list[ScanRawRead]]:
    """
    Schickt das Bild an Gemini und liefert die erkannten Karten.
    None signalisiert einen harten Fehler (Aufrufer kann auf OCR ausweichen).
    """
    if not api_key:
        return None
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
        },
    }
    url = _ENDPOINT.format(model=model)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                params={"key": api_key},
                json=payload,
            )
    except httpx.HTTPError as exc:
        log.warning("Gemini-Request fehlgeschlagen: %s", exc)
        return None

    if resp.status_code != 200:
        log.warning("Gemini Status %s: %s", resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        log.warning("Gemini-Antwort nicht interpretierbar: %s", exc)
        return None

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return None

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
        )
        out.append(read)
    return out


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


def _norm_lang(v) -> Optional[str]:
    s = _str(v)
    if not s:
        return None
    s = s.upper()
    mapping = {"DE": "DE", "GER": "DE", "EN": "EN", "ENG": "EN",
               "JP": "JP", "JA": "JP", "JPN": "JP",
               "CN": "CN", "ZH": "CN", "FR": "FR", "ES": "ES", "IT": "IT"}
    return mapping.get(s, s[:2])
