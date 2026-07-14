"""
Pokédex-Domänenwissen: Generationsgrenzen — die eine Quelle im Backend
(Kredo 1). Das Web hält bewusst eine eigene Kopie in web/src/lib/utils.ts
(generation()) für clientseitiges Dimmen — bei einer Gen-10-Erweiterung
BEIDE Stellen anpassen.
"""

from typing import Optional

GEN_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 151), 2: (152, 251), 3: (252, 386), 4: (387, 493),
    5: (494, 649), 6: (650, 721), 7: (722, 809), 8: (810, 905), 9: (906, 1025),
}


def generation(pokedex_nr: Optional[int]) -> Optional[int]:
    """Pokédex-Nummer → Generation (1-9), None wenn unbekannt/leer."""
    if not pokedex_nr:
        return None
    for gen, (lo, hi) in GEN_RANGES.items():
        if lo <= pokedex_nr <= hi:
            return gen
    return None
