"""Pydantic-Schemas für den Karten-Scan (Web + Android, gemeinsame API)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

ScanMode = Literal["single", "multi", "binder"]


class ScanRawRead(BaseModel):
    """Rohe Erkennung (vor TCGdex-Auflösung)."""
    name: Optional[str] = None
    set_code: Optional[str] = None      # aufgedrucktes Kürzel, z.B. "PAF"
    number: Optional[str] = None        # aufgedruckte Nummer, z.B. "007/091"
    language: Optional[str] = None       # DE/EN/CN/JP …
    position: Optional[int] = None       # Slot-Index bei Binder-Scan (0-basiert)
    confidence: Optional[float] = None   # Roh-Sicherheit der Engine (0..1)


class ScanMatch(BaseModel):
    """Aufgelöste TCGdex-Karte."""
    tcgdex_card_id: Optional[str] = None
    name: Optional[str] = None
    englischer_name: Optional[str] = None
    set_id: Optional[str] = None
    set_code: Optional[str] = None
    set_name: Optional[str] = None
    local_id: Optional[str] = None
    rarity: Optional[str] = None
    dex_id: Optional[int] = None
    image_url: Optional[str] = None
    variants_normal: Optional[bool] = None
    variants_reverse: Optional[bool] = None
    variants_holo: Optional[bool] = None
    variants_firstedition: Optional[bool] = None


class ScanCandidate(BaseModel):
    """
    Ein Scan-Treffer inkl. Vorbefüllung für den Bestätigungs-Dialog.
    `suggested` ist direkt als Karten-Anlage verwendbar (editierbar im UI).
    """
    position: Optional[int] = None
    confidence: float = 0.0
    uncertain_fields: list[str] = []
    raw: ScanRawRead
    match: Optional[ScanMatch] = None
    suggested: dict = {}
    foil_options: list[str] = []          # erlaubte Folierungen laut variants


class ScanResponse(BaseModel):
    engine: str                            # "gemini" | "ocr"
    mode: ScanMode
    candidates: list[ScanCandidate]


# ── Commit (bestätigte Karten ablegen) ───────────────────────────────────────

class ScanCommitItem(BaseModel):
    kartenname: str
    pokedex_nr: Optional[int] = None
    englischer_name: Optional[str] = None
    set_edition: Optional[str] = None
    karten_nr: Optional[str] = None
    seltenheit: Optional[str] = None
    kartenversion: Optional[str] = None
    folierung: Optional[str] = None
    sprache: Optional[str] = "DE"
    zustand: Optional[str] = None
    notizen: Optional[str] = None
    tcgdex_card_id: Optional[str] = None
    set_id: Optional[str] = None
    dex_id: Optional[int] = None
    bild_karte_url: Optional[str] = None   # TCGdex high.webp (wird host-validiert)
    position: Optional[int] = None         # Binder-Slot (0-basiert) für die Ablage


class ScanCommitRequest(BaseModel):
    # Ziel: "pokedex" (nur als besessene Karte) oder Sammlung per ID
    target: Literal["pokedex", "collection"] = "pokedex"
    collection_id: Optional[int] = None
    set_im_pokedex: bool = False           # je pokedex_nr als Pokédex-Vertreter setzen
    items: list[ScanCommitItem]


class ScanCommitResponse(BaseModel):
    created: int
    card_ids: list[int]
