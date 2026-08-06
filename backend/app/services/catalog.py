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
from datetime import datetime, timezone
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.models.collection import Collection, collection_cards
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import tcgcsv, tcgdex
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
        row.image_source = None  # TCGdex übernimmt → evtl. „tcgplayer"-Fallback-Label räumen (#41)
    row.enriched = True
    # Preise lokal cachen (Epic #41 #45): € Cardmarket (+ Holo-Fallback) für alle,
    # $ TCGplayer für westliche Karten (bei JP ist tcgplayer leer → der aus TCGCSV
    # gecachte $-Wert bleibt unangetastet). Zeitstempel je Währung.
    pr = catalog_prices(tc.pricing)
    if pr["eur"] is not None:
        row.price_eur = pr["eur"]
        row.price_eur_updated = pr["eur_updated"]
    if pr["usd"] is not None:
        row.price_usd = pr["usd"]
        row.price_usd_updated = pr["usd_updated"]


def catalog_prices(pricing) -> dict:
    """Repräsentative Preise aus TCGdex-Pricing für die Katalog-Detailanzeige:
    Cardmarket € (avg/low/trend) + TCGplayer $ (marketPrice der Normal-Variante,
    sonst der ersten Variante mit Marktpreis). Fehlende Werte → None (für viele
    JP-Karten ist $ leer). Rein, netzfrei (Epic #41 Preis-Anzeige)."""
    out = {"eur": None, "eur_low": None, "eur_trend": None, "eur_updated": None,
           "usd": None, "usd_updated": None}
    if not pricing:
        return out
    cm = getattr(pricing, "cardmarket", None)
    if cm:
        # Holo-only-Karten führen avg/low/trend nicht (nur avg-holo/…) → darauf
        # zurückfallen, sonst zeigt eine Holo-Karte trotz Preis kein € (Panel-Fund).
        out["eur"] = cm.avg if cm.avg is not None else cm.avg_holo
        out["eur_low"] = cm.low if cm.low is not None else cm.low_holo
        out["eur_trend"] = cm.trend if cm.trend is not None else cm.trend_holo
        out["eur_updated"] = cm.updated
    tp = getattr(pricing, "tcgplayer", None)
    if isinstance(tp, dict):
        chosen = tp.get("normal") if isinstance(tp.get("normal"), dict) else None
        if not (chosen and chosen.get("marketPrice") is not None):
            chosen = next((v for v in tp.values()
                           if isinstance(v, dict) and v.get("marketPrice") is not None), None)
        if chosen:
            out["usd"] = chosen.get("marketPrice")
            out["usd_updated"] = tp.get("updated")
    return out


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
            row.region = "west"      # EN+DE = dieselbe Karte
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
                row.image_source = None  # TCGdex übernimmt → „tcgplayer"-Fallback-Label räumen (#41)
        db.commit()  # je Set committen (kleinere Transaktionen)

    # Nicht-westliche Regionen (JP …) additiv indizieren — eigene Karten.
    from app.services.set_sync import EXTRA_REGIONS
    for region in EXTRA_REGIONS:
        rc, ru = await _index_region_cards(db, region, existing)
        created += rc
        updated += ru

    # Fehlende Regions-Bilder über TCGplayer ergänzen (Epic #41, Slice 1).
    # Externe Quelle → fehlertolerant: ein Ausfall darf den Katalog-Sync nicht kippen.
    for region in EXTRA_REGIONS:
        try:
            await fill_region_from_tcgplayer(db, region)
        except Exception as exc:  # noqa: BLE001 — Sync soll robust bleiben
            db.rollback()  # Session nach DB-Fehler nicht im aborted-Zustand lassen
            log.warning("Bild-Fallback %s übersprungen: %s", region, exc)

    log.info("Katalog-Sync: %d neu, %d aktualisiert (%d West-Sets + Regionen %s).",
             created, updated, len(set_ids), ",".join(EXTRA_REGIONS))
    return {"created": created, "updated": updated, "sets": len(set_ids)}


async def _index_region_cards(
    db: Session, region: str, existing: dict[str, TcgdexCatalog]
) -> tuple[int, int]:
    """
    Katalog-Basis einer nicht-westlichen Region (eigene Karten, z. B. JP)
    indizieren. Der Name kommt in der Regionssprache; `region` wird getaggt.
    dexId/Rarity/Varianten holt später enrich_catalog (regions-sprachig). Pocket
    (Serie `tcgp`) wird über die Set-Details ausgeschlossen. Generisch (#33-Folge).
    """
    sets = await tcgdex.get_sets(region)
    if not sets:
        return 0, 0
    set_meta = {r.set_id: (r.code, r.name) for r in db.scalars(select(PokemonSet)).all() if r.set_id}

    sem = asyncio.Semaphore(_CONC)
    details: dict[str, dict] = {}

    async def one(sid: str):
        async with sem:
            d = await tcgdex.get_set(sid, region)
        if isinstance(d, dict):
            details[sid] = d

    await asyncio.gather(*(one(s.id) for s in sets if s.id))

    created = updated = 0
    for s in sets:
        sid = s.id
        d = details.get(sid)
        if not d:
            continue  # fail-closed: ohne Details nicht halb indizieren
        serie = d["serie"].get("id") if isinstance(d.get("serie"), dict) else None
        if serie in tcgdex.EXCLUDED_SERIES:
            continue
        code, sname = set_meta.get(sid, (None, None))
        for c in (d.get("cards") or []):
            cid = c.get("id")
            if not cid:
                continue
            local_id = c.get("localId")
            image = c.get("image")
            row = existing.get(cid)
            if row is not None and row.region != region:
                # Karte gehört bereits einer anderen Region — sprachübergreifend
                # GETEILTES Set (gleiche card_id, z. B. die alten Neo-Sets, die
                # West UND JP unter derselben set.id führen). NICHT überschreiben:
                # sie bleibt „west" (EN/DE), sonst ginge die westliche Zuordnung
                # verloren. JP-EXKLUSIVE Sets haben eigene card_ids → unberührt.
                continue
            if not row:
                row = TcgdexCatalog(card_id=cid)
                db.add(row)
                existing[cid] = row
                created += 1
            else:
                updated += 1
            row.region = region
            row.set_id = sid
            row.set_code = code
            row.set_name = sname
            row.local_id = local_id
            row.local_id_num = _num(local_id)
            row.name = c.get("name")   # Regionssprache (z. B. JA)
            if image:
                row.image = image
                row.image_url = tcgdex.image_url(image)
                row.image_source = None  # TCGdex übernimmt → „tcgplayer"-Fallback-Label räumen (#41)
        db.commit()
    return created, updated


async def fill_region_from_tcgplayer(db: Session, region: str = "ja") -> dict:
    """
    Übernimmt für eine Region (z. B. JP) Daten aus TCGplayer/tcgcsv (Kat. 85):
    fehlendes Kartenbild (nur wo keins steht), fehlenden englischen Namen
    (TCGplayer benennt JP-Karten englisch) und den $-Marktpreis (täglich
    aufgefrischt). Match: Set-Code ↔ TCGplayer-Gruppe + Kartennummer.
    Fehlertolerant vom Aufrufer zu umschließen (externe Quelle).
    (Epic #41: Slice 1 = Bilder, #45 = Preise/Namen.)
    """
    # TCGplayer-Kategorie je Region. NUR Regionen mit Mapping werden verarbeitet —
    # sonst würde eine künftige Region (z. B. „ko") gegen JAPANISCHE Gruppen
    # gematcht (Erweiterbarkeit, #41).
    region_category = {"ja": tcgcsv.CATEGORY_POKEMON_JP}
    category = region_category.get(region)
    if category is None:
        return {"images": 0, "prices": 0, "sets": 0}

    # ALLE Region-Karten (nicht nur bildlose): Preise frischen wir täglich auf,
    # den EN-Namen füllen wir einmalig, das Bild nur wo keins steht.
    rows_all = db.scalars(
        select(TcgdexCatalog).where(TcgdexCatalog.region == region)
    ).all()
    by_set: dict[str, list[TcgdexCatalog]] = {}
    for row in rows_all:
        if row.set_code:
            by_set.setdefault(row.set_code.upper(), []).append(row)
    if not by_set:
        return {"images": 0, "prices": 0, "sets": 0}

    # TCGplayer-Gruppen der JP-Kategorie → {Set-Code: groupId}. Mehrdeutige Codes
    # (zwei Gruppen, gleicher Code) werden verworfen — lieber nichts als das
    # falsche Set (#41).
    groups = await tcgcsv.get_groups(category)
    code_to_group: dict[str, int] = {}
    ambiguous: set[str] = set()
    for g in groups:
        code = tcgcsv.set_code_from_group(g.get("name"))
        gid = g.get("groupId")
        if not code or gid is None:
            continue
        if code in code_to_group and code_to_group[code] != gid:
            ambiguous.add(code)
        else:
            code_to_group[code] = gid
    for code in ambiguous:
        code_to_group.pop(code, None)

    # Timezone-aware UTC („+00:00") — sonst liest JS den Zeitstempel als Lokalzeit
    # und der angezeigte „Stand" kann um einen Tag danebenliegen (Panel-Fund).
    stamp = datetime.now(timezone.utc).isoformat()
    images = prices = sets_done = 0
    for code, rows in by_set.items():
        gid = code_to_group.get(code)
        if gid is None:
            continue  # kein passendes TCGplayer-Set
        products = await tcgcsv.get_products(category, gid)
        num_to_product: dict[str, dict] = {}
        for p in products:
            num = tcgcsv.product_number(p)
            if num:
                num_to_product.setdefault(num, p)
        price_rows = await tcgcsv.get_prices(category, gid)
        touched = False
        for row in rows:
            lid = row.local_id or ""
            # isascii() zusätzlich zu isdigit(): „²".isdigit() ist True, aber
            # int(„²") wirft — nur echte ASCII-Ziffern normalisieren.
            key = str(int(lid)) if (lid.isascii() and lid.isdigit()) else lid
            p = num_to_product.get(key)
            if not p:
                continue
            # Bild: atomar NUR wo noch keins steht (Race-Schutz gegen ein
            # zwischenzeitlich geschriebenes TCGdex-Bild, #41 Slice 1).
            img = tcgcsv.hires_image_url(p)
            if img:
                res = db.execute(
                    update(TcgdexCatalog)
                    .where(TcgdexCatalog.card_id == row.card_id,
                           TcgdexCatalog.image_url.is_(None))
                    .values(image_url=img, image_source="tcgplayer")
                    .execution_options(synchronize_session=False)
                )
                if res.rowcount:
                    images += 1
                    touched = True
            # EN-Name (nur falls fehlend, via COALESCE) + $-Marktpreis (täglich
            # auffrischen). Ein atomarer UPDATE je Karte.
            usd = tcgcsv.market_usd_for(price_rows, p.get("productId"))
            name = p.get("name")
            vals: dict = {}
            if isinstance(name, str) and name.strip():
                vals["name_en"] = func.coalesce(TcgdexCatalog.name_en, name.strip())
            if usd is not None:
                vals["price_usd"] = usd
                vals["price_usd_updated"] = stamp
            if vals:
                db.execute(
                    update(TcgdexCatalog)
                    .where(TcgdexCatalog.card_id == row.card_id)
                    .values(**vals)
                    .execution_options(synchronize_session=False)
                )
                if "price_usd" in vals:
                    prices += 1
                touched = True
        if touched:
            db.commit()
            sets_done += 1

    log.info("TCGplayer-Übernahme %s: %d Bilder, %d Preise (%d Sets).",
             region, images, prices, sets_done)
    return {"images": images, "prices": prices, "sets": sets_done}


def _catalog_lang(region: Optional[str]) -> str:
    """Regionssprache für den TCGdex-Kartenabruf: west → „en", sonst die
    Region selbst (z. B. „ja"). So werden JP-Karten korrekt japanisch geladen."""
    return "en" if (region or "west") == "west" else region


async def enrich_catalog(db: Session, limit: int = 500) -> dict:
    """Holt Volldetails (Illustrator/Rarity/dexId/Varianten) für N noch nicht
    angereicherte Karten — je Karte in ihrer Regionssprache (#33-Folge)."""
    rows = db.scalars(
        select(TcgdexCatalog).where(TcgdexCatalog.enriched == False).limit(limit)  # noqa: E712
    ).all()
    if not rows:
        return {"enriched": 0, "remaining": 0}

    sem = asyncio.Semaphore(_CONC)
    data: dict[str, object] = {}

    async def one(cid: str, region: Optional[str]):
        async with sem:
            tc = await tcgdex.get_card(cid, _catalog_lang(region))
        if tc:
            data[cid] = tc

    await asyncio.gather(*(one(r.card_id, r.region) for r in rows))

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
        tc = await tcgdex.get_card(row.card_id, _catalog_lang(row.region))
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
