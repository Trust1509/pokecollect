"""
Bild-Spiegel (#120): fremde Bilder über die eigene API ausliefern.

Warum: Der Bild-Optimizer von Next folgt Weiterleitungen und prüft das Ziel
danach nicht mehr gegen seine Allowlist (gemessen im Panel zu #117). Leitete
eines der fremden CDNs weiter, rief der Web-Server jedes Ziel ab, auch
interne. Seit #120 sieht weder der Optimizer noch der Browser ein fremdes
CDN: Fremde Bilder holt dieses Modul — ohne Weiterleitungen
(fremdbild_abruf.bild_holen) — und legt sie unter images_dir/spiegel/ ab.
Der Browser lädt sie von hier wie eigene Fotos, am Optimizer vorbei
(web/src/components/AppImage.tsx).

Der Spiegel-Pfad ist auth-frei (ein <img>-Tag schickt keinen
Authorization-Header — wie beim /images-Mount, ADR-0003) und darum KEIN
offener Abruf: Er nennt die Quelle samt HMAC-Signatur, und nur das Backend
kann signieren. Signiert wird nur, was es selbst in eine Antwort schreibt
(Karten-, Platzhalter-, Sealed- und Katalog-Bilder, Schemas mit
`*_spiegel`). Ohne gültige Signatur: 404, ohne Abruf. Es gibt keinen
unsignierten Pfad — auch der Pokédex-Platzhalter kommt signiert aus der
Karten-Antwort (Panel #120: eine unsignierte Vorlage ließ Unangemeldete
Abrufe auslösen).

Weitere Bremsen (Panel #120): je Quelle höchstens ein Abruf zur Zeit
(gleichzeitige Anfragen warten auf denselben), ein Fehlschlag wird
_FEHLSCHLAG_SEKUNDEN lang nicht wiederholt, und der Dateiname der Ablage ist
eine HMAC der Quelle — wer eine Quelle kennt, kann unter /images/spiegel/
nicht nachsehen, ob sie je angezeigt wurde.

Erlaubt sind genau die drei Bild-Hosts (Owner-Entscheid #120, Variante A):
die zwei aus tcgdex.ALLOWED_IMAGE_HOSTS und www.pokemon.com unter
/static-assets/. Eine von Hand gesetzte Pokédex-Bild-URL zu einem anderen
Host bekommt keinen Spiegel-Pfad — die Anzeige fällt auf das Kartenbild bzw.
den Platzhalter zurück.

Eigenimplementierung (MIT). Kein Code aus Drittprojekten übernommen.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import logging
import os
import re
import time
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

_FEHLSCHLAG_SEKUNDEN = 600.0
_FEHLSCHLAG_MAX_EINTRAEGE = 1000

# je Quelle ein Lock (ein Abruf zur Zeit) und die Zeit des letzten Fehlschlags
_locks: dict[str, asyncio.Lock] = {}
_fehlschlaege: dict[str, float] = {}


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


def _hmac(zweck: bytes, url: str) -> str:
    return hmac.new(_schluessel(), zweck + b"\x00" + url.encode(), hashlib.sha256).hexdigest()


def _signatur(url: str) -> str:
    # 128 Bit der HMAC-SHA256 — mehr als genug gegen Raten.
    return _hmac(b"signatur", url)[:32]


def _kodieren(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()


def spiegel_pfad(url: Optional[str]) -> Optional[str]:
    """Relativer Spiegel-Pfad (`/bild-spiegel/<signatur>/<quelle>`) oder None,
    wenn die URL nicht gespiegelt werden darf. Das Frontend setzt den
    API-Origin davor (lib/utils.ts spiegelUrl)."""
    if not ist_spiegelbar(url):
        return None
    return f"{PRAEFIX}/{_signatur(url)}/{_kodieren(url)}"


def pokedex_url(nr: Optional[int]) -> Optional[str]:
    if nr is None or not 1 <= nr <= POKEDEX_MAX:
        return None
    return _POKEDEX_VORLAGE.format(nr=nr)


def url_aus_pfad(signatur: str, kodiert: str) -> Optional[str]:
    """Quelle zu einem Spiegel-Pfad, oder None bei falscher Form, falscher
    Signatur, nicht kanonischer Kodierung oder nicht (mehr) erlaubter Quelle."""
    if not _SIGNATUR.fullmatch(signatur) or not _KODIERT.fullmatch(kodiert):
        return None
    try:
        url = base64.urlsafe_b64decode(kodiert + "=" * (-len(kodiert) % 4)).decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return None
    # Base64 hat für dieselben Bytes mehrere Schreibweisen (ungenutzte Bits im
    # letzten Zeichen) — nur die eine, die spiegel_pfad baut, gilt (Panel #120).
    if kodiert != _kodieren(url):
        return None
    if not hmac.compare_digest(signatur, _signatur(url)):
        return None
    return url if ist_spiegelbar(url) else None


def _ablage(url: str, endung: str) -> Path:
    return Path(settings.images_dir) / UNTERORDNER / f"{_hmac(b'ablage', url)}{endung}"


def _vorhanden(url: str) -> Optional[Path]:
    for endung in fremdbild_abruf.FORMAT_ENDUNGEN.values():
        datei = _ablage(url, endung)
        if datei.is_file():
            return datei
    return None


def _kuerzlich_gescheitert(url: str) -> bool:
    zeit = _fehlschlaege.get(url)
    if zeit is None:
        return False
    if time.monotonic() - zeit < _FEHLSCHLAG_SEKUNDEN:
        return True
    del _fehlschlaege[url]
    return False


def _fehlschlag_merken(url: str) -> None:
    if len(_fehlschlaege) >= _FEHLSCHLAG_MAX_EINTRAEGE:
        _fehlschlaege.clear()
    _fehlschlaege[url] = time.monotonic()


async def datei_fuer(url: str) -> Optional[Path]:
    """Gespiegelte Datei zu `url` — aus der Ablage, sonst frisch geholt,
    geprüft und atomar abgelegt. None bei jedem Fehlschlag (geloggt); wirft
    nie. Der Aufrufer hat `url` vorher geprüft (url_aus_pfad); bild_holen
    prüft sie mit ist_spiegelbar noch einmal."""
    vorhanden = _vorhanden(url)
    if vorhanden is not None:
        return vorhanden
    # Locks bleiben stehen: Es gibt nur so viele, wie das Backend Quellen
    # signiert hat (Sammlung + Katalog), und Aufräumen öffnete ein Fenster für
    # einen zweiten gleichzeitigen Abruf.
    async with _locks.setdefault(url, asyncio.Lock()):
        # Wer gewartet hat, findet die Datei des Vorgängers — oder dessen Fehlschlag.
        vorhanden = _vorhanden(url)
        if vorhanden is not None:
            return vorhanden
        if _kuerzlich_gescheitert(url):
            return None
        return await _holen_und_ablegen(url)


async def _holen_und_ablegen(url: str) -> Optional[Path]:
    tmp: Optional[Path] = None
    try:
        daten = await fremdbild_abruf.bild_holen(url, erlaubt=ist_spiegelbar)
        endung = fremdbild_abruf.bild_endung(daten)
        ziel = _ablage(url, endung)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        # volle uuid4: der Ordner liegt im auth-freien /images-Baum (wie #82)
        tmp = ziel.with_name(f"{ziel.name}.tmp-{uuid4().hex}")
        tmp.write_bytes(daten)
        os.replace(tmp, ziel)  # atomar: nie eine halbe Datei unter dem Zielnamen
        return ziel
    except Exception as exc:  # noqa: BLE001 — eine fremde Quelle darf die Antwort nie sprengen
        log.warning("Bild-Spiegel: %s nicht abrufbar: %s", url, exc)
        _fehlschlag_merken(url)
        if tmp is not None:
            try:
                tmp.unlink(missing_ok=True)
            except OSError as aufraeum_fehler:
                log.warning("Bild-Spiegel: TMP-Aufräumen fehlgeschlagen: %s", aufraeum_fehler)
        return None
