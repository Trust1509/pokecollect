"""
Automatische Kartenbilder von pokemon.com.

URL-Muster:
  https://www.pokemon.com/static-assets/content-assets/cms2-{locale}/img/cards/web/{CODE}/{CODE}_{LANG}_{NR}.png

Priorität in der App:
  1. bild_karte_pfad  – eigenes Foto (Upload)
  2. bild_pokedex_url – manuell gesetzte URL
  3. bild_karte_url   – auto von pokemon.com (dieses Modul)
  4. Pokédex-Artwork  – immer verfügbar (Fallback im Frontend)
"""

import logging
import re
from typing import Optional

import httpx

log = logging.getLogger(__name__)

# ── Set-Code Mapping: unser Kürzel → pokemon.com interner Code ───────────────
# Kürzel wird aus set_edition-Feld extrahiert: "Paldeas Schicksale (PAF)" → "PAF"
POKEMON_COM_SET_CODES: dict[str, str] = {
    # SV-Ära (Scharlachrot & Violett)
    "SVI":   "SV01",     # Scharlachrot & Violett Basis
    "PAL":   "SV02",     # Paldea Entwicklungen
    "OBF":   "SV03",     # Obsidian Flammen
    "MEW":   "SV3PT5",   # Pokémon 151
    "151":   "SV3PT5",   # Pokémon 151 (alternatives Kürzel)
    "PAR":   "SV04",     # Paradox Rift
    "PAF":   "SV4PT5",   # Paldeas Schicksale ✓ verifiziert
    "TEF":   "SV05",     # Temporale Kräfte
    "TWM":   "SV06",     # Masken der Wandlung
    "SFA":   "SV6PT5",   # Schicksalsfunken
    "SCR":   "SV07",     # Sternenglanz
    "SSP":   "SV08",     # Strahlende Seltenheit
    "PRE":   "SV8PT5",   # Prismatische Entwicklungen ✓ verifiziert
    "JTG":   "SV09",     # Reisegefährten / Journey Together
    "DRI":   "SV9PT5",   # Ewige Rivalen / Destined Rivals
    "SVE":   "SVE",      # SV Energie-Karten
    # SWSH-Ära (Schwert & Schild)
    "SSH":   "SWSH1",    # Schwert & Schild Basis
    "RCL":   "SWSH2",    # Aufziehen des Sturms
    "DAA":   "SWSH3",    # Drachenwandel
    "VIV":   "SWSH4",    # Strahlende Sterne
    "SHF":   "SWSH4PT5", # Shining Fates
    "BST":   "SWSH5",    # Kampf-Stile
    "CRE":   "SWSH6",    # Chilling Reign
    "EVS":   "SWSH7",    # Evolving Skies
    "BLK":   "SWSH7",    # Schwarze Blitze ✓ verifiziert
    "CEL":   "SWSH7PT5", # Celebrations
    "FST":   "SWSH8",    # Fusion Strike
    "BRS":   "SWSH9",    # Brilliant Stars
    "WHT":   "SWSH9",    # Weiße Flammen ✓ verifiziert
    "ASR":   "SWSH10",   # Astral Radiance
    "ASC":   "SWSH10",   # Erhabene Helden ✓ verifiziert
    "PGO":   "SWSH10PT5",# Pokémon GO
    "LOR":   "SWSH11",   # Lost Origin
    "PFL":   "SWSH11",   # Fatale Flammen ✓ verifiziert
    "SIT":   "SWSH12",   # Silver Tempest
    "CRZ":   "SWSH12PT5",# Crown Zenith
    # XY-Ära
    "XY":    "XY1",      # XY Basis
    "FLF":   "XY2",      # Flashfire
    "FFI":   "XY3",      # Furious Fists
    "PHF":   "XY4",      # Phantom Forces
    "PRC":   "XY5",      # Primal Clash
    "DCR":   "XY5PT5",   # Double Crisis
    "ROS":   "XY6",      # Roaring Skies
    "AOR":   "XY7",      # Ancient Origins
    "BKT":   "XY8",      # BREAKthrough
    "MEG":   "XY8",      # Mega-Entwicklung ✓ verifiziert
    "BKP":   "XY9",      # BREAKpoint
    "FAC":   "XY10",     # Fates Collide
    "STS":   "XY11",     # Steam Siege
    "EVO":   "XY12",     # Evolutions
}

# Locale-Mapping: unsere Sprachkürzel → pokemon.com locale
LOCALE_MAP: dict[str, str] = {
    "DE": "de-de",
    "EN": "en-us",
    "FR": "fr-fr",
    "ES": "es-es",
    "IT": "it-it",
    "PT": "pt-br",
}

# Sprachkürzel für die URL selbst (nach dem SET_CODE im Dateinamen)
LANG_IN_URL: dict[str, str] = {
    "DE": "DE",
    "EN": "EN",
    "FR": "FR",
    "ES": "ES",
    "IT": "IT",
    "PT": "PT",
}

BASE_URL = "https://www.pokemon.com/static-assets/content-assets/cms2-{locale}/img/cards/web/{code}/{code}_{lang}_{nr}.png"


def _extract_set_code(set_edition: Optional[str]) -> Optional[str]:
    """
    Extrahiert das Kürzel aus dem set_edition-Feld.
    'Paldeas Schicksale (PAF)' → 'PAF'
    '151 (151C) - Chinesisch'  → '151C'  (erstes kurzes Kürzel in Klammern)
    'Erhabene Helden (Ascended Heroes)' → None  (kein gültiges Kürzel)
    """
    if not set_edition:
        return None
    # Alle Kürzel in Klammern suchen, nur kurze (≤6 Zeichen) rein alphanumerische akzeptieren
    for m in re.finditer(r"\(([A-Z0-9]{1,6})\)", set_edition):
        return m.group(1)
    return None


def _extract_card_nr(karten_nr: Optional[str]) -> Optional[str]:
    """Extrahiert die Nummer: '007/091' → '7', '195/091' → '195', 'TG01/TG30' → None."""
    if not karten_nr:
        return None
    nr_part = karten_nr.split("/")[0].lstrip("0")
    # Buchstaben im Präfix (z.B. "TG01") → nicht unterstützt
    if not nr_part.isdigit():
        return None
    return nr_part or "1"


def build_url(set_edition: Optional[str], karten_nr: Optional[str], sprache: Optional[str]) -> Optional[str]:
    """Konstruiert die pokemon.com URL ohne HEAD-Check."""
    code = _extract_set_code(set_edition)
    if not code:
        return None
    pokemon_code = POKEMON_COM_SET_CODES.get(code)
    if not pokemon_code:
        return None

    lang = sprache or "DE"
    locale = LOCALE_MAP.get(lang, "en-us")
    lang_url = LANG_IN_URL.get(lang, lang)
    nr = _extract_card_nr(karten_nr)
    if not nr:
        return None

    return BASE_URL.format(locale=locale, code=pokemon_code, lang=lang_url, nr=nr)


async def fetch_card_image_url(
    set_edition: Optional[str],
    karten_nr: Optional[str],
    sprache: Optional[str],
) -> Optional[str]:
    """
    Konstruiert die URL und prüft via HEAD ob das Bild existiert.
    Gibt None zurück wenn Set nicht im Mapping oder Bild nicht vorhanden.
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
