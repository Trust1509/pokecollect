from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


SELTENHEIT_VALUES = [
    "Common", "Uncommon", "Rare", "Double Rare",
    "Ultra Rare", "Secret Rare",
    "Illustration Rare", "Special Illustration Rare",
    "Hyper Rare", "Mega Hyper Rare",
    "ACE SPEC Rare", "Shiny Rare", "Shiny Ultra Rare",
    "Rainbow Rare", "Promo",
]

KARTENVERSION_VALUES = [
    "Normal", "Full Art", "Special Art", "Rainbow", "Gold",
    "Shiny", "Illustration Rare", "Special Illustration Rare",
]

FOLIERUNG_VALUES = [
    "Normal", "Holo", "Cosmos Holo", "Reverse Holo",
    "Reverse Holo – Sterne", "Reverse Holo – Energie",
    "Reverse Holo – Pokéball", "Reverse Holo – Masterball",
    "Reverse Holo – Team Rocket R", "Reverse Holo – Muster",
    "Etched Holo", "Bubble Holo",
]

SPRACHE_VALUES = ["DE", "EN", "CN", "JP", "FR", "ES", "IT"]
ZUSTAND_VALUES = ["Mint", "Near Mint", "Excellent", "Good", "Played"]
PRIORITAET_VALUES = ["Chase", "Hoch", "Mittel", "Niedrig"]


class CardBase(BaseModel):
    kartenname: str
    pokedex_nr: Optional[int] = None
    englischer_name: Optional[str] = None
    set_edition: Optional[str] = None
    karten_nr: Optional[str] = None
    seltenheit: Optional[str] = None
    kartenversion: Optional[str] = None
    folierung: Optional[str] = None
    sprache: Optional[str] = "DE"
    besessen: bool = False
    wunschliste: bool = False
    prioritaet: Optional[str] = None
    wert_eur: Optional[Decimal] = None
    notizen: Optional[str] = None
    zustand: Optional[str] = None
    bild_pokedex_url: Optional[str] = None


class CardCreate(CardBase):
    pass


class CardUpdate(BaseModel):
    kartenname: Optional[str] = None
    pokedex_nr: Optional[int] = None
    englischer_name: Optional[str] = None
    set_edition: Optional[str] = None
    karten_nr: Optional[str] = None
    seltenheit: Optional[str] = None
    kartenversion: Optional[str] = None
    folierung: Optional[str] = None
    sprache: Optional[str] = None
    besessen: Optional[bool] = None
    wunschliste: Optional[bool] = None
    prioritaet: Optional[str] = None
    wert_eur: Optional[Decimal] = None
    notizen: Optional[str] = None
    zustand: Optional[str] = None
    bild_pokedex_url: Optional[str] = None


class CardResponse(CardBase):
    id: int
    wert_aktualisiert: Optional[datetime] = None
    bild_karte_url: Optional[str] = None
    bild_karte_pfad: Optional[str] = None
    bild_thumbnail_pfad: Optional[str] = None
    hinzugefuegt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PreisHistorieResponse(BaseModel):
    id: int
    karte_id: int
    wert_eur: Optional[Decimal] = None
    quelle: Optional[str] = None
    erfasst_am: datetime

    model_config = {"from_attributes": True}


class CardListResponse(BaseModel):
    items: list[CardResponse]
    total: int
    page: int
    limit: int
    pages: int


class StatsResponse(BaseModel):
    gesamt: int
    besessen: int
    nicht_besessen: int
    gesamtwert_eur: Optional[Decimal] = None
    sets: dict[str, int]
    seltenheiten: dict[str, int]
    sprachen: dict[str, int]
    top10_teuerste: list[CardResponse]
    zuletzt_hinzugefuegt: list[CardResponse]


class EnumsResponse(BaseModel):
    seltenheit: list[str]
    kartenversion: list[str]
    folierung: list[str]
    sprache: list[str]
    zustand: list[str]
    prioritaet: list[str]
