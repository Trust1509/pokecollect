"""
Scan-Resolver: rohe Erkennung (Gemini/OCR) → konkrete TCGdex-Karte.

Eine Quelle für Web UND Android. Nutzt dieselbe Offline-Brücke (code→set_id)
wie der Set-Sync und füllt den Bestätigungs-Dialog vor.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pokemon_set import PokemonSet
from app.schemas.scan import ScanCandidate, ScanMatch, ScanRawRead
from app.services import tcgdex
from app.services.set_sync import PTCGO_TO_SETID

log = logging.getLogger(__name__)


def _set_by_code(db: Session, code: Optional[str]) -> Optional[PokemonSet]:
    if not code:
        return None
    return db.get(PokemonSet, code.strip().upper())


def _set_by_set_id(db: Session, set_id: Optional[str]) -> Optional[PokemonSet]:
    if not set_id:
        return None
    return db.scalars(select(PokemonSet).where(PokemonSet.set_id == set_id)).first()


def _resolve_set_id(db: Session, code: Optional[str]) -> tuple[Optional[str], Optional[PokemonSet]]:
    """code → set_id (DB-Set bevorzugt, sonst Brücke)."""
    row = _set_by_code(db, code)
    if row and row.set_id:
        return row.set_id, row
    if code:
        mapped = PTCGO_TO_SETID.get(code.strip().upper())
        if mapped:
            return mapped, (row or _set_by_set_id(db, mapped))
    return (row.set_id if row else None), row


def _foil_options(tc) -> list[str]:
    opts: list[str] = []
    v = tc.variants if tc else None
    if not v:
        return ["Normal"]
    if v.normal:
        opts.append("Normal")
    if v.holo:
        opts.append("Holo")
    if v.reverse:
        opts.append("Reverse Holo")
    return opts or ["Normal"]


def _set_edition(db: Session, set_id: Optional[str], fallback_code: Optional[str]) -> Optional[str]:
    row = _set_by_set_id(db, set_id)
    if row:
        return f"{row.name} ({row.code})"
    if fallback_code:
        return fallback_code
    return None


def _karten_nr(local_id: Optional[str], official: Optional[int], raw_number: Optional[str]) -> Optional[str]:
    if local_id and local_id.isdigit() and official:
        return f"{local_id.zfill(3)}/{str(official).zfill(3)}"
    return raw_number


# TCGdex-Seltenheit (englisch) → unser Seltenheits-Enum
_RARITY_MAP = {
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "rare holo": "Rare",
    "double rare": "Double Rare",
    "ultra rare": "Ultra Rare",
    "secret rare": "Secret Rare",
    "illustration rare": "Illustration Rare",
    "special illustration rare": "Special Illustration Rare",
    "hyper rare": "Hyper Rare",
    "shiny rare": "Shiny Rare",
    "shiny ultra rare": "Shiny Ultra Rare",
    "rainbow rare": "Rainbow Rare",
    "ace spec rare": "ACE SPEC Rare",
    "promo": "Promo",
}


def _map_rarity(rarity_en: Optional[str]) -> Optional[str]:
    if not rarity_en:
        return None
    return _RARITY_MAP.get(rarity_en.strip().lower(), rarity_en)


def _is_promo_set(name: Optional[str]) -> bool:
    """Erkennt Promo-Sets am Namen (z.B. 'SVP Black Star Promos')."""
    return bool(name) and "promo" in name.lower()


async def _english_card(tc, lang: str):
    """Liefert die englische Variante (für englischen Namen + Seltenheit)."""
    if lang == "en":
        return tc
    return await tcgdex.get_card(tc.id, "en")


async def _dex_from_results(results: list[dict]) -> tuple[Optional[int], Optional[str]]:
    """
    National-Dex-Nr. + EN-Name aus der ersten Schwesterkarte gleichen Namens, die
    eine dexId trägt. Nötig, weil manche (neue) Sets – z.B. die Mega-Evolution-
    Reihe – an der Karte selbst keine dexId führen (TCGdex liefert dort null).
    """
    for r in results[:6]:
        cid = r.get("id")
        if not cid:
            continue
        sib = await tcgdex.get_card(cid, "en")
        if sib and sib.dex_id is not None:
            return sib.dex_id, sib.name
    return None, None


async def resolve_one(db: Session, read: ScanRawRead, default_lang: str = "DE") -> ScanCandidate:
    app_lang = (read.language or default_lang or "DE").upper()
    tcg_lang = tcgdex.normalize_lang(app_lang)

    set_id, set_row = _resolve_set_id(db, read.set_code)
    local_id = tcgdex.local_id_from_card_nr(read.number)

    tc = None
    if set_id and local_id:
        tc = await tcgdex.fetch_card_by_set_multilang(set_id, local_id, tcg_lang)

    # Fallback: Kartensuche per Name. Wenn die Nummer bekannt ist, über die
    # localId eindeutig machen (robust gegen falsch erkannte Set-Kürzel).
    via_search = False
    via_number = False
    results: list[dict] = []
    if tc is None and read.name:
        results = await tcgdex.search_cards({"name": read.name}, tcg_lang)

        def _norm(x: object) -> str:
            return str(x).lstrip("0") or "0"

        chosen = None
        if local_id:
            matches = [r for r in results if r.get("localId") and _norm(r["localId"]) == local_id]
            if matches:
                chosen = matches[0]
                via_number = True
        if chosen is None and len(results) == 1:
            chosen = results[0]
        if chosen and chosen.get("id"):
            tc = await tcgdex.get_card(chosen["id"], tcg_lang)
            via_search = True
            if tc and tc.set and tc.set.id:
                set_id = tc.set.id

    # Auch ohne exakten Treffer: National-Pokédex-Nr. + EN-Name aus dem ersten
    # Namens-Suchergebnis ableiten (gleiche Spezies → gleiche dexId). So bekommt
    # die Karte trotzdem eine Pokédex-Nr. und taucht im Pokédex auf.
    fallback_dex: Optional[int] = None
    fallback_en: Optional[str] = None
    if tc is None and results:
        fallback_dex, fallback_en = await _dex_from_results(results)

    uncertain: list[str] = []
    if not read.name:
        uncertain.append("name")
    if not set_id:
        uncertain.append("set")
    if not local_id:
        uncertain.append("number")
    if not read.language:
        uncertain.append("language")

    match: Optional[ScanMatch] = None
    suggested: dict = {}
    foil_options: list[str] = []

    if tc:
        official = tc.set.cardCount.official if (tc.set and tc.set.cardCount) else None
        set_id = (tc.set.id if tc.set else set_id)
        en_card = await _english_card(tc, tcg_lang)
        eng = en_card.name if (en_card and tcg_lang != "en") else None
        rarity_en = (en_card.rarity if en_card else None) or tc.rarity
        seltenheit = _map_rarity(rarity_en)
        set_edition = _set_edition(db, set_id, read.set_code)
        knr = _karten_nr(tc.localId, official, read.number)
        foil_options = _foil_options(tc)

        # Promo-Karten (z.B. SVP Black Star Promos): Seltenheit = Promo und die
        # aufgedruckte Nummer ohne Nenner (Promos haben kein "x/y").
        set_name = tc.set.name if tc.set else None
        if _is_promo_set(set_name) or _is_promo_set(set_edition):
            seltenheit = "Promo"
            if tc.localId:
                knr = tc.localId

        # Dex-Nr.: bevorzugt von der Karte; fehlt sie (z.B. Mega-Reihe), über
        # Schwesterkarten gleichen Namens nachschlagen (Spezies-Ebene).
        dex_id = tc.dex_id
        if dex_id is None:
            sib_results = results or await tcgdex.search_cards(
                {"name": read.name or tc.name or ""}, tcg_lang)
            dex_id, sib_en = await _dex_from_results(sib_results)
            if not eng:
                eng = sib_en

        match = ScanMatch(
            tcgdex_card_id=tc.id,
            name=tc.name,
            englischer_name=eng,
            set_id=set_id,
            set_code=(set_row.code if set_row else read.set_code),
            set_name=(tc.set.name if tc.set else None),
            local_id=tc.localId,
            rarity=tc.rarity,
            dex_id=dex_id,
            image_url=tcgdex.image_url(tc.image),
            variants_normal=tc.variants.normal if tc.variants else None,
            variants_reverse=tc.variants.reverse if tc.variants else None,
            variants_holo=tc.variants.holo if tc.variants else None,
            variants_firstedition=tc.variants.firstEdition if tc.variants else None,
        )
        suggested = {
            "kartenname": tc.name or read.name,
            "englischer_name": eng,
            "pokedex_nr": dex_id,
            "set_edition": set_edition,
            "karten_nr": knr,
            "seltenheit": seltenheit,
            "sprache": app_lang,
            "folierung": foil_options[0] if foil_options else "Normal",
            "besessen": True,
            "tcgdex_card_id": tc.id,
            "set_id": set_id,
            "dex_id": dex_id,
        }
    else:
        # Kein Treffer – Rohgelesenes + (falls ermittelbar) Pokédex-Nr./EN-Name
        suggested = {
            "kartenname": read.name or "",
            "englischer_name": fallback_en,
            "pokedex_nr": fallback_dex,
            "dex_id": fallback_dex,
            "set_edition": _set_edition(db, set_id, read.set_code),
            "karten_nr": read.number,
            "sprache": app_lang,
            "besessen": True,
        }
        if "name" not in uncertain:
            uncertain.append("match")

    # Confidence: Roh-Sicherheit der Engine, gedämpft durch fehlende Felder/Match
    base = read.confidence if read.confidence is not None else 0.3
    if tc and not via_search:
        confidence = max(base, 0.85)
    elif tc and via_number:
        confidence = max(base, 0.8)        # Name + Nummer eindeutig
    elif tc and via_search:
        confidence = min(max(base, 0.6), 0.75)
    else:
        confidence = min(base, 0.35)
    confidence = round(confidence * (1 - 0.1 * len(uncertain)), 2)
    confidence = max(0.0, min(1.0, confidence))

    return ScanCandidate(
        position=read.position,
        confidence=confidence,
        uncertain_fields=uncertain,
        raw=read,
        match=match,
        suggested=suggested,
        foil_options=foil_options,
    )


async def resolve_reads(db: Session, reads: list[ScanRawRead], default_lang: str = "DE") -> list[ScanCandidate]:
    candidates: list[ScanCandidate] = []
    for read in reads:
        try:
            candidates.append(await resolve_one(db, read, default_lang))
        except Exception as exc:  # ein fehlerhafter Treffer darf den Rest nicht killen
            log.warning("Resolver-Fehler für %s: %s", read, exc)
            candidates.append(ScanCandidate(
                position=read.position, confidence=0.0,
                uncertain_fields=["match"], raw=read, suggested={"kartenname": read.name or ""},
            ))
    candidates.sort(key=lambda c: (c.position if c.position is not None else 0))
    return candidates
