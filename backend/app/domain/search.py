"""
Such-Domänenlogik: Kurzcode-Erkennung „KÜRZEL NUMMER" (z. B. „PFL 001").
Eine Routine für Katalog- und Kartensuche (Kredo 1 / DRY).
"""

import re
from typing import NamedTuple, Optional

# Set-Kürzel sind 2–6 alphanumerische Zeichen, danach getrennt eine
# Kartennummer (1–4 Ziffern, optionaler Buchstaben-Suffix wie „a"). Der
# Rest der Nummer nach einem „/" (z. B. „125/197") wird ignoriert.
_KURZCODE = re.compile(r"^\s*([A-Za-z0-9]{2,6})\s+(\d{1,4})[a-z]?(?:/\d+)?\s*$")


class Kurzcode(NamedTuple):
    code: str   # Set-Kürzel, upper-case
    nr: str     # Kartennummer ohne führende Nullen ("1", "125")


def parse_kurzcode(query: Optional[str]) -> Optional[Kurzcode]:
    """
    „PFL 001" → Kurzcode(code='PFL', nr='1'); „obf 125" → ('OBF', '125').
    None, wenn das Muster nicht passt (dann normale Volltextsuche).

    Ob das Kürzel wirklich ein bekanntes Set ist, entscheidet der Aufrufer —
    diese Funktion parst nur die Form. So bleibt „Mew 151" ein Kandidat, den
    der Endpoint gegen die Set-Tabelle prüft.
    """
    if not query:
        return None
    m = _KURZCODE.match(query)
    if not m:
        return None
    code = m.group(1).upper()
    nr = m.group(2).lstrip("0") or "0"
    return Kurzcode(code=code, nr=nr)
