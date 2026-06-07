"""
Set-Sync: reichert die `pokemon_sets`-Tabelle mit TCGdex-Daten an.

Quelle der Wahrheit ist die TCGdex-set.id (sprachunabhängig, stabil).
Die EINZIGE manuell gepflegte Stelle ist die Brücke PTCGO_TO_SETID:
  aufgedrucktes Kürzel (code) → TCGdex set.id.
Alles andere (Name EN/DE, Kartenzahlen, Logo, Symbol, Serie) kommt aus der API.

Der Sync braucht nur zwei Requests (/en/sets + /de/sets):
  - Serie wird aus dem Logo-Pfad abgeleitet (…/en/{serie}/{setid}/logo)
  - Symbol wird aus serie + set_id konstruiert (…/univ/{serie}/{setid}/symbol)
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.services import tcgdex

log = logging.getLogger(__name__)


# ── PTCGO-Kürzel → TCGdex set.id ─────────────────────────────────────────────
# Startwerte laut Vorgabe. MEG/PFL/ASC/WHT/BLK wurden nach dem ersten
# /en/sets-Sync gegen die echte API aufgelöst (NICHT geraten):
#   MEG→me01, PFL→me02, ASC→me02.5, WHT→sv10.5w, BLK→sv10.5b
# Künftig neue Kürzel hier ergänzen.
PTCGO_TO_SETID: dict[str, str] = {
    # Karmesin & Purpur / Scarlet & Violet
    "SVI": "sv01",
    "PAL": "sv02",
    "OBF": "sv03",
    "MEW": "sv03.5",
    "151": "sv03.5",
    "PAR": "sv04",
    "PAF": "sv04.5",
    "TEF": "sv05",
    "TWM": "sv06",
    "SFA": "sv06.5",
    "SCR": "sv07",
    "SSP": "sv08",
    "PRE": "sv08.5",
    "JTG": "sv09",
    "DRI": "sv10",
    "WHT": "sv10.5w",
    "BLK": "sv10.5b",
    "SVE": "sve",
    # Mega-Generation (parallel zu SV)
    "MEG": "me01",
    "PFL": "me02",
    "ASC": "me02.5",
    # Schwert & Schild / Sword & Shield
    "ASR": "swsh10",
    "LOR": "swsh11",
    "BRS": "swsh9",
    "EVS": "swsh7",
    # X & Y
    "XY8": "xy8",
}


def _series_from_logo(logo: Optional[str]) -> Optional[str]:
    """…/assets.tcgdex.net/en/sv/sv04.5/logo  →  'sv'."""
    if not logo:
        return None
    parts = logo.rstrip("/").split("/")
    # […, 'en', 'sv', 'sv04.5', 'logo']
    if len(parts) >= 4 and parts[-1] == "logo":
        return parts[-3]
    return None


def _symbol_url(series_id: Optional[str], set_id: str) -> Optional[str]:
    if not series_id:
        return None
    return f"https://assets.tcgdex.net/univ/{series_id}/{set_id}/symbol"


def apply_bridge_to_seed() -> None:
    """
    Setzt set_id auf allen pokemon_sets-Zeilen, deren code in der Brücke steht.
    Offline – kein Netzzugriff. Wird beim Start nach dem Seed aufgerufen.
    """
    db = SessionLocal()
    try:
        rows = db.scalars(select(PokemonSet)).all()
        changed = 0
        for row in rows:
            mapped = PTCGO_TO_SETID.get(row.code)
            if mapped and row.set_id != mapped:
                row.set_id = mapped
                changed += 1
        if changed:
            db.commit()
            log.info("Bridge angewandt: set_id auf %d Sets gesetzt.", changed)
    finally:
        db.close()


async def sync_sets() -> dict:
    """
    Holt /en/sets + /de/sets und reichert alle pokemon_sets-Zeilen mit set_id
    an (Name EN/DE, Kartenzahlen, Logo, Symbol, Serie). Merge über set.id.

    Liefert eine kleine Zusammenfassung inkl. der aufgelösten set_id-Werte
    (zur Verifikation unsicherer Fälle).
    """
    en = await tcgdex.get_sets("en")
    de = await tcgdex.get_sets("de")
    if not en:
        log.warning("Set-Sync: /en/sets lieferte keine Daten – abgebrochen.")
        return {"updated": 0, "error": "no_data"}

    en_by_id = {s.id: s for s in en}
    de_by_id = {s.id: s for s in de}

    db = SessionLocal()
    updated = 0
    resolved: dict[str, str] = {}
    missing: list[str] = []
    try:
        rows = db.scalars(select(PokemonSet)).all()
        for row in rows:
            # set_id ggf. aus der Brücke nachziehen
            if not row.set_id:
                mapped = PTCGO_TO_SETID.get(row.code)
                if mapped:
                    row.set_id = mapped
            if not row.set_id:
                missing.append(row.code)
                continue

            src = en_by_id.get(row.set_id)
            if not src:
                # set_id zeigt auf ein (noch) nicht in der API vorhandenes Set
                missing.append(row.code)
                continue

            resolved[row.code] = row.set_id
            series = _series_from_logo(src.logo)
            row.name_en = src.name or row.name_en
            if src.cardCount:
                row.card_count_official = src.cardCount.official
                row.card_count_total = src.cardCount.total
            row.series_id = series or row.series_id
            # Logo/Symbol: Basis-URL + .png (nur von erlaubtem Host übernehmen)
            if src.logo and tcgdex.is_allowed_image_url(src.logo):
                row.logo_url = f"{src.logo.rstrip('/')}.png"
            sym = _symbol_url(series, row.set_id)
            if sym:
                row.symbol_url = f"{sym}.png"

            # Deutscher Name aus /de/sets nachziehen (Fallback bleibt bestehender Name)
            de_src = de_by_id.get(row.set_id)
            if de_src and de_src.name:
                row.name = de_src.name
            updated += 1
        db.commit()
    finally:
        db.close()

    log.info("Set-Sync fertig: %d Sets aktualisiert.", updated)
    if resolved:
        log.info("Aufgelöste set_id-Werte: %s",
                 ", ".join(f"{c}->{sid}" for c, sid in sorted(resolved.items())))
    if missing:
        log.info("Ohne set_id (Brücke ergänzen falls nötig): %s",
                 ", ".join(sorted(missing)))
    return {"updated": updated, "resolved": resolved, "missing": sorted(missing)}
