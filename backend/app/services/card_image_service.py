"""
Kartendaten-Auflösung über TCGdex (ersetzt die alte pokemon.com-URL-Logik).

Ablauf:
  set_edition ("Paldeas Schicksale (PAF)") → Kürzel "PAF"
  → pokemon_sets.set_id ("sv04.5")   (aus Brücke/Sync, offline)
  → karten_nr "007/091" → localId "7"
  → GET /v2/{lang}/sets/{set_id}/{localId}
  → Bild (high.webp), tcgdex_card_id, dexId, variants, Preise.

Damit entfällt das Set-Code-Mapping, das HEAD-Probing und das
Nummern-Mismatch-Problem der alten pokemon.com-Logik vollständig.

Bild-Priorität in der App (unverändert):
  1. bild_karte_pfad  – eigenes Foto (Upload), immer bevorzugt
  2. bild_pokedex_url – manuell gesetzte URL
  3. bild_karte_url   – auto von TCGdex (dieses Modul)
  4. Pokédex-Artwork  – Platzhalter als letzter Fallback
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.models.pokemon_set import PokemonSet
from app.services import tcgdex
from app.services.tcgdex import TcgdexCard

log = logging.getLogger(__name__)


def extract_set_code(set_edition: Optional[str]) -> Optional[str]:
    """'Paldeas Schicksale (PAF)' → 'PAF'. None wenn kein Kürzel erkennbar."""
    if not set_edition:
        return None
    m = re.search(r"\(([A-Z0-9.]{1,8})\)\s*$", set_edition)
    return m.group(1) if m else None


def resolve_set_id(db: Session, set_edition: Optional[str]) -> Optional[str]:
    """
    Kürzel aus set_edition → set_id. Bevorzugt pokemon_sets (DB),
    fällt sonst auf die PTCGO-Brücke zurück (für Sets, die (noch) keine
    eigene Zeile haben, z.B. MEP/151C).
    """
    code = extract_set_code(set_edition)
    if not code:
        return None
    row = db.get(PokemonSet, code)
    if row and row.set_id:
        return row.set_id
    from app.services.set_sync import PTCGO_TO_SETID
    return PTCGO_TO_SETID.get(code.strip().upper())


async def fetch_tcgdex_card(
    set_id: str,
    karten_nr: Optional[str],
    sprache: Optional[str],
) -> Optional[TcgdexCard]:
    """
    Holt die TCGdex-Karte über Set-ID + aufgedruckte Nummer.
    Versucht zuerst die Kartensprache, dann EN/DE als Fallback
    (Bild/Preise sind dort i.d.R. vollständiger).
    """
    local_id = tcgdex.local_id_from_card_nr(karten_nr)
    if not set_id or not local_id:
        return None

    primary = tcgdex.normalize_lang(sprache)
    langs: list[str] = [primary] + [l for l in tcgdex.FALLBACK_LANGS if l != primary]
    for lang in langs:
        card = await tcgdex.get_card_by_set(set_id, local_id, lang)
        if card:
            return card
    return None


def _result_set_id(result: dict) -> Optional[str]:
    """Set-ID aus einem Such-Treffer ableiten ('swsh3-136' → 'swsh3')."""
    cid = result.get("id")
    if isinstance(cid, str) and "-" in cid:
        return cid.rsplit("-", 1)[0]
    return None


async def fetch_tcgdex_card_by_name(
    name: Optional[str],
    sprache: Optional[str],
    set_id: Optional[str] = None,
) -> Optional[TcgdexCard]:
    """
    Issue 2: Fallback ohne Kartennummer – sucht die Karte über den Namen und
    liefert einen *wahrscheinlichen* Treffer (gleiche Spezies). Bevorzugt einen
    Treffer im bereits bekannten Set; sonst den ersten Namens-Treffer.
    Erzwingt keine exakte Karte, dient v.a. einem plausiblen Bild.
    """
    if not name:
        return None
    primary = tcgdex.normalize_lang(sprache)
    langs: list[str] = [primary] + [l for l in tcgdex.FALLBACK_LANGS if l != primary]
    for lang in langs:
        results = await tcgdex.search_cards({"name": name}, lang)
        if not results:
            continue
        chosen: Optional[dict] = None
        if set_id:
            chosen = next((r for r in results if _result_set_id(r) == set_id), None)
        if chosen is None:
            chosen = results[0]
        cid = chosen.get("id")
        if cid:
            card = await tcgdex.get_card(cid, lang)
            if card:
                return card
    return None


def apply_species_image(card: PokemonCard, tc: TcgdexCard, *, overwrite_image: bool = True) -> None:
    """
    Behutsame Variante für den Namens-Fallback: setzt nur Bild + Pokédex-Nr.
    (Spezies-Ebene, zuverlässig). Lässt set_id/tcgdex_card_id/Varianten in Ruhe,
    um keine womöglich falsche konkrete Karte zu erzwingen.
    """
    if overwrite_image:
        url = tcgdex.image_url(tc.image)
        if url:
            card.bild_karte_url = url
    if tc.dex_id is not None and card.dex_id is None:
        card.dex_id = tc.dex_id


def apply_card_to_model(card: PokemonCard, tc: TcgdexCard, *, overwrite_image: bool = True) -> None:
    """
    Überträgt TCGdex-Felder additiv auf die DB-Karte.
    Überschreibt NUR die automatischen Felder; eigenes Foto / manuelle URL
    bleiben unangetastet (Bild-Priorität wird im Frontend entschieden).
    """
    card.tcgdex_card_id = tc.id
    if tc.set and tc.set.id:
        card.set_id = tc.set.id
    if tc.dex_id is not None:
        card.dex_id = tc.dex_id
    if tc.illustrator:
        card.illustrator = tc.illustrator
    if tc.variants:
        card.variants_normal = tc.variants.normal
        card.variants_reverse = tc.variants.reverse
        card.variants_holo = tc.variants.holo
        card.variants_firstedition = tc.variants.firstEdition
    if overwrite_image:
        url = tcgdex.image_url(tc.image)
        if url:
            card.bild_karte_url = url
