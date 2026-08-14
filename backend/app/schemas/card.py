from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator

from app.schemas._validators import reject_control_chars, reject_explicit_null


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

# Folierung = preis-zuordenbare GRUNDFORM (#63, Expand-Contract Schritt 1):
# die früheren Kombi-Werte („Reverse Holo – Pokéball", „Cosmos Holo", …) leben
# jetzt als Grundform + MUSTER_VALUES weiter; die Light-Migration teilt
# Bestandswerte auf. Server akzeptiert Alt-Werte weiterhin (keine Validierung
# gegen diese Liste — sie speist nur /enums fürs UI).
FOLIERUNG_VALUES = ["Normal", "Holo", "Reverse Holo"]

# Muster/Pattern der Folierung als eigene Dimension. Auswahlfeld statt
# Checkboxen (Owner-Grilling): Muster schließen sich gegenseitig aus.
MUSTER_VALUES = [
    "Pokéball", "Masterball", "Cosmos", "Etched", "Bubble",
    "Sterne", "Energie", "Team Rocket R", "Sonstiges",
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
    muster: Optional[str] = None       # Folierungs-Muster (#63), z. B. Pokéball
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
    # NUR auf dem SCHREIB-Weg prüfen: CardResponse erbt ebenfalls von CardBase,
    # dort würde die Sperre Bestandsdaten mit Steuerzeichen unlesbar machen
    # (Panel-Fund: GET /cards/{id} lieferte 500 statt der Karte).
    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)


class CardUpdate(BaseModel):
    kartenname: Optional[str] = None
    pokedex_nr: Optional[int] = None
    englischer_name: Optional[str] = None
    set_edition: Optional[str] = None
    karten_nr: Optional[str] = None
    seltenheit: Optional[str] = None
    kartenversion: Optional[str] = None
    folierung: Optional[str] = None
    muster: Optional[str] = None
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

    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)
    # Diese Felder dürfen nie null werden: `kartenname`/`erste_edition` liegen
    # auf NOT-NULL-Spalten, die Flags sind es seit der #55-Light-Migration —
    # und die Antwort typisiert sie als bool. Ein ausdrückliches `null` endete
    # als 500. Weglassen = unverändert bleibt unangetastet.
    _v_null = field_validator(
        "kartenname", "erste_edition", "besessen", "wunschliste", "im_pokedex",
    )(reject_explicit_null)


class CardResponse(CardBase):
    # Gürtel UND Hosenträger (#55): die Flags sind seit der Light-Migration
    # NOT NULL — ein Alt-Backup-Restore könnte aber NULLs zurückbringen, und
    # ein einziges davon machte die ganze Liste unlesbar. Beim LESEN daher
    # tolerant auf False abbilden statt die Antwort zu sprengen.
    @field_validator("besessen", "wunschliste", "im_pokedex", "erste_edition",
                     mode="before")
    @classmethod
    def _null_flag_als_false(cls, v):
        return False if v is None else v

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
    # umgerechnet wird. Einzelkarten-Antworten füllen die Felder (case-
    # toleranter Katalog-Lookup, v1.7.3); Listen nicht.
    katalog_preis_usd: Optional[Decimal] = None
    katalog_preis_usd_stand: Optional[str] = None
    # Welche Variante der $-Preis bepreist (pokeball/masterball/holo/reverse/
    # normal) + woher wert_eur zuletzt stammte (Quelle des jüngsten Verlaufs-
    # eintrags, z. B. „tcgplayer-usd@0.867"). Beides nur Anzeige-Wahrheit:
    # das Label darf nicht „Cardmarket" behaupten, wenn TCGplayer zahlte (v1.8.2).
    katalog_preis_usd_variante: Optional[str] = None
    wert_quelle: Optional[str] = None

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
    muster: list[str] = []     # Folierungs-Muster (#63)
    sprache: list[str]
    zustand: list[str]
    prioritaet: list[str]
