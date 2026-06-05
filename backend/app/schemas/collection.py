from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CollectionBase(BaseModel):
    name: str
    beschreibung: Optional[str] = None


class CollectionCreate(CollectionBase):
    pass


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None


class CollectionResponse(CollectionBase):
    id: int
    erstellt_am: Optional[datetime] = None
    karten_anzahl: int = 0

    model_config = {"from_attributes": True}


class CollectionCardAdd(BaseModel):
    card_id: int
