"""
Scan-Resolver, Nummer-nur-Auflösung (#33).

Regression: Eine japanische Karte „009/080" (Nenner 80 = offizielle Set-Größe
des JP-Sets M3) wurde über `card_count_total == 80` fälschlich dem West-Set
„Weg des Champs" (CPA, offiziell 73 / total 80) zugeordnet und landete
selbstsicher auf der falschen Karte. Der auf einer Karte gedruckte Nenner ist
IMMER die OFFIZIELLE Set-Größe — daher darf nur `card_count_official` matchen.
"""

from app.database import SessionLocal
from app.models.pokemon_set import PokemonSet
from app.services.scan.resolver import _sets_matching_count


def _cleanup(db, *codes):
    for c in codes:
        row = db.get(PokemonSet, c)
        if row:
            db.delete(row)
    db.commit()


def test_number_denominator_matches_official_not_total(client):
    # client-Fixture stellt sicher, dass die App/DB initialisiert ist.
    db = SessionLocal()
    try:
        _cleanup(db, "ZZCPA", "ZZ80")
        # CPA-artig: offiziell 73, aber total 80 (7 Secret Rares über 73).
        db.add(PokemonSet(code="ZZCPA", set_id="zztest3.5", name="Test Champ",
                          card_count_official=73, card_count_total=80))
        # Set, dessen OFFIZIELLE Größe wirklich 80 ist.
        db.add(PokemonSet(code="ZZ80", set_id="zztest80", name="Test 80",
                          card_count_official=80, card_count_total=85))
        db.commit()

        got = {s.code for s in _sets_matching_count(db, 80)}
        assert "ZZCPA" not in got, (
            "Nenner 80 (offizielle Größe) darf NICHT das Set mit total=80 treffen — "
            "sonst wird eine JP-Karte 009/080 fälschlich CPA #009 zugeordnet"
        )
        assert "ZZ80" in got, "Set mit offiziell 80 muss beim Nenner 80 treffen"
    finally:
        _cleanup(db, "ZZCPA", "ZZ80")
        db.close()


def test_number_matching_edge_cases(client):
    db = SessionLocal()
    try:
        _cleanup(db, "ZZEQ", "ZZNULL")
        # official == total: normales Set ohne Secret Rares → trifft beim Nenner.
        db.add(PokemonSet(code="ZZEQ", set_id="zzeq", name="Test Eq",
                          card_count_official=100, card_count_total=100))
        # official NULL (nur total gesetzt): ohne offizielle Größe KEIN Nenner-
        # Treffer (der gedruckte Nenner lässt sich nicht zuordnen).
        db.add(PokemonSet(code="ZZNULL", set_id="zznull", name="Test Null",
                          card_count_official=None, card_count_total=100))
        db.commit()

        got = {s.code for s in _sets_matching_count(db, 100)}
        assert "ZZEQ" in got
        assert "ZZNULL" not in got, "official NULL darf beim Nenner nicht treffen"
        # Nenner 0/None → nie ein Treffer (Guard).
        assert _sets_matching_count(db, 0) == []
        assert _sets_matching_count(db, None) == []
    finally:
        _cleanup(db, "ZZEQ", "ZZNULL")
        db.close()
