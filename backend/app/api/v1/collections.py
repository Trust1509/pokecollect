from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.schemas.card import CardResponse
from app.schemas.collection import (
    CollectionCardAdd, CollectionCreate, CollectionResponse, CollectionUpdate,
)

router = APIRouter(prefix="/collections", tags=["collections"])


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
        erstellt_am=coll.erstellt_am,
        karten_anzahl=count,
    )


def _collection_or_404(collection_id: int, db: Session) -> Collection:
    coll = db.get(Collection, collection_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Sammlung nicht gefunden")
    return coll


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
    count = db.scalar(
        select(func.count(collection_cards.c.card_id))
        .where(collection_cards.c.collection_id == collection_id)
    )
    return _to_response(coll, count or 0)


@router.put("/{collection_id}", response_model=CollectionResponse)
def update_collection(collection_id: int, data: CollectionUpdate, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(coll, field, value)
    db.commit()
    db.refresh(coll)
    count = db.scalar(
        select(func.count(collection_cards.c.card_id))
        .where(collection_cards.c.collection_id == collection_id)
    )
    return _to_response(coll, count or 0)


@router.delete("/{collection_id}", status_code=204)
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    db.delete(coll)  # collection_cards-Einträge werden via ondelete=CASCADE entfernt
    db.commit()


# ── Karten einer Sammlung ─────────────────────────────────────────────────────

@router.get("/{collection_id}/cards", response_model=list[CardResponse])
def list_collection_cards(collection_id: int, db: Session = Depends(get_db)):
    _collection_or_404(collection_id, db)
    cards = db.scalars(
        select(PokemonCard)
        .join(collection_cards, collection_cards.c.card_id == PokemonCard.id)
        .where(collection_cards.c.collection_id == collection_id)
        .order_by(PokemonCard.kartenname)
    ).all()
    return cards


@router.post("/{collection_id}/cards", response_model=CardResponse, status_code=201)
def add_card_to_collection(collection_id: int, data: CollectionCardAdd, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    card = db.get(PokemonCard, data.card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Karte nicht gefunden")
    if card not in coll.cards:
        coll.cards.append(card)
        db.commit()
    return card


@router.delete("/{collection_id}/cards/{card_id}", status_code=204)
def remove_card_from_collection(collection_id: int, card_id: int, db: Session = Depends(get_db)):
    coll = _collection_or_404(collection_id, db)
    card = db.get(PokemonCard, card_id)
    if card and card in coll.cards:
        coll.cards.remove(card)
        db.commit()
