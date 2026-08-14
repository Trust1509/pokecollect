"""
#67: Case-toleranter tcgdex_card_id-Abgleich in Katalog-Grid und Set-Zielen.

Der Scan schreibt TCGdex-IDs klein („me03-029"), der JP-Katalog führt sie groß
(„ME03-029"). Vor dem Fix galt eine scan-erfasste JP-Karte im Katalog als NICHT
besessen und erfüllte kein Set-Ziel — obwohl sie im Bestand liegt.
"""

import pytest

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.models.collection import Collection, CollectionSoll
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services.set_goal import soll_status

_TESTNAME = "Case-Testkarte"
_CID_GROSS = "TEST67-029"     # Katalog-Schreibweise (JP-Sets: groß)
_CID_KLEIN = "test67-029"     # Scan-Schreibweise (klein)


@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(CollectionSoll).filter(
            CollectionSoll.tcgdex_card_id.ilike("test67%")).delete(synchronize_session=False)
        session.query(Collection).filter(
            Collection.name.like("Case67%")).delete(synchronize_session=False)
        session.query(PokemonCard).filter(
            PokemonCard.kartenname == _TESTNAME).delete(synchronize_session=False)
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("test67%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _katalogkarte(db):
    db.add(TcgdexCatalog(card_id=_CID_GROSS, region="ja", set_id="test67",
                         set_code="T67", local_id="029", name="Case-Testkarte"))
    db.commit()


def test_katalog_grid_erkennt_scan_karte_als_besessen(db, client):
    _katalogkarte(db)
    # Karte wie vom Scan committet: ID KLEIN geschrieben
    db.add(PokemonCard(kartenname=_TESTNAME, besessen=True, im_pokedex=True,
                       tcgdex_card_id=_CID_KLEIN))
    db.commit()

    items = client.get("/api/v1/catalog", params={"search": "Case-Testkarte",
                                                  "limit": 50}).json()["items"]
    treffer = next(i for i in items if i["card_id"] == _CID_GROSS)
    assert treffer["owned"] is True        # vor dem Fix: False
    assert treffer["in_pokedex"] is True


def test_katalog_detail_erkennt_scan_karte_als_besessen(db, client):
    _katalogkarte(db)
    db.add(PokemonCard(kartenname=_TESTNAME, besessen=True,
                       tcgdex_card_id=_CID_KLEIN))
    db.commit()

    body = client.get(f"/api/v1/catalog/{_CID_GROSS}/detail").json()
    assert body["owned"] is True


def test_set_ziel_wird_von_scan_karte_erfuellt(db):
    _katalogkarte(db)
    coll = Collection(name="Case67-Ziel", typ="set_ziel", ziel_set_id="test67")
    db.add(coll)
    db.flush()
    db.add(CollectionSoll(collection_id=coll.id, tcgdex_card_id=_CID_GROSS))
    db.add(PokemonCard(kartenname=_TESTNAME, besessen=True,
                       tcgdex_card_id=_CID_KLEIN))
    db.commit()

    status = soll_status(db, coll)
    assert len(status) == 1
    assert status[0]["erfuellt"] is True   # vor dem Fix: False


def test_gegenrichtung_katalog_klein_karte_gross(db, client):
    """Auch andersherum (Katalog klein, Karte groß) muss es treffen."""
    db.add(TcgdexCatalog(card_id="test67-gegen", region="west", set_id="test67",
                         name="Case-Testkarte"))
    db.add(PokemonCard(kartenname=_TESTNAME, besessen=True,
                       tcgdex_card_id="TEST67-GEGEN"))
    db.commit()

    body = client.get("/api/v1/catalog/test67-gegen/detail").json()
    assert body["owned"] is True


def test_fremde_karte_bleibt_unbesessen(db, client):
    """Kein Über-Matching: eine andere Karte darf nicht als besessen gelten."""
    _katalogkarte(db)
    db.add(PokemonCard(kartenname=_TESTNAME, besessen=True,
                       tcgdex_card_id="test67-999"))
    db.commit()

    body = client.get(f"/api/v1/catalog/{_CID_GROSS}/detail").json()
    assert body["owned"] is False
