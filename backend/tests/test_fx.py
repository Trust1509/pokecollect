"""
USD→EUR-Tageskurs (services/fx.py, Epic #41 $-Preis-Fallback).

Ohne Netz: MockTransport liefert die Antworten beider Quellen; Cache und
Notnagel (letzter bekannter Kurs) werden je Test zurückgesetzt.
"""

import asyncio
import time
from decimal import Decimal

import httpx
import pytest

from app.services import fx


@pytest.fixture(autouse=True)
def _frischer_cache():
    fx.reset_cache()
    yield
    fx.reset_cache()


def _run(coro):
    return asyncio.run(coro)


def _transport(handler):
    return httpx.MockTransport(handler)


def test_frankfurter_liefert_kurs():
    def handler(request: httpx.Request):
        assert "frankfurter" in str(request.url)
        return httpx.Response(200, json={"base": "USD", "rates": {"EUR": 0.8666}})

    rate = _run(fx.usd_eur_rate(transport=_transport(handler)))
    assert rate == Decimal("0.8666")


def test_cache_vermeidet_zweiten_abruf():
    calls = {"n": 0}

    def handler(request: httpx.Request):
        calls["n"] += 1
        return httpx.Response(200, json={"rates": {"EUR": 0.9}})

    t = _transport(handler)
    assert _run(fx.usd_eur_rate(transport=t)) == Decimal("0.9")
    assert _run(fx.usd_eur_rate(transport=t)) == Decimal("0.9")
    assert calls["n"] == 1  # zweiter Aufruf kam aus dem Cache


def test_fallback_auf_zweite_quelle():
    def handler(request: httpx.Request):
        if "frankfurter" in str(request.url):
            return httpx.Response(503, text="down")
        return httpx.Response(200, json={"result": "success", "rates": {"EUR": 0.87}})

    rate = _run(fx.usd_eur_rate(transport=_transport(handler)))
    assert rate == Decimal("0.87")


def test_beide_quellen_tot_ohne_notnagel_none():
    def handler(request: httpx.Request):
        return httpx.Response(500, text="boom")

    assert _run(fx.usd_eur_rate(transport=_transport(handler))) is None


def test_notnagel_letzter_bekannter_kurs():
    def ok(request: httpx.Request):
        return httpx.Response(200, json={"rates": {"EUR": 0.85}})

    def kaputt(request: httpx.Request):
        return httpx.Response(500, text="boom")

    assert _run(fx.usd_eur_rate(transport=_transport(ok))) == Decimal("0.85")
    fx._cache = None  # Cache abgelaufen simulieren, Notnagel bleibt
    assert _run(fx.usd_eur_rate(transport=_transport(kaputt))) == Decimal("0.85")


def test_unplausibler_kurs_verworfen():
    def handler(request: httpx.Request):
        # 86.66 statt 0.8666 (Datenfehler) → verwerfen, zweite Quelle auch kaputt
        if "frankfurter" in str(request.url):
            return httpx.Response(200, json={"rates": {"EUR": 86.66}})
        return httpx.Response(500)

    assert _run(fx.usd_eur_rate(transport=_transport(handler))) is None


def test_notnagel_verfaellt_nach_sieben_tagen():
    """Ein wochenalter Kurs erzeugt keine €-Werte mehr (Panel-Fund)."""
    fx._last_good = (time.monotonic() - 8 * 24 * 3600, Decimal("0.85"))

    def kaputt(request: httpx.Request):
        return httpx.Response(500, text="boom")

    assert _run(fx.usd_eur_rate(transport=_transport(kaputt))) is None


def test_lock_verhindert_doppel_fetch_bei_kaltem_cache():
    """Zwei parallele Aufrufer bei kaltem Cache → genau EIN Upstream-Fetch."""
    calls = {"n": 0}

    async def handler(request: httpx.Request):
        calls["n"] += 1
        await asyncio.sleep(0.02)   # Fenster, in dem der zweite Aufrufer wartet
        return httpx.Response(200, json={"rates": {"EUR": 0.88}})

    async def beide():
        t = _transport(handler)
        return await asyncio.gather(
            fx.usd_eur_rate(transport=t), fx.usd_eur_rate(transport=t))

    r1, r2 = asyncio.run(beide())
    assert r1 == r2 == Decimal("0.88")
    assert calls["n"] == 1


def test_kurs_kommt_exakt_als_decimal_an():
    """parse_float=Decimal: hochpräziser JSON-Kurs ohne float-Umweg (Panel-Fund)."""
    def handler(request: httpx.Request):
        return httpx.Response(
            200, content=b'{"rates": {"EUR": 0.86499999999999999}}',
            headers={"content-type": "application/json"})

    assert _run(fx.usd_eur_rate(transport=_transport(handler))) == Decimal("0.86499999999999999")
