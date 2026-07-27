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
from pathlib import Path

from app.config import settings


def _dec(v) -> Decimal:
    return Decimal(str(v)) if v is not None else Decimal("0")


def _jpeg_bytes() -> bytes:
    """Kleines echtes JPEG (für den Endungswechsel-Test .png → .jpg)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 14), color=(30, 30, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _sealed_files(pid: int) -> list[str]:
    """Alle Bilddateien eines Sealed-Produkts im Bildverzeichnis (Orphan-Check)."""
    d = Path(settings.images_dir)
    return sorted(p.name for p in d.glob(f"sealed_{pid}.*")) + sorted(
        p.name for p in d.glob(f"sealed_{pid}_thumb.*")
    )


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


# ── Härtung #38: Eingabevalidierung (Negativfälle) ────────────────────────────

def test_sealed_create_rejects_invalid_enums(client):
    assert client.post("/api/v1/sealed", json={"name": "X", "typ": "Quatsch"}).status_code == 422
    assert client.post("/api/v1/sealed", json={"name": "X", "zustand": "Kaputt"}).status_code == 422


def test_sealed_create_rejects_bad_money(client):
    # Negativ (verfälscht Statistik) und über Numeric(8,2) hinaus → 422 statt 500.
    assert client.post("/api/v1/sealed", json={"name": "X", "kaufpreis_eur": "-1"}).status_code == 422
    assert client.post("/api/v1/sealed", json={"name": "X", "wert_eur": "-0.01"}).status_code == 422
    assert client.post("/api/v1/sealed", json={"name": "X", "wert_eur": "12345678.90"}).status_code == 422


def test_sealed_rejects_empty_or_whitespace_name(client):
    # Anlegen: leer bzw. nur Leerzeichen → 422
    assert client.post("/api/v1/sealed", json={"name": ""}).status_code == 422
    assert client.post("/api/v1/sealed", json={"name": "   "}).status_code == 422
    # Update: explizites null bzw. Whitespace → 422 (name ist NOT NULL)
    p = _create(client, "Bearbeitbar")
    pid = p["id"]
    try:
        assert client.put(f"/api/v1/sealed/{pid}", json={"name": None}).status_code == 422
        assert client.put(f"/api/v1/sealed/{pid}", json={"name": "   "}).status_code == 422
        # Der gültige Name blieb erhalten
        assert client.get(f"/api/v1/sealed/{pid}").json()["name"] == "Bearbeitbar"
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_sealed_rejects_too_many_and_too_long_sets(client):
    assert client.post(
        "/api/v1/sealed", json={"name": "X", "set_codes": ["A" * 33]}
    ).status_code == 422
    assert client.post(
        "/api/v1/sealed", json={"name": "X", "set_codes": [f"S{i}" for i in range(51)]}
    ).status_code == 422


def test_sealed_set_codes_stored_uppercased(client):
    # Kleinschreibung wird beim Anlegen normalisiert (Voraussetzung f. Filter).
    p = _create(client, "Klein", set_codes=["obf", "paf"])
    try:
        assert set(p["set_codes"]) == {"OBF", "PAF"}
    finally:
        client.delete(f"/api/v1/sealed/{p['id']}")


def test_sealed_filter_by_set_is_case_insensitive(client):
    p = _create(client, "Case-Set", set_codes=["OBF"])
    pid = p["id"]
    try:
        for q in ("obf", "OBF", " Obf "):
            ids = {i["id"] for i in client.get("/api/v1/sealed", params={"set": q}).json()}
            assert pid in ids, f"Set-Filter case-insensitiv erwartet für {q!r}"
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


# ── Härtung #38: 404 auf unbekannte Id (statt 500) ────────────────────────────

def test_sealed_unknown_id_returns_404(client, png_bytes):
    ghost = 99_000_123
    assert client.get(f"/api/v1/sealed/{ghost}").status_code == 404
    assert client.put(f"/api/v1/sealed/{ghost}", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/v1/sealed/{ghost}").status_code == 404
    assert client.delete(f"/api/v1/sealed/{ghost}/image").status_code == 404
    r = client.post(
        f"/api/v1/sealed/{ghost}/image",
        files={"file": ("box.png", png_bytes, "image/png")},
    )
    assert r.status_code == 404


# ── Härtung #38: Auth-Zwang auf ALLEN mutierenden Endpoints ────────────────────

def test_sealed_mutations_require_auth(anon_client):
    assert anon_client.put("/api/v1/sealed/1", json={"name": "x"}).status_code == 401
    assert anon_client.delete("/api/v1/sealed/1").status_code == 401
    # Datei mitschicken, damit 401 (Auth) eindeutig vor 422 (Body) greift
    r = anon_client.post(
        "/api/v1/sealed/1/image",
        files={"file": ("x.png", b"\x89PNG\r\n", "image/png")},
    )
    assert r.status_code == 401
    assert anon_client.delete("/api/v1/sealed/1/image").status_code == 401


# ── Härtung #38: Löschen räumt Join-Zeilen (keine Waisen) ─────────────────────

def test_delete_sealed_removes_join_rows(client):
    p = _create(client, "Mit-Sets", set_codes=["OBF", "PAF"])
    pid = p["id"]
    client.delete(f"/api/v1/sealed/{pid}")
    # Backup spiegelt die DB → keine sealed_product_sets-Zeile darf auf pid zeigen
    payload = json.loads(
        zipfile.ZipFile(io.BytesIO(client.get("/api/v1/data/backup").content)).read("data.json")
    )
    # Tabelle MUSS im Backup stehen — sonst würde .get(…, []) eine fehlende
    # Tabelle fälschlich als „keine Waisen" durchwinken (Codex-Review).
    assert "sealed_product_sets" in payload["tables"]
    orphans = [
        row for row in payload["tables"]["sealed_product_sets"]
        if row["sealed_product_id"] == pid
    ]
    assert orphans == [], "Join-Zeilen nach Produkt-Löschung verwaist"


# ── Härtung #38: Bild-Ablage lässt bei Endungswechsel keine Waisen ────────────

def test_sealed_image_reupload_other_ext_leaves_no_orphan(client, png_bytes):
    p = _create(client, "Bild-Wechsel")
    pid = p["id"]
    try:
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("box.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200, r.text
        assert r.json()["bild_pfad"].endswith(".png")
        assert _sealed_files(pid) == [f"sealed_{pid}.png", f"sealed_{pid}_thumb.png"]

        # Re-Upload mit anderer Endung → alte .png-Dateien dürfen nicht bleiben
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("box.jpg", _jpeg_bytes(), "image/jpeg")},
        )
        assert r.status_code == 200, r.text
        assert r.json()["bild_pfad"].endswith(".jpg")
        assert _sealed_files(pid) == [f"sealed_{pid}.jpg", f"sealed_{pid}_thumb.jpg"], (
            "Endungswechsel hat Alt-Dateien verwaisen lassen"
        )

        # Löschen entfernt die Dateien wieder vollständig
        assert client.delete(f"/api/v1/sealed/{pid}/image").status_code == 200
        assert _sealed_files(pid) == []
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


# ── Härtung #38: Validierung greift auch im UPDATE-Pfad (nicht nur Create) ─────

def test_sealed_update_rejects_invalid_values(client):
    # SealedProductUpdate traegt dieselben Validatoren separat — hier explizit
    # ueber PUT geprueft, sonst waere der Update-Pfad false-green (Claude-Review).
    p = _create(client, "Update-Validierung")
    pid = p["id"]
    try:
        assert client.put(f"/api/v1/sealed/{pid}", json={"typ": "Quatsch"}).status_code == 422
        assert client.put(f"/api/v1/sealed/{pid}", json={"zustand": "Kaputt"}).status_code == 422
        assert client.put(f"/api/v1/sealed/{pid}", json={"kaufpreis_eur": "-1"}).status_code == 422
        assert client.put(f"/api/v1/sealed/{pid}", json={"wert_eur": "12345678.90"}).status_code == 422
        assert client.put(
            f"/api/v1/sealed/{pid}", json={"set_codes": ["A" * 33]}
        ).status_code == 422
        # Normalisierung (uppercase/dedup) gilt auch beim Update
        r = client.put(f"/api/v1/sealed/{pid}", json={"set_codes": ["obf", "obf", " paf "]})
        assert set(r.json()["set_codes"]) == {"OBF", "PAF"}
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_sealed_rejects_huge_set_codes_list(client):
    # Roh-Liste jenseits von MAX_SET_CODES_RAW (200) prallt auf FELDEBENE ab,
    # bevor sie ueberhaupt dedupliziert/verarbeitet wird (Codex-Review C5).
    assert client.post(
        "/api/v1/sealed", json={"name": "X", "set_codes": ["A"] * 300}
    ).status_code == 422


def test_sealed_filter_matches_mixed_case_stored_code(client):
    # Ehrlicher Case-insensitiv-Test: ein GEMISCHT geschriebener Code wird direkt
    # (unter Umgehung der Upper-Normalisierung) in die Join-Tabelle gelegt, wie
    # ihn Altbestand aus v1.6.0 haben koennte. Der Filter muss ihn per upper()
    # trotzdem finden (Codex-Review C6). Ein Plain-Vergleich waere hier rot.
    from app.database import SessionLocal
    from app.models.sealed import sealed_product_sets

    p = _create(client, "Legacy-Case")
    pid = p["id"]
    db = SessionLocal()
    try:
        db.execute(
            sealed_product_sets.insert().values(sealed_product_id=pid, set_code="oBf")
        )
        db.commit()
    finally:
        db.close()
    try:
        for q in ("obf", "OBF", "oBf", " Obf "):
            ids = {i["id"] for i in client.get("/api/v1/sealed", params={"set": q}).json()}
            assert pid in ids, f"gemischt gespeicherter Code via {q!r} nicht gefunden"
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


# ── Härtung #38: Datei-Aufraeumen ist best-effort, DB ist die Wahrheit ─────────

def test_delete_image_survives_unlink_failure(client, png_bytes, monkeypatch):
    # Schlaegt das Loeschen der Bilddatei fehl (z. B. PermissionError), MUSS der
    # Endpoint nach dem durablen Commit trotzdem 200 liefern und die DB-Felder
    # geleert haben — ein Datei-Leak ist tolerierbar, ein 500 nach Commit nicht.
    import pathlib

    p = _create(client, "Unlink-Fehler")
    pid = p["id"]
    try:
        client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("b.png", png_bytes, "image/png")},
        )

        real_unlink = pathlib.Path.unlink

        def boom(self, *a, **k):
            raise OSError("simulierter Loeschfehler")

        monkeypatch.setattr(pathlib.Path, "unlink", boom)
        r = client.delete(f"/api/v1/sealed/{pid}/image")
        monkeypatch.setattr(pathlib.Path, "unlink", real_unlink)

        assert r.status_code == 200
        assert r.json()["bild_pfad"] is None
        # DB-Feld ist trotz Datei-Loeschfehler geleert (durabel committet)
        assert client.get(f"/api/v1/sealed/{pid}").json()["bild_pfad"] is None
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_upload_commit_failure_keeps_old_image(client, png_bytes, monkeypatch):
    # Kern der #38-Haertung: schlaegt der Commit beim Re-Upload (Endungswechsel)
    # fehl, darf die alte Datei NICHT geloescht sein und die DB muss weiter auf
    # sie zeigen (Orphan-Clean laeuft erst NACH dem Commit). Panel-Blocker.
    import sqlalchemy.orm

    p = _create(client, "Commit-Fehler")
    pid = p["id"]
    try:
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("b.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200
        assert _sealed_files(pid) == [f"sealed_{pid}.png", f"sealed_{pid}_thumb.png"]

        real_commit = sqlalchemy.orm.Session.commit

        def boom(self):
            raise RuntimeError("simulierter Commit-Fehler")

        monkeypatch.setattr(sqlalchemy.orm.Session, "commit", boom)
        try:
            resp = client.post(
                f"/api/v1/sealed/{pid}/image",
                files={"file": ("b.jpg", _jpeg_bytes(), "image/jpeg")},
            )
            # Je nach TestClient-Konfig: 500-Antwort ODER durchgereichte Exception
            assert resp.status_code == 500
        except RuntimeError:
            pass
        finally:
            monkeypatch.setattr(sqlalchemy.orm.Session, "commit", real_commit)

        # Invariante: alte .png-Datei ueberlebt, DB zeigt weiter auf .png
        assert f"sealed_{pid}.png" in _sealed_files(pid), "Alt-Datei vor dem Commit geloescht!"
        assert client.get(f"/api/v1/sealed/{pid}").json()["bild_pfad"].endswith(".png")
    finally:
        client.delete(f"/api/v1/sealed/{pid}")
