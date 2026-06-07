"""
Scan-Variante A: lokale OCR über Tesseract (kostenlos, offline).

Fallback, wenn kein GEMINI_API_KEY gesetzt ist.

- single: ganzes Bild → eine Karte (Name, Set-Kürzel, Nummer unten).
- binder: Bild wird anhand des bekannten Rasters (rows×cols) in Fächer
  zerlegt und jedes Fach einzeln gelesen. Das umgeht die schwierige
  Karten-Segmentierung – die Mappe IST bereits ein Raster.
- multi: lose Karten ohne Raster → Best-Effort als Einzel-Lesung
  (für Multi-Karten ist Gemini deutlich zuverlässiger).

Die OCR ist naturgemäß ungenau → niedrige Confidence, die Nachkontroll-
Routine im UI fängt unsichere Treffer ab.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Optional

from app.schemas.scan import ScanRawRead

log = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"\b(\d{1,3}\s*/\s*\d{1,3})\b")
_TG_RE = re.compile(r"\b([A-Z]{1,3}\d{1,3}\s*/\s*[A-Z]{1,3}\d{1,3})\b")
_SETCODE_RE = re.compile(r"\b([A-Z0-9]{2,5})\b")
_CJK_RE = re.compile(r"[぀-ヿ一-鿿]")


def is_enabled() -> bool:
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return False
    return True


def _ocr_text(img) -> str:
    import pytesseract
    for lang in ("deu+eng", "eng", None):
        try:
            return pytesseract.image_to_string(img, lang=lang) if lang else pytesseract.image_to_string(img)
        except Exception:
            continue
    return ""


def _guess_language(text: str) -> Optional[str]:
    if _CJK_RE.search(text):
        # grobe Heuristik: Hiragana/Katakana → JP, sonst CN
        if re.search(r"[぀-ヿ]", text):
            return "JP"
        return "CN"
    return None


def _parse(text: str) -> dict:
    """Heuristische Extraktion von Name, Set-Kürzel und Nummer aus OCR-Text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    number = None
    m = _NUMBER_RE.search(text) or _TG_RE.search(text)
    if m:
        number = re.sub(r"\s+", "", m.group(1))

    # Set-Kürzel: kurzer Großbuchstaben-Token, bevorzugt nahe der Nummer
    set_code = None
    for line in lines:
        if number and number.split("/")[0] in line.replace(" ", ""):
            for tok in _SETCODE_RE.findall(line):
                if not tok.isdigit() and 2 <= len(tok) <= 5:
                    set_code = tok
                    break
        if set_code:
            break

    # Name: erste hinreichend lange, überwiegend alphabetische Zeile von oben
    name = None
    for line in lines:
        letters = re.sub(r"[^A-Za-zÀ-ÿ]", "", line)
        if len(letters) >= 3 and len(letters) >= len(line) * 0.5:
            name = line
            break

    return {"name": name, "set_code": set_code, "number": number,
            "language": _guess_language(text)}


def extract(
    image_bytes: bytes,
    mode: str = "single",
    rows: int = 0,
    cols: int = 0,
) -> list[ScanRawRead]:
    if not is_enabled():
        log.warning("OCR nicht verfügbar (pytesseract/Tesseract fehlt).")
        return []
    from PIL import Image

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        log.warning("OCR: Bild nicht lesbar: %s", exc)
        return []

    reads: list[ScanRawRead] = []

    if mode == "binder" and rows > 0 and cols > 0:
        w, h = img.size
        cw, ch = w // cols, h // rows
        pos = 0
        for r in range(rows):
            for c in range(cols):
                cell = img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
                text = _ocr_text(cell)
                parsed = _parse(text)
                # leeres Fach überspringen
                if not parsed["name"] and not parsed["number"]:
                    pos += 1
                    continue
                reads.append(ScanRawRead(position=pos, confidence=0.3, **parsed))
                pos += 1
    else:
        text = _ocr_text(img)
        parsed = _parse(text)
        reads.append(ScanRawRead(position=0, confidence=0.3, **parsed))

    return reads
