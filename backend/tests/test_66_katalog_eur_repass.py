"""
#66: Der Katalog-€-Preis wurde nur EINMAL geschrieben (bei der Erstanreicherung
in _apply_full/enrich_catalog) und fror danach ein, während der $-Preis
(TCGCSV-Weg) täglich frisch ist. refresh_catalog_eur() ist der rollierende
Repass für bereits angereicherte Zeilen — mit einem EIGENEN Nachsehe-Stempel
(price_eur_checked), NICHT price_eur_updated (das ist der Stand DER QUELLE und
würde bei unveränderten Quellwerten sofort wieder vorne stehen: Hunger-Effekt).

Netzfrei: tcgdex.get_card gemockt (wie test_catalog_detail.py).
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.database import SessionLocal
from app.main import _run_light_migrations
from app.models.tcgdex_catalog import TcgdexCatalog
from app.services import catalog as catalog_svc
from app.services import tcgdex
from app.services.tcgdex import CardMarketPricing, Pricing, TcgdexCard, Variants


@pytest.fixture()
def db(client):
    session = SessionLocal()
    yield session
    try:
        session.rollback()
        session.query(TcgdexCatalog).filter(
            TcgdexCatalog.card_id.ilike("test66%")).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()


def _zeile(db, cid, *, region="west", enriched=True, price_eur_checked=None, **extra):
    row = TcgdexCatalog(card_id=cid, region=region, set_id="test66set",
                        set_code="T66", local_id="1", enriched=enriched,
                        price_eur_checked=price_eur_checked, **extra)
    db.add(row)
    return row


# ── Reihenfolge: NULL-Stempel zuerst, danach ältester zuerst ────────────────

def test_reihenfolge_null_dann_aeltester_zuerst(db, monkeypatch):
    now = datetime.utcnow()
    _zeile(db, "test66-old", price_eur_checked=now - timedelta(days=5))
    _zeile(db, "test66-null", price_eur_checked=None)
    _zeile(db, "test66-new", price_eur_checked=now - timedelta(hours=1))
    _zeile(db, "test66-unenriched", enriched=False, price_eur_checked=None)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        return None  # Quelle irrelevant — dieser Test prüft nur die Auswahl/Reihenfolge
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    # limit=1: nur die NULL-Zeile wurde noch nie geprüft -> ist zuerst dran,
    # vor JEDEM konkreten Stempel (auch dem 5 Tage alten).
    stats = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=1))
    assert stats["visited"] == 1
    db.expire_all()
    assert db.get(TcgdexCatalog, "test66-null").price_eur_checked is not None
    assert db.get(TcgdexCatalog, "test66-old").price_eur_checked == now - timedelta(days=5)  # unberührt
    assert db.get(TcgdexCatalog, "test66-new").price_eur_checked == now - timedelta(hours=1)  # unberührt

    # nächster Lauf (limit=1): NULL ist jetzt "verbraucht" -> der ÄLTESTE
    # konkrete Stempel (-5 Tage) ist dran, nicht der jüngere (-1 Stunde).
    stats2 = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=1))
    assert stats2["visited"] == 1
    db.expire_all()
    old_row = db.get(TcgdexCatalog, "test66-old")
    assert old_row.price_eur_checked > now - timedelta(days=5)   # gerade neu gestempelt
    new_row = db.get(TcgdexCatalog, "test66-new")
    assert new_row.price_eur_checked == now - timedelta(hours=1)  # war noch nicht dran

    # nicht angereicherte Zeile bleibt in jedem Fall außen vor (kein Stempel)
    assert db.get(TcgdexCatalog, "test66-unenriched").price_eur_checked is None


# ── Stempel rückt auch bei leerer/ausgefallener Quelle vor (kein Hunger) ────

def test_stempel_wird_gesetzt_auch_ohne_quellenpreis(db, monkeypatch):
    _zeile(db, "test66-leer", price_eur_checked=None)      # Karte gefunden, aber ohne Pricing
    _zeile(db, "test66-ausfall", price_eur_checked=None)    # Quelle liefert gar nichts (404/Timeout)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        if card_id == "test66-ausfall":
            return None
        return TcgdexCard(id=card_id)  # gefunden, aber kein pricing-Feld
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    stats = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    assert stats["visited"] == 2
    assert stats["updated"] == 0
    db.expire_all()
    for cid in ("test66-leer", "test66-ausfall"):
        row = db.get(TcgdexCatalog, cid)
        assert row.price_eur_checked is not None, cid
        assert row.price_eur is None, cid


# ── Vorhandener Preis wird bei Ausfall NICHT mit None überschrieben ─────────

def test_vorhandener_preis_bleibt_bei_leerer_quelle(db, monkeypatch):
    _zeile(db, "test66-behalten", price_eur_checked=None,
           price_eur=Decimal("3.50"), price_eur_updated="2026-01-01")
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        return None  # Ausfall -> darf den vorhandenen Preis nicht anfassen
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    db.expire_all()
    row = db.get(TcgdexCatalog, "test66-behalten")
    assert row.price_eur == Decimal("3.50")
    assert row.price_eur_updated == "2026-01-01"
    assert row.price_eur_checked is not None  # der Nachsehe-Stempel rückt trotzdem vor


# ── enriched + Nicht-Preis-Felder bleiben unangetastet ──────────────────────

def test_nicht_preis_felder_bleiben_unangetastet(db, monkeypatch):
    _zeile(db, "test66-felder", price_eur_checked=None,
           rarity="Rare", illustrator="Ken Sugimori", category="Pokemon",
           dex_id=25, variants_normal=True)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        # Die (gemockte) Quelle liefert ABWEICHENDE Werte für alles außer den
        # Preis — der Repass darf sie nicht übernehmen (das darf nur
        # enrich_catalog/_apply_full, hier NICHT aufgerufen).
        return TcgdexCard(
            id=card_id, rarity="Common", illustrator="Jemand anders", category="Trainer",
            dexId=[999],
            variants=Variants(normal=False, reverse=True, holo=True, firstEdition=True),
            pricing=Pricing(cardmarket=CardMarketPricing(avg=1.23, updated="2026-08-18")),
        )
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    db.expire_all()
    row = db.get(TcgdexCatalog, "test66-felder")
    assert row.rarity == "Rare"
    assert row.illustrator == "Ken Sugimori"
    assert row.category == "Pokemon"
    assert row.dex_id == 25
    assert row.variants_normal is True
    assert row.enriched is True
    assert row.price_eur == Decimal("1.23")  # der Preis wird sehr wohl übernommen


# ── Kein Hunger-Effekt: zwei Läufe besuchen verschiedene Zeilen ─────────────

def test_zwei_laeufe_besuchen_verschiedene_zeilen(db, monkeypatch):
    for i in range(4):
        _zeile(db, f"test66-h{i}", price_eur_checked=None)
    db.commit()

    visited: list[str] = []

    async def fake_get_card(card_id, lang="en"):
        visited.append(card_id)
        return None
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=2))
    erster_lauf = set(visited)
    visited.clear()
    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=2))
    zweiter_lauf = set(visited)

    assert len(erster_lauf) == 2
    assert len(zweiter_lauf) == 2
    assert erster_lauf.isdisjoint(zweiter_lauf)  # kein Hunger: unterschiedliche Zeilen


# ── Light-Migration: additiv, Erhalt + Idempotenz (Muster test_63_muster.py) ─
#
# Grenze der Aussage (Rot-Beweis-Fund, lehren.md §1): Löscht man die ADD-COLUMN-
# Zeile in main.py ersatzlos, bleibt dieser Test GRÜN — auf der frischen
# Wegwerf-DB der Test-Suite legt Base.metadata.create_all() die Spalte bereits
# aus dem AKTUELLEN Model an, bevor die Light-Migration überhaupt läuft; sie
# betrifft nur echte Bestands-Installationen ohne die Spalte, die dieser Aufbau
# strukturell nicht nachstellen kann (dieselbe Lücke hätte jede rein additive
# Schema-Migration ohne begleitende Daten-Transformation). Was dieser Test WOHL
# beweist: (a) Existenzsicherheit — fehlt „IF NOT EXISTS", crasht schon der
# ERSTE App-Start (DuplicateColumn, weil create_all() die Spalte längst kennt);
# (b) Modell-Korrektheit — bekäme die Spalte im Model einen Python-seitigen
# Default (`default=…` statt bloß `nullable=True`), würde die Assertion unten
# (`price_eur_checked is None` für die unangetastete Bestandszeile) real rot.
def test_migration_fuegt_price_eur_checked_hinzu_additiv_und_idempotent(db):
    row = TcgdexCatalog(card_id="test66-migration", region="west", set_id="test66set",
                        set_code="T66", local_id="1", enriched=True, price_eur=Decimal("2.00"))
    db.add(row)
    db.commit()
    db.rollback()   # nichts offen lassen — Migration braucht exklusive Locks (Lehre)

    _run_light_migrations()   # idempotent, läuft sonst beim App-Start

    db.expire_all()
    migrated = db.get(TcgdexCatalog, "test66-migration")
    assert migrated.price_eur == Decimal("2.00")   # Altdaten erhalten
    assert migrated.price_eur_checked is None       # neue Spalte: NULL für Bestandszeilen

    # zweiter Lauf ändert nichts (Idempotenz). WICHTIG: das db.get() oben hat
    # (als erster Zugriff nach dem rollback) still eine neue Transaktion auf
    # `db` eröffnet — ohne diesen zweiten rollback blockiert sie die ALTERs
    # der zweiten Migration exklusiv-lockfrei ewig (Lehre, hier live getroffen).
    db.rollback()
    _run_light_migrations()
    db.expire_all()
    again = db.get(TcgdexCatalog, "test66-migration")
    assert again.price_eur == Decimal("2.00")
    assert again.price_eur_checked is None
