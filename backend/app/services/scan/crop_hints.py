"""
Plausibilitäts-Sanitierung der Zuschnitt-Hinweise (Issue #36).

Bei mehreren Karten im Bild nimmt das Lese-Modell (Gemini/OpenAI/OpenRouter,
alle über `vlm.reads_from_json`) gelegentlich eine zu hohe Box bzw. ein zu
hohes Viereck — es schneidet dann eine Nachbarkarte oder ein Mappen-Label mit,
statt exakt an der Zielkarte zu enden. Das Frontend übernimmt bbox/quad für
den Foto-Zuschnitt (`cardCrop.ts::cropToCardPhoto`) weitgehend ungeprüft: der
bbox-Pfad prüft das Seitenverhältnis gar nicht, der quad-Pfad hat nur eine
lockere Schranke (`ratio >= 0.42`), die einen 1,5-Karten-Streifen (~0,48)
durchlässt. Lieber kein Hinweis als ein lügender (dieselbe Klasse wie bei
Preisen, `docs/agents/lehren.md` §4): unplausible Werte werden HIER auf None
gesetzt, damit die nächstbessere Zuschnitt-Stufe greift (quad → bbox →
zentriert — die Kaskade selbst bleibt Frontend-Sache).

`bbox`/`quad` sind Bild-ANTEILE (0..1 relativ zu Breite/Höhe). Ihr WIRKLICHES
(Pixel-)Seitenverhältnis hängt von den Bildmaßen ab — bei einem nicht
quadratischen Foto ergeben dieselben Anteile je nach Bildformat ein anderes
Pixel-Verhältnis. `vlm.py`/`gemini.py` sehen nur die Modell-JSON, nie das
Bild selbst, kennen die Maße also nicht. Deshalb sitzt diese Prüfung hier, im
Aufrufer, der das Foto hält (`api/v1/scan.py::scan`) — NICHT in
`vlm.py::_bbox`/`_quad`, die bleiben unverändert reine Parser der
Modell-Antwort (Format-/Typ-Prüfung, keine Verhältnis-Plausibilität).
"""

from __future__ import annotations

import io
import logging

from PIL import Image

from app.schemas.scan import ScanRawRead

log = logging.getLogger(__name__)

# Eine echte Karte ist ~63:88 mm (kurze:lange Seite) ≈ 0,716. Normalisiert als
# kurze/lange Seite ist dieses Verhältnis IMMER <= 1 — unabhängig davon, ob
# die Karte im Bild hoch oder quer (liegend) erfasst wurde; eine obere
# Schranke gibt es deshalb bewusst NICHT. Das Fehlerbild aus #36 ist ein zu
# HOHER Zuschnitt (mehrere Karten untereinander), der das Verhältnis nach
# UNTEN drückt (1,5-Karten-Streifen ≈ 0,48; 2-Karten-Streifen ≈ 0,36) — nie
# nach oben.
#
# 0,55 liegt klar UNTER einem handfotografierten Einzelbild mit spürbarer
# Perspektive (~0,6 — muss laut Bau-Brief #36 durchkommen: Handkameras
# verzerren beim Fotografieren einer echten Einzelkarte real) und klar ÜBER
# dem kleinsten bekannten Fehlerkennungs-Fall (1,5-Karten-Streifen, ~0,48 —
# muss verworfen werden). Im Zweifel lieber ein zu weites Band als ein zu
# enges: ein NICHT verworfener Fehlgriff verzerrt höchstens EIN Vorschaubild
# (die nächste Zuschnitt-Stufe existiert ja gerade deshalb); ein zu Unrecht
# verworfener Hinweis nimmt einem echten Einzelfoto den besten Zuschnitt weg.
_MIN_RATIO = 0.55


def _ratio(seite_a: float, seite_b: float) -> float:
    """Normalisiertes Seitenverhältnis (<=1), orientierungsunabhängig."""
    if seite_a <= 0 or seite_b <= 0:
        return 0.0
    kurz, lang = (seite_a, seite_b) if seite_a <= seite_b else (seite_b, seite_a)
    return kurz / lang


def _bbox_plausible(bbox: list[float], img_w: float, img_h: float) -> bool:
    """bbox = [x, y, w, h] als Bild-Anteile (0..1) — nur w/h zählen fürs Verhältnis."""
    if len(bbox) != 4:
        return False
    _, _, w, h = bbox
    return _ratio(w * img_w, h * img_h) >= _MIN_RATIO


def _quad_plausible(quad: list[list[float]], img_w: float, img_h: float) -> bool:
    """quad = 4 Eckpunkte [[x,y]…] (TL,TR,BR,BL) als Bild-Anteile (0..1)."""
    if len(quad) != 4 or any(len(p) != 2 for p in quad):
        return False
    pts = [(p[0] * img_w, p[1] * img_h) for p in quad]

    def dist(a: tuple[float, float], b: tuple[float, float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    # Gegenüberliegende Seiten gemittelt statt nur eine Seite je Richtung: ein
    # perspektivisch verzerrtes Viereck ist ein Trapez, keine Raute — erst der
    # Mittelwert schätzt die tatsächliche Karten-Breite/-Höhe robust genug.
    seite_a = (dist(pts[0], pts[1]) + dist(pts[2], pts[3])) / 2  # TL-TR / BR-BL
    seite_b = (dist(pts[1], pts[2]) + dist(pts[3], pts[0])) / 2  # TR-BR / BL-TL
    return _ratio(seite_a, seite_b) >= _MIN_RATIO


def sanitize_crop_hints(reads: list[ScanRawRead], image_bytes: bytes) -> list[ScanRawRead]:
    """
    Verwirft (None) unplausible bbox/quad auf `reads`, IN-PLACE, und gibt
    dieselbe Liste zurück. OCR-Reads haben nie bbox/quad (`ocr.py::extract`
    setzt sie nie) — für sie ist das ein No-Op, ohne dass der Aufrufer nach
    Engine unterscheiden müsste.
    """
    if not any(r.bbox or r.quad for r in reads):
        return reads  # nichts zu prüfen — Bild-Dekodierung sparen

    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img_w, img_h = img.size
    except Exception as exc:
        # Das Bild wurde vom Aufrufer schon akzeptiert (Content-Type/Größe,
        # s. api/v1/scan.py); ein hier unlesbares Bild ist kein Grund, den
        # sonst erfolgreichen Scan zu verwerfen — ohne Maße bleibt nur
        # ungeprüft, nicht abgelehnt (lieber kein Urteil als ein falsches).
        log.warning("Zuschnitt-Sanitierung: Bild nicht dekodierbar (%s) – Hinweise bleiben ungeprüft.", exc)
        return reads

    if img_w <= 0 or img_h <= 0:
        return reads

    for r in reads:
        if r.quad is not None and not _quad_plausible(r.quad, img_w, img_h):
            r.quad = None
        if r.bbox is not None and not _bbox_plausible(r.bbox, img_w, img_h):
            r.bbox = None
    return reads
