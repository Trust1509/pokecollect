from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.schemas.card import CardResponse
from app.schemas.collection import (
    CollectionCardAdd, CollectionCardResponse, CollectionCreate, CollectionResponse,
    CollectionUpdate, ReorderRequest, SlotRequest,
)

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


def _to_response(coll: Collection, count: int) -> CollectionResponse:
    return CollectionResponse(
        id=coll.id,
        name=coll.name,
        beschreibung=coll.beschreibung,
        binder_layout=coll.binder_layout or "3x3",
        erstellt_am=coll.erstellt_am,
        karten_anzahl=count,
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
    return [_to_response(c, counts.get(c.id, 0)) for c in colls]


@router.post("", response_model=CollectionResponse, status_code=201)
def create_collection(data: CollectionCreate, db: Session = Depends(get_db)):
    coll = Collection(**data.model_dump())
    db.add(coll)
    db.commit()
    db.refresh(coll)
    return _to_response(coll, 0)


@router.get("/{collection_id}", response_model=CollectionResponse)
def get_collection(collection_id: int, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    return _to_response(coll, _count(db, collection_id))


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(coll, field, value)
    db.commit()
    db.refresh(coll)
    return _to_response(coll, _count(db, collection_id))


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
