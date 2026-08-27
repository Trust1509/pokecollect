"""
#36: Plausibilitäts-Sanitierung der Zuschnitt-Hinweise (bbox/quad).

Reine Geometrie, netzfrei — kein DB-/HTTP-Fixture nötig. Prüft
`app.services.scan.crop_hints`, den EINEN gemeinsamen Aufrufer-Ort für
bbox/quad aus allen drei VLM-Lese-Engines (Gemini/OpenAI/OpenRouter über
`vlm.reads_from_json`): bei mehreren Karten im Bild nimmt das Modell manchmal
eine zu hohe Box/ein zu hohes Viereck (schneidet Nachbarkarte/Label mit) —
unplausible Werte müssen auf None fallen, damit die nächstbessere
Zuschnitt-Stufe im Frontend greift (quad → bbox → zentriert).

Testaufbau je Geometrie-Fall: `ratio = kurze/lange Seite` (>=0,55 = plausibel,
Konstante + Begründung in crop_hints.py). Die exakten Zahlen sind vorab per
Skript verifiziert (keine Handrechnung im Test).

Zwei Fälle beweisen ausdrücklich, dass die echten BILDMASSE gebraucht werden,
nicht nur die Anteile (Bau-Brief-Befund: "auch quad braucht die Bildmaße"):
- T6 (quad): bei einem nicht-quadratischen Bild sieht ein 2-Karten-Streifen in
  reinen Anteilen plausibel aus (naive Rechnung ≈0,70) — erst mit den echten
  Pixel-Maßen zeigt sich das wahre Verhältnis (≈0,36) und wird verworfen.
- T10 (bbox): umgekehrt sieht eine echte Einzelkarte in reinen Anteilen
  unplausibel aus (naive Rechnung ≈0,36) — erst mit den echten Pixel-Maßen
  zeigt sich, dass sie plausibel ist (≈0,71) und bleibt erhalten.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.schemas.scan import ScanRawRead
from app.services.scan.crop_hints import (
    _bbox_plausible, _quad_plausible, sanitize_crop_hints,
)


def _png_bytes(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(10, 20, 30)).save(buf, format="PNG")
    return buf.getvalue()


# ── quad ──────────────────────────────────────────────────────────────────

def test_quad_karten_verhaeltnis_bleibt_erhalten():
    """Ein sauberes Karten-Viereck (~0,716) übersteht die Sanitierung unverändert."""
    quad = [[0.100, 0.050], [0.415, 0.050], [0.415, 0.490], [0.100, 0.490]]
    assert _quad_plausible(quad, 1000, 1000)


def test_quad_leichte_perspektive_bleibt_erhalten():
    """
    Trapez (oben schmaler als unten, echte Perspektive) mit Verhältnis ~0,6 —
    die Randbedingung aus dem Bau-Brief: ein von Hand fotografiertes
    Einzelkartenfoto mit Perspektive MUSS durchkommen.
    """
    quad = [[0.300, 0.100], [0.700, 0.100], [0.780, 0.900], [0.220, 0.900]]
    assert _quad_plausible(quad, 1000, 1000)


def test_quad_anderthalb_karten_streifen_wird_verworfen():
    """1,5-Karten-Streifen (ratio ≈ 0,48) ist die kleinste bekannte Fehlerkennung."""
    quad = [[0.100, 0.050], [0.730, 0.050], [0.730, 1.370], [0.100, 1.370]]
    assert not _quad_plausible(quad, 1000, 1000)


def test_quad_zwei_karten_streifen_wird_verworfen():
    """2-Karten-Streifen (ratio ≈ 0,36) — deutlicher Fall derselben Fehlerklasse."""
    quad = [[0.100, 0.050], [0.730, 0.050], [0.730, 1.810], [0.100, 1.810]]
    assert not _quad_plausible(quad, 1000, 1000)


def test_quad_querformat_karte_bleibt_erhalten():
    """Liegende Karte: das ROTIERTE Verhältnis zählt, sie darf nicht verworfen werden."""
    quad = [[0.100, 0.050], [0.540, 0.050], [0.540, 0.365], [0.100, 0.365]]
    assert _quad_plausible(quad, 1000, 1000)


def test_quad_braucht_echte_bildmasse_nicht_nur_anteile():
    """
    Nicht-quadratisches Bild (500x2000): in reinen Anteilen sieht dieser
    2-Karten-Streifen plausibel aus (naive Rechnung ≈0,70 ohne Bildmaße) —
    erst mit den echten Pixel-Maßen (126x352 ≈ 0,36) zeigt sich der Fehlgriff.
    """
    quad = [[0.1, 0.05], [0.352, 0.05], [0.352, 0.226], [0.1, 0.226]]
    # Gegenprobe: OHNE Skalierung (Bildmaße 1x1) sähe es plausibel aus — der
    # Bug, den diese Prüfung verhindern soll.
    assert _quad_plausible(quad, 1, 1) is True
    assert _quad_plausible(quad, 500, 2000) is False


# ── bbox ──────────────────────────────────────────────────────────────────

def test_bbox_karten_verhaeltnis_bleibt_erhalten():
    bbox = [0.10, 0.05, 0.315, 0.44]
    assert _bbox_plausible(bbox, 1000, 1000)


def test_bbox_doppelte_hoehe_wird_verworfen():
    """bbox doppelt so hoch wie kartengerecht (ratio ≈ 0,36) — der #36-Fehlgriff."""
    bbox = [0.10, 0.05, 0.315, 0.88]
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_bbox_querformat_karte_bleibt_erhalten():
    """Liegende Karte (breiter als hoch) — das rotierte Verhältnis zählt."""
    bbox = [0.10, 0.05, 0.44, 0.315]
    assert _bbox_plausible(bbox, 1000, 1000)


def test_bbox_braucht_echte_bildmasse_nicht_nur_anteile():
    """
    Nicht-quadratisches Bild (2000x1000): in reinen Anteilen sieht diese echte
    Einzelkarte unplausibel aus (naive Rechnung ≈0,36 ohne Bildmaße) — erst
    mit den echten Pixel-Maßen (200x280 ≈ 0,71) zeigt sich, dass sie stimmt.
    Umgekehrter Fehlerfall zu oben: hier würde eine ungeprüfte Anteils-Rechnung
    ein GUTES Foto zu Unrecht verwerfen.
    """
    bbox = [0.1, 0.2, 0.1, 0.28]
    assert _bbox_plausible(bbox, 1, 1) is False
    assert _bbox_plausible(bbox, 2000, 1000) is True


# ── sanitize_crop_hints (öffentliche Funktion, wie scan.py sie aufruft) ─────

def test_sanitize_crop_hints_bildmasse_werden_korrekt_zugeordnet():
    """
    End-to-End über die öffentliche Funktion mit einem ECHTEN (per PIL
    erzeugten) 800x600-Bild: prüft, dass `img.size` (Breite, Höhe) nicht
    vertauscht in die Verhältnis-Rechnung eingeht — eine Karte mit
    Pixel-Maßen 200x280 (ratio 0,71, plausibel) sähe bei vertauschten
    Bildmaßen (600x800 statt 800x600) unplausibel aus (ratio 0,40).
    """
    image_bytes = _png_bytes(800, 600)
    read = ScanRawRead(name="test36-karte", bbox=[0.1, 0.1, 200 / 800, 280 / 600])
    out = sanitize_crop_hints([read], image_bytes)
    assert out[0].bbox == pytest.approx([0.1, 0.1, 200 / 800, 280 / 600])


def test_sanitize_crop_hints_verwirft_gemischt_und_laesst_plausibles_stehen():
    """Mischliste: die unplausible Box fällt, die plausible bleibt, andere Felder unberührt."""
    image_bytes = _png_bytes(1000, 1000)
    gut = ScanRawRead(name="test36-gut", number="007/091", bbox=[0.10, 0.05, 0.315, 0.44])
    schlecht = ScanRawRead(name="test36-schlecht", quad=[[0.1, 0.05], [0.73, 0.05], [0.73, 1.81], [0.1, 1.81]])
    out = sanitize_crop_hints([gut, schlecht], image_bytes)
    assert out[0].bbox == [0.10, 0.05, 0.315, 0.44]
    assert out[0].number == "007/091"
    assert out[1].quad is None


def test_sanitize_crop_hints_undecodierbares_bild_faellt_offen_aus():
    """
    Ein nicht dekodierbares Bild darf den sonst erfolgreichen Scan nicht zum
    Absturz bringen — ohne Bildmaße bleibt der Hinweis UNGEPRÜFT, nicht
    verworfen (kein falsches Urteil, aber auch kein 500 im Aufrufer).
    """
    read = ScanRawRead(bbox=[0.1, 0.1, 0.315, 0.44])
    out = sanitize_crop_hints([read], b"das-ist-kein-bild")
    assert out[0].bbox == [0.1, 0.1, 0.315, 0.44]


def test_sanitize_crop_hints_ohne_zuschnitt_hinweise_ist_no_op():
    """
    OCR-Reads haben nie bbox/quad — muss klaglos durchlaufen, nichts wird
    angefasst. GRENZE (Lehren §1): dieses Verhalten ist DOPPELT redundant
    abgesichert (die "nichts zu prüfen"-Kurzschluss-Prüfung ganz oben UND die
    einzelnen `is not None`-Wächter in der Schleife) — kein einzelner
    Sabotage-Schnitt an nur EINER der beiden Stellen bringt genau diesen Test
    zum Kippen, weil die jeweils andere Stelle ihn trägt. Echtes, dekodierbares
    Bild (nicht kaputte Bytes), damit die Aussage nicht zufällig am
    Fehlerfall-Rückfall (siehe Test oben) hängt, sondern wirklich an diesen
    beiden Wächtern.
    """
    image_bytes = _png_bytes(500, 500)
    read = ScanRawRead(name="test36-ocr", number="025/165")
    out = sanitize_crop_hints([read], image_bytes)
    assert out[0].bbox is None
    assert out[0].quad is None
