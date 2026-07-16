from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

from app.schemas.card import CardResponse

BINDER_LAYOUTS = ["1x1", "2x2", "3x3", "4x3", "3x4", "4x4"]

# Sammlungs-Typen (Issue #16): "frei" = klassischer Binder,
# "set_ziel" = Set-Sammlung mit kuratierbarer Soll-Liste.
CollectionTyp = Literal["frei", "set_ziel"]


class CollectionBase(BaseModel):
    name: str
    beschreibung: Optional[str] = None


class CollectionCreate(CollectionBase):
    typ: CollectionTyp = "frei"
    ziel_set_id: Optional[str] = None      # Pflicht bei typ="set_ziel"
    ziel_folierung: Optional[str] = None   # NULL = egal
    ziel_sprache: Optional[str] = None     # NULL = egal
    ziel_master_set: bool = False          # inkl. Secret Rares


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    beschreibung: Optional[str] = None
    binder_layout: Optional[str] = None
    binder_slots: Optional[int] = None


class ProgressResponse(BaseModel):
    """Fortschritt eines Sammelziels: erfüllte Soll-Slots / Soll gesamt."""
    erfuellt: int
    soll: int


class CollectionResponse(CollectionBase):
    id: int
    binder_layout: Optional[str] = "3x3"
    binder_slots: Optional[int] = None
    erstellt_am: Optional[datetime] = None
    karten_anzahl: int = 0
    # Set-Sammlung (Issue #16)
    typ: str = "frei"
    ziel_set_id: Optional[str] = None
    ziel_folierung: Optional[str] = None
    ziel_sprache: Optional[str] = None
    ziel_master_set: bool = False
    fortschritt: Optional[ProgressResponse] = None  # nur bei typ="set_ziel"

    model_config = {"from_attributes": True}


# ── Soll-Liste einer Set-Sammlung (Issue #16) ────────────────────────────────

class SollSlotCreate(BaseModel):
    tcgdex_card_id: str
    soll_folierung: Optional[str] = None  # NULL = Regel (ziel_folierung) gilt


class SollSlotUpdate(BaseModel):
    soll_folierung: Optional[str] = None
    position: Optional[int] = None


class SollSlotResponse(BaseModel):
    id: int
    tcgdex_card_id: str
    soll_folierung: Optional[str] = None
    position: Optional[int] = None
    erfuellt: bool = False
    karte_id: Optional[int] = None
    karte: Optional[CardResponse] = None  # erfüllende Bestandskarte (falls vorhanden)
    # Katalog-Anzeige (Platzhalter für fehlende Slots)
    name: Optional[str] = None
    name_en: Optional[str] = None
    local_id: Optional[str] = None
    image_url: Optional[str] = None
    rarity: Optional[str] = None
    set_id: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    dex_id: Optional[int] = None


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


class CardPosition(BaseModel):
    card_id: int
    position: int


class PositionsRequest(BaseModel):
    """Bulk: mehrere Karten-Positionen explizit setzen (Seiten-Reorder/-Löschen)."""
    positions: list[CardPosition]
