"""
Bild-Ablage für Sealed-Produkte (Issue #35, gehärtet #38).

Kein eigener Verarbeitungscode — die Pipeline (Validierung, EXIF-Aufrichtung,
Thumbnail) lebt in services/card_images.py und wird hier 1:1 wiederverwendet
(Kredo: DRY). Der einzige Unterschied zu Karten ist das Datei-Präfix
(`sealed_<id>`) und die Zielfelder am Modell.

Commit-frei (#38, Kredo „testbar by default"): diese Routinen fassen nur
Dateien + Modellfelder an; das `db.commit()` steuert der Router (Atomarität).
"""

from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models.sealed import SealedProduct
from app.services.card_images import _save_upright, _validated_suffix


def _media_full_path(rel: str) -> Path:
    """Relativen DB-Pfad ins Dateisystem auflösen (unterhalb images_dir.parent)."""
    return Path(settings.images_dir).parent / rel


def store_sealed_image(db: Session, product: SealedProduct, file: UploadFile) -> SealedProduct:
    """Upload-Bild (plus Thumbnail) eines Sealed-Produkts ablegen (Bild-Pipeline
    aus card_images) und die Pfadfelder aktualisieren. Wirft ImageValidationError
    bei ungültigen Dateien (Validierung VOR dem ersten Schreiben). KEIN Commit
    und KEIN Löschen von Altdateien — beides steuert der Router: erst commit,
    dann cleanup_sealed_orphans() (#38, Atomarität — nie Datei vor DB löschen)."""
    suffix = _validated_suffix(file)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    img_path = images_dir / f"sealed_{product.id}{suffix}"
    thumb_path = images_dir / f"sealed_{product.id}_thumb{suffix}"
    _save_upright(file, img_path, thumb=thumb_path)

    product.bild_pfad = str(img_path.relative_to(images_dir.parent))
    product.bild_thumbnail_pfad = str(thumb_path.relative_to(images_dir.parent))
    return product


def cleanup_sealed_orphans(product: SealedProduct) -> None:
    """Nach durablem Commit aufräumen: alle sealed_<id>-Dateien entfernen, die
    NICHT die aktuell referenzierten sind (#38). Fängt den Endungswechsel ab
    (.jpg → .png ließe sonst die Altdatei verwaisen). Best-effort und POST-Commit:
    schlägt der Commit vorher fehl, läuft das hier NICHT — dann bleiben die
    Altdateien (auf die die zurückgerollte DB weiter zeigt) unangetastet, und
    höchstens die neu geschriebenen Dateien verwaisen (kein toter DB-Zeiger)."""
    images_dir = Path(settings.images_dir)
    keep = {
        Path(p).name
        for p in (product.bild_pfad, product.bild_thumbnail_pfad)
        if p
    }
    for pattern in (f"sealed_{product.id}.*", f"sealed_{product.id}_thumb.*"):
        for old in images_dir.glob(pattern):
            if old.name not in keep:
                try:
                    old.unlink()
                except OSError:
                    pass  # best-effort — DB ist die Wahrheit, Datei-Leak tolerierbar


def clear_sealed_image(product: SealedProduct) -> list[Path]:
    """Leert die Bild-Pfadfelder und gibt die zugehörigen Dateipfade zurück,
    damit der AUFRUFER sie NACH einem erfolgreichen Commit löscht (#38: erst
    DB durabel, dann Datei entfernen — nie umgekehrt). Kein Commit, kein unlink."""
    paths: list[Path] = []
    for path_field in ("bild_pfad", "bild_thumbnail_pfad"):
        p = getattr(product, path_field)
        if p:
            paths.append(_media_full_path(p))
        setattr(product, path_field, None)
    return paths


def unlink_media_files(paths: list[Path]) -> None:
    """Bilddateien nach durablem DB-Commit entfernen (#38)."""
    for full in paths:
        try:
            if full.exists():
                full.unlink()
        except OSError:
            pass  # Datei weg / nicht löschbar → Feld ist bereits geleert
