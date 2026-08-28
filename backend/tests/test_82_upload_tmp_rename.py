"""
Issue #82: tmp+rename in card_images.py::_save_upright.

Vorher schrieb _save_upright den rohen Upload DIREKT auf die stabile
Zieldatei und löschte bei JEDEM Verarbeitungsfehler Zieldatei UND Thumbnail
(dst.unlink() + thumb.unlink() im except). Ein fehlgeschlagener Re-Upload mit
DERSELBEN Endung (häufigster Fall: jpg → jpg) vernichtete damit das bereits
gültig liegende Foto samt Thumbnail. Seit #82 läuft die Verarbeitung auf
JE-VERSUCH-EINDEUTIGEN TMP-Dateien im Zielverzeichnis; erst nach vollständig
erfolgreicher Verarbeitung übernimmt os.replace() atomar (Vorbild:
catalog_images.py::download_one, #43-Nacharbeit).

Beide Türen (Karten UND Sealed) teilen sich _save_upright — je ein Test pro
Tür belegt, dass der zentrale Fix wirklich BEIDE Konsumenten erreicht, ohne
dass store_card_image oder store_sealed_image selbst geändert wurden.

Panel-Nacharbeit: seit beide os.replace()-Aufrufe INNERHALB des try liegen,
ergibt auch ein scheiternder Rename (os.replace, z. B. Windows
PermissionError bei offenem Leser) einheitlich 400/ImageValidationError
statt einer unbehandelten Exception/500 — eigener Türtest per
monkeypatch(os.replace).

Netzfrei. Fixtures mit Präfix "test82-".
"""

import io
import os
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.services import card_images

# Erfundene kaputte Bytes (abgeschnittener/kein Header) — kein echtes Bild,
# aber Endung+Content-Type sehen für _validated_suffix gültig aus, sodass der
# Fehlschlag garantiert INNERHALB von _save_upright (PIL-Verarbeitung)
# passiert, nicht schon in der vorgelagerten Validierung.
_KAPUTTE_BYTES = b"test82-abgeschnittener-header-kein-gueltiges-bild"


def _jpeg_bytes(color=(20, 90, 160)) -> bytes:
    """Ein kleines, echtes JPEG (für den gleiche-Endung-Re-Upload-Fall)."""
    buf = io.BytesIO()
    Image.new("RGB", (12, 16), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _no_tmp_leftovers():
    """Keine *.tmp-*-Datei darf im Bildverzeichnis liegen bleiben (#82)."""
    leftovers = list(Path(settings.images_dir).glob("*.tmp-*"))
    assert leftovers == [], f"TMP-Leiche(n) im images_dir: {leftovers}"


@pytest.fixture()
def card_id(client):
    r = client.post(
        "/api/v1/cards",
        json={"kartenname": "Test82-Uploadmon", "besessen": True},
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    yield cid
    client.delete(f"/api/v1/cards/{cid}")


@pytest.fixture()
def sealed_id(client):
    r = client.post("/api/v1/sealed", json={"name": "Test82-Sealed-Display"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    yield pid
    client.delete(f"/api/v1/sealed/{pid}")


# ═══════════════════════════════════════════════════════════════════════════
# Karten-Tür (echte Tür: POST /api/v1/cards/{id}/image)
# ═══════════════════════════════════════════════════════════════════════════

def test_karten_tuer_fehlgeschlagener_reupload_laesst_bild_und_thumb_unangetastet(client, card_id):
    """Rot-Beweis: card_images.py::_save_upright zurück auf Direkt-Schreiben
    nach dst + dst.unlink()/thumb.unlink() bei Fehler -> dieser Test fällt,
    weil der Re-Upload das gültige Bild+Thumb VOR der Validierung überschreibt
    und beim Fehlschlag endgültig löscht."""
    r1 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("erst.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    img_path = Path(settings.images_dir).parent / body1["bild_karte_pfad"]
    thumb_path = Path(settings.images_dir).parent / body1["bild_thumbnail_pfad"]
    assert img_path.is_file() and thumb_path.is_file()
    img_bytes_before = img_path.read_bytes()
    thumb_bytes_before = thumb_path.read_bytes()

    # Zweit-Upload MIT DERSELBEN Endung (.jpg), aber kaputte Bytes.
    r2 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("zweit.jpg", _KAPUTTE_BYTES, "image/jpeg")},
    )
    assert r2.status_code == 400, r2.text

    assert img_path.is_file(), "Bild wurde beim Fehlschlag gelöscht"
    assert thumb_path.is_file(), "Thumbnail wurde beim Fehlschlag gelöscht"
    assert img_path.read_bytes() == img_bytes_before, "Bild wurde überschrieben"
    assert thumb_path.read_bytes() == thumb_bytes_before, "Thumbnail wurde überschrieben"

    got = client.get(f"/api/v1/cards/{card_id}").json()
    assert got["bild_karte_pfad"] == body1["bild_karte_pfad"]
    assert got["bild_thumbnail_pfad"] == body1["bild_thumbnail_pfad"]


# ═══════════════════════════════════════════════════════════════════════════
# Panel-Nacharbeit #82: scheiternder os.replace() (Rename) muss dasselbe
# einheitliche 400/ImageValidationError ergeben wie ein Verarbeitungsfehler
# — nie eine unbehandelte Exception/500 (Panel-Fund: unter Windows wirft
# replace bei noch offenem Leser PermissionError; die beiden replace()-
# Aufrufe lagen vorher AUSSERHALB des try).
# ═══════════════════════════════════════════════════════════════════════════

def test_karten_tuer_rename_fehler_wird_400_und_laesst_bestand_unangetastet(client, card_id, monkeypatch):
    """Rot-Beweis: beide os.replace(...) in card_images.py::_save_upright
    zurück HINTER den try-Block ziehen (Stand vor der #82-Panel-Nacharbeit)
    -> dieser Test fällt, weil ein scheiternder Rename dann nicht mehr von
    ImageValidationError gefangen wird und als 500/durchgereichte Exception
    entkommt statt als 400."""
    r1 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("erst.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    img_path = Path(settings.images_dir).parent / body1["bild_karte_pfad"]
    thumb_path = Path(settings.images_dir).parent / body1["bild_thumbnail_pfad"]
    assert img_path.is_file() and thumb_path.is_file()
    img_bytes_before = img_path.read_bytes()
    thumb_bytes_before = thumb_path.read_bytes()

    def _boom(*a, **k):
        raise OSError("simulierter Rename-Fehler (z. B. Windows PermissionError)")

    monkeypatch.setattr(card_images.os, "replace", _boom)

    # Zweit-Upload: gültige Bytes, gleiche Endung — die Verarbeitung selbst
    # gelingt, NUR der abschließende os.replace() scheitert (simuliert).
    r2 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("zweit.jpg", _jpeg_bytes((5, 5, 5)), "image/jpeg")},
    )
    assert r2.status_code == 400, r2.text

    assert img_path.is_file(), "Bild wurde beim Rename-Fehlschlag gelöscht"
    assert thumb_path.is_file(), "Thumbnail wurde beim Rename-Fehlschlag gelöscht"
    assert img_path.read_bytes() == img_bytes_before, "Bild wurde trotz Rename-Fehler überschrieben"
    assert thumb_path.read_bytes() == thumb_bytes_before, "Thumbnail wurde trotz Rename-Fehler überschrieben"

    got = client.get(f"/api/v1/cards/{card_id}").json()
    assert got["bild_karte_pfad"] == body1["bild_karte_pfad"]
    assert got["bild_thumbnail_pfad"] == body1["bild_thumbnail_pfad"]

    _no_tmp_leftovers()


# ═══════════════════════════════════════════════════════════════════════════
# Sealed-Tür (echte Tür: POST /api/v1/sealed/{id}/image) — derselbe Fall,
# belegt, dass der zentrale Fix den ZWEITEN Konsumenten (store_sealed_image)
# ohne eigene Änderung an sealed_images.py/dem Router mit erreicht.
# ═══════════════════════════════════════════════════════════════════════════

def test_sealed_tuer_fehlgeschlagener_reupload_laesst_bild_und_thumb_unangetastet(client, sealed_id):
    r1 = client.post(
        f"/api/v1/sealed/{sealed_id}/image",
        files={"file": ("erst.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    img_path = Path(settings.images_dir).parent / body1["bild_pfad"]
    thumb_path = Path(settings.images_dir).parent / body1["bild_thumbnail_pfad"]
    assert img_path.is_file() and thumb_path.is_file()
    img_bytes_before = img_path.read_bytes()
    thumb_bytes_before = thumb_path.read_bytes()

    r2 = client.post(
        f"/api/v1/sealed/{sealed_id}/image",
        files={"file": ("zweit.jpg", _KAPUTTE_BYTES, "image/jpeg")},
    )
    assert r2.status_code == 400, r2.text

    assert img_path.is_file(), "Bild wurde beim Fehlschlag gelöscht"
    assert thumb_path.is_file(), "Thumbnail wurde beim Fehlschlag gelöscht"
    assert img_path.read_bytes() == img_bytes_before, "Bild wurde überschrieben"
    assert thumb_path.read_bytes() == thumb_bytes_before, "Thumbnail wurde überschrieben"

    got = client.get(f"/api/v1/sealed/{sealed_id}").json()
    assert got["bild_pfad"] == body1["bild_pfad"]
    assert got["bild_thumbnail_pfad"] == body1["bild_thumbnail_pfad"]


# ═══════════════════════════════════════════════════════════════════════════
# Aufräum-Zusicherung: keine TMP-Leiche nach einem Fehlschlag. Eigener,
# einzweckiger Test — die Byte-Identität-Tests oben würden eine entfernte
# TMP-Aufräumung NICHT auffangen (der TMP-Name kollidiert nie mit dem
# Zielnamen, ein liegen gebliebenes TMP-File verändert dst/thumb nicht).
# ═══════════════════════════════════════════════════════════════════════════

def test_aufraeumen_keine_tmp_datei_bleibt_nach_fehlgeschlagenem_upload(client, card_id):
    """Rot-Beweis: das TMP-Aufräumen im Fehlerpfad von _save_upright entfernen
    (die beiden unlink-Zeilen im inneren try) -> dieser Test fällt, obwohl das
    Hauptbild dabei unangetastet bleibt (siehe Docstring oben)."""
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("kaputt.jpg", _KAPUTTE_BYTES, "image/jpeg")},
    )
    assert r.status_code == 400, r.text
    _no_tmp_leftovers()


# ═══════════════════════════════════════════════════════════════════════════
# Original-Zweig: der ZWEITE _save_upright-Aufruf in store_card_image (fürs
# optionale Originalfoto) profitiert vom selben zentralen Fix.
# ═══════════════════════════════════════════════════════════════════════════

def test_original_zweig_kaputtes_original_laesst_vorbestehendes_original_unangetastet(client, card_id):
    """Ein kaputtes 'original' bei GÜLTIGEM Hauptbild darf ein VORBESTEHENDES
    Originalfoto (gleiche Endung) nicht antasten.

    Cross-Call-Atomarität von store_card_image (das Hauptbild wird in diesem
    selben Aufruf bereits ersetzt, bevor der Original-Zweig scheitert) ist
    bewusst NICHT Gegenstand dieses Tests — siehe Bau-Brief #82,
    Randbedingungen (bestehende, unabhängige Einschränkung)."""
    r1 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={
            "file": ("erst.jpg", _jpeg_bytes((10, 10, 10)), "image/jpeg"),
            "original": ("erst_orig.jpg", _jpeg_bytes((250, 250, 250)), "image/jpeg"),
        },
    )
    assert r1.status_code == 200, r1.text
    body1 = r1.json()
    assert body1["bild_original_pfad"]
    orig_path = Path(settings.images_dir).parent / body1["bild_original_pfad"]
    assert orig_path.is_file()
    orig_bytes_before = orig_path.read_bytes()

    # Zweit-Upload: Hauptbild GÜLTIG, Original KAPUTT, beide mit derselben
    # Endung (.jpg) wie beim Erst-Upload.
    r2 = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={
            "file": ("zweit.jpg", _jpeg_bytes((20, 20, 20)), "image/jpeg"),
            "original": ("zweit_orig.jpg", _KAPUTTE_BYTES, "image/jpeg"),
        },
    )
    assert r2.status_code == 400, r2.text

    assert orig_path.is_file(), "Vorbestehendes Originalfoto wurde gelöscht"
    assert orig_path.read_bytes() == orig_bytes_before, "Vorbestehendes Originalfoto wurde überschrieben"

    got = client.get(f"/api/v1/cards/{card_id}").json()
    assert got["bild_original_pfad"] == body1["bild_original_pfad"]

    _no_tmp_leftovers()
