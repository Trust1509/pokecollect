"""
Auth-freier Spiegel-Pfad für fremde Bilder (#120) — Begründung und Grenzen
in services/bild_spiegel.py.

Bewusst NICHT unter dem Auth-Zwang von api/v1 (CLAUDE.md „Auth-Zwang"): Der
Bild-Optimizer von Next ruft diese Pfade serverseitig ab und schickt keine
Anmeldung mit — wie beim /images-Mount. Statt der Anmeldung schützt die
Signatur: Ein Abruf beim fremden Host findet nur für Quellen statt, die das
Backend selbst signiert hat (oder für die feste Pokédex-Vorlage).

Nicht im OpenAPI-Schema (wie der /images-Mount): Die Pfade sind kein Teil der
Fach-Schnittstelle, und ein Fuzzer erreicht ohne Signatur ohnehin nur 404.
Ein Fehlschlag beim fremden Host ist ebenfalls 404, nicht 502 — für den
Aufrufer (Optimizer, Browser) ist das Bild schlicht nicht da.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import bild_spiegel

router = APIRouter(include_in_schema=False)

_MEDIENTYP = {".webp": "image/webp", ".jpg": "image/jpeg", ".png": "image/png"}
_KOPF = {
    # Die Quelle ändert sich unter demselben Pfad nie (Pfad = signierte URL),
    # also darf jeder Zwischenspeicher lange halten.
    "Cache-Control": "public, max-age=2592000, immutable",
    "X-Content-Type-Options": "nosniff",
}
_NR = re.compile(r"[0-9]{1,4}")


async def _ausliefern(url: str) -> FileResponse:
    datei: Path | None = await bild_spiegel.datei_fuer(url)
    if datei is None:
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")
    return FileResponse(datei, media_type=_MEDIENTYP[datei.suffix], headers=_KOPF)


# Vor dem allgemeinen Pfad registriert; "pokedex" ist ohnehin keine gültige
# Signatur (32 Hex-Zeichen), die Reihenfolge ist nur Klarheit.
@router.get(f"{bild_spiegel.PRAEFIX}/pokedex/{{nr}}.png")
async def pokedex_platzhalter(nr: str) -> FileResponse:
    url = bild_spiegel.pokedex_url(int(nr)) if _NR.fullmatch(nr) else None
    if url is None:
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")
    return await _ausliefern(url)


@router.get(f"{bild_spiegel.PRAEFIX}/{{signatur}}/{{kodiert}}")
async def gespiegeltes_bild(signatur: str, kodiert: str) -> FileResponse:
    url = bild_spiegel.url_aus_pfad(signatur, kodiert)
    if url is None:
        raise HTTPException(status_code=404, detail="Bild nicht verfügbar")
    return await _ausliefern(url)
