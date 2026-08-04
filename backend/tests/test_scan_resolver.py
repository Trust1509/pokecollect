"""
resolve_one-Priorität (Issue #33): Set + Nummer sind der zuverlässige Schlüssel,
der Name nur Fallback. Ein unbrauchbarer (Garbage-)Name — typischerweise weil
Gemini Label-/Attackentext einer Nachbarkarte als Namen gelesen hat — darf einen
guten Set+Nummer- bzw. Nummer-Treffer NICHT verhindern.

Kein Netz/DB: die tcgdex-Aufrufe und der Set-Zählabgleich werden gemockt, die
resolve_one-Coroutine läuft über asyncio.run (wie test_gemini_retry.py, ohne
pytest-asyncio).
"""

import asyncio

import pytest

from app.schemas.scan import ScanRawRead
from app.services import tcgdex
from app.services.scan import resolver
from app.services.scan.resolver import _denominator, _name_plausibel, resolve_one
from app.services.tcgdex import CardCount, SetRef, TcgdexCard, Variants


# ── Fakes ────────────────────────────────────────────────────────────────────

class _FakeScalars:
    def __init__(self, rows):
        self._rows = rows

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeDB:
    """
    Minimales Session-Double: liefert nichts aus der DB (get→None, scalars→leer).
    Der Nummer-nur-Pfad wird über resolver._sets_matching_count gemockt, nicht
    über echte Queries — so bleibt der Test DB- und netzfrei.
    """
    def get(self, model, key):
        return None

    def scalars(self, stmt):
        return _FakeScalars([])


class _FakeSet:
    def __init__(self, set_id, code):
        self.set_id = set_id
        self.code = code


def _card(cid, name, set_id="sv03", local_id="113", official=217, dex=6):
    return TcgdexCard(
        id=cid, name=name, localId=local_id,
        dexId=[dex] if dex else None, rarity="Rare",
        set=SetRef(id=set_id, name="Obsidian Flames",
                   cardCount=CardCount(official=official, total=official + 30)),
        variants=Variants(normal=True, holo=True),
    )


def _boom(msg):
    async def _f(*a, **k):
        raise AssertionError(msg)
    return _f


# ── Priorität 1: Set + Nummer schlägt Garbage-Namen ──────────────────────────

def test_set_and_number_beats_garbage_name(monkeypatch):
    """Set + Nummer lesbar, Name Garbage → Karte über Nummer, Namenssuche tabu."""
    read = ScanRawRead(name="Flammenwurf 120 schnappt sich", set_code="OBF",
                       number="113/217", language="DE", confidence=0.2)

    async def fake_fetch(set_id, local_id, lang):
        assert (set_id, local_id) == ("sv03", "113")
        return _card("sv03-113", "Glurak ex")

    async def fake_get_card(cid, lang):
        return _card(cid, "Charizard ex")   # englische Variante

    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)
    monkeypatch.setattr(tcgdex, "search_cards",
                        _boom("Namenssuche darf bei Set+Nummer nicht laufen"))

    cand = asyncio.run(resolve_one(_FakeDB(), read))

    assert cand.match is not None
    assert cand.match.tcgdex_card_id == "sv03-113"
    assert cand.match.set_id == "sv03"
    # Der korrekte Name gewinnt, NICHT der Garbage-Text.
    assert cand.suggested["kartenname"] == "Glurak ex"
    assert cand.suggested["karten_nr"] == "113/217"
    assert "set" not in cand.uncertain_fields
    assert "number" not in cand.uncertain_fields
    # Garbage-Name erkannt und markiert, Karte steht aber (Punkt 3).
    assert "name" in cand.uncertain_fields
    assert cand.confidence >= 0.6


# ── Priorität 2: nur Nummer (Set leer) → über den Nenner genau ein Set ────────

def test_number_only_resolves_when_set_empty(monkeypatch):
    """Set leer, Nummer da, genau ein Set mit passendem Nenner → Treffer."""
    read = ScanRawRead(name="Attacke Wirbelsturm 90", set_code=None,
                       number="113/217", language="DE", confidence=0.19)

    monkeypatch.setattr(resolver, "_sets_matching_count",
                        lambda db, denom: [_FakeSet("sv03", "OBF")] if denom == 217 else [])

    async def fake_fetch(set_id, local_id, lang):
        assert set_id == "sv03" and local_id == "113"
        return _card("sv03-113", "Glurak ex")

    async def fake_get_card(cid, lang):
        return _card(cid, "Charizard ex")

    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)
    monkeypatch.setattr(tcgdex, "search_cards",
                        _boom("Namenssuche darf bei eindeutigem Nummer-Treffer nicht laufen"))

    cand = asyncio.run(resolve_one(_FakeDB(), read))

    assert cand.match is not None
    assert cand.match.tcgdex_card_id == "sv03-113"
    assert cand.match.set_id == "sv03"
    assert cand.suggested["kartenname"] == "Glurak ex"
    assert "set" not in cand.uncertain_fields      # Set über die Nummer bestimmt
    assert "name" in cand.uncertain_fields         # Garbage-Name markiert
    assert cand.confidence >= 0.6


def test_number_only_nonlatin_name_marked_uncertain(monkeypatch):
    """
    Nummer-nur-Treffer (Set nur über den Nenner geraten) mit nicht-lateinischem
    Namen (Katakana): `_name_plausibel` kann den Namen nicht prüfen und winkt ihn
    durch — trotzdem muss „name" als unsicher gelten, damit ein zufälliger
    Nenner-Treffer nicht selbstsicher auf die falsche Karte zeigt (#33, Fix 2).
    """
    read = ScanRawRead(name="ビビヨン", set_code=None, number="009/080",
                       language="JP", confidence=0.9)

    monkeypatch.setattr(resolver, "_sets_matching_count",
                        lambda db, denom: [_FakeSet("zz80", "ZZ80")] if denom == 80 else [])

    async def fake_fetch(set_id, local_id, lang):
        assert set_id == "zz80" and local_id == "9"
        return _card("zz80-9", "Sizzlipede", set_id="zz80", local_id="9", official=80, dex=850)

    async def fake_get_card(cid, lang):
        return _card(cid, "Sizzlipede", set_id="zz80", local_id="9", official=80, dex=850)

    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)
    monkeypatch.setattr(tcgdex, "search_cards",
                        _boom("Namenssuche darf beim eindeutigen Nummer-Treffer nicht laufen"))

    cand = asyncio.run(resolve_one(_FakeDB(), read))

    assert cand.match is not None                 # Karte steht (Nummer-Treffer)
    assert "name" in cand.uncertain_fields        # aber Name unverifizierbar → unsicher
    assert cand.confidence < read.confidence       # gedämpft ggü. Roh-Sicherheit


def test_priority1_nonlatin_name_not_flagged(monkeypatch):
    """
    Gegenprobe zu Fix 2: Set + Nummer (Priorität 1) mit passendem nicht-
    lateinischem Namen darf NICHT als unsicher gelten — Fix 2 gilt AUSSCHLIESSLICH
    für den geratenen Nummer-nur-Pfad (via_number_only). Schützt gegen ein
    versehentlich zu früh gesetztes Flag (#33).
    """
    read = ScanRawRead(name="ビビヨン", set_code="M3", number="009/080",
                       language="JP", confidence=0.9)

    class _DBWithM3:
        def get(self, model, key):
            return _FakeSet("M3", "M3") if key == "M3" else None

        def scalars(self, stmt):
            return _FakeScalars([])

    async def fake_fetch(set_id, local_id, lang):
        assert set_id == "M3" and local_id == "9"
        return _card("M3-9", "ビビヨン", set_id="M3", local_id="9", official=80, dex=666)

    async def fake_get_card(cid, lang):
        return _card(cid, "ビビヨン", set_id="M3", local_id="9", official=80, dex=666)

    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "get_card", fake_get_card)
    monkeypatch.setattr(tcgdex, "search_cards",
                        _boom("Set+Nummer → keine Namenssuche"))

    cand = asyncio.run(resolve_one(_DBWithM3(), read))

    assert cand.match is not None
    assert cand.match.set_id == "M3"
    assert "name" not in cand.uncertain_fields   # Fix 2 feuert bei Priorität 1 NICHT
    assert cand.confidence >= 0.8


def test_number_only_ambiguous_stays_uncertain(monkeypatch):
    """Mehrere Sets mit gleichem Nenner liefern eine Karte → NICHT eindeutig."""
    read = ScanRawRead(name="Garbage Label", set_code=None, number="113/217",
                       language="DE", confidence=0.2)

    monkeypatch.setattr(
        resolver, "_sets_matching_count",
        lambda db, denom: [_FakeSet("sv03", "OBF"), _FakeSet("swsh1", "SSH")])

    async def fake_fetch(set_id, local_id, lang):
        return _card(f"{set_id}-113", "Irgendwas", set_id=set_id)  # beide treffen

    async def fake_search(params, lang):
        return []   # Garbage-Name findet nichts

    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "search_cards", fake_search)
    monkeypatch.setattr(tcgdex, "get_card", _boom("kein Treffer erwartet"))

    cand = asyncio.run(resolve_one(_FakeDB(), read))

    assert cand.match is None
    assert "set" in cand.uncertain_fields
    assert "match" in cand.uncertain_fields
    assert cand.confidence <= 0.35


def test_number_only_needs_denominator(monkeypatch):
    """Ohne Nenner (nackte Nummer, kein „/") kein Nummer-nur-Pfad → unsicher."""
    read = ScanRawRead(name="Garbage", set_code=None, number="113",
                       language="DE", confidence=0.2)

    def _no_count(db, denom):
        raise AssertionError("ohne Nenner darf der Set-Zählabgleich nicht laufen")

    async def fake_fetch(*a, **k):
        raise AssertionError("kein Set → kein Set+Nummer-Fetch")

    async def fake_search(params, lang):
        return []   # Garbage-Name findet nichts

    monkeypatch.setattr(resolver, "_sets_matching_count", _no_count)
    monkeypatch.setattr(tcgdex, "fetch_card_by_set_multilang", fake_fetch)
    monkeypatch.setattr(tcgdex, "search_cards", fake_search)

    cand = asyncio.run(resolve_one(_FakeDB(), read))
    assert cand.match is None
    assert "set" in cand.uncertain_fields
    assert "number" not in cand.uncertain_fields  # localId „113" ist ja lesbar


# ── Reiner Helfer _denominator ───────────────────────────────────────────────

@pytest.mark.parametrize("nr, denom", [
    ("113/217", 217),
    ("068/172", 172),
    ("247/217", 217),     # Secret Rare über der offiziellen Zahl
    ("42", None),
    ("113", None),
    ("7/", None),
    ("TG01/TG30", None),  # alphanumerischer Nenner
    (None, None),
    ("", None),
])
def test_denominator(nr, denom):
    assert _denominator(nr) == denom


# ── Reiner Helfer _name_plausibel ────────────────────────────────────────────

@pytest.mark.parametrize("raw, names, ok", [
    ("Glurak ex", ("Glurak ex", "Charizard ex"), True),
    ("Glurak", ("Glurak ex", "Charizard ex"), True),      # Teilstring
    ("Charizard", ("Glurak", "Charizard"), True),          # EN-Name passt
    ("Glurak-ex", ("Glurak ex", None), True),              # Trennzeichen/Suffix
    ("Flammenwurf 120", ("Glurak ex", "Charizard ex"), False),
    ("Feuersturm Fähigkeit", ("Glurak", None), False),
    (None, ("Glurak", None), True),                        # kein roher Name
    ("", ("Glurak", None), True),
])
def test_name_plausibel(raw, names, ok):
    assert _name_plausibel(raw, *names) is ok
