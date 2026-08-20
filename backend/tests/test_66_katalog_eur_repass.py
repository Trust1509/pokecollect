"""
#66: Der Katalog-€-Preis wurde nur EINMAL geschrieben (bei der Erstanreicherung
in _apply_full/enrich_catalog) und fror danach ein, während der $-Preis
(TCGCSV-Weg) täglich frisch ist. refresh_catalog_eur() ist der rollierende
Repass für bereits angereicherte Zeilen — mit einem EIGENEN Nachsehe-Stempel
(price_eur_checked), NICHT price_eur_updated (das ist der Stand DER QUELLE und
würde bei unveränderten Quellwerten sofort wieder vorne stehen: Hunger-Effekt).

Panel-Nacharbeit (bestätigte Funde, am Code reproduziert): der Repass darf die
$-Pipeline nicht anfassen (BLOCKER 1), eine einzelne kaputte Karte darf den
Schwung nicht kippen (BLOCKER 2), _apply_full muss den Stempel mitsetzen
(WICHTIG 3), ein Preis ohne Datenstand darf den vorhandenen Stempel nicht
löschen (WICHTIG 4), die Kennzahl braucht einen expliziten flush + einen
never_checked-Zähler (KLEIN 6). WICHTIG 5 (zwei kurze statt einer langen
Transaktion) steckt in der Funktion selbst, nicht in einem eigenen Test —
Begründung im Baubericht.

Netzfrei: tcgdex.get_card gemockt (wie test_catalog_detail.py).
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import insert, text

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


# ── Preis OHNE Datenstand darf den vorhandenen Stempel nicht löschen ────────
# Panel-Fund WICHTIG 4: cm.updated ist optional (tcgdex.py). Liefert die
# Quelle einen Preis, aber kein updated-Feld, muss der VORHANDENE
# price_eur_updated stehen bleiben — sonst verschwindet im Grid genau der
# Datenstand, um den es in diesem Issue geht.

def test_preis_ohne_datenstand_loescht_den_alten_stempel_nicht(db, monkeypatch):
    _zeile(db, "test66-ohne-datum", price_eur_checked=None,
           price_eur=Decimal("1.00"), price_eur_updated="2026-01-01")
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        return TcgdexCard(id=card_id,
                          pricing=Pricing(cardmarket=CardMarketPricing(avg=9.99, updated=None)))
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    db.expire_all()
    row = db.get(TcgdexCatalog, "test66-ohne-datum")
    assert row.price_eur == Decimal("9.99")        # der Preis wird sehr wohl übernommen
    assert row.price_eur_updated == "2026-01-01"    # der alte Datenstand bleibt stehen


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


# ── $-Preise/-Varianten bleiben unangetastet (Panel-Fund BLOCKER 1) ─────────
# price_usd_updated ist der GEMEINSAME Datenstand aller $-Spalten inkl. der
# Varianten (price_usd_holo/_reverse/_pokeball/_masterball, #63) — der
# TCGCSV-Weg schreibt ihn nur zusammen MIT diesen Spalten. Der €-Repass sieht
# die Varianten nie; würde er price_usd/price_usd_updated trotzdem
# mitschreiben, verbürgte er Werte, die er nie geprüft hat, und der
# Frische-Riegel _usd_stand_frisch (pricing.py) hielte eingefrorene
# TCGCSV-Varianten nach einem TCGCSV-Ausfall fälschlich für frisch.

def test_dollarpreis_und_varianten_bleiben_unangetastet(db, monkeypatch):
    alter_usd_stempel = "2026-08-15T04:00:58+00:00"
    _zeile(db, "test66-dollar", price_eur_checked=None,
           price_usd=Decimal("1.00"), price_usd_holo=Decimal("5.00"),
           price_usd_reverse=Decimal("3.00"), price_usd_pokeball=Decimal("12.78"),
           price_usd_updated=alter_usd_stempel)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        # Die TCGdex-Antwort enthält SEHR WOHL einen $-Preis (West-Karten
        # führen tcgplayer im selben Response) — genau das darf den Repass
        # nicht dazu verleiten, ihn zu übernehmen.
        return TcgdexCard(
            id=card_id,
            pricing=Pricing(
                cardmarket=CardMarketPricing(avg=2.50, updated="2026-08-19"),
                tcgplayer={"updated": "2026-08-19", "normal": {"marketPrice": 99.99}},
            ),
        )
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    db.expire_all()
    row = db.get(TcgdexCatalog, "test66-dollar")
    assert row.price_eur == Decimal("2.50")            # € wird sehr wohl übernommen
    assert row.price_usd == Decimal("1.00")             # $ UNVERÄNDERT
    assert row.price_usd_holo == Decimal("5.00")
    assert row.price_usd_reverse == Decimal("3.00")
    assert row.price_usd_pokeball == Decimal("12.78")
    assert row.price_usd_updated == alter_usd_stempel    # Stempel UNVERÄNDERT


# ── Eine kaputte Karte stoppt nicht den ganzen Schwung (Panel-Fund BLOCKER 2) ─
# tcgdex.get_card() fängt HTTP-Fehler/404/Nicht-200/kaputtes JSON ab, aber
# TcgdexCard.model_validate() dahinter nicht — ein schemawidriges 200-JSON
# wirft eine ValidationError, die vor dem Stempeln/Committen den ganzen
# asyncio.gather() mitriss. Deterministische Auswahl -> derselbe Schwung würde
# beim nächsten Lauf wieder gezogen: Dauerstillstand.

def test_eine_kaputte_karte_stoppt_nicht_den_ganzen_schwung(db, monkeypatch):
    _zeile(db, "test66-kaputt-a", price_eur_checked=None)
    _zeile(db, "test66-kaputt-b", price_eur_checked=None)   # wirft beim Parsen
    _zeile(db, "test66-kaputt-c", price_eur_checked=None)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        if card_id == "test66-kaputt-b":
            raise ValueError("kaputtes JSON / Schema-Bruch")
        return TcgdexCard(id=card_id,
                          pricing=Pricing(cardmarket=CardMarketPricing(avg=4.20, updated="2026-08-19")))
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    stats = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    assert stats["visited"] == 3
    assert stats["updated"] == 2   # nur die beiden gesunden Karten
    db.expire_all()
    for cid in ("test66-kaputt-a", "test66-kaputt-b", "test66-kaputt-c"):
        assert db.get(TcgdexCatalog, cid).price_eur_checked is not None, cid
    assert db.get(TcgdexCatalog, "test66-kaputt-a").price_eur == Decimal("4.20")
    assert db.get(TcgdexCatalog, "test66-kaputt-b").price_eur is None   # nie gesetzt
    assert db.get(TcgdexCatalog, "test66-kaputt-c").price_eur == Decimal("4.20")


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


# ── Kennzahl: never_checked + korrekter ältester Stempel (Panel-Fund KLEIN 6) ─
# SessionLocal läuft mit autoflush=False (database.py) — ohne expliziten
# flush vor der MIN-Abfrage sähe sie die gerade gesetzten Stempel dieses
# Laufs noch nicht. Und SQL-MIN überspringt NULL-Werte: never_checked macht
# den Rückstand sichtbar, den ein "ältester Stempel" allein verdeckt.

def test_kennzahl_zaehlt_ungeprueften_rueckstand(db, monkeypatch):
    _zeile(db, "test66-k1", price_eur_checked=None)
    _zeile(db, "test66-k2", price_eur_checked=None)
    db.commit()

    async def fake_get_card(card_id, lang="en"):
        return None
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)

    # limit=1: EINE Zeile wird jetzt gestempelt, die andere bleibt NULL.
    stats = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=1))
    assert stats["visited"] == 1
    assert stats["never_checked"] == 1           # die zweite Zeile ist noch nie geprüft
    assert stats["oldest_checked"] is not None   # ohne den expliziten flush wäre das None

    # zweiter Lauf holt die letzte NULL-Zeile -> niemand mehr ungeprüft.
    stats2 = asyncio.run(catalog_svc.refresh_catalog_eur(db, limit=10))
    assert stats2["never_checked"] == 0


# ── _apply_full setzt den Nachsehe-Stempel mit (Panel-Fund WICHTIG 3) ───────
# Ohne diesen Stempel bliebe price_eur_checked für jede frisch angereicherte
# Zeile NULL — NULLS FIRST zöge sie sofort wieder in den Repass, obwohl der
# €-Preis gerade erst frisch war (Doppelabruf, ~30 statt ~12 Nächte Umlauf).
# Reine Funktion, kein DB-Zugriff nötig.

def test_apply_full_setzt_den_nachsehe_stempel():
    row = TcgdexCatalog(card_id="test66-frisch", region="west")
    tc = TcgdexCard(id="test66-frisch", rarity="Rare",
                    pricing=Pricing(cardmarket=CardMarketPricing(avg=0.50, updated="2026-08-19")))
    catalog_svc._apply_full(row, tc)
    assert row.price_eur == 0.50          # unverändertes Verhalten: Preis kommt weiter an
    assert row.price_eur_checked is not None


# ── Light-Migration: additiv, Erhalt + Idempotenz (Muster test_63_muster.py) ─
# Panel-Fund WICHTIG 8: die Spalte wird jetzt VORHER echt gedroppt — erst das
# stellt den Zustand einer Bestands-Installation ohne price_eur_checked
# wirklich her (create_all() legt sie auf der Test-DB sonst aus dem aktuellen
# Model an, bevor die Light-Migration überhaupt läuft).

def test_migration_fuegt_price_eur_checked_hinzu_additiv_und_idempotent(db):
    # Core-Insert statt db.add(TcgdexCatalog(...)) wie in den Tests oben: mit
    # dem ORM-Weg lieferte dieser eine Test hier reproduzierbar ein falsches
    # "UndefinedColumn price_eur_checked", obwohl die Spalte zu dem Zeitpunkt
    # nachweislich existierte (per information_schema UND per Raw-SQL-Insert
    # auf derselben Session bestätigt) — sieht nach einem insertmanyvalues-
    # Cache-Artefakt aus, nicht restlos aufgeklärt. Der Core-Weg umgeht es.
    db.execute(insert(TcgdexCatalog).values(
        card_id="test66-migration", region="west", set_id="test66set",
        set_code="T66", local_id="1", enriched=True, price_eur=Decimal("2.00"),
    ))
    db.commit()
    db.rollback()   # nichts offen lassen — Migration braucht exklusive Locks (Lehre)

    db.execute(text("ALTER TABLE tcgdex_catalog DROP COLUMN IF EXISTS price_eur_checked"))
    db.commit()      # sofort schließen, sonst blockiert die eigene DDL die folgende (Lehre)

    _run_light_migrations()   # idempotent, läuft sonst beim App-Start

    db.expire_all()
    migrated = db.get(TcgdexCatalog, "test66-migration")
    assert migrated.price_eur == Decimal("2.00")   # Altdaten erhalten
    assert migrated.price_eur_checked is None       # neue Spalte: NULL für Bestandszeilen

    # zweiter Lauf ändert nichts (Idempotenz). db.get() oben hat als erster
    # Zugriff nach dem rollback still eine neue Transaktion eröffnet — ohne
    # diesen zweiten rollback blockiert sie die ALTERs des zweiten Laufs
    # exklusiv-lockfrei ewig (Lehre, hier beim Bau live getroffen).
    db.rollback()
    _run_light_migrations()
    db.expire_all()
    again = db.get(TcgdexCatalog, "test66-migration")
    assert again.price_eur == Decimal("2.00")
    assert again.price_eur_checked is None
