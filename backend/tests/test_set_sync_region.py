"""
Set-Sync nicht-westlicher Regionen (#33). Japanische (u. a.) Sets haben eigene
Nummernkreise; TCGdex führt für sie KEIN abbreviation.official, dafür IST die
set.id der aufgedruckte Code (z. B. „M3"). Der Region-Sync legt sie additiv an,
lädt Details (für Serie/Symbol + verlässlichen Pocket-Ausschluss) und dedupt
sprachübergreifend geteilte Sets über die set.id. Netzfrei: get_sets/get_set
werden gemockt.
"""

import asyncio

from sqlalchemy import select

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.services import set_sync, tcgdex
from app.services.tcgdex import CardCount, TcgdexSetBrief

_SETS = [
    TcgdexSetBrief(id="ZZM3", name="JP Test 3", cardCount=CardCount(official=80, total=117)),
    TcgdexSetBrief(id="ZZM1S", name="JP Test 1S", cardCount=CardCount(official=63, total=92)),
    TcgdexSetBrief(id="ZZDUP", name="Kollision", cardCount=CardCount(official=10, total=10)),
    TcgdexSetBrief(id="ZZPKT", name="Pocket", cardCount=CardCount(official=5, total=5)),
    TcgdexSetBrief(id="ZZSHARED", name="Shared", cardCount=CardCount(official=100, total=100)),
    # Details laden (transient) nicht → fail-closed: NICHT anlegen.
    TcgdexSetBrief(id="ZZNODET", name="No Detail", cardCount=CardCount(official=50, total=50)),
]
# Details liefern die Serie (Set-Liste tut das für diese Regionen nicht).
_DETAILS = {
    "ZZM3": {"serie": {"id": "M"}, "symbol": "https://assets.tcgdex.net/univ/M/ZZM3/symbol"},
    "ZZM1S": {"serie": {"id": "M"}},
    "ZZDUP": {"serie": {"id": "M"}},
    "ZZPKT": {"serie": {"id": "tcgp"}},   # Pokémon TCG Pocket → ausgeschlossen
    "ZZSHARED": {"serie": {"id": "neo"}},
}

_ALL = ["ZZM3", "ZZM1S", "ZZDUP", "ZZPKT", "ZZSHARED", "ZZWEST", "ZZNODET"]


def _cleanup(db, *codes):
    for c in codes:
        row = db.get(PokemonSet, c)
        if row:
            db.delete(row)
    db.commit()


def _mock(monkeypatch):
    async def fake_get_sets(region):
        return list(_SETS) if region == "ja" else []

    async def fake_get_set(sid, lang):
        return _DETAILS.get(sid, {})

    monkeypatch.setattr(tcgdex, "get_sets", fake_get_sets)
    monkeypatch.setattr(tcgdex, "get_set", fake_get_set)


def test_region_sets_created_deduped_enriched(client, monkeypatch):
    _mock(monkeypatch)
    db = SessionLocal()
    try:
        _cleanup(db, *_ALL)
        # West-Bestand: (a) geteiltes Set mit set_id ZZSHARED (wie die alten Neo-
        # Sets, JP & West teilen sich die set.id); (b) eine Zeile, die den Code
        # „ZZDUP" belegt (echte Code-Kollision, bleibt über Syncs bestehen).
        db.add(PokemonSet(code="ZZWEST", set_id="ZZSHARED", name="West Shared"))
        db.add(PokemonSet(code="ZZDUP", set_id="ZZDUPW", name="West Dup"))
        db.commit()

        def _state():
            rows = db.scalars(select(PokemonSet)).all()
            return {r.set_id: r for r in rows if r.set_id}, {r.code for r in rows}

        by_setid, used_codes = _state()
        created = asyncio.run(set_sync._sync_region_sets(db, "ja", by_setid, used_codes))
        db.commit()

        m3 = db.get(PokemonSet, "ZZM3")
        assert m3 is not None and m3.set_id == "ZZM3"     # set.id == Code
        assert m3.card_count_official == 80               # Nenner-Auflösung möglich
        assert m3.series_id == "M"                        # aus Details angereichert
        assert m3.symbol_url and m3.symbol_url.endswith(".png")
        assert db.get(PokemonSet, "ZZM1S") is not None
        # Code-Kollision: West-Zeile bleibt UNVERÄNDERT, JP-Set wird übersprungen.
        assert db.get(PokemonSet, "ZZDUP").set_id == "ZZDUPW"
        assert db.get(PokemonSet, "ZZPKT") is None, "tcgp (aus Serie der Details) → ausgeschlossen"
        assert db.get(PokemonSet, "ZZSHARED") is None, "geteilte set.id → nicht dupliziert"
        assert db.get(PokemonSet, "ZZNODET") is None, "ohne Details → fail-closed, nicht angelegt"
        assert created == 2

        # Idempotenz wie in sync_sets: Zustand frisch aus der DB, zweiter Lauf = 0.
        by_setid2, used2 = _state()
        created2 = asyncio.run(set_sync._sync_region_sets(db, "ja", by_setid2, used2))
        assert created2 == 0, "zweiter Sync darf nichts doppelt anlegen"
    finally:
        _cleanup(db, *_ALL)
        db.close()
