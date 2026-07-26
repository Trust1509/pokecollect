"""
Kaufpreis / Einstand + unrealisierter G/V (#26).
- kaufpreis_eur + kaufdatum persistieren (optional)
- Stats: Gesamt-Einstand (Σ Kaufpreise besessener), unrealisierter G/V
  (Σ wert − kaufpreis, nur wo BEIDE gesetzt) — als Delta gegen den Vorzustand
  geprüft (session-weite DB, andere Tests hinterlassen Karten).
"""

from decimal import Decimal


def _owned(client, name: str, **extra) -> dict:
    """Besessene Karte OHNE Pokédex-Nr. → Delete räumt restlos ab."""
    r = client.post("/api/v1/cards", json={"kartenname": name, "besessen": True, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _dec(v) -> Decimal:
    # Über str, damit ein evtl. Float aus der JSON-Serialisierung nicht die
    # Decimal-Genauigkeit verfälscht.
    return Decimal(str(v)) if v is not None else Decimal("0")


def test_kaufpreis_kaufdatum_persist(client):
    card = _owned(client, "Einstandmon", kaufpreis_eur="12.50", kaufdatum="2026-07-20")
    cid = card["id"]
    try:
        got = client.get(f"/api/v1/cards/{cid}").json()
        assert _dec(got["kaufpreis_eur"]) == Decimal("12.50")
        assert got["kaufdatum"] == "2026-07-20"
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def test_kaufpreis_optional_default_none(client):
    card = _owned(client, "Ohne-Einstand")
    cid = card["id"]
    try:
        got = client.get(f"/api/v1/cards/{cid}").json()
        assert got["kaufpreis_eur"] is None
        assert got["kaufdatum"] is None
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def _stats(client) -> dict:
    r = client.get("/api/v1/cards/meta/stats")
    assert r.status_code == 200
    return r.json()


def test_stats_einstand_und_unrealisierter_gv(client):
    before = _stats(client)
    # A: Kaufpreis 10, Wert 15 → G/V +5, Einstand 10
    a = _owned(client, "GV-A", kaufpreis_eur="10.00", wert_eur="15.00")
    # B: Kaufpreis 20, Wert 12 → G/V -8, Einstand 20
    b = _owned(client, "GV-B", kaufpreis_eur="20.00", wert_eur="12.00")
    # C: Kaufpreis 5, KEIN Wert → zählt zum Einstand, NICHT zum G/V
    c = _owned(client, "GV-C", kaufpreis_eur="5.00")
    # D: Wert 9, KEIN Kaufpreis → weder Einstand noch G/V
    d = _owned(client, "GV-D", wert_eur="9.00")
    try:
        after = _stats(client)
        d_einstand = _dec(after["gesamt_einstand_eur"]) - _dec(before["gesamt_einstand_eur"])
        d_gv = _dec(after["unrealisierter_gv_eur"]) - _dec(before["unrealisierter_gv_eur"])
        assert d_einstand == Decimal("35.00")   # 10 + 20 + 5
        assert d_gv == Decimal("-3.00")          # (+5) + (-8); C und D zählen nicht
    finally:
        for card in (a, b, c, d):
            client.delete(f"/api/v1/cards/{card['id']}")
