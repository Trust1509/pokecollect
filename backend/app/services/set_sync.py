"""
Set-Sync: reichert die `pokemon_sets`-Tabelle mit TCGdex-Daten an.

Quelle der Wahrheit ist die TCGdex-set.id (sprachunabhängig, stabil).
set_id wird in zwei Stufen aufgelöst – beide OHNE Raten:
  1. Brücke PTCGO_TO_SETID (offline, sofort) – für Sets, deren Kürzel TCGdex
     nicht als offizielle Abkürzung führt (z.B. MEW/151) oder für die wir die
     ID vorab kennen.
  2. Auto-Auflösung über das `abbreviation.official`-Feld der Set-Details:
     TCGdex liefert pro Set das aufgedruckte Kürzel → exaktes Match auf `code`.
Alles andere (Name EN/DE, Kartenzahlen, Logo, Symbol, Serie) kommt aus der API.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy import select

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.services import tcgdex

log = logging.getLogger(__name__)

_DETAIL_CONCURRENCY = 12


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
    "SVP": "svp",   # Scarlet & Violet Black Star Promos
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
    # Sonne & Mond: COS (Welten im Wandel / Cosmic Eclipse) führt TCGdex ohne
    # offizielle Abkürzung – daher manuell. Alle übrigen SM/SWSH/XY-Sets werden
    # im Sync automatisch über abbreviation.official aufgelöst.
    "COS": "sm12",
    # Sonderfälle der Sammlung:
    # MEP = Mega-Promos (TCGdex-Set "mep"; aktuell ohne Bilder → Platzhalter,
    #       aber Daten/Preise lösen auf).
    "MEP": "mep",
    # 151C = chinesische 151er. TCGdex hat kein zh-tw-151-Set → auf sv03.5
    #        gemappt, Bild kommt per Sprach-Fallback aus EN/DE.
    "151C": "sv03.5",
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


async def _fetch_all_details(set_ids: list[str]) -> dict[str, dict]:
    """Holt Set-Details nebenläufig (begrenzt). Liefert {set_id: detail_json}."""
    sem = asyncio.Semaphore(_DETAIL_CONCURRENCY)
    out: dict[str, dict] = {}

    async def one(sid: str):
        async with sem:
            d = await tcgdex.get_set(sid, "en")
        if isinstance(d, dict):
            out[sid] = d

    await asyncio.gather(*(one(sid) for sid in set_ids))
    return out


async def sync_sets() -> dict:
    """
    Holt /en/sets + /de/sets, löst set_id auf (Brücke + abbreviation.official aus
    den Set-Details) und reichert alle Zeilen an (Name EN/DE, Kartenzahlen, Logo,
    Symbol, Serie). Merge ausschließlich über die stabile set.id.

    Liefert eine Zusammenfassung inkl. aufgelöster set_id-Werte (zur Verifikation).
    """
    en = await tcgdex.get_sets("en")
    de = await tcgdex.get_sets("de")
    if not en:
        log.warning("Set-Sync: /en/sets lieferte keine Daten – abgebrochen.")
        return {"updated": 0, "error": "no_data"}

    en_by_id = {s.id: s for s in en}
    de_by_id = {s.id: s for s in de}

    # Set-Details holen → abbreviation.official → code-Match (Auto-Auflösung),
    # liefert zugleich serie + symbol zuverlässig (anders als die Liste).
    details = await _fetch_all_details([s.id for s in en])
    abbr_to_id: dict[str, str] = {}
    for sid, d in details.items():
        ab = d.get("abbreviation")
        if isinstance(ab, dict) and ab.get("official"):
            abbr_to_id[ab["official"].upper()] = sid

    # Pokémon TCG Pocket (serie 'tcgp') ausschließen – rein digitale Karten.
    excluded_set_ids = {
        sid for sid, d in details.items()
        if isinstance(d.get("serie"), dict) and d["serie"].get("id") in tcgdex.EXCLUDED_SERIES
    }

    def _enrich(row, src, d, de_src):
        row.name_en = d.get("name") or (src.name if src else None) or row.name_en
        cc = d.get("cardCount") or {}
        official = cc.get("official") or (src.cardCount.official if src and src.cardCount else None)
        total = cc.get("total") or (src.cardCount.total if src and src.cardCount else None)
        if official is not None:
            row.card_count_official = official
        if total is not None:
            row.card_count_total = total
        serie = d["serie"].get("id") if isinstance(d.get("serie"), dict) else None
        serie = serie or _series_from_logo(src.logo if src else None)
        if serie:
            row.series_id = serie
        logo = d.get("logo") or (src.logo if src else None)
        if logo and tcgdex.is_allowed_image_url(logo):
            row.logo_url = f"{logo.rstrip('/')}.png"
        symbol = d.get("symbol") or _symbol_url(serie, row.set_id)
        if symbol and tcgdex.is_allowed_image_url(symbol):
            row.symbol_url = f"{symbol.rstrip('/')}.png"
        if de_src and de_src.name:
            row.name = de_src.name

    db = SessionLocal()
    updated = 0
    created = 0
    try:
        # Früher evtl. synchronisierte Pocket-Sets entfernen (Self-Healing).
        db.query(PokemonSet).filter(
            PokemonSet.series_id.in_(tcgdex.EXCLUDED_SERIES)
        ).delete(synchronize_session=False)
        rows = db.scalars(select(PokemonSet)).all()
        by_code = {r.code: r for r in rows}
        by_setid: dict[str, PokemonSet] = {}
        used_codes = set(by_code.keys())

        # Bestehende Zeilen: set_id auflösen (Brücke/abbreviation) + anreichern
        for row in rows:
            if not row.set_id:
                row.set_id = PTCGO_TO_SETID.get(row.code) or abbr_to_id.get(row.code.upper())
            if row.set_id:
                by_setid[row.set_id] = row
                _enrich(row, en_by_id.get(row.set_id), details.get(row.set_id, {}), de_by_id.get(row.set_id))
                updated += 1

        # ALLE TCGdex-Sets übernehmen, die noch keine Zeile haben
        for s in en:
            sid = s.id
            if sid in excluded_set_ids:
                continue  # Pocket-Set nicht anlegen
            if sid in by_setid:
                continue
            d = details.get(sid, {})
            ab = d.get("abbreviation") if isinstance(d.get("abbreviation"), dict) else {}
            code = (ab.get("official") or "").strip().upper()
            if not code or code in used_codes:
                code = sid  # eindeutiger Fallback
            if code in used_codes:
                continue
            de_src = de_by_id.get(sid)
            row = PokemonSet(code=code, name=(de_src.name if de_src and de_src.name else s.name) or sid, set_id=sid)
            db.add(row)
            used_codes.add(code)
            by_setid[sid] = row
            _enrich(row, s, d, de_src)
            created += 1

        db.commit()
    finally:
        db.close()

    log.info("Set-Sync fertig: %d aktualisiert, %d neu angelegt (Gesamt-Sets: %d).",
             updated, created, updated + created)
    return {"updated": updated, "created": created, "total": updated + created}
