"""
Lokaler TCGdex-Katalog: Spiegel aller Karten zum Durchsuchen/Browsen.
- sync_catalog(): Basisdaten (Name DE/EN, Set, Nummer, Bild) aus den Set-Details.
- enrich_catalog(): Volldetails (Illustrator, Rarity, dexId, Varianten) je Karte.
- add_to_wishlist()/add_to_collection(): Katalog-Karte übernehmen.

Katalog-Karten zählen NICHT zu besessenen/Pokédex-Karten.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import tcgdex
from app.services.card_creation import create_owned_card
from app.services.collection_slots import next_free_position
from app.services.scan.resolver import _map_rarity
from app.services.settings import get_setting

log = logging.getLogger(__name__)

_CONC = 10


def _num(local_id: Optional[str]) -> Optional[int]:
    if not local_id:
        return None
    s = str(local_id)
    return int(s) if s.isdigit() else None


def _apply_full(row: TcgdexCatalog, tc) -> None:
    row.dex_id = tc.dex_id
    row.rarity = tc.rarity
    row.illustrator = tc.illustrator
    row.category = tc.category
    if tc.variants:
        row.variants_normal = tc.variants.normal
        row.variants_reverse = tc.variants.reverse
        row.variants_holo = tc.variants.holo
        row.variants_firstedition = tc.variants.firstEdition
    if not row.image and tc.image:
        row.image = tc.image
        row.image_url = tcgdex.image_url(tc.image)
    row.enriched = True


async def sync_catalog(db: Session) -> dict:
    """Katalog-Basis aus allen Set-Details (DE + EN) aufbauen/aktualisieren."""
    en_sets = await tcgdex.get_sets("en")
    if not en_sets:
        return {"error": "no_data"}
    set_ids = [s.id for s in en_sets]

    set_meta = {r.set_id: (r.code, r.name) for r in db.scalars(select(PokemonSet)).all() if r.set_id}

    sem = asyncio.Semaphore(_CONC)
    results: dict[str, dict] = {}

    async def one(sid: str):
        async with sem:
            en_d = await tcgdex.get_set(sid, "en")
            de_d = await tcgdex.get_set(sid, "de")
        results[sid] = {"en": en_d or {}, "de": de_d or {}}

    await asyncio.gather(*(one(sid) for sid in set_ids))

    # Pokémon TCG Pocket (serie 'tcgp') nicht indizieren – rein digitale Karten.
    excluded = {
        sid for sid in set_ids
        if isinstance(results.get(sid, {}).get("en", {}).get("serie"), dict)
        and results[sid]["en"]["serie"].get("id") in tcgdex.EXCLUDED_SERIES
    }

    created = updated = 0
    if excluded:
        # Früher evtl. indizierte Pocket-Karten entfernen (Self-Healing).
        db.query(TcgdexCatalog).filter(
            TcgdexCatalog.set_id.in_(excluded)
        ).delete(synchronize_session=False)
    existing = {r.card_id: r for r in db.scalars(select(TcgdexCatalog)).all()}
    for sid in set_ids:
        if sid in excluded:
            continue  # Pocket-Set überspringen
        res = results.get(sid, {})
        en_d, de_d = res.get("en", {}), res.get("de", {})
        de_cards = {c.get("id"): c for c in (de_d.get("cards") or [])}
        code, sname = set_meta.get(sid, (None, None))
        for c in (en_d.get("cards") or []):
            cid = c.get("id")
            if not cid:
                continue
            dec = de_cards.get(cid, {})
            name_en = c.get("name")
            name_de = dec.get("name") or name_en
            image = dec.get("image") or c.get("image")
            local_id = c.get("localId") or dec.get("localId")
            row = existing.get(cid)
            if not row:
                row = TcgdexCatalog(card_id=cid)
                db.add(row)
                existing[cid] = row
                created += 1
            else:
                updated += 1
            row.set_id = sid
            row.set_code = code
            row.set_name = sname
            row.local_id = local_id
            row.local_id_num = _num(local_id)
            row.name = name_de
            row.name_en = name_en
            if image:
                row.image = image
                row.image_url = tcgdex.image_url(image)
        db.commit()  # je Set committen (kleinere Transaktionen)

    log.info("Katalog-Sync: %d neu, %d aktualisiert (%d Sets).", created, updated, len(set_ids))
    return {"created": created, "updated": updated, "sets": len(set_ids)}


async def enrich_catalog(db: Session, limit: int = 500) -> dict:
    """Holt Volldetails (Illustrator/Rarity/dexId/Varianten) für N noch nicht angereicherte Karten."""
    ids = [r.card_id for r in db.scalars(
        select(TcgdexCatalog).where(TcgdexCatalog.enriched == False).limit(limit)  # noqa: E712
    ).all()]
    if not ids:
        return {"enriched": 0, "remaining": 0}

    sem = asyncio.Semaphore(_CONC)
    data: dict[str, object] = {}

    async def one(cid: str):
        async with sem:
            tc = await tcgdex.get_card(cid, "en")
        if tc:
            data[cid] = tc

    await asyncio.gather(*(one(c) for c in ids))

    n = 0
    for cid, tc in data.items():
        row = db.get(TcgdexCatalog, cid)
        if row:
            _apply_full(row, tc)
            n += 1
    db.commit()
    remaining = db.scalar(
        select(func.count()).select_from(TcgdexCatalog).where(TcgdexCatalog.enriched == False)  # noqa: E712
    ) or 0
    log.info("Katalog-Enrichment: %d angereichert, %d verbleibend.", n, remaining)
    return {"enriched": n, "remaining": int(remaining)}


async def _build_card_from_catalog(db: Session, row: TcgdexCatalog) -> dict:
    """Karten-Felder aus einem Katalog-Eintrag (lädt bei Bedarf Volldetails nach)."""
    if not row.enriched:
        tc = await tcgdex.get_card(row.card_id, "en")
        if tc:
            _apply_full(row, tc)
            db.commit()
    set_edition = None
    if row.set_name and row.set_code:
        set_edition = f"{row.set_name} ({row.set_code})"
    elif row.set_code:
        set_edition = row.set_code
    return {
        "kartenname": row.name or row.name_en or row.card_id,
        "englischer_name": row.name_en,
        "pokedex_nr": row.dex_id,
        "set_edition": set_edition,
        "karten_nr": row.local_id,
        "seltenheit": _map_rarity(row.rarity),
        "tcgdex_card_id": row.card_id,
        "set_id": row.set_id,
        "dex_id": row.dex_id,
        "illustrator": row.illustrator,
        "bild_karte_url": row.image_url if tcgdex.is_allowed_image_url(row.image_url) else None,
    }


def _resolve_card_attrs(
    db: Session,
    *,
    sprache: Optional[str] = None,
    zustand: Optional[str] = None,
    folierung: Optional[str] = None,
    erste_edition: Optional[bool] = None,
) -> dict:
    """Anlege-Attribute einer Katalog-Übernahme. Nicht mitgegebene Felder fallen
    auf die Einstellungs-Defaults (default_language/default_condition) zurück
    statt hart „DE" (#27). Folierung/1st Edition haben keine Einstellung — sie
    kommen aus dem Formular (Default „Normal"/false), sonst leer."""
    lang = sprache or get_setting(db, "default_language") or "DE"
    cond = zustand if zustand not in (None, "") else get_setting(db, "default_condition")
    return {
        "sprache": lang,
        "zustand": cond or None,
        "folierung": folierung or None,
        "erste_edition": bool(erste_edition),
    }


async def add_to_wishlist(
    db: Session,
    card_id: str,
    prioritaet: Optional[str] = None,
    *,
    sprache: Optional[str] = None,
    zustand: Optional[str] = None,
    folierung: Optional[str] = None,
    erste_edition: Optional[bool] = None,
) -> Optional[int]:
    row = db.get(TcgdexCatalog, card_id)
    if not row:
        return None
    fields = await _build_card_from_catalog(db, row)
    attrs = _resolve_card_attrs(
        db, sprache=sprache, zustand=zustand, folierung=folierung, erste_edition=erste_edition,
    )
    card = PokemonCard(**fields, **attrs, besessen=False, wunschliste=True, prioritaet=prioritaet)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card.id


async def add_to_collection(
    db: Session,
    card_id: str,
    collection_id: int,
    *,
    sprache: Optional[str] = None,
    zustand: Optional[str] = None,
    folierung: Optional[str] = None,
    erste_edition: Optional[bool] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> Optional[int]:
    row = db.get(TcgdexCatalog, card_id)
    if not row:
        return None
    coll = db.get(Collection, collection_id)
    if not coll:
        return None
    fields = await _build_card_from_catalog(db, row)
    attrs = _resolve_card_attrs(
        db, sprache=sprache, zustand=zustand, folierung=folierung, erste_edition=erste_edition,
    )
    # Domain-Service: Platzhalter-Adoption + Auto-im_pokedex + Bild-Fetch (Issue #4)
    card = create_owned_card(
        db, {**fields, **attrs},
        background_tasks=background_tasks, commit=False,
    )
    # Echten freien Slot vergeben statt None — sonst würde die Binder-Anzeige
    # beim nächsten Laden kompaktieren und bestehende Karten verschieben (#30).
    position = next_free_position(db, collection_id)
    db.execute(collection_cards.insert().values(collection_id=collection_id, card_id=card.id, position=position))
    db.commit()
    db.refresh(card)
    return card.id
