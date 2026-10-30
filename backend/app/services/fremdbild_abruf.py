"""
Abruf EINES Bildes von einem fremden Bild-Host (#120) — die eine Routine für
den Katalog-Bild-Cache (catalog_images.py) und den Bild-Spiegel
(bild_spiegel.py).

Weiterleitungen werden NICHT verfolgt: Jede Antwort außer 200 ist ein
Fehlschlag. Vorher folgte der Katalog-Cache ihnen und prüfte nur die finale
URL — die Zwischenstationen waren da schon abgerufen. Die drei erlaubten CDNs
liefern ihre Bilder direkt (gemessen 30.10.2026: tcgdex webp/png, tcgplayer
jpg, pokemon.com png — je 200 ohne Weiterleitung).

Die Byte-Kappe greift WÄHREND des Lesens (Stream), nicht erst danach — eine
übergroße Antwort landet nie ganz im Speicher. Sie ist dieselbe wie für
Uploads (card_images._MAX_UPLOAD_BYTES, DRY).

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

from io import BytesIO
from typing import Callable

import httpx
from PIL import Image

from app.services.card_images import _MAX_UPLOAD_BYTES

USER_AGENT = "PokeCollect/0.7 (+self-hosted)"

# Erlaubte Formate und ihre Endung — alles andere (svg, gif, bmp …) wird
# verworfen (Panel-Nacharbeit #43).
FORMAT_ENDUNGEN = {"WEBP": ".webp", "JPEG": ".jpg", "PNG": ".png"}


class AbrufFehler(Exception):
    """Ein fremdes Bild ließ sich nicht abrufen oder ist kein erlaubtes Bild."""


async def bild_holen(url: str, *, erlaubt: Callable[[str], bool]) -> bytes:
    """Holt die Bytes von `url`. Wirft AbrufFehler (oder einen httpx-Fehler),
    wenn `erlaubt(url)` nicht wahr ist — VOR jeder Verbindung —, bei jeder
    Antwort außer 200, bei fehlendem oder fremdem Content-Type und bei
    Überschreiten der Byte-Kappe. Das Host-Urteil ist Pflicht-Argument (Panel
    #120): Ein künftiger Aufrufer kann die Prüfung nicht vergessen."""
    if not erlaubt(url):
        raise AbrufFehler(f"Quelle nicht erlaubt: {url!r}")
    # identity: Die Kappe zählt gelesene Bytes; bei gzip zählte sie entpackte,
    # und ein einzelner entpackter Block läge vor der Prüfung ganz im Speicher
    # (Gegenprüfer #120). Bilder sind ohnehin komprimiert.
    async with httpx.AsyncClient(
        timeout=10.0, follow_redirects=False,
        headers={"User-Agent": USER_AGENT, "Accept-Encoding": "identity"},
    ) as client:
        async with client.stream("GET", url) as resp:
            if resp.status_code != 200:
                # 3xx eingeschlossen: Weiterleitungen werden nicht verfolgt.
                raise AbrufFehler(f"HTTP {resp.status_code} statt 200")
            content_type = resp.headers.get("content-type", "")
            if not content_type.lower().startswith("image/"):
                raise AbrufFehler(f"unerwarteter Content-Type: {content_type!r}")
            laenge = resp.headers.get("content-length", "")
            if laenge.isdigit() and int(laenge) > _MAX_UPLOAD_BYTES:
                raise AbrufFehler(f"Bild zu groß ({laenge} Bytes laut Kopf, Grenze {_MAX_UPLOAD_BYTES})")
            teile: list[bytes] = []
            gelesen = 0
            async for teil in resp.aiter_bytes():
                gelesen += len(teil)
                if gelesen > _MAX_UPLOAD_BYTES:
                    raise AbrufFehler(f"Bild zu groß (über {_MAX_UPLOAD_BYTES} Bytes)")
                teile.append(teil)
    return b"".join(teile)


def bild_endung(daten: bytes) -> str:
    """Endung nach dem ECHTEN Format (PIL), nicht nach URL oder Kopf. Wirft
    AbrufFehler bei kaputtem Bild oder nicht erlaubtem Format."""
    try:
        with Image.open(BytesIO(daten)) as img:
            img.verify()
            fmt = img.format
    except Exception as exc:  # noqa: BLE001 — jedes PIL-Problem heißt: kein Bild
        raise AbrufFehler(f"kein lesbares Bild: {exc}") from exc
    endung = FORMAT_ENDUNGEN.get(fmt or "")
    if endung is None:
        raise AbrufFehler(f"unerwartetes Bildformat: {fmt!r}")
    return endung
