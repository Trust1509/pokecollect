"""
Upload-Verarbeitung und Bild-Backfill für Karten (Issue #14).

Hier lebt alles Nicht-HTTP rund um Kartenbilder:
  - Validierung von Upload-Dateien (Allowlist, Content-Type, Größe)
  - Aufrecht-Speichern (EXIF-Orientierung) + Thumbnail
  - Ablegen/Entfernen der Bilddateien einer Karte inkl. DB-Feldern
  - Backfill-Job (TCGdex-Bilder + Metadaten für alle besessenen Karten)

Fehler werden als ImageValidationError (ValueError) gemeldet; der Router
mappt sie auf HTTPException (400/413).
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.card import PokemonCard
from app.services.card_image_service import (
    apply_card_to_model,
    fetch_tcgdex_card,
    resolve_set_id,
)

log = logging.getLogger(__name__)

THUMB_SIZE = (200, 280)

# Upload-Härtung (Issue #2): nur echte Bildformate, die StaticFiles gefahrlos
# ausliefern kann — kein .svg/.html im /images-Verzeichnis (aktive Inhalte).
_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB, analog Scan-Endpoint


class ImageValidationError(ValueError):
    """Ungültiges Upload-Bild; status_code trennt 400 (Format) und 413 (Größe)."""

    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _validated_suffix(upload: UploadFile) -> str:
    """
    Prüft Suffix (Allowlist), Content-Type (image/*) und Größe (12 MB) eines
    Upload-Bilds. Liefert das normalisierte Suffix oder wirft
    ImageValidationError (400/413).
    """
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise ImageValidationError(
            f"Dateityp {suffix} nicht erlaubt (nur .jpg, .jpeg, .png, .webp)"
        )
    if not (upload.content_type or "").lower().startswith("image/"):
        raise ImageValidationError("Content-Type muss image/* sein")
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > _MAX_UPLOAD_BYTES:
        raise ImageValidationError("Bild zu groß (max. 12 MB)", status_code=413)
    return suffix


def _save_upright(upload: UploadFile, dst: Path, *, thumb: Optional[Path] = None) -> None:
    """
    Speichert ein hochgeladenes Bild aufrecht (EXIF-Orientierung angewandt) und
    optional ein Thumbnail. Handy-/Galerie-Uploads tragen oft nur eine
    Orientierungs-Marke statt gedrehter Pixel → sonst läge das Foto quer.
    Bei Verarbeitungsfehlern wird die bereits geschriebene Rohdatei entfernt.
    """
    suffix = dst.suffix.lower()
    is_jpeg = suffix in (".jpg", ".jpeg")
    with dst.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    try:
        with Image.open(dst) as img:
            upright = ImageOps.exif_transpose(img)
            if is_jpeg and upright.mode not in ("RGB", "L"):
                upright = upright.convert("RGB")
            kw = {"quality": 90} if is_jpeg else {}
            upright.save(dst, **kw)   # aufrecht zurückschreiben (Marke entfernt)
            if thumb is not None:
                t = upright.copy()
                t.thumbnail(THUMB_SIZE)
                t.save(thumb, **kw)
    except Exception as exc:
        # Rohdatei nicht liegen lassen (Issue #2) — sie wäre sonst öffentlich
        # unter /images erreichbar, obwohl sie kein gültiges Bild ist.
        dst.unlink(missing_ok=True)
        if thumb is not None:
            thumb.unlink(missing_ok=True)
        log.warning("Upload-Bild nicht verarbeitbar: %s", exc)
        raise ImageValidationError("Bilddatei konnte nicht verarbeitet werden")


def store_card_image(
    db: Session,
    card: PokemonCard,
    file: UploadFile,
    original: Optional[UploadFile] = None,
) -> PokemonCard:
    """
    Legt das Upload-Bild (plus Thumbnail, optional Originalfoto) einer Karte
    ab und aktualisiert die Bild-Pfadfelder. Wirft ImageValidationError bei
    ungültigen Dateien — Validierung läuft für beide Dateien VOR dem ersten
    Schreiben.
    """
    suffix = _validated_suffix(file)
    osuffix: Optional[str] = None
    if original is not None and original.filename:
        osuffix = _validated_suffix(original)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    img_path = images_dir / f"card_{card.id}{suffix}"
    thumb_path = images_dir / f"card_{card.id}_thumb{suffix}"
    _save_upright(file, img_path, thumb=thumb_path)
    card.bild_karte_pfad = str(img_path.relative_to(images_dir.parent))
    card.bild_thumbnail_pfad = str(thumb_path.relative_to(images_dir.parent))

    # Optional: ungeschnittenes Originalfoto aufbewahren → spätere Bearbeitung
    # kann großzügiger neu zuschneiden (statt nur den vorhandenen Zuschnitt).
    if osuffix is not None:
        orig_path = images_dir / f"card_{card.id}_orig{osuffix}"
        _save_upright(original, orig_path)
        card.bild_original_pfad = str(orig_path.relative_to(images_dir.parent))

    db.commit()
    db.refresh(card)
    return card


def remove_card_images(db: Session, card: PokemonCard) -> PokemonCard:
    """Löscht alle lokalen Bilddateien einer Karte und leert die Pfadfelder."""
    for path_field in ("bild_karte_pfad", "bild_thumbnail_pfad", "bild_original_pfad"):
        p = getattr(card, path_field)
        if p:
            full = Path(settings.images_dir).parent / p
            if full.exists():
                full.unlink()
        setattr(card, path_field, None)
    db.commit()
    db.refresh(card)
    return card


async def backfill_images_task(force: bool = False):
    """
    Holt TCGdex-Daten (Bild high.webp + Metadaten) für alle besessenen Karten.
    force=True überschreibt auch bereits vorhandene bild_karte_url.
    Läuft als Hintergrund-Job (eigene Session, kein Request-Kontext).
    """
    db = SessionLocal()
    try:
        q = select(PokemonCard).where(PokemonCard.besessen == True)
        if not force:
            q = q.where(PokemonCard.bild_karte_url.is_(None))
            q = q.where(PokemonCard.bild_karte_pfad.is_(None))
            q = q.where(PokemonCard.bild_pokedex_url.is_(None))
        cards = db.scalars(q).all()
        log.info(f"Backfill gestartet: {len(cards)} Karten")
        ok = 0
        for card in cards:
            set_id = card.set_id or resolve_set_id(db, card.set_edition)
            if not set_id:
                continue
            tc = await fetch_tcgdex_card(set_id, card.karten_nr, card.sprache)
            if not tc:
                continue
            overwrite = force or not (card.bild_karte_pfad or card.bild_pokedex_url)
            apply_card_to_model(card, tc, overwrite_image=overwrite)
            ok += 1
        db.commit()
        log.info(f"Backfill abgeschlossen: {ok}/{len(cards)} Karten angereichert")
    finally:
        db.close()
