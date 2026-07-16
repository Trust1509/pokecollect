"""
Set-Sammlungen / Sammelziele (Issue #16).

Eine Sammlung mit typ="set_ziel" hat eine kuratierbare Soll-Liste
(collection_soll): welche Katalog-Karten (mit welcher Folierung) zum Ziel
gehören. Dieses Modul bündelt die beiden Invarianten:

- prefill_soll(): Soll-Liste beim Anlegen aus tcgdex_catalog vorbefüllen
  (Set bis offizielle Nummer bzw. Master-Set; Folierungs-Regel als
  Startvorschlag über die variants_*-Flags). Nur ein Startvorschlag —
  der Nutzer kuratiert danach frei.
- soll_status()/progress(): erfüllt = besessene PokemonCard mit passender
  tcgdex_card_id (Fallback: Set + Kartennummer) UND Folierung laut Slot
  bzw. Ziel (NULL = egal) UND Sprache laut Ziel (NULL = egal).
  Mehrfach-Zählung über Ziele hinweg ist ausdrücklich ok — Karten werden
  NICHT exklusiv einem Ziel zugeordnet (Lock-Spec, Owner-Antwort 2).

Services nehmen db: Session als Parameter (Kredo: testbar by default).
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.card import PokemonCard
from app.models.collection import Collection, CollectionSoll
from app.models.pokemon_set import PokemonSet
from app.models.tcgdex_catalog import TcgdexCatalog


def _official_count(db: Session, set_id: Optional[str]) -> Optional[int]:
    """Offizielle Kartenzahl des Sets (ohne Secret Rares); Fallback max_card_nr."""
    if not set_id:
        return None
    row = db.scalars(select(PokemonSet).where(PokemonSet.set_id == set_id)).first()
    if not row:
        return None
    return row.card_count_official or row.max_card_nr


def _variant_filter(rows: list[TcgdexCatalog], ziel_folierung: Optional[str]) -> list[TcgdexCatalog]:
    """
    Startvorschlag bei Folierungs-Regel: "Reverse …" → nur reverse-fähige
    Karten, "… Holo" (ohne Reverse) → nur holo-fähige; sonst alle.
    TCGdex-Varianten sind nur teilweise gepflegt — deshalb ist das bewusst
    nur die Vorbefüllung, kuratieren kann der Nutzer immer.
    """
    fol = ziel_folierung or ""
    if "Reverse" in fol:
        return [r for r in rows if r.variants_reverse]
    if "Holo" in fol:
        return [r for r in rows if r.variants_holo]
    return rows


def prefill_soll(db: Session, collection: Collection, commit: bool = True) -> int:
    """Soll-Liste einer Set-Sammlung aus dem Katalog vorbefüllen (Startvorschlag)."""
    if not collection.ziel_set_id:
        return 0
    rows = db.scalars(
        select(TcgdexCatalog)
        .where(TcgdexCatalog.set_id == collection.ziel_set_id)
        .order_by(TcgdexCatalog.local_id_num.nulls_last(), TcgdexCatalog.local_id)
    ).all()
    if not collection.ziel_master_set:
        official = _official_count(db, collection.ziel_set_id)
        if official:
            rows = [r for r in rows if r.local_id_num is not None and r.local_id_num <= official]
    rows = _variant_filter(list(rows), collection.ziel_folierung)
    for pos, r in enumerate(rows):
        db.add(CollectionSoll(
            collection_id=collection.id,
            tcgdex_card_id=r.card_id,
            soll_folierung=None,  # NULL = Regel (ziel_folierung) gilt
            position=pos,
        ))
    if commit:
        db.commit()
    return len(rows)


def _nr_matches(karten_nr: Optional[str], local_id: Optional[str]) -> bool:
    """Kartennummer "136/198" bzw. "136" gegen Katalog-local_id "136" abgleichen."""
    if not karten_nr or not local_id:
        return False
    lhs = str(karten_nr).split("/")[0].strip().lstrip("0") or "0"
    rhs = str(local_id).strip().lstrip("0") or "0"
    return lhs.lower() == rhs.lower()


def _set_matches(card: PokemonCard, cat: TcgdexCatalog) -> bool:
    """Set-Zugehörigkeit: stabile set_id, sonst Set-Kürzel im set_edition-Feld."""
    if card.set_id:
        return card.set_id == cat.set_id
    if cat.set_code and card.set_edition:
        return f"({cat.set_code})" in card.set_edition
    return False


def _rule_ok(card: PokemonCard, required_folierung: Optional[str], required_sprache: Optional[str]) -> bool:
    if required_folierung is not None and card.folierung != required_folierung:
        return False
    if required_sprache is not None and card.sprache != required_sprache:
        return False
    return True


def soll_status(db: Session, collection: Collection) -> list[dict]:
    """
    Alle Soll-Slots inkl. erfüllt/fehlend, erfüllender Karte und Katalog-Daten
    (Bild-URL etc.) — eine Routine für GET /soll und den Fortschritt (DRY).
    """
    slots = db.scalars(
        select(CollectionSoll)
        .where(CollectionSoll.collection_id == collection.id)
        .order_by(CollectionSoll.position.nulls_last(), CollectionSoll.id)
    ).all()
    if not slots:
        return []

    tcg_ids = {s.tcgdex_card_id for s in slots}
    catalog = {
        r.card_id: r for r in db.scalars(
            select(TcgdexCatalog).where(TcgdexCatalog.card_id.in_(tcg_ids))
        ).all()
    }
    set_ids = {c.set_id for c in catalog.values() if c.set_id}

    # Bestand in einem Rutsch laden: direkte tcgdex-Treffer + Set-Kandidaten
    # für den Set+Nummer-Fallback (Karten ohne tcgdex_card_id).
    conds = [PokemonCard.tcgdex_card_id.in_(tcg_ids)]
    if set_ids:
        conds.append(PokemonCard.set_id.in_(set_ids))
    set_codes = {c.set_code for c in catalog.values() if c.set_code}
    for code in set_codes:
        conds.append(PokemonCard.set_edition.ilike(f"%({code})%"))
    owned = db.scalars(
        select(PokemonCard).where(PokemonCard.besessen == True, or_(*conds))  # noqa: E712
    ).all()

    by_tcgdex: dict[str, list[PokemonCard]] = {}
    fallback_pool: list[PokemonCard] = []
    for card in owned:
        if card.tcgdex_card_id:
            by_tcgdex.setdefault(card.tcgdex_card_id, []).append(card)
        else:
            fallback_pool.append(card)

    result: list[dict] = []
    for slot in slots:
        cat = catalog.get(slot.tcgdex_card_id)
        required_fol = slot.soll_folierung if slot.soll_folierung is not None else collection.ziel_folierung
        candidates = list(by_tcgdex.get(slot.tcgdex_card_id, []))
        if cat:
            candidates += [
                c for c in fallback_pool
                if _set_matches(c, cat) and _nr_matches(c.karten_nr, cat.local_id)
            ]
        match = next(
            (c for c in candidates if _rule_ok(c, required_fol, collection.ziel_sprache)),
            None,
        )
        result.append({
            "id": slot.id,
            "tcgdex_card_id": slot.tcgdex_card_id,
            "soll_folierung": slot.soll_folierung,
            "position": slot.position,
            "erfuellt": match is not None,
            "karte_id": match.id if match else None,
            "karte": match,
            # Katalog-Anzeige (Platzhalter-Bild für fehlende Slots)
            "name": cat.name if cat else None,
            "name_en": cat.name_en if cat else None,
            "local_id": cat.local_id if cat else None,
            "image_url": cat.image_url if cat else None,
            "rarity": cat.rarity if cat else None,
            "set_id": cat.set_id if cat else None,
            "set_code": cat.set_code if cat else None,
            "set_name": cat.set_name if cat else None,
            "dex_id": cat.dex_id if cat else None,
        })
    return result


def progress(db: Session, collection: Collection) -> dict:
    """Fortschritt eines Sammelziels: erfüllte Slots / Soll (Anzeige "X / Soll")."""
    status = soll_status(db, collection)
    return {
        "erfuellt": sum(1 for s in status if s["erfuellt"]),
        "soll": len(status),
    }
