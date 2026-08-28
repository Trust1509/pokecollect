"""
Lokaler Bild-Cache für den Katalog (#43, Slice 2 von Epic #41).

Der Katalog (`tcgdex_catalog`) hält für jede Karte nur die externe CDN-URL
(`image_url`). Diese Datei füllt zusätzlich `image_pfad` — einen lokal
gecachten Pfad, wahlweise für gar keine (Stufe "urls", Default), die
besessenen/wunschgelisteten (Stufe "owned") oder alle Katalogbilder (Stufe
"all"). Zwei Aufrufer teilen sich dieselbe Download-Routine (`download_one`):

  - Nachtlauf-Etappe (`run_catalog_image_cache`, aufgerufen aus services/cron.py
    NACH dem €-Repass) — füllt den Cache gemäß Stufe in kleinen Schwüngen.
  - On-demand (`cache_one_on_demand`, als FastAPI-BackgroundTask aus dem
    Katalog-Detail-Endpunkt) — cached genau die eine gerade angesehene Karte,
    falls die Stufe das erlaubt und sie nicht schon da ist.

Auswahl-Helfer `resolve_catalog_image_url()` ist die EINE Stelle, die
entscheidet, ob eine Antwort den lokalen Pfad oder die CDN-URL zeigt (DRY,
Bau-Brief Block 3) — von der Katalog-Liste, dem Katalog-Detail UND den
Soll-Slots (set_goal.py) genutzt.

Traversal-Lehre (docs/agents/lehren.md, test_security_traversal.py): card_id
kommt aus Fremddaten (TCGdex/TCGplayer) und wandert in einen Dateinamen —
NUR [A-Za-z0-9._-] bleibt erhalten. Speicher-Konvention wie
PokemonCard.bild_karte_pfad (relativ zu images_dir.parent), damit
services.card_images.safe_media_path UNVERÄNDERT wiederverwendet wird (DRY,
kein zweiter Pfad-Prüfer) — sowohl für die Existenzprüfung beim Ausliefern als
auch (über MEDIA_PATH_COLUMNS) für die Restore-Neutralisierung (#37).

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Optional
from uuid import uuid4

import httpx
from PIL import Image
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import tcgdex
from app.services.card_images import _MAX_UPLOAD_BYTES, safe_media_path
from app.services.settings import get_setting

log = logging.getLogger(__name__)

# Feste Katalog-Unterablage unter images_dir (main.py:406 mountet images_dir
# insgesamt auf "/images" — dieses Präfix ist deshalb hier ein eigener,
# bewusst NICHT aus images_dir abgeleiteter Konstanten-String, siehe
# resolve_catalog_image_url()).
CATALOG_SUBDIR = "catalog"
_IMAGES_MOUNT_PREFIX = "images"

# card_id kommt aus Fremddaten und wandert in einen Dateinamen — nur dieses
# Alphabet bleibt erhalten (Traversal-Lehre). "/" UND "\\" fallen weg, damit
# aus dem Ergebnis strukturell KEIN Verzeichniswechsel mehr möglich ist, auch
# wenn Punkte (erlaubte Einzelzeichen) erhalten bleiben.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def safe_catalog_filename(card_id: str) -> str:
    """
    card_id -> sicherer Dateiname (ohne Endung). Jedes nicht erlaubte Zeichen
    wird EINZELN durch "_" ersetzt statt das Segment zu verwerfen — sonst
    kollabierten unterschiedliche card_ids auf denselben Dateinamen. Ohne "/"
    bzw. "\\" im Ergebnis kann selbst ein erhaltenes ".." keinen
    Verzeichniswechsel mehr bewirken (kein Pfadtrenner übrig). Nie leer: eine
    (praktisch unmögliche, card_id ist Primärschlüssel) leere Eingabe ergäbe
    sonst einen Kollisions-Dateinamen für alle Treffer.

    Panel-Nacharbeit #43 — zwei Löcher, die die reine Zeichen-Ersetzung allein
    nicht schließt:
    - Kollisionsfreiheit: "A/B" und "A\\B" ersetzen beide ihr Trennzeichen
      durch "_" und ergäben BEIDE "A_B" — zwei verschiedene card_ids auf
      derselben Datei.
    - Überlänge: eine ~300-Zeichen card_id ergab beim Schreiben ENAMETOOLONG.
    Deshalb: auf 100 Zeichen kappen, und NUR wenn tatsächlich ersetzt oder
    gekappt wurde, einen sha1-Suffix der ROHEN card_id anhängen — das macht
    sonst gleich aussehende Ergebnisse wieder eindeutig und hält die Länge
    unter dem Limit. Unveränderte IDs (der Normalfall, "sv03-125" & Co.)
    behalten ihren schönen, lesbaren Namen.
    """
    raw = card_id or ""
    substituted = _UNSAFE_FILENAME_CHARS.sub("_", raw)
    was_replaced = substituted != raw
    was_truncated = len(substituted) > 100
    cleaned = substituted[:100]
    if not cleaned:
        return "_"
    if was_replaced or was_truncated:
        cleaned = f"{cleaned}-{hashlib.sha1(raw.encode()).hexdigest()[:10]}"
    return cleaned


def catalog_image_disk_path(card_id: str, ext: str = ".webp") -> Path:
    """
    Absoluter Ziel-Dateipfad eines Katalogbilds. `ext` (MIT Punkt, z. B.
    ".jpg") folgt seit der Panel-Nacharbeit #43 dem ECHTEN Quellformat
    (download_one erkennt es per PIL nach dem Download) — vorher stand hier
    IMMER ".webp", obwohl z. B. die tcgplayer-Quelle JPEG liefert. Default
    ".webp" erhält bestehende Aufrufer/Tests unverändert: Tests, die
    synthetische Cache-Dateien manuell anlegen (resolve/Detail/Restore),
    schreiben nie über download_one und kennen die echte Quell-Endung deshalb
    ohnehin nicht — sie bleiben bewusst bei ".webp".
    """
    return Path(settings.images_dir) / CATALOG_SUBDIR / f"{safe_catalog_filename(card_id)}{ext}"


def catalog_image_db_pfad(card_id: str, ext: str = ".webp") -> str:
    """Wert für tcgdex_catalog.image_pfad — relativ zu images_dir.parent,
    exakt wie PokemonCard.bild_karte_pfad (siehe Modul-Docstring). `ext` MUSS
    derselbe Wert sein, der für DIESELBE Datei an catalog_image_disk_path()
    ging (download_one übergibt beiden Aufrufen dieselbe lokale Variable) —
    beide Funktionen sind rein und deterministisch, das Ergebnis ist damit
    IMMER vom tatsächlich geschriebenen Pfad abgeleitet, nie unabhängig davon
    geraten."""
    disk = catalog_image_disk_path(card_id, ext)
    return str(disk.relative_to(Path(settings.images_dir).parent))


def resolve_catalog_image_url(
    image_pfad: Optional[str],
    image_url: Optional[str],
    base_url: str,
) -> Optional[str]:
    """
    EINE Stelle für „lokaler Pfad bevorzugt, sonst CDN" (#43, DRY). Reine
    Funktion (kein DB-Zugriff) — leicht direkt testbar.

    - Kein image_pfad -> unverändert die CDN-URL (Verhalten vor #43).
    - image_pfad gesetzt UND die Datei existiert wirklich -> absolute lokale
      URL. Der URL-Teil hinter "/images/" wird aus dem von safe_media_path
      AUFGELÖSTEN Absolutpfad relativ zu images_dir gebildet (nicht durch
      Parsen des gespeicherten Strings) — das bleibt korrekt, unabhängig
      davon, wie images_dir tatsächlich heißt (Prod ".../images", Teststand
      ein mkdtemp-Name, gates.sh "/tmp/test-images"). base_url ist dieselbe
      Basis wie die Antwort selbst (request.base_url) — das Frontend bekommt
      dieselbe Form (fertige URL) wie bisher und braucht keine Änderung.
    - image_pfad gesetzt, Datei aber (z. B. nach manuellem Aufräumen) nicht
      mehr vorhanden ODER unsicher (Backup-Manipulation) -> CDN-URL statt
      eines toten Links/404 im Grid.
    """
    if image_pfad:
        full = safe_media_path(image_pfad)
        if full is not None and full.is_file():
            rel = full.relative_to(Path(settings.images_dir).resolve()).as_posix()
            return f"{base_url}{_IMAGES_MOUNT_PREFIX}/{rel}"
    return image_url


def _owned_or_wishlisted_clause():
    """Bedingung „besessen ODER wunschgelistet" — gemeinsame Grundlage für
    Stufe „owned" im Nachtlauf UND im On-demand-Pfad (Bau-Brief Prüffrage 4:
    dieselbe Zweck-Identität, nie zwei Fassungen derselben Regel)."""
    return or_(PokemonCard.besessen == True, PokemonCard.wunschliste == True)  # noqa: E712


def _owned_or_wishlisted_cid_upper_subquery():
    """Case-tolerante (#67) Menge aller verknüpften tcgdex_card_ids, GROSS."""
    return select(func.upper(PokemonCard.tcgdex_card_id)).where(
        PokemonCard.tcgdex_card_id.isnot(None), _owned_or_wishlisted_clause(),
    )


def stage_allows(db: Session, card_id: str, stage: str) -> bool:
    """
    Ob EINE Katalogzeile unter der aktuellen Stufe heruntergeladen werden darf
    — Einzelprüfung für den On-demand-Pfad, dieselbe Regel wie der
    Mengen-Filter des Nachtlaufs (_owned_or_wishlisted_clause, s. o.).
    "all": immer. "owned": nur wenn card_id (case-tolerant, #67) zu einer
    besessenen ODER wunschgelisteten Karte gehört. Alles andere (u. a.
    "urls" und ein unbekannter/künftiger Wert): nie — fail-closed, kein
    Download ohne erkannte Erlaubnis.
    """
    if stage == "all":
        return True
    if stage != "owned":
        return False
    cid_upper = (card_id or "").upper()
    return bool(db.scalar(
        select(PokemonCard.id).where(
            func.upper(PokemonCard.tcgdex_card_id) == cid_upper, _owned_or_wishlisted_clause(),
        ).limit(1)
    ))


async def _fetch_image_bytes(url: str) -> bytes:
    """
    Reine Netz-I/O, keine Validierung/kein Schreiben (eigener Seam fürs Mocken
    in Tests — netzfrei, wie tcgdex.get_card). Wirft bei HTTP-Fehler,
    Nicht-2xx, unerwartetem Content-Type ODER wenn die FINALE URL nach
    Redirects nicht mehr auf einem erlaubten Host liegt (Panel-Nacharbeit #43:
    die Host-Prüfung vor dem Abruf sieht nur die AUSGANGS-URL — ein erlaubter
    Host könnte auf einen fremden umleiten); der Aufrufer (download_one) fängt
    das ab.
    """
    async with httpx.AsyncClient(
        timeout=10.0, follow_redirects=True,
        headers={"User-Agent": "PokeCollect/0.7 (+self-hosted)"},
    ) as client:
        resp = await client.get(url)
    resp.raise_for_status()
    if not tcgdex.is_allowed_image_url(str(resp.url)):
        raise ValueError(f"finale URL nach Redirects nicht erlaubt: {resp.url!r}")
    content_type = resp.headers.get("content-type", "")
    if content_type and not content_type.lower().startswith("image/"):
        raise ValueError(f"unerwarteter Content-Type: {content_type!r}")
    return resp.content


# Katalogbilder, deren Endung download_one nach dem echten PIL-Format wählt
# (Panel-Nacharbeit #43) — alles andere gilt als nicht darstellbares/nicht
# unterstütztes Format und wird verworfen (kein .svg/.gif/.bmp im Bildbaum).
_FORMAT_EXTENSIONS = {"WEBP": ".webp", "JPEG": ".jpg", "PNG": ".png"}


async def download_one(db: Session, row: TcgdexCatalog) -> bool:
    """
    Lädt GENAU EIN Katalogbild, validiert es und setzt image_pfad. Committet
    selbst (Aufrufer iterieren viele Zeilen unabhängig voneinander, #75-Klasse:
    ein Fehlschlag darf die anderen nicht anstecken — sofortiges Commit macht
    jeden Erfolg sofort dauerhaft, unabhängig vom Ausgang der nächsten Zeile).

    Nur erlaubte Hosts (tcgdex.is_allowed_image_url — kein eigenes
    Host-Urteil, Lehre aus #47; _fetch_image_bytes prüft zusätzlich die
    FINALE URL nach Redirects). Byte-Kappe WIEDERVERWENDET
    card_images._MAX_UPLOAD_BYTES (12 MB, DRY — keine zweite Konstante für
    dieselbe Bedeutung).

    tmp+rename (Panel-Nacharbeit #43): Die Bytes gehen zuerst in eine JE-
    VERSUCH-EINDEUTIGE TMP-Datei im Zielverzeichnis (uuid4-Suffix) — zwei
    gleichzeitige Versuche derselben Karte kollidieren nicht, und ein
    gescheiterter Versuch kann eine aus einem FRÜHEREN Erfolg dort bereits
    gültig liegende Datei nicht mehr treffen (vorher: Direkt-Schreiben nach
    `dest` + `dest.unlink()` bei jedem Fehlschlag riss auch eine bereits
    gültige Datei aus einem früheren Lauf mit). Erst NACH erfolgreicher
    PIL-Validierung wird per os.replace() atomar an den Zielort verschoben,
    dessen Endung dem ECHTEN erkannten Format folgt (PIL img.format) statt
    blind ".webp" anzunehmen — die tcgplayer-Quelle liefert JPEG. Schreib-
    Vorbild wie card_images.py::_save_upright, hier ohne EXIF-Aufrichtung/
    Thumbnail, die braucht ein bereits korrekt orientiertes CDN-Bild nicht.

    False bei JEDEM Grund, nicht zu schreiben (kein Bild/Host, Netzfehler, zu
    groß, kaputtes/unbekanntes Format) — wirft NIE nach außen, auch nicht beim
    Aufräumen der TMP-Datei (eigener INNERER Fang: ein werfender unlink — z. B.
    bei einer extrem langen card_id — darf den Originalfehler weder verdecken
    noch selbst nach außen dringen).
    """
    url = row.image_url
    if not url or not tcgdex.is_allowed_image_url(url):
        return False
    # dest dient hier NUR als Namens-Anker fürs Zielverzeichnis (das
    # Verzeichnis ist unabhängig von der Endung) — die tatsächliche Endung
    # steht erst nach der PIL-Erkennung weiter unten fest.
    dest = catalog_image_disk_path(row.card_id)
    tmp = dest.with_name(dest.name + f".tmp-{uuid4().hex[:8]}")
    try:
        content = await _fetch_image_bytes(url)
        if len(content) > _MAX_UPLOAD_BYTES:
            raise ValueError(f"Bild zu groß ({len(content)} Bytes, Grenze {_MAX_UPLOAD_BYTES})")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with tmp.open("wb") as f:
            f.write(content)
        with Image.open(tmp) as img:
            img.verify()  # wirft bei kaputtem/keinem Bild
            fmt = img.format
        ext = _FORMAT_EXTENSIONS.get(fmt or "")
        if ext is None:
            raise ValueError(f"unerwartetes Bildformat: {fmt!r}")
        final = catalog_image_disk_path(row.card_id, ext)
        os.replace(tmp, final)  # atomar — ab hier existiert entweder die alte ODER die neue Datei, nie ein Zwischenzustand
        row.image_pfad = catalog_image_db_pfad(row.card_id, ext)
        db.commit()
    except Exception as exc:  # noqa: BLE001 — Netz/Datei/Bild-Fehler einer FREMDEN Quelle dürfen nie werfen
        log.warning("Katalog-Bild-Download %s fehlgeschlagen: %s", row.card_id, exc)
        db.rollback()  # Session nie 'aborted' hinterlassen (lehren.md §2) — der Aufrufer sieht diese Exception nicht mehr
        try:
            tmp.unlink(missing_ok=True)
        except Exception as cleanup_exc:  # noqa: BLE001 — ein werfender unlink darf den Originalfehler nicht verdecken
            log.warning("Katalog-Bild-Download %s: TMP-Aufräumen fehlgeschlagen: %s", row.card_id, cleanup_exc)
        return False
    return True


async def run_catalog_image_cache(db: Session, limit: int = 60) -> dict:
    """
    Nachtlauf-Schritt (#43, aufgerufen aus cron.py::_daily_catalog_sync NACH
    dem €-Repass, eigenes Budget). Füllt den lokalen Bild-Cache gemäß der
    aktuellen Stufe (Setting catalog_image_cache_level) in einer Etappe von
    `limit` Bildern. "urls" (Default) lädt nichts — kein Überraschungs-
    Download. Überspringt bereits gecachte Zeilen (image_pfad IS NOT NULL)
    und Zeilen ohne CDN-Bild.

    Sequenziell statt konkurrent (bewusste Vereinfachung gegenüber
    enrich_catalog/refresh_catalog_eur, die TCGdex-JSON-Metadaten parallel
    holen): ein Bild-Download schreibt zusätzlich eine Datei — pro Zeile
    sofort commiten hält das einfach UND macht jeden Fortschritt
    interruption-sicher (ein Abbruch mitten in der Etappe verliert nur die
    noch nicht committeten Zeilen, nicht die bereits geschriebenen). Bei einem
    kleinen Etappen-Limit ist der Laufzeit-Unterschied zu konkurrenten Abrufen
    für einen Nachtlauf ohne wartenden Nutzer vernachlässigbar.

    Eine kaputte/nicht erreichbare Karte darf den Schwung nicht kippen
    (#75-Klasse) — download_one() fängt selbst ab; ein DB-Fehler INNERHALB
    einer Zeile (z. B. beim commit) wird hier zusätzlich gefangen und die
    Session zurückgerollt, bevor es weitergeht (Rollback-Falle, lehren.md §2 —
    ohne rollback() stünde die Session nach einem DB-Fehler auf „aborted" und
    jede folgende Zeile schlüge an InFailedSqlTransaction fehl).

    Zählt geladen/übersprungen/fehlgeschlagen und loggt EINE Zusammenfassungs-
    zeile je Lauf.
    """
    stage = get_setting(db, "catalog_image_cache_level")
    if stage != "owned" and stage != "all":
        return {"stage": stage, "loaded": 0, "skipped": 0, "failed": 0}

    # image_pfad IS NULL hier ist eine EFFIZIENZ-Grenze (nicht erst Tausende
    # längst gecachter Zeilen in `ids` laden) — die eigentliche KORREKTHEITS-
    # Garantie „nichts bereits Gecachtes wird erneut geladen" liefert die
    # zweite, unabhängige Prüfung unten in der Schreibschleife (row.image_pfad
    # nach dem frischen Reload). Ein Test, der NUR diesen Filter entfernt,
    # bleibt deshalb grün — die zweite Schicht fängt es ab (siehe Kommentar im
    # zugehörigen Test, test_43_bild_cache.py).
    query = select(TcgdexCatalog.card_id).where(
        TcgdexCatalog.image_pfad.is_(None),
        TcgdexCatalog.image_url.isnot(None),
    )
    if stage == "owned":
        query = query.where(func.upper(TcgdexCatalog.card_id).in_(_owned_or_wishlisted_cid_upper_subquery()))
    # #43-Nacharbeit G: zufällige statt card_id-sortierte Auswahl — sonst
    # blockieren dauerhaft fehlschlagende Zeilen (z. B. tote CDN-URLs) mit
    # LIMIT n jede Nacht dieselben Budgetplätze (Panel-Sonde: drei Nächte in
    # Folge failed=2 bei unveränderter Stufe, eine gesunde Zeile dahinter kam
    # nie an die Reihe). Kein eigener Test hierfür (keine neue Zusage — die
    # bestehenden Tests sind mengen-, nicht reihenfolgebasiert und bleiben
    # unter zufälliger Reihenfolge unverändert grün).
    ids = list(db.scalars(query.order_by(func.random()).limit(limit)).all())

    loaded = skipped = failed = 0
    for cid in ids:
        # #43-Nacharbeit E: Stufe VOR JEDEM Download erneut lesen — nimmt der
        # Owner sie während eines laufenden Schwungs zurück (z. B. "all" ->
        # "urls"), bricht die Etappe sofort ab statt das bereits gezogene
        # Budget zu Ende zu laden. Rest bleibt ungezählt liegen (nächste Nacht
        # greift der Auswahl-Filter oben erneut).
        current_stage = get_setting(db, "catalog_image_cache_level")
        if current_stage != "owned" and current_stage != "all":
            break
        row = db.get(TcgdexCatalog, cid)
        # row.image_pfad hier ist die MASSGEBLICHE Korrektheits-Prüfung (s. o.):
        # deckt sowohl "zwischen Auswahl und Verarbeitung anderweitig gecacht"
        # als auch "der SQL-Filter oben hätte sie fälschlich mitgeliefert" ab.
        if row is None or row.image_pfad:  # in der Zwischenzeit verschwunden/schon gecacht
            skipped += 1
            continue
        try:
            ok = await download_one(db, row)
        except Exception as exc:  # noqa: BLE001 — #75-Klasse: eine Zeile darf den Schwung nicht kippen
            log.warning("Katalog-Bild-Cache: %s unerwartet fehlgeschlagen: %s", cid, exc)
            db.rollback()  # Session nach einem DB-Fehler nicht im aborted-Zustand lassen (lehren.md §2)
            ok = False
        if ok:
            loaded += 1
        else:
            failed += 1

    log.info(
        "Katalog-Bild-Cache (%s): %d geladen, %d übersprungen, %d fehlgeschlagen.",
        stage, loaded, skipped, failed,
    )
    return {"stage": stage, "loaded": loaded, "skipped": skipped, "failed": failed}


async def cache_one_on_demand(card_id: str) -> None:
    """
    On-demand-Cache für GENAU EINE Katalogkarte (#43) — als FastAPI-
    BackgroundTask aus dem Katalog-Detail-Endpunkt geplant, läuft NACH dem
    Response-Versand (Starlette sendet erst die Antwort, ruft dann die
    BackgroundTasks auf – der Aufrufer wartet nicht darauf). GET bleibt so
    schnell und nebenwirkungsarm: eigene, neue Session (kein Request-Kontext,
    Vorbild card_creation.py::_trigger_image_fetch), genau EIN Bild statt
    einer Batch-Iteration.

    Fail-open: JEDER Fehler wird geloggt, NIE geworfen — ein Cache-Miss darf
    dem Popup nie schaden, das seine Antwort längst hat (Bau-Brief Prüffrage 1).
    Idempotent: bricht sofort ab, wenn die Zeile fehlt oder schon gecacht ist.
    """
    db = SessionLocal()
    try:
        row = db.get(TcgdexCatalog, card_id)
        if not row or row.image_pfad:
            return
        stage = get_setting(db, "catalog_image_cache_level")
        if not stage_allows(db, row.card_id, stage):
            return
        await download_one(db, row)
    except Exception as exc:  # noqa: BLE001 — GET hat längst geantwortet, ein Cache-Miss darf nicht laut werden
        log.warning("Katalog-Bild on-demand für %s fehlgeschlagen: %s", card_id, exc)
    finally:
        db.close()
