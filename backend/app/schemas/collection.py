from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.card import CardResponse

BINDER_LAYOUTS = ["1x1", "2x2", "3x3", "4x3", "3x4", "4x4"]


class CollectionBase(BaseModel):
    name: str
    beschreibung: Optional[str] = None


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None
    binder_layout: Optional[str] = None
    binder_slots: Optional[int] = None


class CollectionResponse(CollectionBase):
    id: int
    binder_layout: Optional[str] = "3x3"
    binder_slots: Optional[int] = None
    erstellt_am: Optional[datetime] = None
    karten_anzahl: int = 0

    model_config = {"from_attributes": True}


class CollectionCardAdd(BaseModel):
    card_id: int


class CollectionCardResponse(CardResponse):
    """Karte innerhalb einer Sammlung inkl. Slot-Position."""
    position: Optional[int] = None


class ReorderRequest(BaseModel):
    """Kompakte Neuordnung (Grid-DnD): Karten-IDs in gewünschter Reihenfolge."""
    order: list[int]


class SlotRequest(BaseModel):
    """Binder-DnD: Karte auf Slot-Index verschieben (Tausch falls belegt)."""
    slot: int
