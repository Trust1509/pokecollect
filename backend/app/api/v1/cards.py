import math
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select, update, or_, and_, cast, String
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain.pokedex import GEN_RANGES
from app.services.card_creation import _trigger_image_fetch, create_owned_card
from app.services.card_images import (
    ImageValidationError,
    backfill_images_task,
    remove_card_images,
    store_card_image,
)
from app.services.stats import collect_stats
from app.domain.search import parse_kurzcode
from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.models.pokemon_set import PokemonSet
from app.schemas.card import (
    CardCreate, CardListResponse, CardResponse, CardUpdate,
    EnumsResponse, StatsResponse,
    SELTENHEIT_VALUES, KARTENVERSION_VALUES, FOLIERUNG_VALUES,
    SPRACHE_VALUES, ZUSTAND_VALUES, PRIORITAET_VALUES,
)
from app.schemas.collection import CollectionResponse

router = APIRouter(prefix="/cards", tags=["cards"])


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
        # Kurzcode „PFL 001" → Set-Kürzel + Kartennummer, aber nur wenn das
        # Kürzel ein bekanntes Set ist (sonst kapert es die Namenssuche).
        kc = parse_kurzcode(search)
        kc_hit = False
        if kc:
            is_set = db.scalar(select(PokemonSet.code).where(PokemonSet.code == kc.code))
            if is_set:
                q = q.where(
                    or_(
                        PokemonCard.set_edition.ilike(f"%({kc.code})%"),
                        PokemonCard.set_edition.ilike(kc.code),
                    ),
                    func.ltrim(func.split_part(PokemonCard.karten_nr, "/", 1), "0") == kc.nr,
                )
                kc_hit = True
        if not kc_hit:
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
# Verarbeitung (Validierung, EXIF-Aufrichtung, Ablage) lebt in
# services/card_images.py — der Router mappt nur Fehler auf HTTP (Issue #14).

@router.post("/{card_id}/image", response_model=CardResponse)
async def upload_image(
    card_id: int,
    file: UploadFile = File(...),
    original: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    card = _card_or_404(card_id, db)
    try:
        return store_card_image(db, card, file, original)
    except ImageValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.delete("/{card_id}/image", response_model=CardResponse)
def delete_image(card_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    card = _card_or_404(card_id, db)
    card = remove_card_images(db, card)
    # Kein eigenes Foto / keine manuelle URL mehr → TCGdex-Bild (neu) abrufen,
    # damit nicht der Platzhalter stehen bleibt.
    if card.besessen and not card.bild_karte_url and not card.bild_pokedex_url:
        background_tasks.add_task(_trigger_image_fetch, card.id)
    return card


# ── Statistiken ──────────────────────────────────────────────────────────────

@router.get("/meta/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    return collect_stats(db)


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

@router.post("/meta/backfill-images")
def backfill_images(
    background_tasks: BackgroundTasks,
    force: bool = False,
):
    """
    Startet einen Hintergrund-Job, der TCGdex-Bilder + Metadaten für alle
    besessenen Karten abruft (services/card_images.py).
    force=True: auch Karten mit vorhandener bild_karte_url neu abrufen.
    """
    background_tasks.add_task(backfill_images_task, force)
    return {"detail": "Backfill gestartet – läuft im Hintergrund."}
