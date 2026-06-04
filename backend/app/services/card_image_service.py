"""
Automatische Kartenbilder von pokemon.com.

URL-Muster:
  https://www.pokemon.com/static-assets/content-assets/cms2-{locale}/img/cards/web/{CODE}/{CODE}_{LANG}_{NR}.png

WICHTIG: Die URL-Nummer entspricht NICHT der aufgedruckten Kartennummer.
Pokemon.com verwendet eine eigene interne Sortierung pro Set.
→ URL nie direkt aus der Kartennummer konstruieren.
→ Für SV-Era Sets stimmt die Nummerierung zufällig überein (internationale
   Simultanveröffentlichung). Für SWSH/XY-era deutsche Subsets weicht sie ab.

Aktueller Stand:
  - SV-Era: direkte Nummerierung funktioniert, gecacht in bild_karte_url
  - SWSH/XY DE-Subsets: nicht automatisch möglich → manuelle URL oder Pokédex-Artwork
  - Zukünftig (v0.7.0): PokémonTCG.io API für korrekte sprachspezifische Kartendaten

Bild-Priorität in der App:
  1. bild_karte_pfad  – eigenes Foto (Upload), immer bevorzugt
  2. bild_pokedex_url – manuell gesetzte URL
  3. bild_karte_url   – auto von pokemon.com (dieses Modul, nur SV-Era zuverlässig)
  4. Pokédex-Artwork  – immer verfügbar als letzter Fallback
"""

import logging
import re
from typing import Optional

import httpx

log = logging.getLogger(__name__)

# ── Set-Code Mapping ──────────────────────────────────────────────────────────
# Nur Sets wo aufgedruckte Kartennummer = pokemon.com URL-Nummer (SV-Era ✓)
# SWSH/XY-era deutsche Sets absichtlich ausgelassen: Nummerierung weicht ab
# → würden falsche Kartenbilder zeigen
POKEMON_COM_SET_CODES: dict[str, Optional[str]] = {
    # SV-Ära — internationale Simultanveröffentlichung, Nummerierung identisch ✓
    "SVI":   "SV01",     # Scharlachrot & Violett Basis ✓
    "PAL":   None,       # Entwicklungen in Paldea — DE-Nummerierung weicht ab
    "OBF":   "SV03",     # Obsidian Flammen ✓
    "MEW":   "SV3PT5",   # Pokémon 151 ✓
    "151":   "SV3PT5",   # Pokémon 151 (alternatives Kürzel) ✓
    "PAR":   None,       # Paradox Rift — DE-Nummerierung weicht ab
    "PAF":   "SV4PT5",   # Paldeas Schicksale ✓ verifiziert
    "TEF":   "SV05",     # Temporale Kräfte ✓
    "TWM":   "SV06",     # Masken der Wandlung ✓
    "SFA":   "SV6PT5",   # Schicksalsfunken ✓
    "SCR":   "SV07",     # Sternenglanz ✓
    "SSP":   "SV08",     # Surging Sparks ✓ verifiziert
    "PRE":   "SV8PT5",   # Prismatische Entwicklungen ✓ verifiziert
    "JTG":   "SV09",     # Reisegefährten / Journey Together ✓ verifiziert
    "DRI":   "SV10",     # Ewige Rivalen / Destined Rivals ✓ verifiziert
    "SVE":   "SVE",      # SV Energie-Karten ✓
    # SWSH/XY-Ära: deutsche Subsets haben andere Nummerierung → nicht gelistet
    # ASC, PFL, BLK, BRS, WHT, MEG etc. → manuelle URL über "Bild-URL hinterlegen"
    # oder zukünftig via PokémonTCG.io API (v0.7.0)
}

LOCALE_MAP: dict[str, str] = {
    "DE": "de-de",
    "EN": "en-us",
    "FR": "fr-fr",
    "ES": "es-es",
    "IT": "it-it",
    "PT": "pt-br",
}

BASE_URL = "https://www.pokemon.com/static-assets/content-assets/cms2-{locale}/img/cards/web/{code}/{code}_{lang}_{nr}.png"


def _extract_set_code(set_edition: Optional[str]) -> Optional[str]:
    """
    Extrahiert das Kürzel aus dem set_edition-Feld.
    'Paldeas Schicksale (PAF)' → 'PAF'
    '151 (151C) - Chinesisch'  → '151C'
    'Erhabene Helden (Ascended Heroes)' → None (zu lang, kein gültiges Kürzel)
    """
    if not set_edition:
        return None
    for m in re.finditer(r"\(([A-Z0-9]{1,6})\)", set_edition):
        return m.group(1)
    return None


def _extract_card_nr(karten_nr: Optional[str]) -> Optional[str]:
    """
    Extrahiert die Nummer ohne führende Nullen.
    '007/091' → '7', '195/091' → '195'
    'TG01/TG30' → None (Buchstaben-Präfix nicht unterstützt)

    HINWEIS: Diese Nummer entspricht nur bei SV-Era Sets der URL-Nummer.
    Für ältere Sets weicht die interne pokemon.com Nummerierung ab.
    """
    if not karten_nr:
        return None
    nr_part = karten_nr.split("/")[0].lstrip("0")
    if not nr_part.isdigit():
        return None
    return nr_part or "1"


def build_url(set_edition: Optional[str], karten_nr: Optional[str], sprache: Optional[str]) -> Optional[str]:
    """Konstruiert die pokemon.com URL ohne HEAD-Check. None wenn Set nicht unterstützt."""
    code_key = _extract_set_code(set_edition)
    if not code_key:
        return None
    pokemon_code = POKEMON_COM_SET_CODES.get(code_key)
    if not pokemon_code:
        return None  # Set explizit als None markiert oder nicht im Mapping

    lang = sprache or "DE"
    locale = LOCALE_MAP.get(lang, "en-us")
    nr = _extract_card_nr(karten_nr)
    if not nr:
        return None

    return BASE_URL.format(locale=locale, code=pokemon_code, lang=lang, nr=nr)


async def fetch_card_image_url(
    set_edition: Optional[str],
    karten_nr: Optional[str],
    sprache: Optional[str],
) -> Optional[str]:
    """
    Konstruiert die URL und prüft via HEAD ob das Bild existiert.
    Gibt None zurück wenn Set nicht im Mapping, Set explizit None ist,
    oder Bild nicht vorhanden (HTTP ≠ 200).
    """
    url = build_url(set_edition, karten_nr, sprache)
    if not url:
        return None

    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.head(url)
            if resp.status_code == 200:
                log.debug(f"Kartenbild gefunden: {url}")
                return url
            log.debug(f"Kartenbild nicht gefunden (HTTP {resp.status_code}): {url}")
    except Exception as e:
        log.warning(f"HEAD-Check fehlgeschlagen für {url}: {e}")

    return None
