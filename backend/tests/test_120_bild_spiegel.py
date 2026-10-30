"""
#120: Fremde Bilder über die eigene API (services/bild_spiegel.py,
api/bild_spiegel.py) und Abruf ohne Weiterleitungen
(services/fremdbild_abruf.py).

Netzfrei: httpx.AsyncClient bekommt eine MockTransport untergeschoben — der
echte Abrufcode (Status, Kopf, Stream, Kappe) läuft, nur das Netz nicht.
Fixture-URLs sind erfunden (Pfade in der Form der echten Hosts).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import httpx
import pytest

from app.schemas.card import CardResponse
from app.schemas.sealed import SealedCatalogItem, SealedProductResponse
from app.services import bild_spiegel, fremdbild_abruf
from app.services.card_images import _MAX_UPLOAD_BYTES

TCGDEX = "https://assets.tcgdex.net/de/swsh/swsh3/136/high.webp"
TCGPLAYER = "https://tcgplayer-cdn.tcgplayer.com/product/42346_in_1000x1000.jpg"
POKEMON = "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/025.png"


def _eindeutig(basis: str = "https://assets.tcgdex.net/de/test120") -> str:
    """Je Test eine eigene Quelle — die Ablage unter images_dir lebt über die
    ganze Sitzung, ein Treffer aus einem anderen Test verfälschte sonst
    "wurde abgerufen"."""
    return f"{basis}/{uuid4().hex}/high.webp"


@pytest.fixture()
def netz(monkeypatch):
    """Ersetzt das Netz durch `handler`; zeichnet Aufrufe und die
    Client-Optionen auf."""
    aufgezeichnet = {"anfragen": [], "optionen": []}
    zustand = {"handler": None}
    echt = httpx.AsyncClient

    def client(**optionen):
        aufgezeichnet["optionen"].append(optionen)

        def weiter(request: httpx.Request) -> httpx.Response:
            aufgezeichnet["anfragen"].append(str(request.url))
            return zustand["handler"](request)

        return echt(transport=httpx.MockTransport(weiter), **optionen)

    monkeypatch.setattr(fremdbild_abruf.httpx, "AsyncClient", client)

    def setzen(handler):
        zustand["handler"] = handler
        return aufgezeichnet

    return setzen


def _bild(daten: bytes, typ: str = "image/png"):
    return lambda request: httpx.Response(200, headers={"content-type": typ}, content=daten)


# ── Welche Quellen gespiegelt werden dürfen ─────────────────────────────────

@pytest.mark.parametrize("url", [TCGDEX, TCGPLAYER, POKEMON])
def test_die_drei_hosts_sind_spiegelbar(url):
    assert bild_spiegel.ist_spiegelbar(url)


@pytest.mark.parametrize("url", [
    None,
    "",
    "http://assets.tcgdex.net/de/x/high.webp",               # kein https
    "https://assets.tcgdex.net:443/de/x/high.webp",          # Port
    "https://assets.tcgdex.net:/de/x/high.webp",             # leerer Port
    "https://nutzer@assets.tcgdex.net/de/x/high.webp",       # Anmeldedaten
    "https://ASSETS.tcgdex.net/de/x/high.webp",              # Großschreibung
    "https://assets.tcgdex.net/de/x/high.webp?v=1",          # Query
    "https://assets.tcgdex.net/de/x/high.webp#a",            # Fragment
    "https://assets.tcgdex.net.evil.invalid/x.webp",         # Host als Präfix
    "https://evil.invalid/x.png",                            # fremder Host
    "https://www.pokemon.com/us/pokedex/pikachu",            # pokemon.com außerhalb /static-assets/
    "https://www.pokemon.com/static-assets/../us/x.png",     # Punkt-Segment
    "https://assets.tcgdex.net/de/./x/high.webp",            # Punkt-Segment
    "https://assets.tcgdex.net/de/%2e%2e/high.webp",         # Prozent-Kodierung
    "https://assets.tcgdex.net/de\\x/high.webp",             # Rückstrich
    "https://assets.tcgdex.net/de/x y/high.webp",            # Leerzeichen
    "https://assets.tcg\ndex.net/de/x/high.webp",            # urlsplit entfernt \n still
    "https://assets.tcgdex.net/de/x/high.webp\t",            # dito Tab
    "https://assets.tcgdex.net/de/ä/high.webp",              # nicht ASCII
    "https://assets.tcgdex.net",                             # leerer Pfad
])
def test_alles_andere_ist_nicht_spiegelbar(url):
    assert not bild_spiegel.ist_spiegelbar(url)
    assert bild_spiegel.spiegel_pfad(url) is None


# ── Signatur ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", [TCGDEX, TCGPLAYER, POKEMON, "https://assets.tcgdex.net/a"])
def test_spiegel_pfad_fuehrt_zur_quelle_zurueck(url):
    pfad = bild_spiegel.spiegel_pfad(url)
    praefix, signatur, kodiert = pfad.rsplit("/", 2)
    assert praefix == bild_spiegel.PRAEFIX
    assert bild_spiegel.url_aus_pfad(signatur, kodiert) == url


def test_falsche_oder_fremde_signatur_fuehrt_nirgendwohin():
    _, signatur, kodiert = bild_spiegel.spiegel_pfad(TCGDEX).rsplit("/", 2)
    _, andere_signatur, _ = bild_spiegel.spiegel_pfad(TCGPLAYER).rsplit("/", 2)
    gekippt = ("0" if signatur[0] != "0" else "1") + signatur[1:]
    assert bild_spiegel.url_aus_pfad(gekippt, kodiert) is None
    assert bild_spiegel.url_aus_pfad(andere_signatur, kodiert) is None
    assert bild_spiegel.url_aus_pfad(signatur.upper(), kodiert) is None
    assert bild_spiegel.url_aus_pfad(signatur, kodiert + "A") is None
    assert bild_spiegel.url_aus_pfad(signatur, "") is None


def test_signatur_haengt_am_geheimnis(monkeypatch):
    pfad = bild_spiegel.spiegel_pfad(TCGDEX)
    monkeypatch.setattr(bild_spiegel.settings, "jwt_secret", "ein-anderes-geheimnis")
    assert bild_spiegel.spiegel_pfad(TCGDEX) != pfad
    _, signatur, kodiert = pfad.rsplit("/", 2)
    assert bild_spiegel.url_aus_pfad(signatur, kodiert) is None


def test_signierte_aber_nicht_spiegelbare_quelle_wird_abgelehnt():
    """Signiert jemand (z. B. ein früherer Stand) eine Quelle, die heute nicht
    erlaubt ist, liefert url_aus_pfad trotzdem nichts."""
    url = "https://evil.invalid/x.png"
    kodiert = bild_spiegel.base64.urlsafe_b64encode(url.encode()).rstrip(b"=").decode()
    assert bild_spiegel.url_aus_pfad(bild_spiegel._signatur(url), kodiert) is None


# ── Antwort-Felder ──────────────────────────────────────────────────────────

def test_karte_traegt_spiegel_pfade_nur_fuer_erlaubte_hosts():
    karte = CardResponse(id=1, kartenname="Testkarte", bild_karte_url=TCGDEX,
                         bild_pokedex_url="https://bilder.example.invalid/eigen.png")
    daten = karte.model_dump()
    assert daten["bild_karte_spiegel"] == bild_spiegel.spiegel_pfad(TCGDEX)
    # Owner-Entscheid #120 (A): fremder Host → kein Pokédex-Bild
    assert daten["bild_pokedex_spiegel"] is None
    # die Quell-Felder bleiben unverändert (Bearbeiten, Herkunft)
    assert daten["bild_pokedex_url"] == "https://bilder.example.invalid/eigen.png"


def test_sealed_felder_tragen_spiegel_pfade():
    produkt = SealedProductResponse(id=1, name="Testdisplay", bild_url=TCGPLAYER)
    assert produkt.model_dump()["bild_spiegel"] == bild_spiegel.spiegel_pfad(TCGPLAYER)
    eintrag = SealedCatalogItem(product_id=1, region="EN", name="Testdisplay", image_url=TCGPLAYER)
    assert eintrag.model_dump()["image_spiegel"] == bild_spiegel.spiegel_pfad(TCGPLAYER)
    assert SealedProductResponse(id=2, name="Ohne Bild").model_dump()["bild_spiegel"] is None


def test_kartenliste_der_api_liefert_spiegel_pfad(client):
    r = client.post("/api/v1/cards", json={
        "kartenname": f"Spiegeltest {uuid4().hex[:6]}", "bild_pokedex_url": POKEMON,
    })
    assert r.status_code in (200, 201), r.text
    karte = client.get(f"/api/v1/cards/{r.json()['id']}").json()
    assert karte["bild_pokedex_spiegel"] == bild_spiegel.spiegel_pfad(POKEMON)
    client.delete(f"/api/v1/cards/{karte['id']}")


# ── Abruf ohne Weiterleitungen ──────────────────────────────────────────────

def test_weiterleitung_wird_nicht_verfolgt(netz, png_bytes):
    def handler(request):
        if request.url.host == "assets.tcgdex.net":
            return httpx.Response(302, headers={"location": "http://169.254.169.254/x.png"})
        return _bild(png_bytes)(request)

    aufgezeichnet = netz(handler)
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="302"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig()))
    assert len(aufgezeichnet["anfragen"]) == 1          # das Ziel wurde nie abgerufen
    assert aufgezeichnet["optionen"][0]["follow_redirects"] is False


@pytest.mark.parametrize("kopf", [{}, {"content-type": "text/html"}])
def test_ohne_bild_content_type_kein_bild(netz, png_bytes, kopf):
    netz(lambda request: httpx.Response(200, headers=kopf, content=png_bytes))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="Content-Type"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig()))


def test_zu_grosser_kopf_wird_vor_dem_lesen_abgelehnt(netz):
    netz(lambda request: httpx.Response(
        200, headers={"content-type": "image/png", "content-length": str(_MAX_UPLOAD_BYTES + 1)},
        content=b"x"))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="laut Kopf"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig()))


def test_zu_grosser_stream_ohne_kopf_wird_beim_lesen_abgebrochen(netz):
    gelesen = {"bloecke": 0}

    async def bloecke():
        for _ in range(_MAX_UPLOAD_BYTES // (1 << 20) + 5):
            gelesen["bloecke"] += 1
            yield b"x" * (1 << 20)

    netz(lambda request: httpx.Response(200, headers={"content-type": "image/png"}, content=bloecke()))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="zu groß"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig()))
    # abgebrochen kurz hinter der Kappe, nicht alles gelesen
    assert gelesen["bloecke"] <= _MAX_UPLOAD_BYTES // (1 << 20) + 2


@pytest.mark.parametrize("daten", [b"kein bild", b"GIF89a" + b"\x00" * 20])
def test_kein_erlaubtes_bildformat(daten):
    with pytest.raises(fremdbild_abruf.AbrufFehler):
        fremdbild_abruf.bild_endung(daten)


# ── Die Tür: auth-freier Spiegel-Pfad ───────────────────────────────────────

def test_spiegel_liefert_bild_ohne_anmeldung_und_holt_nur_einmal(anon_client, netz, png_bytes):
    url = _eindeutig()
    aufgezeichnet = netz(_bild(png_bytes))
    pfad = bild_spiegel.spiegel_pfad(url)
    for _ in range(2):
        r = anon_client.get(pfad)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "image/png"
        assert r.headers["x-content-type-options"] == "nosniff"
        assert "immutable" in r.headers["cache-control"]
        assert r.content == png_bytes
    assert aufgezeichnet["anfragen"] == [url]            # zweiter Abruf aus der Ablage


def test_spiegel_ohne_gueltige_signatur_ruft_nichts_ab(anon_client, netz, png_bytes):
    aufgezeichnet = netz(_bild(png_bytes))
    _, signatur, kodiert = bild_spiegel.spiegel_pfad(_eindeutig()).rsplit("/", 2)
    gekippt = ("0" if signatur[0] != "0" else "1") + signatur[1:]
    for pfad in (
        f"{bild_spiegel.PRAEFIX}/{gekippt}/{kodiert}",
        f"{bild_spiegel.PRAEFIX}/{'0' * 32}/{kodiert}",
        f"{bild_spiegel.PRAEFIX}/kaputt/{kodiert}",
    ):
        r = anon_client.get(pfad)
        assert r.status_code == 404, pfad
    assert aufgezeichnet["anfragen"] == []


def test_spiegel_fehlschlag_beim_host_ist_404_und_legt_nichts_ab(anon_client, netz):
    url = _eindeutig()
    netz(lambda request: httpx.Response(500))
    assert anon_client.get(bild_spiegel.spiegel_pfad(url)).status_code == 404
    name = bild_spiegel.hashlib.sha256(url.encode()).hexdigest()
    assert list(bild_spiegel._ablage(url, ".png").parent.glob(f"{name}*")) == []


def test_spiegel_legt_kaputtes_bild_nicht_ab(anon_client, netz):
    url = _eindeutig()
    netz(_bild(b"kein bild"))
    assert anon_client.get(bild_spiegel.spiegel_pfad(url)).status_code == 404
    name = bild_spiegel.hashlib.sha256(url.encode()).hexdigest()
    ablage = bild_spiegel._ablage(url, ".png").parent
    assert [p for p in ablage.glob(f"{name}*")] == []


def test_pokedex_platzhalter_nach_fester_vorlage(anon_client, netz, png_bytes):
    aufgezeichnet = netz(_bild(png_bytes))
    # 1024 wählt eine Nummer, die kein anderer Test anfragt (Ablage lebt über die Sitzung)
    r = anon_client.get(f"{bild_spiegel.PRAEFIX}/pokedex/1024.png")
    assert r.status_code == 200, r.text
    assert aufgezeichnet["anfragen"] == [
        "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/1024.png"]
    assert bild_spiegel.pokedex_url(7) == (
        "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/007.png")


@pytest.mark.parametrize("nr", ["0", "1026", "99999", "abc", "-1", "1e3", "25.5"])
def test_pokedex_ausserhalb_der_vorlage_ruft_nichts_ab(anon_client, netz, png_bytes, nr):
    aufgezeichnet = netz(_bild(png_bytes))
    assert anon_client.get(f"{bild_spiegel.PRAEFIX}/pokedex/{nr}.png").status_code == 404
    assert aufgezeichnet["anfragen"] == []


def test_spiegel_pfade_stehen_nicht_im_schema(anon_client):
    pfade = anon_client.get("/openapi.json").json()["paths"]
    assert not [p for p in pfade if p.startswith(bild_spiegel.PRAEFIX)]
