"""
Plausibilitäts-Sanitierung der Zuschnitt-Hinweise (Issue #36 + Panel-Nacharbeit).

Bei mehreren Karten im Bild nimmt das Lese-Modell (Gemini/OpenAI/OpenRouter,
alle über `vlm.reads_from_json`) gelegentlich eine zu hohe/zu große Box bzw.
ein zu hohes/zu großes Viereck — es schneidet dann eine Nachbarkarte, ein
Mappen-Label oder gleich eine ganze Mappenseite mit, statt exakt an der
Zielkarte zu enden. Das Frontend übernimmt bbox/quad für den Foto-Zuschnitt
(`cardCrop.ts::cropToCardPhoto`) weitgehend ungeprüft: der bbox-Pfad prüft das
Seitenverhältnis gar nicht, der quad-Pfad hat nur eine lockere Schranke
(`ratio >= 0.42`), die einen 1,5-Karten-Streifen (~0,48) durchlässt. Lieber
kein Hinweis als ein lügender (dieselbe Klasse wie bei Preisen,
`docs/agents/lehren.md` §4): unplausible Werte werden HIER auf None gesetzt.

WICHTIG (Panel-Nacharbeit, Auflage 6): Das Frontend hat KEINE Zuschnitt-
Kaskade "quad → bbox → zentriert". Ohne bbox UND quad gibt es keinen eigenen
Zuschnitt und kein eigenes Foto (`web/src/app/scan/page.tsx`:
`usePhoto = !!(bbox || quad)`, `cropToCardPhoto` wird ohne beide gar nicht
erst aufgerufen) — die Karte bekommt stattdessen das Katalogbild. Der
zentrierte Fallback in `cropToCardPhoto` existiert zwar im Code, wird auf
diesem Weg aber nie erreicht. Jede Verwerfung hier tauscht also ein
(potenziell verzerrtes) eigenes Foto gegen das Katalogbild — akzeptierte,
vorbestehende Degradation, kein Rückschritt durch diese Datei. Eine echte
Kaskade wäre eine Frontend-Änderung; dafür ist ein eigenes Issue vorgesehen.

`bbox`/`quad` sind Bild-ANTEILE (0..1 relativ zu Breite/Höhe). Ihr WIRKLICHES
(Pixel-)Seitenverhältnis hängt von den Bildmaßen ab — bei einem nicht
quadratischen Foto ergeben dieselben Anteile je nach Bildformat ein anderes
Pixel-Verhältnis. `vlm.py`/`gemini.py` sehen nur die Modell-JSON, nie das Bild
selbst, kennen die Maße also nicht. Deshalb sitzt diese Prüfung hier, im
Aufrufer, der das Foto hält (`api/v1/scan.py::scan`) — NICHT in
`vlm.py::_bbox`/`_quad`, die bleiben unverändert reine Parser der
Modell-Antwort (Format-/Typ-Prüfung, keine Verhältnis-/Flächen-/Koordinaten-
Plausibilität).

Drei unabhängige Prüfungen, jede kann allein verwerfen (Details je an der
Konstante bzw. Funktion):
1. **Koordinaten** — x/y/w/h bzw. jeder Quad-Punkt muss ein echter Bild-Anteil
   sein (Auflage 3), inklusive w>0/h>0 bei der bbox. Fängt z.B.
   `vlm.py::_bbox`s Fallback-Skalierung: das rohe `[200,10,63,88]` wird dort
   (nur ab Werten > 1,5 wird durch 100 geteilt) zu `[2.0, 0.1, 0.63, 0.88]` —
   x=2.0 liegt weit außerhalb des Bildes. Verwerfen statt klammern: eine
   geklammerte Koordinate zeichnet aus der FALSCHEN Bildregion, das ist
   schlimmer als gar kein Hinweis. Braucht KEIN Bild (reine Anteils-Prüfung).
2. **Seitenverhältnis** (kurze/lange Seite, orientierungsunabhängig) muss in
   [`_MIN_RATIO`, `_MAX_RATIO`] liegen. Beim quad wird dafür ZUERST nach
   Bildposition geordnet (Auflage 4) — sonst verwechselt die Messung
   Diagonalen mit Seiten, sobald die Ecken in Lese-Reihenfolge (TL,TR,BL,BR)
   statt Umlauf-Reihenfolge (TL,TR,BR,BL) ankommen.
3. **Flächen-Kappe**, NUR mode multi/binder (Auflage 2) — Begründung an
   `_AREA_CAP`.

ZWEI FUNKTIONEN, ZWEI ZEITPUNKTE (Panel-Runde 3 — Regression aus Runde 2
behoben): `discard_invalid_coords` prüft NUR Prüfung 1 (Koordinaten) und
braucht dafür kein Bild. Sie muss laufen, BEVOR `api/v1/scan.py` im
single-Modus die Hauptkarte per roher bbox-Fläche auswählt: ohne diese
Vorstufe hat ein koordinaten-kaputter Hinweis (z.B. der vlm.py-Fallback-Bug
oben, `[2.0, 0.1, 0.63, 0.88]`) trotzdem eine reale, aber BEDEUTUNGSLOSE
Fläche (0,63*0,88=0,5544) und kann eine echte, nur unplausibel-großformatige
Hauptkarte (Auflage-1-Fall) aus der Auswahl verdrängen — genau das war die
Runde-3-Regression (die Auswahl las die rohe bbox OHNE Gültigkeitsfilter).
`sanitize_crop_hints` prüft danach alle drei Stufen (Koordinaten erneut, plus
Verhältnis + Flächen-Kappe) NACH der Auswahl, am GEWINNER — eine bereits
durch `discard_invalid_coords` verworfene bbox/quad bleibt None, die
Koordinaten-Wiederholung dort ist redundant, aber harmlos (Verteidigung in
der Tiefe statt eines fehleranfälligen "wurde das schon geprüft?"-Zustands).
"""

from __future__ import annotations

import io
import logging
from collections import Counter

from PIL import Image

from app.schemas.scan import ScanMode, ScanRawRead

log = logging.getLogger(__name__)

# Eine echte Karte ist ~63:88 mm (kurze:lange Seite) ≈ 0,716. Normalisiert als
# kurze/lange Seite ist dieses Verhältnis IMMER <= 1 — unabhängig davon, ob
# die Karte im Bild hoch oder quer (liegend) erfasst wurde.
#
# 0,55 liegt klar UNTER einem handfotografierten Einzelbild mit spürbarer
# Perspektive (~0,6 — muss laut Bau-Brief #36 durchkommen: Handkameras
# verzerren beim Fotografieren einer echten Einzelkarte real) und klar ÜBER
# dem kleinsten bekannten Fehlerkennungs-Fall (1,5-Karten-Streifen, ~0,48 —
# muss verworfen werden). Im Zweifel lieber ein zu weites Band als ein zu
# enges: ein NICHT verworfener Fehlgriff verzerrt höchstens EIN Vorschaubild;
# ein zu Unrecht verworfener Hinweis nimmt einem echten Einzelfoto den besten
# Zuschnitt weg und liefert statt eines eigenen Fotos nur noch das
# Katalogbild (Frontend hat keine Kaskade, siehe Moduldocstring).
#
# Schwellen-Entscheidung, arbitriert (Panel-Nacharbeit #36 — NICHT verändert):
# eine um die Längsachse geneigte Karte fällt bei 0,55 ab ~39,8° Neigung unter
# die Schranke; das Frontend-eigene Warp-Netz (`cardCrop.ts`, ratio>=0,42)
# verkraftet dieselbe Karte noch bis ~54,1°. Im Fenster 40°-54° stirbt hier
# also der quad-Hinweis, die bbox überlebt aber meist noch (>=0,648) und
# liefert ein brauchbares achsenparalleles Foto — kein Totalverlust. Der
# Slice heißt "Nachbarkarte nicht mitschneiden", nicht "Warp-Fenster
# maximieren"; Feintuning mit echten Karten macht der Owner.
_MIN_RATIO = 0.55

# Obere Schranke (Panel-Nacharbeit #36, Runde 2) — ohne sie passierten ein
# 1,5-Karten-Streifen QUER (Verhältnis ~0,931) und das ganze Bild (Verhältnis
# 1,0 bei bbox=[0,0,1,1] auf einem QUADRATISCHEN Bild) als "plausible Karte".
# Eine echte liegende (Querformat-)Karte liegt bei ~0,716 und bleibt klar
# darunter. WICHTIG: "das ganze Bild passiert nicht" gilt nur, wenn das Bild
# selbst nahe quadratisch ist — bei einem 3:4-Bild hat bbox=[0,0,1,1] das
# Seitenverhältnis 0,75 und bleibt im single-Modus PLAUSIBEL (kein Fehler:
# ein formatfüllendes Einzelfoto ist dort normal); im Mehrkarten-Modus fängt
# die Flächen-Kappe (`_AREA_CAP`) denselben Fall unabhängig vom Bildformat.
#
# GRENZE, bewusst NICHT gelöst: 2 echte Karten NEBENEINANDER (Hochformat,
# beide vollständig im Bild) ergeben ein Verhältnis von ~0,698 — praktisch
# identisch mit einer einzelnen liegenden Karte (~0,716) und über das
# Seitenverhältnis ALLEIN prinzipiell nicht unterscheidbar. Siehe
# `test_36_zuschnitt_plausibilitaet.py` (Grenzfall-Test weiter unten in
# dieser Datei referenziert) für den Beleg, dass das ABSICHTLICH durchkommt.
#
# ZWEITES KIPP-FENSTER, dokumentiert (Panel-Runde 3, Auflage B3 — Konstante
# bleibt unverändert): die obere Schranke kann auch eine ECHTE Einzelkarte
# treffen, die um ihre KURZE Achse geneigt fotografiert wurde (Kamera kippt
# die Karte nach hinten/vorne, nicht seitlich) — dabei staucht sich die LANGE
# Seite perspektivisch, das Verhältnis steigt Richtung 1,0 statt zu sinken.
# Bei ~38,9° Neigung um die kurze Achse überschreitet das projizierte
# Verhältnis 0,92 (Crossover zum quadratischen Aussehen liegt bei ~44,3°).
# Das Frontend-Netz hat für diese Richtung KEINE obere Schranke — ein solches
# Foto würde dort durchgehen. Bewusst nicht gegengesteuert: dieselbe
# Güterabwägung wie bei `_MIN_RATIO` (ein zu Unrecht verworfener Hinweis
# kostet nur den eigenen Zuschnitt, nicht die Karte selbst), Feintuning mit
# echten Karten macht der Owner.
_MAX_RATIO = 0.92

# Flächen-Kappe (Panel-Nacharbeit #36, Runde 2) — wirkt NUR bei mode
# multi/binder (Parameter `mode`, s. `sanitize_crop_hints`), im single-Modus
# nie: ein formatfüllendes Einzelfoto ist dort normal (eine Karte darf das
# ganze Bild einnehmen).
#
# Grund: eine komplette 3×3-Mappenseite (9 Karten, 3 breit × 3 hoch) hat
# UNVERÄNDERT dasselbe Seitenverhältnis wie eine einzelne Karte (3×63mm :
# 3×88mm kürzt sich zu 63:88 ≈ 0,716) — kein Seitenverhältnis-Test kann diesen
# Fall je erkennen. Sie belegt aber, weil sie eine ganze Seite statt einer
# Karte zeigt, einen weit größeren Anteil des Fotos: im Mehrkarten-Modus
# erwarten wir je Hinweis GENAU eine Karte, nicht das halbe Bild. 0,60 liegt
# klar über dem, was eine korrekt zugeschnittene EINZELNE Karte in einem
# Mehrkarten-Foto realistisch einnimmt, und klar unter einer vollen Seite.
_AREA_CAP = 0.60

# Koordinaten-Toleranz (Panel-Nacharbeit #36, Runde 2): bbox/quad sind Bild-
# ANTEILE, gehören also nach [0, 1]. ε=0,02 lässt Rundungsrauschen am Rand zu,
# fängt aber grobe Fehlwerte wie `vlm.py::_bbox`s Fallback-Skalierung
# (`[200,10,63,88]` → `[2.0, 0.1, 0.63, 0.88]`, x=2.0 weit außerhalb).
_COORD_EPS = 0.02


def _ratio(seite_a: float, seite_b: float) -> float:
    """Normalisiertes Seitenverhältnis (<=1), orientierungsunabhängig."""
    if seite_a <= 0 or seite_b <= 0:
        return 0.0
    kurz, lang = (seite_a, seite_b) if seite_a <= seite_b else (seite_b, seite_a)
    return kurz / lang


def _ratio_plausible(ratio: float) -> bool:
    return _MIN_RATIO <= ratio <= _MAX_RATIO


def _values_in_bounds(values: list[float]) -> bool:
    """Jeder Wert in [0-ε, 1+ε] — Bild-ANTEILE dürfen das nicht verlassen (Auflage 3)."""
    return all(-_COORD_EPS <= v <= 1 + _COORD_EPS for v in values)


def _bbox_coords_valid(bbox: list[float]) -> bool:
    """
    Reine Koordinaten-Gültigkeit einer bbox — bildUNABHÄNGIG (keine img_w/
    img_h nötig), deshalb vor jeder Flächen-/Größen-Verwendung aufrufbar
    (Panel-Runde 3, `discard_invalid_coords`). Prüft NUR Lage/Format, NICHT
    das Seitenverhältnis. w<=0/h<=0 zählt HIER als Koordinaten-Defekt, nicht
    als Verhältnis-Defekt (Panel-Runde 3, Auflage B4) — eine Größe von Null
    oder mit falschem Vorzeichen ist kein "zu spitzes Verhältnis", sondern
    eine kaputte Angabe; das macht die Verwerfungs-Ursache im Log (Auflage
    B1) ehrlich.
    """
    if len(bbox) != 4:
        return False
    x, y, w, h = bbox
    if not _values_in_bounds([x, y, w, h]):
        return False
    if x + w > 1 + _COORD_EPS or y + h > 1 + _COORD_EPS:
        return False
    if w <= 0 or h <= 0:
        return False
    return True


def _quad_coords_valid(quad: list[list[float]]) -> bool:
    """
    Reine Koordinaten-Gültigkeit eines quad — bildUNABHÄNGIG, s.
    `_bbox_coords_valid`. Prüft nur, ob alle 4 Punkte echte Bild-Anteile
    sind; Form/Fläche/Selbstüberschneidung sind Sache der Verhältnis- bzw.
    Flächen-Prüfung weiter unten.
    """
    if len(quad) != 4 or any(len(p) != 2 for p in quad):
        return False
    return _values_in_bounds([v for p in quad for v in p])


def _order_quad(pts: list[list[float]]) -> list[list[float]]:
    """
    Sortiert 4 Punkte nach Bildposition in die Reihenfolge TL,TR,BR,BL —
    Python-Äquivalent von `orderQuad` in `web/src/lib/cardCrop.ts`. Muss VOR
    jeder Seiten-/Flächen-Messung laufen (Auflage 4, Panel-Beleg): ohne
    Ordnung verwechselt die Messung unten Diagonalen mit Seiten, sobald die
    Ecken in Lese-Reihenfolge (TL,TR,BL,BR) statt Umlauf-Reihenfolge
    (TL,TR,BR,BL) ankommen — eine echte Karte (richtig geordnet ~0,62 im
    Test) fällt sonst fälschlich unter `_MIN_RATIO`.

    Gibt eine NEUE Liste zurück (mutiert `pts` nicht): der Aufrufer
    (`sanitize_crop_hints`) gibt weiterhin die ORIGINAL-Reihenfolge nach
    außen — das Frontend ordnet beim Zuschnitt selbst (`autoOrient=true`),
    diese Funktion braucht die Ordnung nur für die eigene Messung.
    """
    by_y = sorted(pts, key=lambda p: p[1])
    top = sorted(by_y[:2], key=lambda p: p[0])     # TL, TR
    bottom = sorted(by_y[2:], key=lambda p: p[0])  # BL, BR
    return [top[0], top[1], bottom[1], bottom[0]]  # TL, TR, BR, BL


def _polygon_area_fraction(pts: list[list[float]]) -> float:
    """
    Fläche eines (bereits geordneten) Vierecks als Anteil der BILDFLÄCHE
    (0..1) — Shoelace-Formel direkt auf den Bild-ANTEILEN, nicht auf Pixeln.
    Kein Näherungswert: eine Skalierung mit img_w/img_h in x bzw. y kürzt
    sich im Verhältnis Fläche_px / (img_w*img_h) exakt heraus — anders als
    beim Seitenverhältnis werden die Bildmaße für die FLÄCHE gar nicht
    gebraucht. Erwartet geordnete Punkte (`_order_quad`): ein sich selbst
    überschneidendes Viereck (falsche Reihenfolge) läge sonst falsch.
    """
    n = len(pts)
    flaeche_x2 = 0.0
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        flaeche_x2 += x1 * y2 - x2 * y1
    return abs(flaeche_x2) / 2.0


def _bbox_reject_reason(bbox: list[float], img_w: float, img_h: float, mode: str) -> str | None:
    """None = plausibel; sonst der Verwerfungsgrund fürs Logging (Auflage 5/B1)."""
    if not _bbox_coords_valid(bbox):
        return "koordinaten"
    _x, _y, w, h = bbox
    if not _ratio_plausible(_ratio(w * img_w, h * img_h)):
        return "verhaeltnis"
    if mode in ("multi", "binder") and (w * h) > _AREA_CAP:
        return "flaeche"
    return None


def _quad_reject_reason(quad: list[list[float]], img_w: float, img_h: float, mode: str) -> str | None:
    """None = plausibel; sonst der Verwerfungsgrund fürs Logging (Auflage 5/B1)."""
    if not _quad_coords_valid(quad):
        return "koordinaten"
    ordered = _order_quad(quad)  # Auflage 4: erst ordnen, dann messen

    def dist(a: list[float], b: list[float]) -> float:
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

    pts = [(p[0] * img_w, p[1] * img_h) for p in ordered]
    # Gegenüberliegende Seiten gemittelt statt nur eine Seite je Richtung: ein
    # perspektivisch verzerrtes Viereck ist ein Trapez, keine Raute — erst der
    # Mittelwert schätzt die tatsächliche Karten-Breite/-Höhe robust genug.
    seite_a = (dist(pts[0], pts[1]) + dist(pts[2], pts[3])) / 2  # TL-TR / BR-BL
    seite_b = (dist(pts[1], pts[2]) + dist(pts[3], pts[0])) / 2  # TR-BR / BL-TL
    if not _ratio_plausible(_ratio(seite_a, seite_b)):
        return "verhaeltnis"
    if mode in ("multi", "binder") and _polygon_area_fraction(ordered) > _AREA_CAP:
        return "flaeche"
    return None


def _bbox_plausible(bbox: list[float], img_w: float, img_h: float, mode: ScanMode = "single") -> bool:
    """bbox = [x, y, w, h] als Bild-Anteile (0..1). `mode` s. `sanitize_crop_hints`."""
    return _bbox_reject_reason(bbox, img_w, img_h, mode) is None


def _quad_plausible(quad: list[list[float]], img_w: float, img_h: float, mode: ScanMode = "single") -> bool:
    """
    quad = 4 Eckpunkte [[x,y]…] als Bild-Anteile (0..1), Reihenfolge BELIEBIG
    (wird intern nach Bildposition geordnet, Auflage 4). `mode` s.
    `sanitize_crop_hints`.
    """
    return _quad_reject_reason(quad, img_w, img_h, mode) is None


def discard_invalid_coords(reads: list[ScanRawRead]) -> list[ScanRawRead]:
    """
    Verwirft (None) bbox/quad mit UNGÜLTIGEN Koordinaten, IN-PLACE — reine
    Anteils-Prüfung, kein Bild nötig (im Unterschied zu `sanitize_crop_hints`
    unten). Muss laufen, BEVOR `api/v1/scan.py` im single-Modus die
    Hauptkarte per roher bbox-Fläche auswählt (Panel-Runde 3, Auflage A1 —
    Regression aus Runde 2, siehe Moduldocstring): ein Koordinaten-Müll-Wert
    wie `[2.0, 0.1, 0.63, 0.88]` (vlm.py-Fallback-Bug) hat sonst eine reale,
    aber BEDEUTUNGSLOSE Fläche und kann eine echte, nur unplausibel-
    großformatige Hauptkarte aus der Auswahl verdrängen.

    Prüft ABSICHTLICH nur Koordinaten, NICHT Verhältnis/Fläche — eine zu
    große, aber koordinaten-gültige Box bleibt ein gültiges Größensignal für
    die Auswahl (das ist der Runde-2-Blocker-Fix, Auflage 1, und bleibt
    unangetastet). Verhältnis/Fläche prüft weiterhin ausschließlich
    `sanitize_crop_hints`, NACH der Auswahl, am Gewinner.
    """
    for r in reads:
        if r.bbox is not None and not _bbox_coords_valid(r.bbox):
            r.bbox = None
        if r.quad is not None and not _quad_coords_valid(r.quad):
            r.quad = None
    return reads


def _format_reasons(counter: "Counter[str]") -> str:
    """'N× grund, M× grund2' — alphabetisch sortiert für ein deterministisches Log."""
    return ", ".join(f"{n}× {reason}" for reason, n in sorted(counter.items()))


def sanitize_crop_hints(
    reads: list[ScanRawRead], image_bytes: bytes, mode: ScanMode = "single",
) -> list[ScanRawRead]:
    """
    Verwirft (None) unplausible bbox/quad auf `reads`, IN-PLACE, und gibt
    dieselbe Liste zurück. OCR-Reads haben nie bbox/quad (`ocr.py::extract`
    setzt sie nie) — für sie ist das ein No-Op, ohne dass der Aufrufer nach
    Engine unterscheiden müsste.

    `mode` steuert NUR die Flächen-Kappe (`_AREA_CAP`): im single-Modus nie
    aktiv (ein formatfüllendes Einzelfoto ist dort normal), in multi/binder
    aktiv (dort ist je Hinweis GENAU eine Karte erwartet). Koordinaten- und
    Seitenverhältnis-Prüfung laufen IMMER, unabhängig vom Modus. Default
    "single" ist die konservativste Wahl für einen Aufrufer, der `mode`
    nicht mitgibt (verwirft dann nie ZU VIEL, nur zu wenig) — im Repo gibt es
    dafür aktuell keinen Aufrufer außer `api/v1/scan.py::scan`, der den
    echten Modus immer mitgibt (Konsumenten-Check der Panel-Nacharbeit).

    Läuft NACH `discard_invalid_coords` + der Einzelkarten-Auswahl in
    scan.py (Panel-Runde 3) — prüft hier trotzdem erneut Koordinaten (plus
    Verhältnis + Fläche): redundant für bereits geprüfte Reads, aber
    notwendig, weil diese Funktion auch eigenständig aufrufbar bleibt (z.B.
    aus Tests) und sich nicht auf eine vorgelagerte Prüfung verlassen soll.

    Zählt Verwerfungen samt GRUND getrennt nach bbox/quad und loggt EINE
    Zeile je Aufruf, wenn mindestens eine Verwerfung stattfand (Auflage 5;
    Runde 3, Auflage B1: der geloggte Grund ist der TATSÄCHLICHE, nicht nur
    eine statische Aufzählung aller möglichen Gründe).
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

    bbox_reasons: "Counter[str]" = Counter()
    quad_reasons: "Counter[str]" = Counter()
    for r in reads:
        if r.quad is not None:
            reason = _quad_reject_reason(r.quad, img_w, img_h, mode)
            if reason is not None:
                r.quad = None
                quad_reasons[reason] += 1
        if r.bbox is not None:
            reason = _bbox_reject_reason(r.bbox, img_w, img_h, mode)
            if reason is not None:
                r.bbox = None
                bbox_reasons[reason] += 1

    if bbox_reasons or quad_reasons:
        parts = []
        if bbox_reasons:
            parts.append(f"{sum(bbox_reasons.values())} bbox ({_format_reasons(bbox_reasons)})")
        if quad_reasons:
            parts.append(f"{sum(quad_reasons.values())} quad ({_format_reasons(quad_reasons)})")
        log.info("Zuschnitt-Hinweise verworfen: %s", ", ".join(parts))
    return reads
