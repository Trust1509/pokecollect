"""
#43 (Epic #41, Slice 2): Lokaler Bild-Cache für den Katalog.

Drei Stufen (Setting catalog_image_cache_level): "urls" (Default, nur externe
URLs) | "owned" (besessene + wunschgelistete Karten lokal) | "all" (ganzer
Katalog). Ein Nachtlauf-Schritt (services/cron.py, NACH dem €-Repass) füllt
den Cache gemäß Stufe in Etappen; das Detail-Popup cached zusätzlich
on-demand. Antworten liefern bei vorhandenem, tatsächlich existierendem Cache
den lokalen Pfad statt der CDN-URL (services/catalog_images.py).

Netzfrei: `catalog_images._fetch_image_bytes` gemockt (wie tcgdex.get_card in
test_66/test_75). URLs nur auf dem echten erlaubten Host `assets.tcgdex.net`
erfunden (tcgdex.ALLOWED_IMAGE_HOSTS).
"""

import asyncio
import io
import json
import zipfile
from pathlib import Path

import pytest
from sqlalchemy import insert, text

from app.config import settings
from app.database import SessionLocal
from app.main import _run_light_migrations
from app.models.card import PokemonCard
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog_images

_ALLOWED_HOST = "assets.tcgdex.net"


def _url(suffix: str) -> str:
    """Erfundene, aber echte-Host-URL (tcgdex.ALLOWED_IMAGE_HOSTS)."""
    return f"https://{_ALLOWED_HOST}/en/test43-{suffix}/high.webp"


@pytest.fixture()
def db(client):
    """Muster wie test_66/test_75: eigene Sitzung + Aufräumen von DB-Zeilen
    UND evtl. geschriebenen Bilddateien (Wegwerf-images_dir, aber sauber)."""
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("test43%")).delete(synchronize_session=False)
        session.query(PokemonCard).filter(
            PokemonCard.kartenname.ilike("Test43%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()
    catalog_dir = Path(settings.images_dir) / catalog_images.CATALOG_SUBDIR
    if catalog_dir.is_dir():
        for p in catalog_dir.glob("*test43*"):
            p.unlink(missing_ok=True)


@pytest.fixture()
def cache_stufe(client):
    """Setzt die Bildcache-Stufe über den echten Endpunkt (übt die
    Validierung mit aus) und stellt am Ende IMMER den Default wieder her —
    Muster wie test_55::test_settings_grenzen_schuetzen_die_kartenliste."""
    def _set(value: str):
        r = client.put("/api/v1/settings", json={"catalog_image_cache_level": value})
        assert r.status_code == 200, r.text
    yield _set
    _set("urls")


def _zeile(db, cid, *, region="west", image_url=None, image_pfad=None):
    row = TcgdexCatalog(card_id=cid, region=region, set_id="test43set",
                        set_code="T43", local_id="1",
                        image_url=image_url, image_pfad=image_pfad)
    db.add(row)
    return row


# ═══════════════════════════════════════════════════════════════════════════
# 1) Migration: additiv, Erhalt + Idempotenz (Muster test_66)
# ═══════════════════════════════════════════════════════════════════════════

def test_migration_fuegt_image_pfad_hinzu_additiv_und_idempotent(db):
    db.execute(insert(TcgdexCatalog).values(
        card_id="test43-migration", region="west", set_id="test43set",
        set_code="T43", local_id="1",
        image_url="https://assets.tcgdex.net/en/test43-mig/high.webp",
    ))
    db.commit()
    db.rollback()  # nichts offen lassen — Migration braucht exklusive Locks (Lehre)

    db.execute(text("ALTER TABLE tcgdex_catalog DROP COLUMN IF EXISTS image_pfad"))
    db.commit()  # sofort schließen, sonst blockiert die eigene DDL die folgende (Lehre)

    _run_light_migrations()  # idempotent, läuft sonst beim App-Start

    db.expire_all()
    migrated = db.get(TcgdexCatalog, "test43-migration")
    assert migrated.image_url == "https://assets.tcgdex.net/en/test43-mig/high.webp"  # Altdaten erhalten
    assert migrated.image_pfad is None  # neue Spalte: NULL für Bestandszeilen

    # zweiter Lauf ändert nichts (Idempotenz); db.get() oben hat als erster
    # Zugriff nach dem rollback still eine neue Transaktion eröffnet — ohne
    # diesen zweiten rollback blockiert sie die ALTERs des zweiten Laufs (Lehre).
    db.rollback()
    _run_light_migrations()
    db.expire_all()
    again = db.get(TcgdexCatalog, "test43-migration")
    assert again.image_url == "https://assets.tcgdex.net/en/test43-mig/high.webp"
    assert again.image_pfad is None


# ═══════════════════════════════════════════════════════════════════════════
# 2) Stufen-Validierung
# ═══════════════════════════════════════════════════════════════════════════

def test_bild_cache_stufe_lehnt_unsinn_ab(client, cache_stufe):
    for bad in ("murks", "URLS", "", "1", "Owned"):
        r = client.put("/api/v1/settings", json={"catalog_image_cache_level": bad})
        assert r.status_code == 422, f"{bad!r} haette 422 liefern muessen: {r.text}"


def test_bild_cache_stufe_akzeptiert_die_drei_werte(client, cache_stufe):
    for good in ("urls", "owned", "all"):
        r = client.put("/api/v1/settings", json={"catalog_image_cache_level": good})
        assert r.status_code == 200, r.text
        assert r.json()["catalog_image_cache_level"] == good
        assert client.get("/api/v1/settings").json()["catalog_image_cache_level"] == good


# ═══════════════════════════════════════════════════════════════════════════
# 3) Auswahl-Helfer (reine Funktion, kein DB-Zugriff)
# ═══════════════════════════════════════════════════════════════════════════

def test_resolve_ohne_pfad_liefert_cdn():
    assert catalog_images.resolve_catalog_image_url(None, _url("x"), "http://api/") == _url("x")


def test_resolve_mit_pfad_und_datei_liefert_lokale_url():
    cid = "test43-resolve-lokal"
    dest = catalog_images.catalog_image_disk_path(cid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(b"irrelevant-fuer-diesen-test")
    try:
        pfad = catalog_images.catalog_image_db_pfad(cid)
        got = catalog_images.resolve_catalog_image_url(pfad, _url("resolve"), "http://api/")
        assert got == f"http://api/images/catalog/{catalog_images.safe_catalog_filename(cid)}.webp"
        assert got != _url("resolve")
    finally:
        dest.unlink(missing_ok=True)


def test_resolve_pfad_gesetzt_datei_fehlt_liefert_cdn():
    cid = "test43-resolve-fehlend"
    pfad = catalog_images.catalog_image_db_pfad(cid)  # Pfad berechnet, Datei NIE angelegt
    got = catalog_images.resolve_catalog_image_url(pfad, _url("fehlend"), "http://api/")
    assert got == _url("fehlend")  # kein 404 ins Grid — CDN statt totem lokalem Link


# ═══════════════════════════════════════════════════════════════════════════
# 4) Sanitisierung / Traversal (card_id -> Dateiname)
# ═══════════════════════════════════════════════════════════════════════════

def test_safe_catalog_filename_entfernt_pfadtrenner():
    dirty = "../../etc/passwd"
    clean = catalog_images.safe_catalog_filename(dirty)
    assert "/" not in clean and "\\" not in clean


def test_catalog_image_disk_path_bleibt_unter_images_dir_bei_boesartiger_id():
    media_root = Path(settings.images_dir).resolve()
    for boese_id in ("../../etc/passwd", "..\\..\\windows\\system32", "a/b/../../c", "...."):
        disk = catalog_images.catalog_image_disk_path(boese_id).resolve()
        assert disk.is_relative_to(media_root), boese_id
        assert disk.parent == media_root / catalog_images.CATALOG_SUBDIR, boese_id


# ═══════════════════════════════════════════════════════════════════════════
# 5) download_one() — Einzel-Download, Validierung, Fehlschläge
# ═══════════════════════════════════════════════════════════════════════════

def test_download_one_erfolg_setzt_image_pfad(db, monkeypatch, png_bytes):
    row = _zeile(db, "test43-dl-ok", image_url=_url("ok"))
    db.commit()

    async def fake_bytes(url):
        assert url == _url("ok")
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    ok = asyncio.run(catalog_images.download_one(db, row))
    assert ok is True
    db.expire_all()
    reloaded = db.get(TcgdexCatalog, "test43-dl-ok")
    assert reloaded.image_pfad is not None
    disk = catalog_images.catalog_image_disk_path("test43-dl-ok")
    assert disk.is_file()
    assert disk.read_bytes() == png_bytes


def test_download_one_netzfehler_liefert_false_ohne_image_pfad(db, monkeypatch):
    row = _zeile(db, "test43-dl-netz", image_url=_url("netz"))
    db.commit()

    async def fake_bytes(url):
        raise RuntimeError("Verbindung abgebrochen")
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    ok = asyncio.run(catalog_images.download_one(db, row))
    assert ok is False
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-dl-netz").image_pfad is None
    assert not catalog_images.catalog_image_disk_path("test43-dl-netz").exists()


def test_download_one_kaputtes_bild_wird_verworfen(db, monkeypatch):
    row = _zeile(db, "test43-dl-kaputt", image_url=_url("kaputt"))
    db.commit()

    async def fake_bytes(url):
        return b"das-ist-kein-bild"
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    ok = asyncio.run(catalog_images.download_one(db, row))
    assert ok is False
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-dl-kaputt").image_pfad is None
    # Datei darf NICHT liegen bleiben (sonst später öffentlich unter /images erreichbar)
    assert not catalog_images.catalog_image_disk_path("test43-dl-kaputt").exists()


def test_download_one_verbotener_host_ruft_gar_nicht_erst_ab(db, monkeypatch, png_bytes):
    """WICHTIG: der Fake liefert bei Aufruf ein GÜLTIGES Bild statt zu werfen
    — download_one fängt jeden Fehler ab und läge bei einem werfenden Fake
    auch dann bei ok=False, wenn die Host-Prüfung fehlte (dieselbe Falle wie
    bei on-demand/Stufe "owned"). Nur ein erfolgreicher Fake unterscheidet
    "Host korrekt abgewiesen" von "Host-Prüfung kaputt, Abruf versucht"."""
    row = _zeile(db, "test43-dl-fremdhost", image_url="https://evil.example.com/x.webp")
    db.commit()

    async def fake_bytes(url):
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    ok = asyncio.run(catalog_images.download_one(db, row))
    assert ok is False
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-dl-fremdhost").image_pfad is None


def test_download_one_ohne_cdn_url_liefert_false(db):
    row = _zeile(db, "test43-dl-leer", image_url=None)
    db.commit()
    assert asyncio.run(catalog_images.download_one(db, row)) is False


# ═══════════════════════════════════════════════════════════════════════════
# 6) run_catalog_image_cache() — Nachtlauf-Etappe
# ═══════════════════════════════════════════════════════════════════════════

def test_stufe_urls_laedt_gar_nichts(db, monkeypatch, cache_stufe):
    cache_stufe("urls")
    _zeile(db, "test43-batch-urls", image_url=_url("batch-urls"))
    db.commit()

    async def darf_nicht_aufgerufen_werden(url):
        raise AssertionError("Stufe urls darf nie herunterladen")
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", darf_nicht_aufgerufen_werden)

    stats = asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    assert stats == {"stage": "urls", "loaded": 0, "skipped": 0, "failed": 0}
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-batch-urls").image_pfad is None


def test_stufe_all_laedt_alle_ungecachten(db, monkeypatch, cache_stufe, png_bytes):
    """Grenze dieser Aussage (Rot-Beweis-Fund): "test43-all-schon-da" bleibt
    ungeladen auch dann, wenn NUR der SQL-Filter (image_pfad IS NULL) in
    run_catalog_image_cache entfernt wird — die Schreibschleife prüft
    row.image_pfad ein zweites Mal nach dem Reload und überspringt es
    trotzdem (siehe Kommentar dort). Dieser Test beweist "bereits Gecachtes
    wird nie erneut geladen" als GESAMTAUSSAGE, nicht welche der beiden
    Schichten das im Einzelnen trägt."""
    cache_stufe("all")
    _zeile(db, "test43-all-a", image_url=_url("all-a"))
    _zeile(db, "test43-all-b", image_url=_url("all-b"))
    # bereits gecacht -> muss uebersprungen werden (Vorhandenes nicht neu laden)
    _zeile(db, "test43-all-schon-da", image_url=_url("all-schon-da"),
           image_pfad="sentinel-bereits-gecacht")
    db.commit()

    aufgerufen: list[str] = []

    async def fake_bytes(url):
        aufgerufen.append(url)
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    stats = asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    assert stats["stage"] == "all"
    assert stats["loaded"] == 2
    assert stats["failed"] == 0
    assert _url("all-schon-da") not in aufgerufen  # Vorhandenes wird NICHT neu geladen
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-all-a").image_pfad is not None
    assert db.get(TcgdexCatalog, "test43-all-b").image_pfad is not None
    # unveraendert stehen geblieben (kein Ueberschreiben eines vorhandenen Werts)
    assert db.get(TcgdexCatalog, "test43-all-schon-da").image_pfad == "sentinel-bereits-gecacht"


def test_stufe_owned_laedt_nur_besessene_und_wunschgelistete_case_tolerant(db, monkeypatch, cache_stufe, png_bytes):
    cache_stufe("owned")
    # Katalog GROSS geschrieben (JP-Konvention), Karten-Verknuepfung klein (Scan-Konvention) — #67
    _zeile(db, "TEST43-OWNED-BESESSEN", image_url=_url("owned-besessen"))
    _zeile(db, "TEST43-OWNED-WUNSCH", image_url=_url("owned-wunsch"))
    _zeile(db, "TEST43-OWNED-UNVERKNUEPFT", image_url=_url("owned-unverknuepft"))
    db.add(PokemonCard(kartenname="Test43-Besessen", besessen=True,
                       tcgdex_card_id="test43-owned-besessen"))
    db.add(PokemonCard(kartenname="Test43-Wunsch", besessen=False, wunschliste=True,
                       tcgdex_card_id="test43-owned-wunsch"))
    db.commit()

    async def fake_bytes(url):
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    stats = asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    assert stats["loaded"] == 2
    db.expire_all()
    assert db.get(TcgdexCatalog, "TEST43-OWNED-BESESSEN").image_pfad is not None
    assert db.get(TcgdexCatalog, "TEST43-OWNED-WUNSCH").image_pfad is not None
    # weder besessen noch wunschgelistet -> bleibt bei Stufe "owned" ungecacht
    assert db.get(TcgdexCatalog, "TEST43-OWNED-UNVERKNUEPFT").image_pfad is None


def test_ein_fehlschlag_kippt_den_schwung_nicht(db, monkeypatch, cache_stufe, png_bytes):
    """#75-Klasse: eine kaputte Karte darf die anderen nicht anstecken.

    Grenze dieser Aussage (Rot-Beweis-Fund): dieser Test bleibt GRÜN, selbst
    wenn man das äußere try/except in run_catalog_image_cache komplett
    entfernt — download_one() fängt einen Netzfehler bereits selbst ab (kein
    Raise erreicht die äußere Schleife). Das äußere try/except (inkl.
    db.rollback()) schützt einen ANDEREN, eigenen Fall: einen echten
    DB-Fehler INNERHALB einer Zeile (siehe
    test_db_fehler_einer_zeile_vergiftet_die_folgezeilen_nicht, das dafür
    extra sorgt)."""
    cache_stufe("all")
    _zeile(db, "test43-schwung-a", image_url=_url("schwung-a"))
    _zeile(db, "test43-schwung-kaputt", image_url=_url("schwung-kaputt"))
    _zeile(db, "test43-schwung-b", image_url=_url("schwung-b"))
    db.commit()

    async def fake_bytes(url):
        if url == _url("schwung-kaputt"):
            raise RuntimeError("Netzfehler nur bei dieser einen Karte")
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    stats = asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    assert stats["loaded"] == 2
    assert stats["failed"] == 1
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-schwung-a").image_pfad is not None
    assert db.get(TcgdexCatalog, "test43-schwung-b").image_pfad is not None
    assert db.get(TcgdexCatalog, "test43-schwung-kaputt").image_pfad is None


def test_db_fehler_einer_zeile_vergiftet_die_folgezeilen_nicht(db, monkeypatch, cache_stufe):
    """Rollback-Falle (lehren.md §2): ohne db.rollback() im Fang stuende die
    Session nach dem echten DB-Fehler auf 'aborted' und JEDE FOLGEZEILE
    schluege an InFailedSqlTransaction fehl — deshalb sortieren die card_ids
    absichtlich so, dass die kaputte Zeile VOR mindestens einer gesunden
    verarbeitet wird (ORDER BY card_id in run_catalog_image_cache)."""
    cache_stufe("all")
    _zeile(db, "test43-dbfehler-1-a", image_url=_url("dbfehler-1-a"))
    _zeile(db, "test43-dbfehler-2-kaputt", image_url=_url("dbfehler-2-kaputt"))
    _zeile(db, "test43-dbfehler-3-b", image_url=_url("dbfehler-3-b"))
    db.commit()

    async def fake_download_one(session, row):
        if row.card_id == "test43-dbfehler-2-kaputt":
            session.execute(text("SELECT 1/0"))  # echter DB-Fehler, keine Python-Exception
        row.image_pfad = catalog_images.catalog_image_db_pfad(row.card_id)
        session.commit()
        return True
    monkeypatch.setattr(catalog_images, "download_one", fake_download_one)

    stats = asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    assert stats["loaded"] == 2
    assert stats["failed"] == 1
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-dbfehler-1-a").image_pfad is not None
    # DIESE Zeile kommt NACH der kaputten dran — beweist, dass der rollback()
    # im except-Zweig die Session tatsächlich wieder benutzbar macht.
    assert db.get(TcgdexCatalog, "test43-dbfehler-3-b").image_pfad is not None
    assert db.get(TcgdexCatalog, "test43-dbfehler-2-kaputt").image_pfad is None
    # Session danach wieder normal nutzbar (kein 'aborted' haengen geblieben)
    assert db.execute(text("SELECT 1")).scalar() == 1


def test_loggt_genau_eine_zusammenfassungszeile(db, monkeypatch, cache_stufe, png_bytes, caplog):
    cache_stufe("all")
    _zeile(db, "test43-log-a", image_url=_url("log-a"))
    _zeile(db, "test43-log-b", image_url=_url("log-b"))
    db.commit()

    async def fake_bytes(url):
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    with caplog.at_level("INFO", logger="app.services.catalog_images"):
        asyncio.run(catalog_images.run_catalog_image_cache(db, limit=10))
    zusammenfassungen = [r for r in caplog.records if "Katalog-Bild-Cache" in r.getMessage()
                        and "geladen" in r.getMessage()]
    assert len(zusammenfassungen) == 1, [r.getMessage() for r in caplog.records]


# ═══════════════════════════════════════════════════════════════════════════
# 7) cache_one_on_demand() — Einzel-Cache
# ═══════════════════════════════════════════════════════════════════════════

def test_on_demand_ueberspringt_bereits_gecachte_zeile(db, monkeypatch, cache_stufe, png_bytes):
    """WICHTIG: der Fake liefert bei Aufruf ein GÜLTIGES Bild statt zu werfen —
    ein werfender Fake ließe "sentinel" auch dann unverändert stehen, wenn die
    Bereits-gecacht-Prüfung fehlte (dieselbe Falle wie oben). Nur ein
    erfolgreicher Fake würde "sentinel" sichtbar überschreiben, wenn er
    fälschlich aufgerufen würde."""
    cache_stufe("all")
    _zeile(db, "test43-ondemand-schon-da", image_url=_url("ondemand-schon-da"),
           image_pfad="sentinel")
    db.commit()

    async def fake_bytes(url):
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    asyncio.run(catalog_images.cache_one_on_demand("test43-ondemand-schon-da"))
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-ondemand-schon-da").image_pfad == "sentinel"


def test_on_demand_respektiert_stufe_owned(db, monkeypatch, cache_stufe, png_bytes):
    """WICHTIG: der Fake liefert bei Aufruf ein GÜLTIGES Bild (statt zu werfen)
    — cache_one_on_demand fängt JEDEN Fehler fail-open ab, ein werfender Fake
    würde also selbst bei kaputter Stufenprüfung dieselbe Endlage (image_pfad
    bleibt None) erzeugen und der Test bewiese gar nichts. Nur ein Fake, der
    bei falscher Freigabe tatsächlich einen Pfad setzen WÜRDE, unterscheidet
    "korrekt blockiert" von "Stufenprüfung kaputt"."""
    cache_stufe("owned")
    _zeile(db, "test43-ondemand-unverknuepft", image_url=_url("ondemand-unverknuepft"))
    db.commit()

    async def fake_bytes(url):
        return png_bytes
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    asyncio.run(catalog_images.cache_one_on_demand("test43-ondemand-unverknuepft"))
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-ondemand-unverknuepft").image_pfad is None


def test_on_demand_fehler_wird_verschluckt_nicht_geworfen(db, monkeypatch, cache_stufe):
    """Prüffrage 1: die Schreib-Nebenwirkung darf niemals nach außen dringen.

    Grenze dieser Aussage (Rot-Beweis-Fund): bleibt GRÜN, selbst wenn man das
    äußere try/except in cache_one_on_demand komplett entfernt — download_one()
    fängt den hier simulierten Netzfehler bereits selbst ab. Das äußere
    try/except ist zusätzliche Absicherung für Fehler AUSSERHALB von
    download_one() (z. B. in get_setting()/stage_allows()/db.get()), die dieser
    Test nicht einzeln auslöst."""
    cache_stufe("all")
    _zeile(db, "test43-ondemand-fehler", image_url=_url("ondemand-fehler"))
    db.commit()

    async def fake_bytes(url):
        raise RuntimeError("beliebiger Fehler")
    monkeypatch.setattr(catalog_images, "_fetch_image_bytes", fake_bytes)

    asyncio.run(catalog_images.cache_one_on_demand("test43-ondemand-fehler"))  # darf NICHT werfen
    db.expire_all()
    assert db.get(TcgdexCatalog, "test43-ondemand-fehler").image_pfad is None


# ═══════════════════════════════════════════════════════════════════════════
# 8) Naht-Rot-Beweis durch die echte Tür
# ═══════════════════════════════════════════════════════════════════════════

def test_detail_endpunkt_liefert_lokale_url_wenn_pfad_gesetzt_und_datei_da(db, client, png_bytes):
    cid = "test43-detail-lokal"
    cdn_url = _url("detail-lokal")
    row = _zeile(db, cid, image_url=cdn_url)
    db.commit()
    dest = catalog_images.catalog_image_disk_path(cid)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png_bytes)
    try:
        row.image_pfad = catalog_images.catalog_image_db_pfad(cid)
        db.commit()

        body = client.get(f"/api/v1/catalog/{cid}/detail").json()
        assert body["image_url"] is not None
        assert body["image_url"] != cdn_url
        assert body["image_url"].startswith(("http://", "https://"))
        assert body["image_url"].endswith(
            f"images/{catalog_images.CATALOG_SUBDIR}/{catalog_images.safe_catalog_filename(cid)}.webp")
    finally:
        dest.unlink(missing_ok=True)


def test_detail_endpunkt_liefert_cdn_url_ohne_pfad(db, client):
    cid = "test43-detail-cdn"
    cdn_url = _url("detail-cdn")
    _zeile(db, cid, image_url=cdn_url)
    db.commit()
    body = client.get(f"/api/v1/catalog/{cid}/detail").json()
    assert body["image_url"] == cdn_url


def test_on_demand_task_wird_nur_ausserhalb_von_urls_registriert(db, client, monkeypatch, cache_stufe):
    """Naht-Rot-Beweis: die Registrierung selbst (nicht nur ihre Wirkung) hängt
    an der Stufe. Sabotage: die `if stage != "urls":`-Verdrahtung im
    Detail-Endpunkt entfernen -> genau dieser Test fällt."""
    cid = "test43-ondemand-wiring"
    _zeile(db, cid, image_url=_url("ondemand-wiring"))
    db.commit()

    calls: list[str] = []

    async def fake_cache_one(card_id: str):
        calls.append(card_id)
    monkeypatch.setattr(catalog_images, "cache_one_on_demand", fake_cache_one)

    cache_stufe("urls")  # Default: KEIN Task
    assert client.get(f"/api/v1/catalog/{cid}/detail").status_code == 200
    assert calls == []

    cache_stufe("owned")  # != urls: Task WIRD registriert (TestClient führt ihn synchron aus)
    assert client.get(f"/api/v1/catalog/{cid}/detail").status_code == 200
    assert calls == [cid]


# ═══════════════════════════════════════════════════════════════════════════
# 9) Restore-Traversal-Schutz für die neue Spalte (Muster test_security_traversal.py)
# ═══════════════════════════════════════════════════════════════════════════

def _rezip_with_modified_payload(backup_bytes: bytes, payload: dict) -> bytes:
    zin = zipfile.ZipFile(io.BytesIO(backup_bytes))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.writestr("data.json", json.dumps(payload))
        for info in zin.infolist():
            if info.filename != "data.json":
                zout.writestr(info.filename, zin.read(info.filename))
    return buf.getvalue()


def test_restore_neutralisiert_traversal_in_tcgdex_catalog_image_pfad(db, client):
    cid = "test43-restore-traversal"
    _zeile(db, cid, image_url=_url("restore-traversal"))
    db.commit()
    try:
        backup = client.get("/api/v1/data/backup").content
        payload = json.loads(zipfile.ZipFile(io.BytesIO(backup)).read("data.json"))
        hit = False
        for row in payload["tables"]["tcgdex_catalog"]:
            if row["card_id"] == cid:
                row["image_pfad"] = "images/../../../../etc/passwd"  # relativer Ausbruch
                hit = True
        assert hit, "Testzeile nicht im Backup gefunden — Mutation lief ins Leere"

        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("b.zip", _rezip_with_modified_payload(backup, payload), "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text

        db.expire_all()
        restored = db.get(TcgdexCatalog, cid)
        assert restored is not None, "Zeile ist nach dem Restore verschwunden"
        assert restored.image_pfad is None, "Traversal-Pfad wurde ungefiltert in die DB geschrieben"
    finally:
        # Nach einem vollen Restore reicht die db-Fixture-Bereinigung allein
        # nicht (die Session der Fixture ist eine andere) — hier zusätzlich
        # über eine frische Session sicherstellen.
        cleanup = SessionLocal()
        try:
            cleanup.query(TcgdexCatalog).filter(TcgdexCatalog.card_id == cid).delete()
            cleanup.commit()
        finally:
            cleanup.close()
