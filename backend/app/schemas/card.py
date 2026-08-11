from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


SELTENHEIT_VALUES = [
    "Common", "Uncommon", "Rare",
    # Schwert & Schild V-Ära (eigener TCGdex-Seltenheitsgrad, gedruckt: schwarzer Stern)
    "Holo Rare V", "Holo Rare VMAX", "Holo Rare VSTAR",
    "Double Rare",
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
    erste_edition: bool = False
    sprache: Optional[str] = "DE"
    besessen: bool = False
    wunschliste: bool = False
    im_pokedex: bool = False
    prioritaet: Optional[str] = None
    wert_eur: Optional[Decimal] = None
    kaufpreis_eur: Optional[Decimal] = None
    kaufdatum: Optional[date] = None
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
    erste_edition: Optional[bool] = None
    sprache: Optional[str] = None
    besessen: Optional[bool] = None
    wunschliste: Optional[bool] = None
    im_pokedex: Optional[bool] = None
    prioritaet: Optional[str] = None
    wert_eur: Optional[Decimal] = None
    kaufpreis_eur: Optional[Decimal] = None
    kaufdatum: Optional[date] = None
    notizen: Optional[str] = None
    zustand: Optional[str] = None
    bild_pokedex_url: Optional[str] = None


class CardResponse(CardBase):
    id: int
    wert_aktualisiert: Optional[datetime] = None
    bild_karte_url: Optional[str] = None
    bild_karte_pfad: Optional[str] = None
    bild_thumbnail_pfad: Optional[str] = None
    bild_original_pfad: Optional[str] = None
    # TCGdex-Anreicherung
    tcgdex_card_id: Optional[str] = None
    set_id: Optional[str] = None
    dex_id: Optional[int] = None
    illustrator: Optional[str] = None
    variants_normal: Optional[bool] = None
    variants_reverse: Optional[bool] = None
    variants_holo: Optional[bool] = None
    variants_firstedition: Optional[bool] = None
    hinzugefuegt_am: Optional[datetime] = None
    aktualisiert_am: Optional[datetime] = None
    # TCGplayer-$-Marktpreis aus dem Katalog-Cache (Epic #41): reiner Anzeige-
    # Zusatz in der Detailansicht — v. a. für JP-Karten, deren wert_eur daraus
    # umgerechnet wird. Nur GET /cards/{id} füllt die Felder (PK-Lookup).
    katalog_preis_usd: Optional[Decimal] = None
    katalog_preis_usd_stand: Optional[str] = None

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
    # Persönlicher Einstand + unrealisierter G/V der besessenen Karten (#26).
    # gesamt_einstand_eur = Σ kaufpreis_eur (besessen, Kaufpreis gesetzt);
    # unrealisierter_gv_eur = Σ (wert_eur − kaufpreis_eur), nur wo BEIDE gesetzt.
    gesamt_einstand_eur: Optional[Decimal] = None
    unrealisierter_gv_eur: Optional[Decimal] = None
    # ── Sealed-Produkte (#35): getrennt ausgewiesen + Karten+Sealed kombiniert ──
    # Die obigen gesamt*/unrealisiert*-Felder beziehen sich weiter NUR auf Karten;
    # sealed_* ist die Sealed-Summe, kombiniert_* = Karten + Sealed.
    sealed_anzahl: int = 0
    sealed_wert_eur: Optional[Decimal] = None
    sealed_einstand_eur: Optional[Decimal] = None
    sealed_unrealisierter_gv_eur: Optional[Decimal] = None
    kombiniert_wert_eur: Optional[Decimal] = None
    kombiniert_einstand_eur: Optional[Decimal] = None
    kombiniert_unrealisierter_gv_eur: Optional[Decimal] = None
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
