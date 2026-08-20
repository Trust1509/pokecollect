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

    assert "anreicherung" in gelaufen               # der Schritt lief und starb
    assert "repass" in gelaufen                     # und der nächste lief trotzdem
    assert gelaufen.index("repass") > gelaufen.index("anreicherung")
