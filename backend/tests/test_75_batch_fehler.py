"""
#75: Eine kaputte Karte darf einen Batch-Lauf nicht kippen — und ein
gescheiterter Schritt des Nachtlaufs nicht die folgenden.

Befund (am Code verifiziert): `tcgdex.get_card` fängt über `_get_json` zwar
HTTP-Fehler, 404, Nicht-200 und kaputtes JSON ab (alles → None), aber die
Schema-Prüfung `TcgdexCard.model_validate(data)` steht ungeschützt dahinter.
Eine 200-Antwort, die nicht zum Modell passt, wirft — und riss über
`asyncio.gather` den ganzen Schwung mit, BEVOR etwas geschrieben war.

Zweiter Teil: `_daily_catalog_sync` hatte alle Schritte in EINEM try/except.
Scheiterte die Anreicherung, lief der €-Repass (#66) in derselben Nacht gar
nicht mehr — obwohl er mit dem Fehler nichts zu tun hat.

Abgegrenzt: `get_set`/`get_sets` können NICHT werfen (rohes `_get_json` bzw.
try/except je Element), ihre gather-Stellen brauchen also nichts. Der
Einzelabruf in `_build_card_from_catalog` (on-demand beim Übernehmen einer
Karte) liegt außerhalb: Dort ist ein Fehler sichtbar, nicht still.

Netzfrei: `tcgdex.get_card` gemockt.
"""

import asyncio

import pytest

from app.database import SessionLocal
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import cron as cron_svc
from app.services import tcgdex
from app.services.tcgdex import TcgdexCard


@pytest.fixture()
def db(client):
    """Eigene Sitzung + Aufräumen; Muster wie test_66 (kein globales db-Fixture)."""
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("test75%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _rohling(db, card_id: str):
    """Nicht angereicherte Katalogzeile — genau das, was enrich_catalog zieht."""
    db.add(TcgdexCatalog(card_id=card_id, region="west", set_id="test75set",
                         set_code="T75", local_id="1", enriched=False))


def test_eine_kaputte_karte_kippt_die_anreicherung_nicht(db, monkeypatch):
    for cid in ("test75-gut-a", "test75-kaputt", "test75-gut-b"):
        _rohling(db, cid)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        if card_id == "test75-kaputt":
            raise ValueError("schemawidriges 200-JSON")
        return TcgdexCard(id=card_id)

    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    ergebnis = asyncio.run(catalog_svc.enrich_catalog(db, limit=10))

    db.expire_all()
    assert db.get(TcgdexCatalog, "test75-gut-a").enriched is True
    assert db.get(TcgdexCatalog, "test75-gut-b").enriched is True
    # Die kaputte bleibt liegen und wird beim nächsten Lauf erneut versucht —
    # das ist gewollt: Der Fehler kann vorübergehend sein.
    assert db.get(TcgdexCatalog, "test75-kaputt").enriched is False
    assert ergebnis["enriched"] == 2
    # Ohne diese Zahl wäre ein systematischer Schema-Bruch der Quelle
    # unsichtbar — der Lauf meldete brav „0 angereichert" (Klasse: stille Ausfälle).
    assert ergebnis["failed"] == 1


def test_gescheiterter_schritt_stoppt_den_nachtlauf_nicht(db, monkeypatch):
    """Der €-Repass muss laufen, auch wenn die Anreicherung vorher stirbt."""
    gelaufen: list[str] = []

    async def ok(name):
        gelaufen.append(name)

    async def fake_sync_sets():
        await ok("sets")

    async def fake_sync_catalog(_db):
        await ok("basis")

    async def fake_enrich(_db, limit=0):
        gelaufen.append("anreicherung")
        raise RuntimeError("eine kaputte Karte")

    async def fake_repass(_db, limit=0):
        await ok("repass")

    monkeypatch.setattr("app.services.set_sync.sync_sets", fake_sync_sets)
    monkeypatch.setattr(catalog_svc, "sync_catalog", fake_sync_catalog)
    monkeypatch.setattr(catalog_svc, "enrich_catalog", fake_enrich)
    monkeypatch.setattr(catalog_svc, "refresh_catalog_eur", fake_repass)

    asyncio.run(cron_svc._daily_catalog_sync(db))   # darf NICHT werfen

    # Panel-Fund KLEIN: Ohne diese beiden Zusicherungen liessen sich die ersten
    # zwei Schritte ersatzlos aus dem Nachtlauf entfernen, ohne dass ein Test
    # faellt — die Fakes schrieben brav mit, niemand las es.
    assert gelaufen[0] == "sets"
    assert gelaufen[1] == "basis"
    assert "anreicherung" in gelaufen               # der Schritt lief und starb
    assert "repass" in gelaufen                     # und der nächste lief trotzdem
    assert gelaufen.index("repass") > gelaufen.index("anreicherung")


def test_db_fehler_vergiftet_die_folgeschritte_nicht(db, monkeypatch):
    """Panel-Fund BLOCKER: Alle Schritte teilen dieselbe Session. Ohne rollback()
    im Fang steht sie nach einem DB-Fehler auf „aborted", und jeder Folgeschritt
    scheitert an InFailedSqlTransaction — der Fang haelfe dann nur gegen Fehler,
    die die Session gar nicht beruehren."""
    from sqlalchemy import text
    gelaufen: list[str] = []

    async def fake_sync_sets():
        gelaufen.append("sets")

    async def fake_sync_catalog(session):
        gelaufen.append("basis")                     # hier bewusst davor: der Schritt SOLL scheitern
        session.execute(text("SELECT 1/0"))          # echter DB-Fehler

    # WICHTIG: Erst das SQL, DANN anhaengen. Andersherum stuende der Name auch
    # dann in der Liste, wenn die Anweisung scheitert — der Test pruefte dann
    # nur, dass der Schritt AUFGERUFEN wurde, nicht dass er FUNKTIONIERTE.
    async def fake_enrich(session, limit=0):
        session.execute(text("SELECT 1"))            # muss WIEDER gehen
        gelaufen.append("anreicherung")

    async def fake_repass(session, limit=0):
        session.execute(text("SELECT 1"))
        gelaufen.append("repass")

    monkeypatch.setattr("app.services.set_sync.sync_sets", fake_sync_sets)
    monkeypatch.setattr(catalog_svc, "sync_catalog", fake_sync_catalog)
    monkeypatch.setattr(catalog_svc, "enrich_catalog", fake_enrich)
    monkeypatch.setattr(catalog_svc, "refresh_catalog_eur", fake_repass)

    asyncio.run(cron_svc._daily_catalog_sync(db))

    assert gelaufen == ["sets", "basis", "anreicherung", "repass"]


def test_abgebrochener_schritt_wird_nicht_vom_naechsten_mitcommittet(db, monkeypatch):
    """Panel-Fund BLOCKER, zweite Haelfte: Ohne rollback() schreibt das commit()
    des NAECHSTEN Schritts die halbfertige Arbeit des abgebrochenen mit."""
    async def fake_sync_sets():
        pass

    async def fake_sync_catalog(session):
        session.add(TcgdexCatalog(card_id="test75-halbfertig", region="west",
                                  set_id="test75set", set_code="T75",
                                  local_id="9", enriched=False))
        session.flush()                    # in der Session, NICHT committet
        raise RuntimeError("Abbruch mitten drin")

    async def fake_enrich(session, limit=0):
        session.commit()                   # committet, was in der Session liegt

    async def fake_repass(session, limit=0):
        pass

    monkeypatch.setattr("app.services.set_sync.sync_sets", fake_sync_sets)
    monkeypatch.setattr(catalog_svc, "sync_catalog", fake_sync_catalog)
    monkeypatch.setattr(catalog_svc, "enrich_catalog", fake_enrich)
    monkeypatch.setattr(catalog_svc, "refresh_catalog_eur", fake_repass)

    asyncio.run(cron_svc._daily_catalog_sync(db))

    # Unabhaengige Sitzung: liegt die abgebrochene Arbeit in der Datenbank?
    pruef = SessionLocal()
    try:
        assert pruef.get(TcgdexCatalog, "test75-halbfertig") is None
    finally:
        pruef.close()


def test_ohne_frische_sets_wird_die_katalog_basis_uebersprungen(db, monkeypatch):
    """Panel-Fund KLEIN: Scheitern die Sets, schriebe die Katalog-Basis für
    brandneue Sets NULL-Codes in den Katalog — ein halber Zustand, den es vor
    dem Schritt-für-Schritt-Fang nicht gab. Die folgenden Schritte laufen
    trotzdem, sie hängen nicht an den Sets."""
    gelaufen: list[str] = []

    async def fake_sync_sets():
        gelaufen.append("sets")
        raise RuntimeError("Set-Quelle down")

    async def fake_sync_catalog(_db):
        gelaufen.append("basis")

    async def fake_enrich(_db, limit=0):
        gelaufen.append("anreicherung")

    async def fake_repass(_db, limit=0):
        gelaufen.append("repass")

    monkeypatch.setattr("app.services.set_sync.sync_sets", fake_sync_sets)
    monkeypatch.setattr(catalog_svc, "sync_catalog", fake_sync_catalog)
    monkeypatch.setattr(catalog_svc, "enrich_catalog", fake_enrich)
    monkeypatch.setattr(catalog_svc, "refresh_catalog_eur", fake_repass)

    asyncio.run(cron_svc._daily_catalog_sync(db))

    assert "basis" not in gelaufen                  # uebersprungen
    assert gelaufen == ["sets", "anreicherung", "repass"]


def test_leerpfad_liefert_den_fehlzaehler(db, monkeypatch):
    """Panel-Fund KLEIN: Wer `failed` liest, bekam auf dem haeufigsten Pfad
    (nichts anzureichern) einen KeyError."""
    async def nie_aufgerufen(card_id, lang="en"):
        raise AssertionError("darf nicht abrufen, es gibt nichts zu tun")

    monkeypatch.setattr(tcgdex, "get_card", nie_aufgerufen)
    # limit=0 statt die Tabelle leerzuräumen: Der Leerpfad ist derselbe, aber
    # der Test fasst keine fremden Zeilen an (Panel-Fund zur tabellenweiten
    # Kopplung — ein Test, der global löscht, ist eine Mine für jede andere Datei).
    ergebnis = asyncio.run(catalog_svc.enrich_catalog(db, limit=0))
    assert ergebnis == {"enriched": 0, "failed": 0, "remaining": 0}
