"""
Sliding-Window für RPM/TPM live (Issue #22) — pur, Zeit injiziert.

Kein echtes Warten: `now` wird explizit übergeben. Prüft, dass Einträge älter
als das Fenster (60s) herausfallen und die Summen im Fenster stimmen.
"""

from app.services.scan.rate_window import SlidingWindow, gemini_rate


def test_summen_im_fenster_stimmen():
    w = SlidingWindow()
    w.record(requests=1, tokens=10, now=100.0)
    w.record(requests=1, tokens=5, now=120.0)
    w.record(requests=2, tokens=0, now=150.0)
    assert w.snapshot(now=150.0) == (4, 15)


def test_alte_eintraege_fallen_raus():
    w = SlidingWindow()
    w.record(requests=1, tokens=100, now=0.0)    # bei t=61 → 61s alt → raus
    w.record(requests=1, tokens=200, now=30.0)   # bei t=61 → 31s alt → bleibt
    assert w.snapshot(now=61.0) == (1, 200)


def test_alles_ausserhalb_fenster_leer():
    w = SlidingWindow()
    w.record(requests=3, tokens=999, now=0.0)
    assert w.snapshot(now=1000.0) == (0, 0)


def test_grenze_genau_60s_faellt_raus():
    w = SlidingWindow()
    w.record(requests=1, tokens=1, now=0.0)
    # Alter genau 60s (== Fenster) → nicht mehr "letzte 60s" → raus.
    assert w.snapshot(now=60.0) == (0, 0)
    w.record(requests=1, tokens=7, now=100.0)
    # Alter 59.9s → innerhalb Fenster → bleibt.
    assert w.snapshot(now=159.9) == (1, 7)


def test_record_prunt_selbst_und_haelt_deque_klein():
    w = SlidingWindow()
    for i in range(200):
        # Ein Event pro Sekunde; das Fenster hält höchstens ~60 Einträge.
        w.record(requests=1, tokens=1, now=float(i))
    req, tok = w.snapshot(now=199.0)
    # Nur Events mit Alter < 60s zählen: now-fenster = 139.0, also Einträge mit
    # ts > 139.0 → ts in {140..199} = 60 Stück.
    assert req == 60
    assert tok == 60
    assert len(w._events) == 60


def test_custom_fenster():
    w = SlidingWindow(fenster=10.0)
    w.record(requests=1, tokens=1, now=0.0)
    w.record(requests=1, tokens=1, now=5.0)
    assert w.snapshot(now=9.0) == (2, 2)
    assert w.snapshot(now=11.0) == (1, 1)   # 0.0-Eintrag ist 11s alt → raus


def test_globaler_tracker_roundtrip():
    """gemini_rate ist eine nutzbare SlidingWindow-Instanz."""
    assert isinstance(gemini_rate, SlidingWindow)
    r0, t0 = gemini_rate.snapshot()
    assert isinstance(r0, int) and isinstance(t0, int)


def test_usage_endpunkt_liefert_rpm_tpm(client):
    """/scan/usage meldet den Live-Verbrauch rpm_used/tpm_used (Issue #22)."""
    body = client.get("/api/v1/scan/usage").json()
    assert "rpm_used" in body and "tpm_used" in body
    assert isinstance(body["rpm_used"], int) and body["rpm_used"] >= 0
    assert isinstance(body["tpm_used"], int) and body["tpm_used"] >= 0
