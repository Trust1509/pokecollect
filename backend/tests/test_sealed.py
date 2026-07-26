"""
Sealed-Produkte (Issue #35) — eigene Entität, n:m-Set-Bezug, manueller Wert.

Läuft gegen die session-weite Test-DB (andere Tests hinterlassen Daten) →
Stats werden als Delta gegen den Vorzustand geprüft, angelegte Produkte werden
in finally wieder gelöscht.
"""

import io
import json
import zipfile
from decimal import Decimal


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _create(client, name="Display Obsidianflammen", **extra) -> dict:
    r = client.post("/api/v1/sealed", json={"name": name, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _stats(client) -> dict:
    r = client.get("/api/v1/cards/meta/stats")
    assert r.status_code == 200
    return r.json()


# ── CRUD + G/V ────────────────────────────────────────────────────────────────

def test_sealed_crud_and_gv(client):
    p = _create(
        client, "Booster-Bundle 151", typ="Bundle", zustand="Versiegelt",
        kaufpreis_eur="30.00", wert_eur="45.00", kaufdatum="2026-07-20",
        notizen="Größenprüfung äöü",
    )
    pid = p["id"]
    try:
        assert p["typ"] == "Bundle"
        assert p["zustand"] == "Versiegelt"
        # Unrealisierter G/V = wert − kaufpreis = 15.00
        assert _dec(p["unrealisierter_gv_eur"]) == Decimal("15.00")

        got = client.get(f"/api/v1/sealed/{pid}").json()
        assert got["name"] == "Booster-Bundle 151"
        assert got["kaufdatum"] == "2026-07-20"
        assert got["notizen"] == "Größenprüfung äöü"

        # Update: Wert ändern → G/V zieht nach
        r = client.put(f"/api/v1/sealed/{pid}", json={"wert_eur": "50.00"})
        assert r.status_code == 200
        assert _dec(r.json()["unrealisierter_gv_eur"]) == Decimal("20.00")

        # In der Liste enthalten
        lst = client.get("/api/v1/sealed").json()
        assert any(item["id"] == pid for item in lst)
    finally:
        assert client.delete(f"/api/v1/sealed/{pid}").status_code == 204
    # Nach Delete weg
    assert client.get(f"/api/v1/sealed/{pid}").status_code == 404


def test_sealed_gv_only_one_side_is_none(client):
    a = _create(client, "Nur-Wert", wert_eur="10.00")            # kein Kaufpreis
    b = _create(client, "Nur-Kaufpreis", kaufpreis_eur="8.00")   # kein Wert
    try:
        assert client.get(f"/api/v1/sealed/{a['id']}").json()["unrealisierter_gv_eur"] is None
        assert client.get(f"/api/v1/sealed/{b['id']}").json()["unrealisierter_gv_eur"] is None
    finally:
        client.delete(f"/api/v1/sealed/{a['id']}")
        client.delete(f"/api/v1/sealed/{b['id']}")


# ── n:m Set-Zuordnung ─────────────────────────────────────────────────────────

def test_sealed_nm_sets_create_dedup_replace(client):
    # Anlegen mit mehreren Sets (inkl. Duplikat, Leerwert, Whitespace → normalisiert)
    p = _create(client, "Multi-Set-Bundle", set_codes=["OBF", "OBF", " PAF ", ""])
    pid = p["id"]
    try:
        assert set(p["set_codes"]) == {"OBF", "PAF"}

        # Ersetzen (n:m komplett neu)
        r = client.put(f"/api/v1/sealed/{pid}", json={"set_codes": ["MEW"]})
        assert set(r.json()["set_codes"]) == {"MEW"}

        # set_codes NICHT mitschicken → unverändert
        r = client.put(f"/api/v1/sealed/{pid}", json={"name": "Umbenannt"})
        assert r.json()["name"] == "Umbenannt"
        assert set(r.json()["set_codes"]) == {"MEW"}

        # Leere Liste → alle Sets entfernen
        r = client.put(f"/api/v1/sealed/{pid}", json={"set_codes": []})
        assert r.json()["set_codes"] == []
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_sealed_filter_by_set(client):
    a = _create(client, "A", set_codes=["OBF", "PAF"])
    b = _create(client, "B", set_codes=["OBF"])
    c = _create(client, "C", set_codes=[])
    try:
        ids_paf = {i["id"] for i in client.get("/api/v1/sealed", params={"set": "PAF"}).json()}
        assert a["id"] in ids_paf and b["id"] not in ids_paf and c["id"] not in ids_paf

        ids_obf = {i["id"] for i in client.get("/api/v1/sealed", params={"set": "OBF"}).json()}
        assert {a["id"], b["id"]} <= ids_obf and c["id"] not in ids_obf
    finally:
        for p in (a, b, c):
            client.delete(f"/api/v1/sealed/{p['id']}")


def test_sealed_filter_by_typ_and_zustand(client):
    a = _create(client, "ETB versiegelt", typ="ETB", zustand="Versiegelt")
    b = _create(client, "Tin geöffnet", typ="Tin", zustand="Geöffnet")
    try:
        ids_etb = {i["id"] for i in client.get("/api/v1/sealed", params={"typ": "ETB"}).json()}
        assert a["id"] in ids_etb and b["id"] not in ids_etb

        ids_geoeffnet = {i["id"] for i in client.get("/api/v1/sealed", params={"zustand": "Geöffnet"}).json()}
        assert b["id"] in ids_geoeffnet and a["id"] not in ids_geoeffnet
    finally:
        for p in (a, b):
            client.delete(f"/api/v1/sealed/{p['id']}")


# ── Enums ─────────────────────────────────────────────────────────────────────

def test_sealed_enums(client):
    r = client.get("/api/v1/sealed/meta/enums")
    assert r.status_code == 200
    body = r.json()
    assert "Booster" in body["typ"] and "Sonstiges" in body["typ"]
    assert body["zustand"] == ["Versiegelt", "Geöffnet", "Beschädigt"]


# ── Bild-Upload (bestehende Pipeline) ─────────────────────────────────────────

def test_sealed_image_upload_and_delete(client, png_bytes):
    p = _create(client, "Bild-Display")
    pid = p["id"]
    try:
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("box.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["bild_pfad"] and body["bild_thumbnail_pfad"]

        r = client.delete(f"/api/v1/sealed/{pid}/image")
        assert r.status_code == 200
        assert r.json()["bild_pfad"] is None
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_sealed_image_rejects_non_image(client):
    p = _create(client, "Kein-Bild")
    pid = p["id"]
    try:
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("x.txt", b"not an image", "text/plain")},
        )
        assert r.status_code == 400
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


# ── Auth-Zwang (ADR-0003) ─────────────────────────────────────────────────────

def test_sealed_requires_auth(anon_client):
    assert anon_client.get("/api/v1/sealed").status_code == 401
    assert anon_client.post("/api/v1/sealed", json={"name": "x"}).status_code == 401
    assert anon_client.get("/api/v1/sealed/meta/enums").status_code == 401


# ── Statistik: Sealed getrennt + Karten+Sealed kombiniert (#35, baut auf #26) ──

def test_stats_include_sealed_and_combined(client):
    before = _stats(client)
    # A: Kaufpreis 30, Wert 45 → Einstand +30, G/V +15, Wert +45
    a = _create(client, "Stat-A", kaufpreis_eur="30.00", wert_eur="45.00")
    # B: nur Wert 10 → Wert +10, weder Einstand noch G/V
    b = _create(client, "Stat-B", wert_eur="10.00")
    try:
        after = _stats(client)
        assert after["sealed_anzahl"] - before["sealed_anzahl"] == 2
        assert _dec(after["sealed_wert_eur"]) - _dec(before["sealed_wert_eur"]) == Decimal("55.00")
        assert _dec(after["sealed_einstand_eur"]) - _dec(before["sealed_einstand_eur"]) == Decimal("30.00")
        assert _dec(after["sealed_unrealisierter_gv_eur"]) - _dec(before["sealed_unrealisierter_gv_eur"]) == Decimal("15.00")
        # kombiniert = Karten + Sealed; hier ändert sich nur Sealed → Delta 55
        assert _dec(after["kombiniert_wert_eur"]) - _dec(before["kombiniert_wert_eur"]) == Decimal("55.00")
        assert _dec(after["kombiniert_einstand_eur"]) - _dec(before["kombiniert_einstand_eur"]) == Decimal("30.00")
    finally:
        for p in (a, b):
            client.delete(f"/api/v1/sealed/{p['id']}")


# ── Backup/Restore erfasst die neuen Tabellen (generischer Mechanismus) ───────

def test_backup_restore_includes_sealed(client):
    p = _create(
        client, "Backup-Display äöü", typ="Display", zustand="Versiegelt",
        kaufpreis_eur="20.00", wert_eur="35.00", set_codes=["OBF", "PAF"],
    )
    pid = p["id"]
    try:
        # Backup ziehen — sealed_products + sealed_product_sets müssen drin sein
        r = client.get("/api/v1/data/backup")
        assert r.status_code == 200
        backup_bytes = r.content
        zf = zipfile.ZipFile(io.BytesIO(backup_bytes))
        payload = json.loads(zf.read("data.json"))
        assert "sealed_products" in payload["tables"]
        assert "sealed_product_sets" in payload["tables"]
        assert any(row["id"] == pid for row in payload["tables"]["sealed_products"])
        our_sets = {
            row["set_code"]
            for row in payload["tables"]["sealed_product_sets"]
            if row["sealed_product_id"] == pid
        }
        assert our_sets == {"OBF", "PAF"}

        # Produkt löschen → dann Restore muss es inkl. n:m + G/V zurückbringen
        client.delete(f"/api/v1/sealed/{pid}")
        assert client.get(f"/api/v1/sealed/{pid}").status_code == 404

        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("backup.zip", backup_bytes, "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["restored"]["sealed_products"] >= 1

        got = client.get(f"/api/v1/sealed/{pid}")
        assert got.status_code == 200, "Sealed-Produkt hat den Backup-Roundtrip nicht überlebt"
        body = got.json()
        assert body["name"] == "Backup-Display äöü"
        assert set(body["set_codes"]) == {"OBF", "PAF"}, "n:m-Set-Zuordnung nicht wiederhergestellt"
        assert _dec(body["unrealisierter_gv_eur"]) == Decimal("15.00")
    finally:
        client.delete(f"/api/v1/sealed/{pid}")
