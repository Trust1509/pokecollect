import math
import os
import shutil
from pathlib import Path
from typing import Optional

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile

log = logging.getLogger(__name__)
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, SessionLocal
from app.services.card_image_service import fetch_card_image_url
from app.models.card import PokemonCard, PreisHistorie
from app.schemas.card import (
    CardCreate, CardListResponse, CardResponse, CardUpdate,
    EnumsResponse, PreisHistorieResponse, StatsResponse,
    SELTENHEIT_VALUES, KARTENVERSION_VALUES, FOLIERUNG_VALUES,
    SPRACHE_VALUES, ZUSTAND_VALUES,
)

router = APIRouter(prefix="/cards", tags=["cards"])

THUMB_SIZE = (200, 280)


def _card_or_404(card_id: int, db: Session) -> PokemonCard:
    card = db.get(PokemonCard, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")
    return card


def _generation(pokedex_nr: Optional[int]) -> Optional[int]:
    if not pokedex_nr:
        return None
    ranges = [(1, 151), (152, 251), (252, 386), (387, 493),
              (494, 649), (650, 721), (722, 809), (810, 905), (906, 1025)]
    for gen, (lo, hi) in enumerate(ranges, start=1):
        if lo <= pokedex_nr <= hi:
            return gen
    return None


@router.get("", response_model=CardListResponse)
def list_cards(
    besessen: Optional[bool] = None,
    set: Optional[str] = None,
    seltenheit: Optional[str] = None,
    sprache: Optional[str] = None,
    generation: Optional[int] = None,
    search: Optional[str] = None,
    pokedex_nr: Optional[int] = None,
    bild_status: Optional[str] = Query(None, pattern="^(eigenes_foto|externe_url|platzhalter)$"),
    sort: str = Query("pokedex_nr", pattern="^(pokedex_nr|wert|hinzugefuegt_am)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = select(PokemonCard)

    if besessen is not None:
        q = q.where(PokemonCard.besessen == besessen)
    if set:
        q = q.where(PokemonCard.set_edition.ilike(f"%{set}%"))
    if seltenheit:
        q = q.where(PokemonCard.seltenheit == seltenheit)
    if sprache:
        q = q.where(PokemonCard.sprache == sprache)
    if pokedex_nr is not None:
        q = q.where(PokemonCard.pokedex_nr == pokedex_nr)
    if search:
        term = f"%{search}%"
        q = q.where(
            PokemonCard.kartenname.ilike(term) | PokemonCard.englischer_name.ilike(term)
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
        gen_ranges = {
            1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493),
            5: (494, 649), 6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025),
        }
        r = gen_ranges.get(generation)
        if r:
            q = q.where(PokemonCard.pokedex_nr.between(r[0], r[1]))

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


@router.get("/pokedex/{nr}", response_model=list[CardResponse])
def cards_by_pokedex(nr: int, db: Session = Depends(get_db)):
    cards = db.scalars(select(PokemonCard).where(PokemonCard.pokedex_nr == nr)).all()
    return cards


@router.get("/{card_id}", response_model=CardResponse)
def get_card(card_id: int, db: Session = Depends(get_db)):
    return _card_or_404(card_id, db)


async def _trigger_image_fetch(card_id: int):
    """Holt die pokemon.com URL im Hintergrund und speichert sie."""
    db = SessionLocal()
    try:
        card = db.get(PokemonCard, card_id)
        if not card or not card.besessen or card.bild_karte_pfad or card.bild_pokedex_url:
            return  # nur besessene Karten, eigenes Foto / manuelle URL hat Vorrang
        url = await fetch_card_image_url(card.set_edition, card.karten_nr, card.sprache)
        if url:
            card.bild_karte_url = url
            db.commit()
    finally:
        db.close()


@router.post("", response_model=CardResponse, status_code=201)
def create_card(data: CardCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    card = PokemonCard(**data.model_dump())
    db.add(card)
    db.commit()
    db.refresh(card)
    background_tasks.add_task(_trigger_image_fetch, card.id)
    return card


@router.put("/{card_id}", response_model=CardResponse)
def update_card(card_id: int, data: CardUpdate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    updated = data.model_dump(exclude_unset=True)
    for field, value in updated.items():
        setattr(card, field, value)
    # Bild neu abrufen wenn relevante Felder geändert wurden
    if any(k in updated for k in ("set_edition", "karten_nr", "sprache")):
        card.bild_karte_url = None  # wird neu gesetzt
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
    db.delete(card)
    db.commit()


# ── Bilder ──────────────────────────────────────────────────────────────────

@router.post("/{card_id}/image", response_model=CardResponse)
async def upload_image(
    card_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    card = _card_or_404(card_id, db)
    images_dir = Path(settings.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix.lower() or ".jpg"
    img_path = images_dir / f"card_{card_id}{suffix}"
    thumb_path = images_dir / f"card_{card_id}_thumb{suffix}"

    with img_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Thumbnail erzeugen
    with Image.open(img_path) as img:
        img.thumbnail(THUMB_SIZE)
        img.save(thumb_path)

    card.bild_karte_pfad = str(img_path.relative_to(images_dir.parent))
    card.bild_thumbnail_pfad = str(thumb_path.relative_to(images_dir.parent))
    db.commit()
    db.refresh(card)
    return card


@router.delete("/{card_id}/image", response_model=CardResponse)
def delete_image(card_id: int, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    for path_field in ("bild_karte_pfad", "bild_thumbnail_pfad"):
        p = getattr(card, path_field)
        if p:
            full = Path(settings.images_dir).parent / p
            if full.exists():
                full.unlink()
        setattr(card, path_field, None)
    db.commit()
    db.refresh(card)
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


@router.get("/meta/sets", response_model=list[str])
def get_sets(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(PokemonCard.set_edition)
        .where(PokemonCard.set_edition.isnot(None))
        .distinct()
        .order_by(PokemonCard.set_edition)
    ).all()
    return list(rows)


@router.get("/meta/enums", response_model=EnumsResponse)
def get_enums():
    return EnumsResponse(
        seltenheit=SELTENHEIT_VALUES,
        kartenversion=KARTENVERSION_VALUES,
        folierung=FOLIERUNG_VALUES,
        sprache=SPRACHE_VALUES,
        zustand=ZUSTAND_VALUES,
    )


# ── Bilder Backfill ───────────────────────────────────────────────────────────

async def _backfill_images_task(force: bool = False):
    """
    Holt pokemon.com URLs für alle Karten die noch kein Bild haben.
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
            url = await fetch_card_image_url(card.set_edition, card.karten_nr, card.sprache)
            if url:
                card.bild_karte_url = url
                ok += 1
        db.commit()
        log.info(f"Backfill abgeschlossen: {ok}/{len(cards)} Bilder gefunden")
    finally:
        db.close()


@router.post("/meta/backfill-images")
def backfill_images(
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """
    Startet einen Hintergrund-Job der pokemon.com Bilder für alle Karten abruft.
    force=True: auch Karten mit vorhandener bild_karte_url neu abrufen.
    """
    background_tasks.add_task(_backfill_images_task, force)
    return {"detail": "Backfill gestartet – läuft im Hintergrund."}
