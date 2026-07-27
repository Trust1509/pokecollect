"""
Security (#37): Pfad-Traversal beim Bild-Löschen.

Ein manipuliertes Backup kann `bild_pfad`/`bild_thumbnail_pfad`/
`bild_original_pfad` mit `../…`- oder absoluten Pfaden füllen. Ohne Prüfung
würde ein späteres Löschen `Path(images_dir).parent / bild_pfad` unlinken —
bei absolutem Pfad ist das der absolute Pfad selbst → beliebige Serverdatei.

Der Fix (`safe_media_path`) lehnt solche Pfade ab: beim Restore werden die
Spalten neutralisiert und vor jedem unlink wird erneut geprüft.
"""

import io
import json
import os
import tempfile
import zipfile


def _create_sealed(client, name="X", **extra) -> dict:
    r = client.post("/api/v1/sealed", json={"name": name, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _rezip_with_modified_payload(backup_bytes: bytes, payload: dict) -> bytes:
    """Backup-ZIP neu bauen: data.json ersetzen, restliche Einträge übernehmen."""
    zin = zipfile.ZipFile(io.BytesIO(backup_bytes))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        zout.writestr("data.json", json.dumps(payload))
        for info in zin.infolist():
            if info.filename != "data.json":
                zout.writestr(info.filename, zin.read(info.filename))
    return buf.getvalue()


def test_restore_neutralizes_absolute_bild_pfad_and_delete_is_safe(client):
    # Opfer-Datei AUSSERHALB des Bildverzeichnisses
    victim = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    victim.write(b"nicht loeschen")
    victim.close()
    victim_path = victim.name

    p = _create_sealed(client, "Traversal-Opfer")
    pid = p["id"]
    try:
        # Echtes Backup ziehen und die eigene Sealed-Zeile mit absolutem Pfad
        # (= Traversal) versehen.
        backup = client.get("/api/v1/data/backup").content
        payload = json.loads(zipfile.ZipFile(io.BytesIO(backup)).read("data.json"))
        hit = False
        for row in payload["tables"]["sealed_products"]:
            if row["id"] == pid:
                row["bild_pfad"] = victim_path  # absoluter Pfad
                hit = True
        assert hit, "Testzeile nicht im Backup gefunden"

        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("b.zip", _rezip_with_modified_payload(backup, payload), "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text

        # (a) Defense-in-depth: der Traversal-Pfad darf NICHT gespeichert worden sein
        got = client.get(f"/api/v1/sealed/{pid}").json()
        assert got["bild_pfad"] is None, "Traversal-Pfad wurde ungefiltert in die DB geschrieben"

        # (b) selbst ein Löschen darf die Datei ausserhalb NICHT entfernen
        assert client.delete(f"/api/v1/sealed/{pid}").status_code == 204
        assert os.path.exists(victim_path), "Löschen hat eine Datei ausserhalb des Bildordners entfernt!"
    finally:
        client.delete(f"/api/v1/sealed/{pid}")
        if os.path.exists(victim_path):
            os.unlink(victim_path)


def test_restore_neutralizes_dotdot_bild_pfad(client):
    # Relativer Ausbruch (../) wird ebenso neutralisiert wie ein absoluter Pfad.
    p = _create_sealed(client, "DotDot-Opfer")
    pid = p["id"]
    try:
        backup = client.get("/api/v1/data/backup").content
        payload = json.loads(zipfile.ZipFile(io.BytesIO(backup)).read("data.json"))
        hit = False
        for row in payload["tables"]["sealed_products"]:
            if row["id"] == pid:
                row["bild_pfad"] = "images/../../../../etc/passwd"
                hit = True
        assert hit, "Testzeile nicht im Backup gefunden — Mutation lief ins Leere"
        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("b.zip", _rezip_with_modified_payload(backup, payload), "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text
        assert client.get(f"/api/v1/sealed/{pid}").json()["bild_pfad"] is None
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_restore_neutralizes_traversal_in_card_columns(client):
    # #37 nennt Karten UND Sealed — hier die Karten-Spalte bild_karte_pfad.
    r = client.post(
        "/api/v1/cards",
        json={
            "kartenname": "Traversal-Karte", "englischer_name": "Traversal Card",
            "set_edition": "OBF", "karten_nr": "001", "besessen": True,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    try:
        backup = client.get("/api/v1/data/backup").content
        payload = json.loads(zipfile.ZipFile(io.BytesIO(backup)).read("data.json"))
        hit = False
        for row in payload["tables"]["pokemon_cards"]:
            if row["id"] == cid:
                row["bild_karte_pfad"] = "/etc/shadow"                 # absolut
                row["bild_thumbnail_pfad"] = "images/../../../../etc/hosts"  # ../
                row["bild_original_pfad"] = "images/../secret"          # relativer Ausbruch
                hit = True
        assert hit, "Testzeile nicht im Backup gefunden — Mutation lief ins Leere"
        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("b.zip", _rezip_with_modified_payload(backup, payload), "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text
        got = client.get(f"/api/v1/cards/{cid}").json()
        # ALLE drei lokalen Karten-Pfadspalten müssen neutralisiert sein
        assert got["bild_karte_pfad"] is None
        assert got["bild_thumbnail_pfad"] is None
        assert got["bild_original_pfad"] is None
    finally:
        client.delete(f"/api/v1/cards/{cid}")


def test_safe_media_path_contract():
    # Die gemeinsame Sicherheits-Primitive direkt (beide Image-Services nutzen sie).
    from pathlib import Path

    from app.config import settings
    from app.services.card_images import safe_media_path

    media_root = Path(settings.images_dir).resolve()

    # Gültiger relativer Pfad → aufgelöst UNTER dem Bildordner. bild_* wird als
    # relativ zu images_dir.parent gespeichert, beginnt also mit dem Basisnamen
    # des Bildordners (in prod „images/…", im Teststand der mkdtemp-Name).
    valid_rel = f"{Path(settings.images_dir).name}/card_1.jpg"
    ok = safe_media_path(valid_rel)
    assert ok is not None and ok.is_relative_to(media_root)

    # Leer/None, absolut, ../-Ausbruch, Geschwister ausserhalb images/ → None
    assert safe_media_path(None) is None
    assert safe_media_path("") is None
    assert safe_media_path("/etc/passwd") is None
    assert safe_media_path("images/../../etc/passwd") is None
    assert safe_media_path("../secret") is None
    # „main.py" läge unter images_dir.parent, aber NICHT unter dem Bildordner
    assert safe_media_path("main.py") is None
    # Der Bildordner SELBST ist kein löschbares Medium (sonst IsADirectoryError)
    assert safe_media_path(media_root.name) is None
    # Fail-closed statt Exception: NUL-Byte und Nicht-String → None
    assert safe_media_path("images/a\x00b.jpg") is None
    assert safe_media_path({"x": 1}) is None  # type: ignore[arg-type]
    assert safe_media_path(123) is None  # type: ignore[arg-type]


# ── unlink-Guard ISOLIERT (unabhängig vom Restore-Filter) ─────────────────────

def test_delete_sealed_with_malicious_db_path_spares_outside_file(client):
    # Gefährlichen Pfad DIREKT in die DB legen (Restore-Filter umgehen) und dann
    # löschen → der safe_media_path-Guard im Service verhindert das unlink
    # ausserhalb. OHNE den Guard verschwände die Opfer-Datei. (Codex/Claude)
    from app.database import SessionLocal
    from app.models.sealed import SealedProduct

    victim = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    victim.write(b"x")
    victim.close()
    pid = _create_sealed(client, "Boeser-DB-Pfad")["id"]
    db = SessionLocal()
    try:
        obj = db.get(SealedProduct, pid)
        obj.bild_pfad = victim.name                       # absoluter Pfad
        obj.bild_thumbnail_pfad = "images/../../../../etc/passwd"  # ../
        db.commit()
    finally:
        db.close()
    try:
        assert client.delete(f"/api/v1/sealed/{pid}").status_code == 204
        assert os.path.exists(victim.name), "unlink-Guard fehlt: Datei ausserhalb gelöscht!"
    finally:
        client.delete(f"/api/v1/sealed/{pid}")
        if os.path.exists(victim.name):
            os.unlink(victim.name)


def test_delete_card_image_with_malicious_db_path_spares_outside_file(client):
    from app.database import SessionLocal
    from app.models.card import PokemonCard

    victim = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    victim.write(b"x")
    victim.close()
    r = client.post(
        "/api/v1/cards",
        json={
            "kartenname": "Boese-Karte", "englischer_name": "Evil",
            "set_edition": "OBF", "karten_nr": "002", "besessen": True,
        },
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    db = SessionLocal()
    try:
        obj = db.get(PokemonCard, cid)
        obj.bild_karte_pfad = victim.name            # absoluter Pfad
        obj.bild_original_pfad = "/etc/passwd"
        db.commit()
    finally:
        db.close()
    try:
        assert client.delete(f"/api/v1/cards/{cid}/image").status_code == 200
        assert os.path.exists(victim.name), "unlink-Guard fehlt (Karte): Datei ausserhalb gelöscht!"
    finally:
        client.delete(f"/api/v1/cards/{cid}")
        if os.path.exists(victim.name):
            os.unlink(victim.name)


# ── Gegenprobe: legitimer Pfad darf NICHT über-neutralisiert werden ───────────

def test_restore_keeps_legit_image_path_and_stays_deletable(client, png_bytes):
    # Fängt eine Über-Nullung im Restore-Filter (bzw. falls jemand die Grenze auf
    # images_dir statt .parent verschöbe): ein LEGITIMER Bildpfad überlebt den
    # Restore und bleibt danach löschbar. (Claude-Review)
    pid = _create_sealed(client, "Legit-Bild")["id"]
    try:
        r = client.post(
            f"/api/v1/sealed/{pid}/image",
            files={"file": ("b.png", png_bytes, "image/png")},
        )
        assert r.status_code == 200, r.text
        legit = r.json()["bild_pfad"]
        assert legit, "Upload lieferte keinen Pfad"

        backup = client.get("/api/v1/data/backup").content
        r = client.post(
            "/api/v1/data/restore",
            files={"file": ("b.zip", backup, "application/zip")},
            data={"confirm": "JA_WIRKLICH"},
        )
        assert r.status_code == 200, r.text
        # Legitimer Pfad überlebt den Restore unverändert (nicht genullt)
        assert client.get(f"/api/v1/sealed/{pid}").json()["bild_pfad"] == legit
        # … und ist danach noch löschbar (Datei wird tatsächlich entfernt)
        assert client.delete(f"/api/v1/sealed/{pid}/image").status_code == 200
        assert client.get(f"/api/v1/sealed/{pid}").json()["bild_pfad"] is None
    finally:
        client.delete(f"/api/v1/sealed/{pid}")
