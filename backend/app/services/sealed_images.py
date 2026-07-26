"""
Bild-Ablage für Sealed-Produkte (Issue #35).

Kein eigener Verarbeitungscode — die Pipeline (Validierung, EXIF-Aufrichtung,
Thumbnail) lebt in services/card_images.py und wird hier 1:1 wiederverwendet
(Kredo: DRY). Der einzige Unterschied zu Karten ist das Datei-Präfix
(`sealed_<id>`) und die Zielfelder am Modell.
"""

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sealed import SealedProduct
from app.services.card_images import _save_upright, _validated_suffix


def store_sealed_image(db: Session, product: SealedProduct, file: UploadFile) -> SealedProduct:
    """Upload-Bild (plus Thumbnail) eines Sealed-Produkts ablegen (Bild-Pipeline
    aus card_images) und die Pfadfelder aktualisieren. Wirft ImageValidationError
    bei ungültigen Dateien (Validierung VOR dem ersten Schreiben)."""
    suffix = _validated_suffix(file)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    img_path = images_dir / f"sealed_{product.id}{suffix}"
    thumb_path = images_dir / f"sealed_{product.id}_thumb{suffix}"
    _save_upright(file, img_path, thumb=thumb_path)
    product.bild_pfad = str(img_path.relative_to(images_dir.parent))
    product.bild_thumbnail_pfad = str(thumb_path.relative_to(images_dir.parent))

    db.commit()
    db.refresh(product)
    return product


def remove_sealed_image(db: Session, product: SealedProduct) -> SealedProduct:
    """Löscht die lokalen Bilddateien eines Sealed-Produkts und leert die Felder."""
    for path_field in ("bild_pfad", "bild_thumbnail_pfad"):
        p = getattr(product, path_field)
        if p:
            full = Path(settings.images_dir).parent / p
            if full.exists():
                full.unlink()
        setattr(product, path_field, None)
    db.commit()
    db.refresh(product)
    return product
