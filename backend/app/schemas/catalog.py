from typing import Optional
from pydantic import BaseModel


class CatalogItem(BaseModel):
    card_id: str
    region: Optional[str] = None   # "west" | "ja" | … (Regionsfilter)
    set_id: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    local_id: Optional[str] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    dex_id: Optional[int] = None
    rarity: Optional[str] = None
    illustrator: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    variants_normal: Optional[bool] = None
    variants_reverse: Optional[bool] = None
    variants_holo: Optional[bool] = None
    variants_firstedition: Optional[bool] = None
    enriched: Optional[bool] = None
    owned: bool = False
    in_pokedex: bool = False
    # Gecachte Preise (Epic #41 Slice 4): auch in LISTEN anzeigen — kommen
    # direkt aus der Katalogzeile (kein Live-Fetch), können also None sein.
    price_eur: Optional[float] = None        # € Cardmarket (Cache)
    price_usd: Optional[float] = None        # $ TCGplayer (Cache; JP via TCGCSV)

    model_config = {"from_attributes": True}


class CatalogDetail(CatalogItem):
    """Katalog-Karte + live von TCGdex geholte Zusatzinfos für das angereicherte
    Detail-Popup: fehlende Felder (dex/rarity/illustrator/kategorie/varianten)
    werden aus dem Live-Abruf aufgefüllt, dazu aktuelle Preise (Cardmarket € +
    TCGplayer $, letzteres bei vielen JP-Karten leer)."""
    price_eur_low: Optional[float] = None    # nur aus Live-Abruf
    price_eur_trend: Optional[float] = None  # nur aus Live-Abruf
    price_eur_updated: Optional[str] = None  # Datenstand €
    price_usd_updated: Optional[str] = None  # Datenstand $
    # Varianten-$-Preise aus dem Cache (#63): Holo/Reverse (Subtypen) +
    # Pokéball/Masterball (eigene TCGplayer-Produkte je Karte)
    price_usd_holo: Optional[float] = None
    price_usd_reverse: Optional[float] = None
    price_usd_pokeball: Optional[float] = None
    price_usd_masterball: Optional[float] = None


class CatalogListResponse(BaseModel):
    items: list[CatalogItem]
    total: int
    page: int
    limit: int
    pages: int


class CatalogAddRequest(BaseModel):
    """Optionale Felder beim Übernehmen einer Katalog-Karte (#28). Nicht
    gesetzte Felder werden serverseitig aus den Einstellungs-Defaults
    aufgefüllt (#27). `prioritaet` gilt nur für die Wunschliste."""
    sprache: Optional[str] = None
    zustand: Optional[str] = None
    folierung: Optional[str] = None
    erste_edition: Optional[bool] = None
    prioritaet: Optional[str] = None
