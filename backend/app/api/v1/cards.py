import math
import os
import shutil
from pathlib import Path
from typing import Optional

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

log = logging.getLogger(__name__)
from PIL import Image, ImageOps
from sqlalchemy import func, select, update, or_, and_, cast, String
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.domain.pokedex import GEN_RANGES
from app.services.card_creation import _trigger_image_fetch, create_owned_card
from app.services.card_image_service import (
    apply_card_to_model,
    fetch_tcgdex_card,
    resolve_set_id,
)
from app.models.card import PokemonCard, PreisHistorie
from app.models.collection import Collection, collection_cards
from app.schemas.card import (
    CardCreate, CardListResponse, CardResponse, CardUpdate,
    EnumsResponse, PreisHistorieResponse, StatsResponse,
    SELTENHEIT_VALUES, KARTENVERSION_VALUES, FOLIERUNG_VALUES,
    SPRACHE_VALUES, ZUSTAND_VALUES, PRIORITAET_VALUES,
)
from app.schemas.collection import CollectionResponse

router = APIRouter(prefix="/cards", tags=["cards"])

THUMB_SIZE = (200, 280)


def _card_or_404(card_id: int, db: Session) -> PokemonCard:
    card = db.get(PokemonCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")
    return card


@router.get("", response_model=CardListResponse)
def list_cards(
    besessen: Optional[bool] = None,
    wunschliste: Optional[bool] = None,
    im_pokedex: Optional[bool] = None,
    pokedex_view: bool = False,
    prioritaet: Optional[str] = None,
    set: Optional[str] = None,
    seltenheit: Optional[str] = None,
    sprache: Optional[str] = None,
    illustrator: Optional[str] = None,
    generation: Optional[int] = None,
    search: Optional[str] = None,
    pokedex_nr: Optional[int] = None,
    bild_status: Optional[str] = Query(None, pattern="^(eigenes_foto|externe_url|platzhalter)$"),
    sort: str = Query("pokedex_nr", pattern="^(pokedex_nr|wert|hinzugefuegt_am|set)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=5000),  # Binder-Ansicht lädt den ganzen Pokédex auf einmal
    db: Session = Depends(get_db),
):
    q = select(PokemonCard)

    # Pokédex-Ansicht: je pokedex_nr genau eine Karte (im_pokedex=True bevorzugt,
    # dann erste besessene Karte als Fallback, dann Platzhalter für nicht gesammelte)
    if pokedex_view:
        flagged = select(PokemonCard.pokedex_nr).where(
            PokemonCard.im_pokedex == True,
            PokemonCard.pokedex_nr.isnot(None),
        )
        owned_nrs = select(PokemonCard.pokedex_nr).where(
            PokemonCard.besessen == True,
            PokemonCard.pokedex_nr.isnot(None),
        )
        fallback = (
            select(func.min(PokemonCard.id))
            .where(
                PokemonCard.pokedex_nr.isnot(None),
                PokemonCard.besessen == True,
                ~PokemonCard.pokedex_nr.in_(flagged),
            )
            .group_by(PokemonCard.pokedex_nr)
        )
        q = q.where(
            PokemonCard.pokedex_nr.isnot(None),
            or_(
                PokemonCard.im_pokedex == True,
                PokemonCard.id.in_(fallback),
                # Platzhalter nur, wenn die Spezies weder geflaggt noch besessen ist
                and_(
                    PokemonCard.besessen == False,
                    ~PokemonCard.pokedex_nr.in_(flagged),
                    ~PokemonCard.pokedex_nr.in_(owned_nrs),
                ),
            ),
        )

    if besessen is not None:
        q = q.where(PokemonCard.besessen == besessen)
    if wunschliste is not None:
        q = q.where(PokemonCard.wunschliste == wunschliste)
    if im_pokedex is not None:
        q = q.where(PokemonCard.im_pokedex == im_pokedex)
    if prioritaet:
        q = q.where(PokemonCard.prioritaet == prioritaet)
    if set:
        q = q.where(PokemonCard.set_edition.ilike(f"%{set}%"))
    if seltenheit:
        q = q.where(PokemonCard.seltenheit == seltenheit)
    if sprache:
        q = q.where(PokemonCard.sprache == sprache)
    if illustrator:
        q = q.where(PokemonCard.illustrator.ilike(f"%{illustrator}%"))
    if pokedex_nr is not None:
        q = q.where(PokemonCard.pokedex_nr == pokedex_nr)
    if search:
        term = f"%{search}%"
        # Suche nach Name UND partieller Pokédex-Nr. (z.B. "2" findet #2, #23, #253 …)
        q = q.where(
            PokemonCard.kartenname.ilike(term)
            | PokemonCard.englischer_name.ilike(term)
            | cast(PokemonCard.pokedex_nr, String).ilike(term)
        )
    if bild_status == "eigenes_foto":
        q = q.where(PokemonCard.bild_karte_pfad.isnot(None))
    elif bild_status == "externe_url":
        q = q.where(PokemonCard.bild_karte_pfad.is_(None))
        q = q.where(PokemonCard.bild_pokedex_url.isnot(None))
    elif bild_status == "platzhalter":
        q = q.where(PokemonCard.bild_karte_pfad.is_(None))
        q = q.where(PokemonCard.bild_pokedex_url.is_(None))
    if generation:
        r = GEN_RANGES.get(generation)
        if r:
            q = q.where(PokemonCard.pokedex_nr.between(r[0], r[1]))

    if sort == "set":
        # Nach Set, dann aufgedruckter Kartennummer (Format NNN/… ist nullgepolstert)
        q = q.order_by(PokemonCard.set_edition.nulls_last(), PokemonCard.karten_nr.nulls_last())
    else:
        sort_col = {
            "pokedex_nr": PokemonCard.pokedex_nr,
            "wert": PokemonCard.wert_eur,
            "hinzugefuegt_am": PokemonCard.hinzugefuegt_am,
        }[sort]
        q = q.order_by(sort_col.nulls_last())

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    items = db.scalars(q.offset((page - 1) * limit).limit(limit)).all()

    return CardListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=math.ceil(total / limit) if total else 1,
    )


@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: int, db: Session = Depends(get_db)):
    return _card_or_404(card_id, db)


@router.get("/{card_id}/collections", response_model=list[CollectionResponse])
def get_card_collections(card_id: int, db: Session = Depends(get_db)):
    _card_or_404(card_id, db)
    colls = db.scalars(
        select(Collection)
        .join(collection_cards, collection_cards.c.collection_id == Collection.id)
        .where(collection_cards.c.card_id == card_id)
        .order_by(Collection.name)
    ).all()
    return [
        CollectionResponse(
            id=c.id, name=c.name, beschreibung=c.beschreibung,
            binder_layout=c.binder_layout or "3x3", erstellt_am=c.erstellt_am,
        )
        for c in colls
    ]


@router.post("", response_model=CardResponse, status_code=201)
def create_card(data: CardCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    # Besessene Karten laufen über den Domain-Service (Adoption + Auto-Flag
    # + Bild-Fetch — eine Routine für alle Anlege-Pfade, Issue #4).
    if data.besessen:
        return create_owned_card(db, data.model_dump(), background_tasks=background_tasks)

    card = PokemonCard(**data.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/{card_id}", response_model=CardResponse)
def update_card(card_id: int, data: CardUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    updated = data.model_dump(exclude_unset=True)
    # Pokédex-Exklusivität: wenn im_pokedex=True gesetzt wird, alle anderen Karten
    # mit gleicher pokedex_nr auf False zurücksetzen (1 Pokédex-Slot pro Pokémon)
    if updated.get("im_pokedex") is True and card.pokedex_nr:
        db.execute(
            update(PokemonCard)
            .where(PokemonCard.pokedex_nr == card.pokedex_nr)
            .where(PokemonCard.id != card.id)
            .values(im_pokedex=False)
        )
    for field, value in updated.items():
        setattr(card, field, value)
    # Bild + TCGdex-Referenz neu abrufen wenn relevante Felder geändert wurden
    if any(k in updated for k in ("set_edition", "karten_nr", "sprache")):
        card.bild_karte_url = None  # wird neu gesetzt
        card.set_id = None          # erzwingt Neuauflösung aus set_edition
        background_tasks.add_task(_trigger_image_fetch, card.id)
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: int, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    if not card.besessen:
        raise HTTPException(
            status_code=400,
            detail="Nicht-besessene Karten (Pokédex-Platzhalter) können nicht gelöscht werden.",
        )
    # Pokédex-Daten vor dem Löschen sichern
    pokedex_nr     = card.pokedex_nr
    kartenname     = card.kartenname
    englischer_name = card.englischer_name
    bild_pokedex_url = card.bild_pokedex_url

    db.delete(card)
    db.flush()  # Löschung sichtbar machen, Transaktion noch offen

    # Wenn keine weitere Karte für diese Pokédex-Nr. existiert → Platzhalter neu anlegen
    if pokedex_nr:
        remaining = db.scalar(
            select(func.count(PokemonCard.id))
            .where(PokemonCard.pokedex_nr == pokedex_nr)
        )
        if remaining == 0:
            db.add(PokemonCard(
                pokedex_nr=pokedex_nr,
                kartenname=kartenname,
                englischer_name=englischer_name,
                bild_pokedex_url=bild_pokedex_url,
                besessen=False,
            ))

    db.commit()


# ── Bilder ──────────────────────────────────────────────────────────────────

# Upload-Härtung (Issue #2): nur echte Bildformate, die StaticFiles gefahrlos
# ausliefern kann — kein .svg/.html im /images-Verzeichnis (aktive Inhalte).
_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_MAX_UPLOAD_BYTES = 12 * 1024 * 1024  # 12 MB, analog Scan-Endpoint


def _validated_suffix(upload: UploadFile) -> str:
    """
    Prüft Suffix (Allowlist), Content-Type (image/*) und Größe (12 MB) eines
    Upload-Bilds. Liefert das normalisierte Suffix oder wirft 400/413.
    """
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    if suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail=f"Dateityp {suffix} nicht erlaubt (nur .jpg, .jpeg, .png, .webp)",
        )
    if not (upload.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Content-Type muss image/* sein")
    upload.file.seek(0, os.SEEK_END)
    size = upload.file.tell()
    upload.file.seek(0)
    if size > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Bild zu groß (max. 12 MB)")
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
        raise HTTPException(status_code=400, detail="Bilddatei konnte nicht verarbeitet werden")


@router.post("/{card_id}/image", response_model=CardResponse)
async def upload_image(
    card_id: int,
    file: UploadFile = File(...),
    original: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    card = _card_or_404(card_id, db)
    suffix = _validated_suffix(file)
    if original is not None and original.filename:
        osuffix = _validated_suffix(original)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    img_path = images_dir / f"card_{card_id}{suffix}"
    thumb_path = images_dir / f"card_{card_id}_thumb{suffix}"
    _save_upright(file, img_path, thumb=thumb_path)
    card.bild_karte_pfad = str(img_path.relative_to(images_dir.parent))
    card.bild_thumbnail_pfad = str(thumb_path.relative_to(images_dir.parent))

    # Optional: ungeschnittenes Originalfoto aufbewahren → spätere Bearbeitung
    # kann großzügiger neu zuschneiden (statt nur den vorhandenen Zuschnitt).
    if original is not None and original.filename:
        orig_path = images_dir / f"card_{card_id}_orig{osuffix}"
        _save_upright(original, orig_path)
        card.bild_original_pfad = str(orig_path.relative_to(images_dir.parent))

    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}/image", response_model=CardResponse)
def delete_image(card_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    for path_field in ("bild_karte_pfad", "bild_thumbnail_pfad", "bild_original_pfad"):
        p = getattr(card, path_field)
        if p:
            full = Path(settings.images_dir).parent / p
            if full.exists():
                full.unlink()
        setattr(card, path_field, None)
    db.commit()
    db.refresh(card)
    # Kein eigenes Foto / keine manuelle URL mehr → TCGdex-Bild (neu) abrufen,
    # damit nicht der Platzhalter stehen bleibt.
    if card.besessen and not card.bild_karte_url and not card.bild_pokedex_url:
        background_tasks.add_task(_trigger_image_fetch, card.id)
    return card


# ── Statistiken ──────────────────────────────────────────────────────────────

@router.get("/meta/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count(PokemonCard.id)))
    besessen_count = db.scalar(
        select(func.count(PokemonCard.id)).where(PokemonCard.besessen == True)
    )
    gesamtwert = db.scalar(
        select(func.sum(PokemonCard.wert_eur)).where(PokemonCard.besessen == True)
    )

    def _count_group(col):
        rows = db.execute(
            select(col, func.count(PokemonCard.id))
            .where(col.isnot(None))
            .group_by(col)
            .order_by(func.count(PokemonCard.id).desc())
        ).all()
        return {r[0]: r[1] for r in rows}

    top10 = db.scalars(
        select(PokemonCard)
        .where(PokemonCard.wert_eur.isnot(None))
        .order_by(PokemonCard.wert_eur.desc())
        .limit(10)
    ).all()

    recent = db.scalars(
        select(PokemonCard)
        .order_by(PokemonCard.hinzugefuegt_am.desc())
        .limit(10)
    ).all()

    return StatsResponse(
        gesamt=total,
        besessen=besessen_count,
        nicht_besessen=total - besessen_count,
        gesamtwert_eur=gesamtwert,
        sets=_count_group(PokemonCard.set_edition),
        seltenheiten=_count_group(PokemonCard.seltenheit),
        sprachen=_count_group(PokemonCard.sprache),
        top10_teuerste=top10,
        zuletzt_hinzugefuegt=recent,
    )


@router.get("/meta/enums", response_model=EnumsResponse)
def get_enums():
    return EnumsResponse(
        seltenheit=SELTENHEIT_VALUES,
        kartenversion=KARTENVERSION_VALUES,
        folierung=FOLIERUNG_VALUES,
        sprache=SPRACHE_VALUES,
        zustand=ZUSTAND_VALUES,
        prioritaet=PRIORITAET_VALUES,
    )


# ── Bilder Backfill ───────────────────────────────────────────────────────────

async def _backfill_images_task(force: bool = False):
    """
    Holt TCGdex-Daten (Bild high.webp + Metadaten) für alle besessenen Karten.
    force=True überschreibt auch bereits vorhandene bild_karte_url.
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


@router.post("/meta/backfill-images")
def backfill_images(
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """
    Startet einen Hintergrund-Job, der TCGdex-Bilder + Metadaten für alle
    besessenen Karten abruft.
    force=True: auch Karten mit vorhandener bild_karte_url neu abrufen.
    """
    background_tasks.add_task(_backfill_images_task, force)
    return {"detail": "Backfill gestartet – läuft im Hintergrund."}
