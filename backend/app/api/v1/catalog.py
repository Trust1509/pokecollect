"""
TCGdex-Katalog: durchsuchbares Nachschlagewerk aller Karten.
Read-only; per Stern auf die Wunschliste / in Sammlungen übernehmbar.
"""

import math

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.schemas.catalog import CatalogItem, CatalogListResponse
from app.services import catalog as catalog_svc
from app.services.set_sync import sync_sets

router = APIRouter(prefix="/catalog", tags=["catalog"])

_GEN_RANGES = {
    1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493),
    5: (494, 649), 6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025),
}


@router.get("", response_model=CatalogListResponse)
def list_catalog(
    q: str | None = None,
    set_code: str | None = None,
    set_id: str | None = None,
    illustrator: str | None = None,
    generation: int | None = None,
    sort: str = Query("set", pattern="^(set|name|dex)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(60, ge=1, le=500),
    db: Session = Depends(get_db),
):
    query = select(TcgdexCatalog)
    if q:
        term = f"%{q.strip()}%"
        query = query.where(or_(
            TcgdexCatalog.name.ilike(term),
            TcgdexCatalog.name_en.ilike(term),
            TcgdexCatalog.illustrator.ilike(term),
            TcgdexCatalog.local_id.ilike(term),
        ))
    if set_code:
        query = query.where(TcgdexCatalog.set_code == set_code)
    if set_id:
        query = query.where(TcgdexCatalog.set_id == set_id)
    if illustrator:
        query = query.where(TcgdexCatalog.illustrator.ilike(f"%{illustrator}%"))
    if generation and generation in _GEN_RANGES:
        lo, hi = _GEN_RANGES[generation]
        query = query.where(TcgdexCatalog.dex_id.between(lo, hi))

    if sort == "name":
        query = query.order_by(TcgdexCatalog.name.nulls_last())
    elif sort == "dex":
        query = query.order_by(TcgdexCatalog.dex_id.nulls_last(), TcgdexCatalog.set_id)
    else:  # set + Kartennummer
        query = query.order_by(
            TcgdexCatalog.set_id,
            TcgdexCatalog.local_id_num.nulls_last(),
            TcgdexCatalog.local_id,
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.offset((page - 1) * limit).limit(limit)).all()

    # Besitz-/Pokédex-Status der angezeigten Karten ermitteln (grüner/roter Punkt)
    ids = [r.card_id for r in rows]
    owned_ids: set[str] = set()
    pokedex_ids: set[str] = set()
    if ids:
        owned_ids = set(db.scalars(
            select(PokemonCard.tcgdex_card_id).where(
                PokemonCard.tcgdex_card_id.in_(ids), PokemonCard.besessen == True)  # noqa: E712
        ).all())
        pokedex_ids = set(db.scalars(
            select(PokemonCard.tcgdex_card_id).where(
                PokemonCard.tcgdex_card_id.in_(ids), PokemonCard.im_pokedex == True)  # noqa: E712
        ).all())

    items = []
    for r in rows:
        ci = CatalogItem.model_validate(r)
        ci.owned = r.card_id in owned_ids
        ci.in_pokedex = r.card_id in pokedex_ids
        items.append(ci)

    return CatalogListResponse(
        items=items, total=total, page=page, limit=limit,
        pages=math.ceil(total / limit) if total else 1,
    )


@router.get("/meta")
def catalog_meta(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(TcgdexCatalog)) or 0
    enriched = db.scalar(
        select(func.count()).select_from(TcgdexCatalog).where(TcgdexCatalog.enriched == True)  # noqa: E712
    ) or 0
    return {"total": int(total), "enriched": int(enriched)}


@router.post("/sync")
async def trigger_catalog_sync(background_tasks: BackgroundTasks):
    """Sets voll-syncen + Katalog-Basis aufbauen (Hintergrund). Danach ggf. /enrich."""
    async def _job():
        await sync_sets()
        await catalog_svc.sync_catalog()
    background_tasks.add_task(_job)
    return {"detail": "Katalog-Sync gestartet (Sets + Katalog-Basis) – läuft im Hintergrund."}


@router.post("/enrich")
async def trigger_catalog_enrich(background_tasks: BackgroundTasks, limit: int = Query(500, ge=1, le=5000)):
    """Volldetails (Illustrator/Rarity/dexId/Varianten) für N Karten nachladen."""
    background_tasks.add_task(catalog_svc.enrich_catalog, limit)
    return {"detail": f"Enrichment für bis zu {limit} Karten gestartet."}


@router.post("/enrich-all")
async def trigger_catalog_enrich_all(background_tasks: BackgroundTasks):
    """Reichert ALLE noch offenen Karten an (läuft selbstständig durch). Einmal aufrufen."""
    background_tasks.add_task(catalog_svc.enrich_all)
    return {"detail": "Enrichment aller Karten gestartet – läuft im Hintergrund bis fertig."}


@router.get("/illustrators")
def list_illustrators(db: Session = Depends(get_db)):
    """Alle bekannten Illustratoren (für das Filter-Dropdown)."""
    rows = db.scalars(
        select(TcgdexCatalog.illustrator)
        .where(TcgdexCatalog.illustrator.isnot(None))
        .distinct()
        .order_by(TcgdexCatalog.illustrator)
    ).all()
    return [r for r in rows if r]


@router.post("/{card_id}/wishlist")
async def catalog_to_wishlist(card_id: str, prioritaet: str | None = Body(None, embed=True), db: Session = Depends(get_db)):
    new_id = await catalog_svc.add_to_wishlist(db, card_id, prioritaet)
    if not new_id:
        raise HTTPException(status_code=404, detail="Katalog-Karte nicht gefunden")
    return {"card_id": new_id}


@router.post("/{card_id}/collection")
async def catalog_to_collection(card_id: str, collection_id: int = Query(...), db: Session = Depends(get_db)):
    new_id = await catalog_svc.add_to_collection(db, card_id, collection_id)
    if not new_id:
        raise HTTPException(status_code=404, detail="Katalog-Karte oder Sammlung nicht gefunden")
    return {"card_id": new_id}
