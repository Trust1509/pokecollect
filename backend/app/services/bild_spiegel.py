"""
Bild-Spiegel (#120): fremde Bilder über die eigene API ausliefern.

Warum: Der Bild-Optimizer von Next folgt Weiterleitungen und prüft das Ziel
danach nicht mehr gegen seine Allowlist (gemessen im Panel zu #117). Leitete
eines der fremden CDNs weiter, rief der Web-Server jedes Ziel ab, auch
interne. Seit #120 erlaubt der Optimizer nur noch die eigene API; fremde
Bilder holt dieses Modul — ohne Weiterleitungen (fremdbild_abruf.bild_holen)
— und legt sie unter images_dir/spiegel/ ab.

Der Spiegel-Pfad ist auth-frei (der Optimizer schickt keine Anmeldung mit)
und darum KEIN offener Abruf: Er nennt die Quelle samt HMAC-Signatur, und nur
das Backend kann signieren. Signiert wird nur, was es selbst in eine Antwort
schreibt (Karten-, Sealed- und Katalog-Bild-URLs, Schemas mit `*_spiegel`).
Wer die Signatur nicht kennt, bekommt 404, ohne dass ein Abruf stattfindet.
Einzige unsignierte Ausnahme: die Pokédex-Platzhalter, eine feste Vorlage
mit der Nummer 1–1025 (höchstens 1025 Dateien).

Erlaubt sind genau die drei Bild-Hosts (Owner-Entscheid #120, Variante A):
die zwei aus tcgdex.ALLOWED_IMAGE_HOSTS und www.pokemon.com unter
/static-assets/. Eine von Hand gesetzte Pokédex-Bild-URL zu einem anderen
Host bekommt keinen Spiegel-Pfad — die Anzeige fällt auf das Kartenbild bzw.
den Platzhalter zurück.

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit
from uuid import uuid4

from app.config import settings
from app.services import fremdbild_abruf, tcgdex

log = logging.getLogger(__name__)

PRAEFIX = "/bild-spiegel"
UNTERORDNER = "spiegel"

_POKEMON_HOST = "www.pokemon.com"
_POKEMON_PFAD = "/static-assets/"
_POKEDEX_VORLAGE = (
    "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/{nr:03d}.png"
)
POKEDEX_MAX = 1025

# Nur dieses Alphabet im Pfad der Quelle — die echten Bild-URLs aller drei
# Hosts kommen damit aus (tcgdex /de/swsh/swsh3/136/high.webp, tcgplayer
# /product/42346_in_1000x1000.jpg, pokemon.com …/full/025.png). Kein "%",
# kein "\\", keine Leerzeichen: nichts, was ein Server anders auslegen könnte
# als dieser Vergleich.
_PFAD_ZEICHEN = re.compile(r"/[A-Za-z0-9._/-]*")
_SIGNATUR = re.compile(r"[0-9a-f]{32}")
_KODIERT = re.compile(r"[A-Za-z0-9_-]{1,700}")


def ist_spiegelbar(url: Optional[str]) -> bool:
    """True nur für eine https-URL ohne Anmeldedaten, Port, Query und
    Fragment auf einem der drei erlaubten Hosts, mit einem Pfad aus dem
    sicheren Alphabet und ohne Punkt-Segmente."""
    if not url or not url.isascii():
        return False
    # urlsplit entfernt Tab und Zeilenumbruch still (Python-Schutz gegen
    # bpo-43882) — geprüft würde dann eine andere URL als die abgerufene.
    if any(ord(z) <= 0x20 or ord(z) == 0x7F for z in url):
        return False
    try:
        teile = urlsplit(url)
        port = teile.port
    except ValueError:
        return False
    if teile.scheme != "https" or port is not None or teile.query or teile.fragment:
        return False
    host = teile.hostname or ""
    # netloc muss GENAU der Host sein: keine Anmeldedaten, kein leerer Port
    # ("host:"), keine Großschreibung, die hostname still angleicht.
    if teile.netloc != host:
        return False
    pfad = teile.path
    if not _PFAD_ZEICHEN.fullmatch(pfad):
        return False
    if any(segment in (".", "..") for segment in pfad.split("/")):
        return False
    if host in tcgdex.ALLOWED_IMAGE_HOSTS:
        return True
    return host == _POKEMON_HOST and pfad.startswith(_POKEMON_PFAD)


def _schluessel() -> bytes:
    # Eigener Schlüssel, aus dem JWT-Geheimnis abgeleitet — nie das Geheimnis
    # selbst als HMAC-Schlüssel für einen zweiten Zweck.
    return hmac.new(settings.jwt_secret.encode(), b"pokecollect/bild-spiegel/v1", hashlib.sha256).digest()


def _signatur(url: str) -> str:
    return hmac.new(_schluessel(), url.encode(), hashlib.sha256).hexdigest()[:32]


def spiegel_pfad(url: Optional[str]) -> Optional[str]:
    """Relativer Spiegel-Pfad (`/bild-spiegel/<signatur>/<quelle>`) oder None,
    wenn die URL nicht gespiegelt werden darf. Das Frontend setzt den
    API-Origin davor (lib/utils.ts spiegelUrl)."""
    if not ist_spiegelbar(url):
        return None
    kodiert = base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()
    return f"{PRAEFIX}/{_signatur(url)}/{kodiert}"


def url_aus_pfad(signatur: str, kodiert: str) -> Optional[str]:
    """Quelle zu einem Spiegel-Pfad, oder None bei falscher Form, falscher
    Signatur oder nicht (mehr) erlaubter Quelle."""
    if not _SIGNATUR.fullmatch(signatur) or not _KODIERT.fullmatch(kodiert):
        return None
    try:
        url = base64.urlsafe_b64decode(kodiert + "=" * (-len(kodiert) % 4)).decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return None
    if not hmac.compare_digest(signatur, _signatur(url)):
        return None
    return url if ist_spiegelbar(url) else None


def pokedex_url(nr: int) -> Optional[str]:
    if not 1 <= nr <= POKEDEX_MAX:
        return None
    return _POKEDEX_VORLAGE.format(nr=nr)


def _ablage(url: str, endung: str) -> Path:
    name = hashlib.sha256(url.encode()).hexdigest()
    return Path(settings.images_dir) / UNTERORDNER / f"{name}{endung}"


async def datei_fuer(url: str) -> Optional[Path]:
    """Gespiegelte Datei zu `url` — aus der Ablage, sonst frisch geholt,
    geprüft und atomar abgelegt. None bei jedem Fehlschlag (geloggt); wirft
    nie. Der Aufrufer hat `url` vorher geprüft (url_aus_pfad/pokedex_url)."""
    for endung in fremdbild_abruf.FORMAT_ENDUNGEN.values():
        vorhanden = _ablage(url, endung)
        if vorhanden.is_file():
            return vorhanden
    tmp: Optional[Path] = None
    try:
        daten = await fremdbild_abruf.bild_holen(url)
        endung = fremdbild_abruf.bild_endung(daten)
        ziel = _ablage(url, endung)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        # volle uuid4: der Ordner liegt im auth-freien /images-Baum (wie #82)
        tmp = ziel.with_name(f"{ziel.name}.tmp-{uuid4().hex}")
        tmp.write_bytes(daten)
        os.replace(tmp, ziel)  # atomar: zwei gleichzeitige Abrufe sehen nie eine halbe Datei
        return ziel
    except Exception as exc:  # noqa: BLE001 — eine fremde Quelle darf die Antwort nie sprengen
        log.warning("Bild-Spiegel: %s nicht abrufbar: %s", url, exc)
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as aufraeum_fehler:
                log.warning("Bild-Spiegel: TMP-Aufräumen fehlgeschlagen: %s", aufraeum_fehler)
        return None
