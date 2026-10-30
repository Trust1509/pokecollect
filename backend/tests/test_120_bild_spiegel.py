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


@pytest.fixture(autouse=True)
def frischer_zustand(monkeypatch):
    """Fehlschlag-Speicher und Locks gelten je Prozess — jeder Test fängt leer an."""
    monkeypatch.setattr(bild_spiegel, "_fehlschlaege", {})
    monkeypatch.setattr(bild_spiegel, "_locks", {})


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


def _keine_ablage(url: str) -> None:
    """Weder eine Datei noch ein TMP-Rest zur Quelle — gesucht über den
    Stamm des echten Ablage-Namens (Blindprüfer #120: die frühere Suche nach
    sha256(url) fand nach dem Umstieg auf HMAC nie etwas und prüfte nichts)."""
    stamm = bild_spiegel._ablage(url, "").name
    ordner = bild_spiegel._ablage(url, "").parent
    reste = sorted(p.name for p in ordner.glob("*") if p.name.startswith(stamm)) if ordner.exists() else []
    assert reste == []


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
    "https://evil-assets.tcgdex.net/x.webp",                 # Host als Endung
    "https://sub.assets.tcgdex.net/x.webp",                  # Unterdomain
    "https://evil-tcgplayer-cdn.tcgplayer.com/x.jpg",        # dito
    "https://www.pokemon.com/static-assetsX/x.png",          # Pfad-Präfix ohne Schrägstrich
    "https://pokemon.com/static-assets/x.png",               # ohne www
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
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))
    assert len(aufgezeichnet["anfragen"]) == 1          # das Ziel wurde nie abgerufen
    optionen = aufgezeichnet["optionen"][0]
    assert optionen["follow_redirects"] is False
    assert optionen["timeout"] == 10.0
    assert optionen["headers"]["Accept-Encoding"] == "identity"


@pytest.mark.parametrize("kopf", [{}, {"content-type": "text/html"}])
def test_ohne_bild_content_type_kein_bild(netz, png_bytes, kopf):
    netz(lambda request: httpx.Response(200, headers=kopf, content=png_bytes))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="Content-Type"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))


def test_zu_grosser_kopf_wird_vor_dem_lesen_abgelehnt(netz):
    netz(lambda request: httpx.Response(
        200, headers={"content-type": "image/png", "content-length": str(_MAX_UPLOAD_BYTES + 1)},
        content=b"x"))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="laut Kopf"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))


def test_zu_grosser_stream_ohne_kopf_wird_beim_lesen_abgebrochen(netz):
    gelesen = {"bloecke": 0}

    async def bloecke():
        for _ in range(_MAX_UPLOAD_BYTES // (1 << 20) + 5):
            gelesen["bloecke"] += 1
            yield b"x" * (1 << 20)

    netz(lambda request: httpx.Response(200, headers={"content-type": "image/png"}, content=bloecke()))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="zu groß"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))
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
        assert r.headers["cache-control"] == "public, max-age=604800"
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
    _keine_ablage(url)


def test_spiegel_legt_kaputtes_bild_nicht_ab(anon_client, netz):
    url = _eindeutig()
    netz(_bild(b"kein bild"))
    assert anon_client.get(bild_spiegel.spiegel_pfad(url)).status_code == 404
    _keine_ablage(url)


def test_platzhalter_kommt_signiert_aus_der_karte():
    karte = CardResponse(id=1, kartenname="Testkarte", pokedex_nr=7).model_dump()
    assert karte["bild_platzhalter_spiegel"] == bild_spiegel.spiegel_pfad(
        "https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/007.png")
    for nr in (None, 0, 1026):
        assert CardResponse(id=1, kartenname="Testkarte", pokedex_nr=nr).model_dump()[
            "bild_platzhalter_spiegel"] is None
    assert bild_spiegel.pokedex_url(1025).endswith("/full/1025.png")


@pytest.mark.parametrize("pfad", [
    "/bild-spiegel/pokedex/025.png", "/bild-spiegel/pokedex/25.png", "/bild-spiegel/pokedex/0.png",
])
def test_kein_unsignierter_pfad(anon_client, netz, png_bytes, pfad):
    """Panel #120 (Fremdprüfer): eine unsignierte Pokédex-Vorlage ließ
    Unangemeldete Abrufe auslösen — es gibt keinen unsignierten Pfad mehr."""
    aufgezeichnet = netz(_bild(png_bytes))
    assert anon_client.get(pfad).status_code == 404
    assert aufgezeichnet["anfragen"] == []


def test_nicht_kanonische_kodierung_wird_abgelehnt():
    """Base64 hat für dieselben Bytes mehrere Schreibweisen (Blindprüfer #120)."""
    # 28 Bytes: 28 mod 3 = 1 → zwei Base64-Zeichen am Ende, vier Bits davon ungenutzt
    url = "https://assets.tcgdex.net/ab"
    _, signatur, kodiert = bild_spiegel.spiegel_pfad(url).rsplit("/", 2)
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    varianten = [kodiert[:-1] + z for z in alphabet if z != kodiert[-1]]
    gleich = [v for v in varianten
              if bild_spiegel.base64.urlsafe_b64decode(v + "=" * (-len(v) % 4)) == url.encode()]
    assert gleich, "Probe trifft keine gleichwertige Schreibweise — Fixture prüfen"
    for v in gleich:
        assert bild_spiegel.url_aus_pfad(signatur, v) is None
    assert bild_spiegel.url_aus_pfad(signatur, kodiert) == url


def test_schluessel_ist_nicht_das_jwt_geheimnis():
    # Das JWT-Geheimnis signiert Anmeldungen — derselbe Schlüssel für einen
    # zweiten Zweck ist verboten, abgeleitet ist Pflicht.
    assert bild_spiegel._schluessel() != bild_spiegel.settings.jwt_secret.encode()
    assert len(bild_spiegel._schluessel()) == 32
    url = TCGDEX
    roh = bild_spiegel.hmac.new(bild_spiegel.settings.jwt_secret.encode(), url.encode(),
                                bild_spiegel.hashlib.sha256).hexdigest()
    signatur = bild_spiegel._signatur(url)
    assert signatur not in roh
    assert len(set(signatur[i:i + 8] for i in range(0, 32, 8))) == 4   # keine Wiederholung eines kurzen Kerns


def test_ablage_name_ist_nicht_aus_der_quelle_ableitbar(anon_client, netz, png_bytes):
    """Blindprüfer #120: mit sha256(url) als Name konnte jeder unter
    /images/spiegel/ nachsehen, ob ein Bild je angezeigt wurde."""
    url = _eindeutig()
    netz(_bild(png_bytes))
    assert anon_client.get(bild_spiegel.spiegel_pfad(url)).status_code == 200
    roh = bild_spiegel.hashlib.sha256(url.encode()).hexdigest()
    assert anon_client.get(f"/images/spiegel/{roh}.png").status_code == 404
    assert bild_spiegel._ablage(url, ".png").is_file()
    name = bild_spiegel._ablage(url, "").name
    # keine schlüssellose Ableitung der Quelle …
    for algo in ("md5", "sha1", "sha224", "sha256", "sha384", "sha512", "blake2b", "blake2s", "sha3_256"):
        assert name != bild_spiegel.hashlib.new(algo, url.encode()).hexdigest(), algo
    # … nicht die (öffentliche) Signatur und nicht mit ihr verwandt …
    signatur = bild_spiegel._signatur(url)
    assert signatur not in name and name[:16] != signatur[:16]
    # … und hängt am Geheimnis
    alt = name
    bild_spiegel.settings.jwt_secret, vorher = "ein-anderes-geheimnis", bild_spiegel.settings.jwt_secret
    try:
        assert bild_spiegel._ablage(url, "").name != alt
    finally:
        bild_spiegel.settings.jwt_secret = vorher


@pytest.mark.parametrize("fmt,typ,endung", [("WEBP", "image/webp", ".webp"), ("JPEG", "image/jpeg", ".jpg"),
                                             ("PNG", "image/png", ".png")])
def test_jedes_format_mit_richtigem_typ_und_aus_der_ablage(anon_client, netz, fmt, typ, endung):
    import io

    from PIL import Image

    puffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(1, 2, 3)).save(puffer, format=fmt)
    daten = puffer.getvalue()
    url = _eindeutig()
    aufgezeichnet = netz(_bild(daten, "image/irgendwas"))
    for _ in range(2):
        r = anon_client.get(bild_spiegel.spiegel_pfad(url))
        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == typ          # nach dem echten Format, nicht nach dem Kopf
    assert aufgezeichnet["anfragen"] == [url]
    assert bild_spiegel._ablage(url, endung).is_file()


def test_gif_ist_kein_erlaubtes_format():
    import io

    from PIL import Image

    puffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(puffer, format="GIF")
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="Bildformat"):
        fremdbild_abruf.bild_endung(puffer.getvalue())


def test_abgeschnittenes_png_ist_kein_bild(png_bytes):
    """Kopf ist PNG, Rest fehlt — nur verify() bemerkt das (Gegenprüfer #120)."""
    with pytest.raises(fremdbild_abruf.AbrufFehler):
        fremdbild_abruf.bild_endung(png_bytes[:-20])


def test_schreibfehler_hinterlaesst_keine_halbe_datei(anon_client, netz, monkeypatch, png_bytes):
    """Gegenprüfer #120: Schriebe der Spiegel direkt in die Zieldatei, läge
    nach einem Schreibfehler eine halbe Datei dort und würde danach als
    Treffer ausgeliefert."""
    url = _eindeutig()
    aufgezeichnet = netz(_bild(png_bytes))
    echt = bild_spiegel.Path.write_bytes

    def halb(self, daten):
        echt(self, daten[: len(daten) // 2])
        raise OSError("Platte voll")

    monkeypatch.setattr(bild_spiegel.Path, "write_bytes", halb)
    assert asyncio.run(bild_spiegel.datei_fuer(url)) is None
    monkeypatch.setattr(bild_spiegel.Path, "write_bytes", echt)
    monkeypatch.setattr(bild_spiegel, "_FEHLSCHLAG_SEKUNDEN", 0.0)
    datei = asyncio.run(bild_spiegel.datei_fuer(url))
    assert datei is not None and datei.read_bytes() == png_bytes
    assert len(aufgezeichnet["anfragen"]) == 2       # zweiter Versuch holt neu, kein halber Treffer


def test_gleichzeitige_anfragen_holen_einmal(netz, png_bytes):
    """Blindprüfer #120: 50 gleichzeitige Anfragen ergaben 50 Abrufe."""
    url = _eindeutig()

    async def langsam(request):
        await asyncio.sleep(0.05)
        return _bild(png_bytes)(request)

    aufgezeichnet = netz(lambda request: langsam(request))

    async def viele():
        return await asyncio.gather(*(bild_spiegel.datei_fuer(url) for _ in range(20)))

    ergebnisse = asyncio.run(viele())
    assert len(set(ergebnisse)) == 1 and ergebnisse[0] is not None
    assert aufgezeichnet["anfragen"] == [url]


def test_ein_langsamer_host_haelt_andere_quellen_nicht_auf(netz, png_bytes):
    """Je Quelle ein Lock, kein globales (Blindprüfer NA1 #120)."""
    langsam_url, schnell_url = _eindeutig(), _eindeutig()
    reihenfolge: list[str] = []

    async def antwort(request):
        if str(request.url) == langsam_url:
            await asyncio.sleep(0.3)
        reihenfolge.append(str(request.url))
        return _bild(png_bytes)(request)

    netz(lambda request: antwort(request))

    async def beide():
        langsam = asyncio.create_task(bild_spiegel.datei_fuer(langsam_url))
        await asyncio.sleep(0.05)
        await bild_spiegel.datei_fuer(schnell_url)
        await langsam

    asyncio.run(beide())
    assert reihenfolge == [schnell_url, langsam_url]


def test_kaputtes_bild_zaehlt_als_fehlschlag(anon_client, netz):
    url = _eindeutig()
    aufgezeichnet = netz(_bild(b"kein bild"))
    for _ in range(3):
        assert anon_client.get(bild_spiegel.spiegel_pfad(url)).status_code == 404
    assert aufgezeichnet["anfragen"] == [url]


def test_fehlschlag_frist_und_speicher_sind_begrenzt():
    assert bild_spiegel._FEHLSCHLAG_SEKUNDEN >= 300
    for i in range(bild_spiegel._FEHLSCHLAG_MAX_EINTRAEGE + 50):
        bild_spiegel._fehlschlag_merken(f"https://assets.tcgdex.net/x/{i}")
    assert len(bild_spiegel._fehlschlaege) <= bild_spiegel._FEHLSCHLAG_MAX_EINTRAEGE


def test_fehlschlag_wird_eine_weile_nicht_wiederholt(anon_client, netz, monkeypatch, png_bytes):
    url = _eindeutig()
    antworten = {"status": 500}
    aufgezeichnet = netz(lambda request: httpx.Response(antworten["status"])
                         if antworten["status"] != 200 else _bild(png_bytes)(request))
    pfad = bild_spiegel.spiegel_pfad(url)
    for _ in range(3):
        assert anon_client.get(pfad).status_code == 404
    assert aufgezeichnet["anfragen"] == [url]
    # nach Ablauf der Frist wird es wieder versucht
    antworten["status"] = 200
    monkeypatch.setattr(bild_spiegel, "_FEHLSCHLAG_SEKUNDEN", 0.0)
    assert anon_client.get(pfad).status_code == 200
    assert aufgezeichnet["anfragen"] == [url, url]


def test_tmp_datei_wird_bei_fehler_nach_dem_schreiben_entfernt(netz, monkeypatch, png_bytes):
    url = _eindeutig()
    netz(_bild(png_bytes))

    def kaputt(quelle, ziel):
        raise OSError("Platte voll")

    monkeypatch.setattr(bild_spiegel.os, "replace", kaputt)
    assert asyncio.run(bild_spiegel.datei_fuer(url)) is None
    name = bild_spiegel._ablage(url, ".png").name
    assert list(bild_spiegel._ablage(url, ".png").parent.glob(f"{name}*")) == []


def test_bild_holen_prueft_den_host_selbst(netz, png_bytes):
    """Fremdprüfer #120: das Host-Urteil ist Pflicht-Argument der gemeinsamen
    Routine — kein Aufrufer kann es vergessen."""
    aufgezeichnet = netz(_bild(png_bytes))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="nicht erlaubt"):
        asyncio.run(fremdbild_abruf.bild_holen("http://169.254.169.254/x.png",
                                               erlaubt=bild_spiegel.ist_spiegelbar))
    with pytest.raises(TypeError):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig()))   # ohne Urteil kein Aufruf
    assert aufgezeichnet["anfragen"] == []


@pytest.mark.parametrize("status", [201, 203, 204, 206])
def test_nur_200_gilt(netz, png_bytes, status):
    netz(lambda request: httpx.Response(status, headers={"content-type": "image/png"}, content=png_bytes))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match=str(status)):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))


def test_genau_die_kappe_ist_erlaubt(netz):
    netz(lambda request: httpx.Response(200, headers={"content-type": "image/png"},
                                        content=b"x" * _MAX_UPLOAD_BYTES))
    daten = asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))
    assert len(daten) == _MAX_UPLOAD_BYTES


def test_ein_byte_ueber_der_kappe_ohne_kopf_ist_zu_gross(netz):
    async def bloecke():
        yield b"x" * _MAX_UPLOAD_BYTES
        yield b"x"

    netz(lambda request: httpx.Response(200, headers={"content-type": "image/png"}, content=bloecke()))
    with pytest.raises(fremdbild_abruf.AbrufFehler, match="zu groß"):
        asyncio.run(fremdbild_abruf.bild_holen(_eindeutig(), erlaubt=bild_spiegel.ist_spiegelbar))


def test_spiegel_pfade_stehen_nicht_im_schema(anon_client):
    pfade = anon_client.get("/openapi.json").json()["paths"]
    assert not [p for p in pfade if p.startswith(bild_spiegel.PRAEFIX)]


def test_backup_laesst_die_spiegel_ablage_aus(client, netz, png_bytes):
    """Blindprüfer NA1 #120: die Ablage wuchs ungedeckelt ins Backup-ZIP —
    sie ist Zwischenspeicher, kein Bestand."""
    import io
    import zipfile

    url = _eindeutig()
    netz(_bild(png_bytes))
    assert asyncio.run(bild_spiegel.datei_fuer(url)) is not None
    r = client.get("/api/v1/data/backup")
    assert r.status_code == 200
    namen = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "data.json" in namen
    assert not [n for n in namen if n.startswith(f"images/{bild_spiegel.UNTERORDNER}/")]
