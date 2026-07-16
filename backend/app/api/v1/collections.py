from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard
from app.models.collection import Collection, CollectionSoll, collection_cards
from app.models.tcgdex_catalog import TcgdexCatalog
from app.schemas.card import CardResponse
from app.schemas.collection import (
    CollectionCardAdd, CollectionCardResponse, CollectionCreate, CollectionResponse,
    CollectionUpdate, PositionsRequest, ProgressResponse, ReorderRequest,
    SlotRequest, SollSlotCreate, SollSlotResponse, SollSlotUpdate,
)
from app.services import catalog as catalog_svc
from app.services import set_goal

router = APIRouter(prefix="/collections", tags=["collections"])


def _card_with_position(card: PokemonCard, position) -> CollectionCardResponse:
    base = CardResponse.model_validate(card).model_dump()
    return CollectionCardResponse(**base, position=position)


def _card_counts(db: Session) -> dict[int, int]:
    rows = db.execute(
        select(collection_cards.c.collection_id, func.count(collection_cards.c.card_id))
        .group_by(collection_cards.c.collection_id)
    ).all()
    return {r[0]: r[1] for r in rows}


def _to_response(db: Session, coll: Collection, count: int) -> CollectionResponse:
    typ = coll.typ or "frei"
    return CollectionResponse(
        id=coll.id,
        name=coll.name,
        beschreibung=coll.beschreibung,
        binder_layout=coll.binder_layout or "3x3",
        binder_slots=coll.binder_slots,
        erstellt_am=coll.erstellt_am,
        karten_anzahl=count,
        typ=typ,
        ziel_set_id=coll.ziel_set_id,
        ziel_folierung=coll.ziel_folierung,
        ziel_sprache=coll.ziel_sprache,
        ziel_master_set=bool(coll.ziel_master_set),
        fortschritt=(
            ProgressResponse(**set_goal.progress(db, coll)) if typ == "set_ziel" else None
        ),
    )


def _collection_or_404(collection_id: int, db: Session) -> Collection:
    coll = db.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Sammlung nicht gefunden")
    return coll


def _count(db: Session, collection_id: int) -> int:
    return db.scalar(
        select(func.count(collection_cards.c.card_id))
        .where(collection_cards.c.collection_id == collection_id)
    ) or 0


@router.get("", response_model=list[CollectionResponse])
def list_collections(db: Session = Depends(get_db)):
    colls = db.scalars(select(Collection).order_by(Collection.name)).all()
    counts = _card_counts(db)
    return [_to_response(db, c, counts.get(c.id, 0)) for c in colls]


@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    if data.typ == "set_ziel" and not data.ziel_set_id:
        raise HTTPException(status_code=400, detail="Set-Sammlung braucht ein ziel_set_id")
    coll = Collection(**data.model_dump())
    db.add(coll)
    db.commit()
    db.refresh(coll)
    if coll.typ == "set_ziel":
        # Soll-Liste automatisch vorbefüllen (Startvorschlag, danach kuratierbar)
        set_goal.prefill_soll(db, coll)
    return _to_response(db, coll, 0)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    return _to_response(db, coll, _count(db, collection_id))


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(coll, field, value)
    db.commit()
    db.refresh(coll)
    return _to_response(db, coll, _count(db, collection_id))


@router.delete("/{collection_id}", status_code=204)
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    db.delete(coll)  # collection_cards-Einträge via ondelete=CASCADE
    db.commit()


# ── Karten einer Sammlung ─────────────────────────────────────────────────────

@router.get("/{collection_id}/cards", response_model=list[CollectionCardResponse])
def list_collection_cards(collection_id: int, db: Session = Depends(get_db)):
    _collection_or_404(collection_id, db)
    rows = db.execute(
        select(PokemonCard, collection_cards.c.position)
        .join(collection_cards, collection_cards.c.card_id == PokemonCard.id)
        .where(collection_cards.c.collection_id == collection_id)
        .order_by(collection_cards.c.position.nulls_last(), PokemonCard.id)
    ).all()
    return [_card_with_position(card, position) for card, position in rows]


@router.post("/{collection_id}/cards", response_model=CollectionCardResponse, status_code=201)
def add_card_to_collection(collection_id: int, data: CollectionCardAdd, db: Session = Depends(get_db)):
    _collection_or_404(collection_id, db)
    card = db.get(PokemonCard, data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")
    existing = db.execute(
        select(collection_cards.c.position)
        .where(collection_cards.c.collection_id == collection_id)
        .where(collection_cards.c.card_id == data.card_id)
    ).first()
    if existing:
        position = existing[0]
    else:
        max_pos = db.scalar(
            select(func.max(collection_cards.c.position))
            .where(collection_cards.c.collection_id == collection_id)
        )
        position = (max_pos + 1) if max_pos is not None else 0
        db.execute(
            collection_cards.insert().values(
                collection_id=collection_id, card_id=data.card_id, position=position,
            )
        )
        db.commit()
    return _card_with_position(card, position)


@router.delete("/{collection_id}/cards/{card_id}", status_code=204)
def remove_card_from_collection(collection_id: int, card_id: int, db: Session = Depends(get_db)):
    _collection_or_404(collection_id, db)
    db.execute(
        collection_cards.delete()
        .where(collection_cards.c.collection_id == collection_id)
        .where(collection_cards.c.card_id == card_id)
    )
    db.commit()


@router.put("/{collection_id}/cards/order", status_code=204)
def reorder_cards(collection_id: int, data: ReorderRequest, db: Session = Depends(get_db)):
    """Kompakte Neuordnung (Grid-DnD): Positionen 0..n gemäß übergebener Reihenfolge."""
    _collection_or_404(collection_id, db)
    for idx, card_id in enumerate(data.order):
        db.execute(
            collection_cards.update()
            .where(collection_cards.c.collection_id == collection_id)
            .where(collection_cards.c.card_id == card_id)
            .values(position=idx)
        )
    db.commit()


@router.put("/{collection_id}/cards/positions", status_code=204)
def set_positions(collection_id: int, data: PositionsRequest, db: Session = Depends(get_db)):
    """Bulk: explizite Positionen setzen (für Seiten verschieben/löschen mit Nachrücken)."""
    _collection_or_404(collection_id, db)
    for p in data.positions:
        db.execute(
            collection_cards.update()
            .where(collection_cards.c.collection_id == collection_id)
            .where(collection_cards.c.card_id == p.card_id)
            .values(position=p.position)
        )
    db.commit()


@router.put("/{collection_id}/cards/{card_id}/slot", status_code=204)
def move_card_to_slot(collection_id: int, card_id: int, data: SlotRequest, db: Session = Depends(get_db)):
    """Binder-DnD: Karte auf Slot-Index setzen. Ist der Slot belegt → Karten tauschen."""
    _collection_or_404(collection_id, db)
    cur = db.execute(
        select(collection_cards.c.position)
        .where(collection_cards.c.collection_id == collection_id)
        .where(collection_cards.c.card_id == card_id)
    ).first()
    if not cur:
        raise HTTPException(status_code=404, detail="Karte nicht in dieser Sammlung")
    old_pos = cur[0]

    # Karte, die aktuell auf dem Ziel-Slot liegt (falls vorhanden)
    occupant = db.execute(
        select(collection_cards.c.card_id)
        .where(collection_cards.c.collection_id == collection_id)
        .where(collection_cards.c.position == data.slot)
    ).first()

    if occupant and occupant[0] != card_id:
        # Swap: Besetzer bekommt die alte Position der gezogenen Karte
        db.execute(
            collection_cards.update()
            .where(collection_cards.c.collection_id == collection_id)
            .where(collection_cards.c.card_id == occupant[0])
            .values(position=old_pos)
        )
    db.execute(
        collection_cards.update()
        .where(collection_cards.c.collection_id == collection_id)
        .where(collection_cards.c.card_id == card_id)
        .values(position=data.slot)
    )
    db.commit()


# ── Soll-Liste / Fortschritt einer Set-Sammlung (Issue #16) ──────────────────

def _soll_or_404(collection_id: int, soll_id: int, db: Session) -> CollectionSoll:
    slot = db.get(CollectionSoll, soll_id)
    if not slot or slot.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Soll-Eintrag nicht gefunden")
    return slot


def _slot_response(db: Session, coll: Collection, soll_id: int) -> SollSlotResponse:
    """Einen einzelnen Slot über die zentrale Status-Routine ausgeben (DRY)."""
    for s in set_goal.soll_status(db, coll):
        if s["id"] == soll_id:
            return SollSlotResponse(**s)
    raise HTTPException(status_code=404, detail="Soll-Eintrag nicht gefunden")


@router.get("/{collection_id}/soll", response_model=list[SollSlotResponse])
def list_soll(collection_id: int, db: Session = Depends(get_db)):
    """Soll-Liste inkl. erfüllt/fehlend, erfüllender Karte und Katalog-Bild."""
    coll = _collection_or_404(collection_id, db)
    return [SollSlotResponse(**s) for s in set_goal.soll_status(db, coll)]


@router.post("/{collection_id}/soll", response_model=SollSlotResponse, status_code=201)
def add_soll(collection_id: int, data: SollSlotCreate, db: Session = Depends(get_db)):
    """Katalog-Karte zur Soll-Liste hinzufügen (Kuratieren)."""
    coll = _collection_or_404(collection_id, db)
    if not db.get(TcgdexCatalog, data.tcgdex_card_id):
        raise HTTPException(status_code=404, detail="Katalog-Karte nicht gefunden")
    max_pos = db.scalar(
        select(func.max(CollectionSoll.position))
        .where(CollectionSoll.collection_id == collection_id)
    )
    slot = CollectionSoll(
        collection_id=collection_id,
        tcgdex_card_id=data.tcgdex_card_id,
        soll_folierung=data.soll_folierung,
        position=(max_pos + 1) if max_pos is not None else 0,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return _slot_response(db, coll, slot.id)


@router.put("/{collection_id}/soll/{soll_id}", response_model=SollSlotResponse)
def update_soll(collection_id: int, soll_id: int, data: SollSlotUpdate, db: Session = Depends(get_db)):
    """Slot kuratieren: Folierung (null = Regel gilt) bzw. Position ändern."""
    coll = _collection_or_404(collection_id, db)
    slot = _soll_or_404(collection_id, soll_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(slot, field, value)
    db.commit()
    return _slot_response(db, coll, slot.id)


@router.delete("/{collection_id}/soll/{soll_id}", status_code=204)
def remove_soll(collection_id: int, soll_id: int, db: Session = Depends(get_db)):
    _collection_or_404(collection_id, db)
    slot = _soll_or_404(collection_id, soll_id, db)
    db.delete(slot)
    db.commit()


@router.post("/{collection_id}/soll/{soll_id}/wishlist")
async def soll_to_wishlist(collection_id: int, soll_id: int, db: Session = Depends(get_db)):
    """Fehlende Soll-Karte auf die Wunschliste übernehmen (bestehender Katalog-Pfad, DRY)."""
    _collection_or_404(collection_id, db)
    slot = _soll_or_404(collection_id, soll_id, db)
    new_id = await catalog_svc.add_to_wishlist(db, slot.tcgdex_card_id)
    if not new_id:
        raise HTTPException(status_code=404, detail="Katalog-Karte nicht gefunden")
    return {"card_id": new_id}


@router.get("/{collection_id}/progress", response_model=ProgressResponse)
def get_progress(collection_id: int, db: Session = Depends(get_db)):
    """Fortschritt "X / Soll" eines Sammelziels."""
    coll = _collection_or_404(collection_id, db)
    return ProgressResponse(**set_goal.progress(db, coll))
