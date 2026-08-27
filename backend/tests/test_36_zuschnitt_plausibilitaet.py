"""
#36: Plausibilitäts-Sanitierung der Zuschnitt-Hinweise (bbox/quad).

Reine Geometrie, netzfrei — kein DB-/HTTP-Fixture nötig (Ausnahme: die beiden
Verdrahtungs-/Auswahl-Tests der Panel-Nacharbeit unten, die über den echten
Endpunkt POST /api/v1/scan laufen, weil dort scan.py selbst entscheidet, nicht
crop_hints.py allein). Prüft `app.services.scan.crop_hints`, den EINEN
gemeinsamen Aufrufer-Ort für bbox/quad aus allen drei VLM-Lese-Engines
(Gemini/OpenAI/OpenRouter über `vlm.reads_from_json`): bei mehreren Karten im
Bild nimmt das Modell manchmal eine zu hohe/zu große Box bzw. ein zu
hohes/großes Viereck (schneidet Nachbarkarte/Mappenseite/Label mit) —
unplausible Werte müssen auf None fallen. WICHTIG (Panel-Nacharbeit #36,
Auflage 6 — korrigiert einen Fehler, der bis dahin genau in diesem Absatz
stand): Das Frontend hat KEINE Kaskade "quad → bbox → zentriert". Verworfen
heißt: kein eigener Foto-Zuschnitt, die Karte bekommt das Katalogbild statt
eines eigenen Fotos (Details: Moduldocstring in `crop_hints.py`).

Testaufbau je Geometrie-Fall: `ratio = kurze/lange Seite`, plausibel im
Band [0,55; 0,92] (Konstanten + Begründung in crop_hints.py). Die exakten
Zahlen sind vorab per Skript verifiziert (keine Handrechnung im Test).

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
    _bbox_plausible, _bbox_reject_reason, _quad_plausible, sanitize_crop_hints,
)
from app.services.scan.vlm import ReaderResult

# Wiederverwendet (Panel-Nacharbeit #36, Block 7 des Bau-Briefs): dieselbe
# Fixture wie in test_scan_reader.py, per Import geteilt statt dupliziert —
# baut Provider=OpenAI + Test-Key auf, mockt vlm.extract und resolve_reads
# hermetisch. `client`/`png_bytes` kommen aus conftest.py (dateiübergreifend
# automatisch verfügbar), `reader_openai` ist lokal in test_scan_reader.py
# definiert und wird hier bewusst importiert statt kopiert (DRY).
from test_scan_reader import reader_openai  # noqa: F401 — pytest-Fixture, nicht direkt benutzt


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


# ── Panel-Nacharbeit #36, Auflage 1 (BLOCKER): Auswahl vor Sanitierung ──────
#
# Beide Tests unten gehen bewusst über den ECHTEN Endpunkt POST /api/v1/scan
# (reader_openai + png_bytes aus der vorhandenen Infrastruktur, Block 7 des
# Bau-Briefs) statt `sanitize_crop_hints` direkt aufzurufen: die Auswahl der
# Hauptkarte (mode=single) UND die Reihenfolge Auswahl→Sanitierung sitzen in
# `api/v1/scan.py::scan`, nicht in crop_hints.py — nur ein Test über den
# echten Aufrufer kann diese Reihenfolge überhaupt prüfen.
#
# png_bytes (conftest.py) ist ein ECHTES 10x14-Bild — die bbox-Zahlen unten
# sind extra für dieses Seitenverhältnis gewählt (nicht für ein quadratisches
# Bild wie bei den reinen Geometrie-Tests oben), per Skript gegen die echte
# `_bbox_plausible`-Funktion nachgerechnet.

def test_verdrahtung_scan_endpoint_ruft_sanitize_crop_hints_wirklich_auf(client, reader_openai, png_bytes):
    """
    Verdrahtungs-Test (Panel-Nacharbeit #36 — beide Panel-Stimmen konvergent,
    DER wichtigste Test dieser Nacharbeit): Ein Read mit unplausibler bbox
    (0,315 x 0,88 -> Pixel-Verhältnis auf dem 10x14-Bild ≈0,26, klar unter
    0,55 — der #36-Fehlgriff: deutlich zu hoch für eine Karte) kommt am
    Kandidaten mit raw.bbox=None an, wenn er den ECHTEN Endpunkt durchläuft.

    Rot-Beweis: den `sanitize_crop_hints`-Aufruf in scan.py entfernen → GENAU
    dieser Test fällt. Vor dieser Nacharbeit bestand die Lücke, dass ein
    solcher Rückbau die gesamte bestehende Suite grün gelassen hätte, weil
    sie `sanitize_crop_hints` nur DIREKT aufrief statt über den Aufrufer.
    """
    reader_openai(ReaderResult(
        [ScanRawRead(name="test36-verdrahtung", number="001/999",
                     bbox=[0.10, 0.05, 0.315, 0.88])],
        11, None))
    r = client.post("/api/v1/scan", files={"file": ("scan.png", png_bytes, "image/png")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidates"][0]["raw"]["name"] == "test36-verdrahtung"
    assert body["candidates"][0]["raw"]["bbox"] is None


def test_auswahl_vor_sanitierung_haelt_hauptkarte_trotz_unplausibler_box(client, reader_openai, png_bytes):
    """
    Blocker-Test (Panel-Nacharbeit #36, Auflage 1): mode=single, zwei Reads —
    die Hauptkarte hat eine unplausible Box (27% der Bildfläche, Pixel-
    Verhältnis ≈0,47 auf dem 10x14-Bild — zu breit/flach für eine Karte),
    der Nachbar eine kleine, aber PLAUSIBLE Box (1,68% Fläche, Verhältnis
    ≈0,61). Die Auswahl muss die Hauptkarte behalten: eine unplausible Box
    ist immer noch ein gültiges GRÖSSEN-Signal für die Auswahl, auch wenn sie
    danach als Zuschnitt-Hinweis selbst verworfen wird.

    Rot-Beweis: Reihenfolge zurücktauschen (Sanitierung vor Auswahl, wie vor
    dieser Nacharbeit) → dieser Test fällt: die Hauptkarten-Box zählt dann
    (schon sanitiert) als Fläche 0,0, der Nachbar (seine Box übersteht die
    Sanitierung, sie ist ja plausibel) gewinnt die Auswahl — der GANZE Read
    der Hauptkarte (Name, Nummer, alles) geht verloren, nicht nur ihr
    Zuschnitt.
    """
    reader_openai(ReaderResult(
        [
            ScanRawRead(name="test36-hauptkarte", number="123/456",
                        bbox=[0.02, 0.02, 0.90, 0.30]),
            ScanRawRead(name="test36-nachbar", number="999/999",
                        bbox=[0.60, 0.02, 0.12, 0.14]),
        ],
        22, None))
    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
        data={"mode": "single"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["candidates"]) == 1
    raw = body["candidates"][0]["raw"]
    assert raw["name"] == "test36-hauptkarte"
    assert raw["number"] == "123/456"
    assert raw["bbox"] is None  # unplausibel -> verworfen, aber NACH der Auswahl


# ── Panel-Nacharbeit #36, Auflage 2: obere Schranke + Flächen-Kappe ─────────

def test_bbox_anderthalb_karten_quer_wird_verworfen():
    """1,5-Karten-Streifen QUER (Verhältnis ≈0,931) — obere Schranke fängt das."""
    bbox = [0.02, 0.02, 0.945, 0.880]
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_bbox_ganzes_bild_wird_verworfen():
    """Das ganze Bild als bbox (Verhältnis 1,0 bei quadratischem Bild) — obere Schranke fängt das."""
    bbox = [0.0, 0.0, 1.0, 1.0]
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_bbox_querformat_karte_bleibt_trotz_oberer_schranke_erhalten():
    """Echte liegende Karte (≈0,716) bleibt klar unter der neuen oberen Schranke 0,92."""
    bbox = [0.02, 0.02, 0.88, 0.63]
    assert _bbox_plausible(bbox, 1000, 1000)


def test_bbox_dreimaldrei_mappenseite_binder_modus_wird_von_flaechenkappe_gefangen():
    """
    Eine komplette 3x3-Mappenseite (9 Karten, 3 breit x 3 hoch) behält
    UNVERÄNDERT das Seitenverhältnis einer einzelnen Karte (3x63mm : 3x88mm
    kürzt sich zu 63:88 ≈ 0,716) — kein Seitenverhältnis-Test kann diesen
    Fall je vom Verhältnis einer echten Karte unterscheiden (Grund für die
    Flächen-Kappe, Auflage 2). Sie bedeckt aber ≈64,6% der Bildfläche, weit
    über einer einzelnen, korrekt zugeschnittenen Karte in einem
    Mehrkarten-Foto — die Flächen-Kappe (nur mode multi/binder) verwirft sie.
    """
    bbox = [0.02, 0.02, 0.6801136363636363, 0.95]
    assert not _bbox_plausible(bbox, 1000, 1000, mode="binder")


def test_bbox_dreimaldrei_mappenseite_single_modus_ueberlebt():
    """
    Dieselbe 3x3-Box wie im Test oben, aber mode=single: KEINE Flächen-Kappe
    (Auflage 2 — ein formatfüllendes Einzelfoto ist dort normal). Nur das
    Seitenverhältnis zählt, und das ist ja (siehe Test oben) identisch mit
    dem einer echten Karte — sie überlebt.
    """
    bbox = [0.02, 0.02, 0.6801136363636363, 0.95]
    assert _bbox_plausible(bbox, 1000, 1000, mode="single")


def test_grenze_zwei_karten_nebeneinander_nicht_unterscheidbar_von_querformat():
    """
    GRENZE, bewusst NICHT gelöst (Panel-Nacharbeit #36 — Kommentar an
    `_MAX_RATIO` in crop_hints.py): 2 echte Karten im Hochformat nebeneinander
    (126mm breit x 88mm hoch, beide vollständig im Bild) ergeben ein
    Seitenverhältnis von ≈0,698 — praktisch identisch mit einer einzelnen
    liegenden (Querformat-)Karte (≈0,716). Reines Seitenverhältnis kann diese
    beiden Fälle PRINZIPIELL nicht unterscheiden. Anders als bei der
    3x3-Mappenseite oben rettet hier auch die Flächen-Kappe nichts: dieser
    Ausschnitt bedeckt nur ≈56,6% der Bildfläche, klar unter der 60%-Kappe —
    er kommt deshalb in JEDEM Modus durch.

    Dieser Test dokumentiert die Grenze, er beweist keinen Fix: das
    Durchkommen ist GEWOLLT (Bau-Brief, Auflage 2), keine Regression.
    """
    bbox = [0.02, 0.02, 0.90, 0.90 * 88 / 126]
    assert _bbox_plausible(bbox, 1000, 1000, mode="single")
    assert _bbox_plausible(bbox, 1000, 1000, mode="binder")  # Fläche 56,6% < 60%-Kappe


# ── Panel-Nacharbeit #36, Auflage 3: Gültigkeit der Koordinaten ─────────────

def test_bbox_koordinate_ausserhalb_des_bildes_wird_verworfen():
    """
    Nachgebaut aus `vlm.py::_bbox`s Fallback-Skalierung (dort wird nur ab
    Werten > 1,5 durch 100 geteilt): das rohe Modell-Bbox [200,10,63,88] wird
    dort zu [2.0, 0.1, 0.63, 0.88] normalisiert — x=2.0 liegt weit außerhalb
    des Bildes. w/h ALLEIN ergäben ein Seitenverhältnis von ≈0,716 (plausibel
    — vor Auflage 3 wäre das also NICHT aufgefallen, weil die Sanitierung x/y
    ignorierte). Jetzt: verwerfen statt klammern (klammern würde das Frontend
    aus der FALSCHEN Bildregion zeichnen lassen).
    """
    bbox = [2.0, 0.1, 0.63, 0.88]
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_bbox_ragt_ueber_rechten_bildrand_hinaus_wird_verworfen():
    """
    x+w > 1+ε (Auflage 3) — auch das ergäbe über w/h ALLEIN ein plausibles
    Verhältnis (≈0,571): erst x+w deckt die ungültige Koordinate auf.
    """
    bbox = [0.5, 0.1, 0.7, 0.4]  # x + w = 1.2
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_quad_koordinate_ausserhalb_des_bildes_wird_verworfen():
    """
    Dieselbe Form wie die bekannte, plausible Querformat-Karte oben
    (`test_quad_querformat_karte_bleibt_erhalten`), nur um +1,9 in x
    verschoben — die FORM (und damit das Seitenverhältnis) ist unverändert
    plausibel, erst die Koordinaten-Prüfung (Auflage 3) fängt das.
    """
    quad = [[2.0, 0.05], [2.44, 0.05], [2.44, 0.365], [2.0, 0.365]]
    assert not _quad_plausible(quad, 1000, 1000)


# ── Panel-Nacharbeit #36, Auflage 4: Eckreihenfolge vor der Messung ─────────

def test_quad_falsche_eckreihenfolge_wird_vor_der_messung_korrigiert():
    """
    Panel-Beleg (Auflage 4): kommen die Ecken in LESE-Reihenfolge
    (TL,TR,BL,BR) statt UMLAUF-Reihenfolge (TL,TR,BR,BL) an, verwechselt eine
    Messung ohne vorherige Ordnung die Diagonalen mit den echten Seiten und
    verwirft eine echte Karte fälschlich. Diese Karte, korrekt geordnet
    gemessen, hat ein Verhältnis von ≈0,641 (klar plausibel) — sie wird hier
    ABSICHTLICH in der FALSCHEN (Lese-)Reihenfolge übergeben.

    Rot-Beweis: die Ordnung vor der Messung entfernen (`_order_quad` nicht
    mehr aufrufen) → dieser Test fällt, weil dann die Diagonalen gemessen
    werden (≈0,540, unter 0,55).
    """
    quad_lese_reihenfolge = [[0.275, 0.05], [0.725, 0.05], [0.325, 0.75], [0.775, 0.75]]  # TL,TR,BL,BR
    assert _quad_plausible(quad_lese_reihenfolge, 1000, 1000)


def test_quad_korrekte_und_falsche_eckreihenfolge_ergeben_dasselbe_urteil():
    """
    Gegenprobe zum Test oben: dieselbe Karte, einmal schon richtig (TL,TR,BR,BL)
    einmal falsch (TL,TR,BL,BR) geordnet übergeben — nach dem Fix (Auflage 4)
    macht die Reihenfolge, in der das Modell die Ecken liefert, keinen
    Unterschied mehr fürs Ergebnis.
    """
    TL, TR, BR, BL = [0.275, 0.05], [0.725, 0.05], [0.775, 0.75], [0.325, 0.75]
    assert _quad_plausible([TL, TR, BR, BL], 1000, 1000)
    assert _quad_plausible([TL, TR, BL, BR], 1000, 1000)


# ── Panel-Nacharbeit #36, Auflage 5: Verworfenes zählen statt schweigen ─────

def test_sanitize_crop_hints_loggt_verwerfungen_getrennt_gezaehlt(caplog):
    """
    Klasse "stille Ausfälle" (lehren.md §3 + §9): eine Verwerfung darf nicht
    stumm bleiben. EINE Logzeile je Aufruf, mit getrennten bbox/quad-Zählern,
    nur wenn mindestens eine Verwerfung stattfand.

    Panel-Runde 3, Auflage B1 (Nachbesserung): Die Logzeile muss den
    TATSÄCHLICHEN Verwerfungsgrund je Hinweis nennen, nicht nur eine
    statische Aufzählung aller möglichen Gründe (das läse sich wie der
    echte Grund, wäre es aber nicht). `schlecht_bbox` hat hier ein zu
    schmales Verhältnis (Grund "verhaeltnis"), `schlecht_quad` einen
    Koordinaten-Ausreißer (y=1,81, Grund "koordinaten") — beide Wörter
    müssen wörtlich in der Logzeile stehen, nicht nur "Verhältnis/Fläche/
    Koordinaten" als Fließtext-Erklärung.

    Rot-Beweis: die Grund-Weitergabe kappen (z.B. wieder nur zählen statt
    den Grund zu übernehmen) → dieser Test fällt, obwohl die reinen
    Zähl-Assertions weiter grün blieben (das war exakt die Lücke).
    """
    image_bytes = _png_bytes(1000, 1000)
    gut = ScanRawRead(name="test36-log-gut", bbox=[0.10, 0.05, 0.315, 0.44])
    schlecht_bbox = ScanRawRead(name="test36-log-schlecht-bbox", bbox=[0.10, 0.05, 0.315, 0.88])
    schlecht_quad = ScanRawRead(
        name="test36-log-schlecht-quad",
        quad=[[0.1, 0.05], [0.73, 0.05], [0.73, 1.81], [0.1, 1.81]],
    )
    with caplog.at_level("INFO", logger="app.services.scan.crop_hints"):
        sanitize_crop_hints([gut, schlecht_bbox, schlecht_quad], image_bytes)
    assert caplog.text.count("Zuschnitt-Hinweise verworfen") == 1
    assert "1 bbox" in caplog.text
    assert "1 quad" in caplog.text
    # Der ECHTE Grund je Hinweis, nicht nur die Zählung (Auflage B1):
    assert "verhaeltnis" in caplog.text
    assert "koordinaten" in caplog.text
    # Gegenprobe: "flaeche" kommt hier gar nicht vor (kein Read verletzt die
    # Kappe) — würde die Logik alle drei Wörter immer statisch anhängen
    # (die alte, unzureichende Fassung), stünde "flaeche" fälschlich mit da.
    assert "flaeche" not in caplog.text


def test_bbox_negative_breite_zaehlt_als_koordinaten_nicht_verhaeltnis():
    """
    Panel-Runde 3, Auflage B4: w<=0 bzw. h<=0 ist ein KOORDINATEN-Defekt
    (eine kaputte Größenangabe), keine Verhältnis-Frage. Zwei Gründe, warum
    das mehr als Kosmetik ist: (1) macht B1s Log-Aussage ehrlich — sonst
    stünde "verhaeltnis" im Log für einen Wert, der nie ein Seitenverhältnis
    hatte; (2) zwei NEGATIVE Werte multiplizieren sich zu einer POSITIVEN
    "Fläche" (w=-0,5, h=-0,3 -> w*h=+0,15) — ohne diese Prüfung in der
    Koordinaten-Stufe wäre das ein zweiter Weg, die Auswahl in scan.py zu
    kapern (dieselbe Fehlerklasse wie Auflage A1, nur über das Vorzeichen
    statt über den Wertebereich).

    Rot-Beweis: die w<=0/h<=0-Prüfung aus `_bbox_coords_valid` entfernen →
    dieser Test fällt (Grund würde dann "verhaeltnis").
    """
    assert _bbox_reject_reason([0.1, 0.1, 0.0, 0.5], 1000, 1000, "single") == "koordinaten"
    assert _bbox_reject_reason([0.1, 0.1, 0.3, -0.2], 1000, 1000, "single") == "koordinaten"
    assert _bbox_reject_reason([0.1, 0.1, -0.5, -0.3], 1000, 1000, "single") == "koordinaten"


def test_sanitize_crop_hints_loggt_nichts_wenn_alles_plausibel(caplog):
    """Gegenprobe: keine Verwerfung -> keine Logzeile (kein Rauschen im Normalfall)."""
    image_bytes = _png_bytes(1000, 1000)
    gut = ScanRawRead(name="test36-log-nur-gut", bbox=[0.10, 0.05, 0.315, 0.44])
    with caplog.at_level("INFO", logger="app.services.scan.crop_hints"):
        sanitize_crop_hints([gut], image_bytes)
    assert "Zuschnitt-Hinweise verworfen" not in caplog.text


# ── Panel-Nacharbeit #36, Runde 3, Auflage A1 (Regression): ─────────────────
# Koordinaten-Müll darf die Auswahl nicht kapern
#
# Sonden-Beleg der Delta-Prüfung: `[200,10,63,88]` wird via vlm.py-Fallback
# zu `[2.0, 0.1, 0.63, 0.88]` (x=2.0 weit außerhalb). Roh gerechnet hat das
# eine Fläche von 0,63*0,88=0,5544 — mehr als die echte Hauptkarte (0,504)
# im selben Foto. Unter der Runde-2-Reihenfolge (Auswahl liest die ROHE
# bbox ohne Gültigkeitsfilter) gewann der Müll-Read die Auswahl, und die
# echte Hauptkarte (Name+Nummer) ging komplett verloren.

def test_koordinaten_muell_kapert_die_auswahl_nicht(client, reader_openai, png_bytes):
    """
    Integrationstest über den echten Endpunkt (mode=single): eine echte,
    plausible Hauptkarte (Fläche 0,504 auf dem 10x14-Bild, Verhältnis
    ≈0,735 — beides im grünen Bereich) tritt gegen einen Koordinaten-Müll-
    Read an (bbox=[2.0, 0.1, 0.63, 0.88], rohe Fläche 0,5544 — GRÖSSER als
    die Hauptkarte). Die Hauptkarte muss trotzdem gewinnen: der Müll-Read
    hat keine gültige Koordinate und darf gar nicht erst als Größensignal
    zählen.

    Rot-Beweis: die Koordinaten-Vorstufe (`crop_hints.discard_invalid_coords`
    in scan.py) entfernen → dieser Test fällt, weil dann der Müll-Read
    (0,5544 > 0,504) die Auswahl gewinnt.
    """
    reader_openai(ReaderResult(
        [
            ScanRawRead(name="test36-hauptkarte", number="321/654",
                        bbox=[0.02, 0.02, 0.72, 0.70]),   # Fläche 0,504, plausibel
            ScanRawRead(name="test36-parse-muell", number="000/000",
                        bbox=[2.0, 0.1, 0.63, 0.88]),      # Koordinaten-Müll, rohe Fläche 0,5544
        ],
        44, None))
    r = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
        data={"mode": "single"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["candidates"]) == 1
    raw = body["candidates"][0]["raw"]
    assert raw["name"] == "test36-hauptkarte"
    assert raw["number"] == "321/654"
    assert raw["bbox"] is not None  # koordinaten- UND verhältnis-gültig, übersteht auch Phase 2


# ── Panel-Nacharbeit #36, Runde 3, Auflage C1: Flächen-Kappe am echten ──────
# Endpunkt (mode=mode ist sonst spurlos entfernbar)

def test_flaechenkappe_greift_am_echten_endpunkt_nur_in_binder_nicht_in_single(client, reader_openai, png_bytes):
    """
    Ohne diesen Test war `mode=mode` beim `sanitize_crop_hints`-Aufruf in
    scan.py spurlos entfernbar (491/491 blieben grün) — die Flächen-Kappe
    wäre in mode=multi/binder am echten Endpunkt still tot gewesen, weil
    `sanitize_crop_hints` ohne den Parameter auf den Default "single"
    zurückfällt.

    Box mit 68% der Bildfläche (0,85 x 0,80) und plausiblem Verhältnis
    (≈0,759 auf dem 10x14-Bild) — genau der Mappenseiten-Fall aus Auflage 2.

    Rot-Beweis: `mode=mode` aus dem `sanitize_crop_hints`-Aufruf in scan.py
    entfernen → die mode=binder-Hälfte dieses Tests fällt (bbox würde
    fälschlich überleben).
    """
    grosse_seite = [0.02, 0.02, 0.85, 0.80]  # Fläche 0,68; Verhältnis ≈0,759 auf 10x14

    reader_openai(ReaderResult([ScanRawRead(name="test36-seite", bbox=list(grosse_seite))], 55, None))
    r_binder = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
        data={"mode": "binder"},
    )
    assert r_binder.status_code == 200, r_binder.text
    assert r_binder.json()["candidates"][0]["raw"]["bbox"] is None

    reader_openai(ReaderResult([ScanRawRead(name="test36-seite", bbox=list(grosse_seite))], 56, None))
    r_single = client.post(
        "/api/v1/scan",
        files={"file": ("scan.png", png_bytes, "image/png")},
        data={"mode": "single"},
    )
    assert r_single.status_code == 200, r_single.text
    assert r_single.json()["candidates"][0]["raw"]["bbox"] == grosse_seite


# ── Panel-Nacharbeit #36, Runde 3, Auflage C2: quad-Zwilling ────────────────
# der Flächen-Kappe (die quad-Hälfte hatte null Testabdeckung)

def test_quad_dreimaldrei_mappenseite_binder_modus_wird_von_flaechenkappe_gefangen():
    """
    quad-Zwilling von `test_bbox_dreimaldrei_mappenseite_binder_modus_wird_von_flaechenkappe_gefangen`
    (Auflage 2b) — als Rechteck-Viereck dieselbe Geometrie, damit exakt
    dieselbe Fläche (≈64,6%) und dasselbe Verhältnis (≈0,716) herauskommen.
    Ohne diesen Test war `_polygon_area_fraction` (die Flächen-Berechnung
    für quad) ersatzlos löschbar, ohne dass irgendein Test das bemerkt hätte.

    Rot-Beweis: die Flächen-Kappe aus `_quad_reject_reason` entfernen →
    dieser Test fällt.
    """
    w, h = 0.6801136363636363, 0.95
    x, y = 0.02, 0.02
    quad = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
    assert not _quad_plausible(quad, 1000, 1000, mode="binder")


def test_quad_dreimaldrei_mappenseite_single_modus_ueberlebt():
    """Gegenprobe zum Test oben: dieselbe quad-Box, mode=single -> keine Flächen-Kappe, überlebt."""
    w, h = 0.6801136363636363, 0.95
    x, y = 0.02, 0.02
    quad = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
    assert _quad_plausible(quad, 1000, 1000, mode="single")


# ── Panel-Nacharbeit #36, Runde 3, Auflage B2: _MAX_RATIO-Kommentar war ─────
# nur für quadratische Bilder korrekt

def test_bbox_ganzbild_auf_3zu4_bild_ueberlebt_im_single_faellt_an_flaechenkappe_im_binder():
    """
    Der ursprüngliche Kommentar an `_MAX_RATIO` behauptete pauschal, ein
    Ganzbild-bbox `[0,0,1,1]` werde von der oberen Schranke gefangen — das
    gilt nur bei einem QUADRATISCHEN Bild. Auf einem 3:4-Bild hat
    `[0,0,1,1]` das Seitenverhältnis 3/4=0,75 und ist damit nach reinem
    Seitenverhältnis PLAUSIBEL (kein Fehler: ein formatfüllendes Einzelfoto
    ist im single-Modus normal). Die Flächen-Kappe fängt denselben Fall im
    Mehrkarten-Modus trotzdem, unabhängig vom Bildformat (Fläche ist immer
    1,0).
    """
    bbox = [0.0, 0.0, 1.0, 1.0]
    image_bytes = _png_bytes(300, 400)  # 3:4
    assert _bbox_plausible(bbox, 300, 400, mode="single")
    out = sanitize_crop_hints([ScanRawRead(name="test36-3zu4-ganzbild", bbox=list(bbox))], image_bytes, mode="binder")
    assert out[0].bbox is None


# ── Panel-Nacharbeit #36, Runde 3, Auflage C3: _COORD_EPS an der Grenze ─────
# festnageln (bisher nur implizit über weit-außerhalb-Werte getestet)

def test_bbox_knapp_ausserhalb_der_koordinaten_toleranz_wird_verworfen():
    """
    x+w = 1,05 — knapp über der Toleranzgrenze 1+ε=1,02 (ε=0,02). w/h ALLEIN
    ergäben ein plausibles Verhältnis (0,63/0,88≈0,716): erst die Grenze
    selbst entscheidet.

    Rot-Beweis: `_COORD_EPS` auf 0,19 weiten → dieser Test fällt (1,05 läge
    dann innerhalb 1+0,19=1,19).
    """
    bbox = [0.42, 0.05, 0.63, 0.88]  # x + w = 1.05
    assert not _bbox_plausible(bbox, 1000, 1000)


def test_bbox_knapp_innerhalb_der_koordinaten_toleranz_ueberlebt():
    """Gegenprobe: x+w = 1,01 — knapp INNERHALB von 1+ε=1,02 — überlebt."""
    bbox = [0.38, 0.05, 0.63, 0.88]  # x + w = 1.01
    assert _bbox_plausible(bbox, 1000, 1000)
