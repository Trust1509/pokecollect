"""
CSV-Export + Backup/Restore (Issue #17).

- CSV: BOM, Semikolon, alle Kartenspalten, Umlaute überleben.
- Backup→Restore-Roundtrip: Zählstände (Karten, Sammlungen, n:m) und eine
  Bilddatei überleben; nach dem Restore funktionieren neue INSERTs
  (Sequenzen nachgezogen).
- Restore ohne confirm → 400; kaputte/fremde ZIPs → 400.
"""

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from app.config import settings


@pytest.fixture()
def roundtrip_data(client):
    """Karte mit Umlauten + Sammlung (mit n:m-Zuordnung) + eine Bilddatei."""
    r = client.post(
        "/api/v1/cards",
        json={"kartenname": "Glumanda Jubiläums-Röntgenkarte ß", "besessen": True, "notizen": "Größenprüfung äöü"},
    )
    assert r.status_code == 201
    card_id = r.json()["id"]

    r = client.post("/api/v1/collections", json={"name": "Backup-Binder äö"})
    assert r.status_code in (200, 201)
    collection_id = r.json()["id"]
    r = client.post(f"/api/v1/collections/{collection_id}/cards", json={"card_id": card_id})
    assert r.status_code in (200, 201)

    image = Path(settings.images_dir) / "card_roundtrip_test.jpg"
    image.write_bytes(b"\xff\xd8\xff\xe0FAKEJPEGDATA-roundtrip")

    yield {"card_id": card_id, "collection_id": collection_id, "image": image}

    # Aufräumen (best effort — nach einem Restore existieren die IDs wieder)
    client.delete(f"/api/v1/collections/{collection_id}")
    client.delete(f"/api/v1/cards/{card_id}")
    image.unlink(missing_ok=True)


def _card_count(client) -> int:
    r = client.get("/api/v1/cards", params={"limit": 1})
    assert r.status_code == 200
    return r.json()["total"]


def test_export_csv_bom_columns_umlaute(client, roundtrip_data):
    r = client.get("/api/v1/data/export.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "pokecollect-export-" in r.headers["content-disposition"]
    assert ".csv" in r.headers["content-disposition"]

    raw = r.content
    assert raw.startswith(b"\xef\xbb\xbf"), "UTF-8-BOM fehlt (Excel-Erkennung)"

    text = raw.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text), delimiter=";")
    header = next(reader)
    # Alle Kartenfelder als Spalten
    for col in ("id", "kartenname", "pokedex_nr", "set_edition", "karten_nr",
                "seltenheit", "wert_eur", "notizen", "tcgdex_card_id",
                "hinzugefuegt_am", "aktualisiert_am"):
        assert col in header, f"Spalte {col} fehlt im CSV-Header"

    rows = list(reader)
    name_idx = header.index("kartenname")
    besessen_idx = header.index("besessen")
    ours = [row for row in rows if row[name_idx] == "Glumanda Jubiläums-Röntgenkarte ß"]
    assert ours, "Karte mit Umlauten nicht im CSV gefunden"
    assert ours[0][besessen_idx] == "ja"


def test_backup_restore_roundtrip(client, roundtrip_data):
    cards_before = _card_count(client)
    collections_before = client.get("/api/v1/collections").json()
    image_bytes = roundtrip_data["image"].read_bytes()

    # ── Backup ziehen ────────────────────────────────────────────────────────
    r = client.get("/api/v1/data/backup")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/zip")
    backup_bytes = r.content

    zf = zipfile.ZipFile(io.BytesIO(backup_bytes))
    names = zf.namelist()
    assert "data.json" in names
    assert "images/card_roundtrip_test.jpg" in names

    payload = json.loads(zf.read("data.json"))
    assert payload["format"] == 1
    assert payload["app_version"], "Versionsfeld fehlt im Backup"
    for table in ("pokemon_cards", "collections", "collection_cards",
                  "app_settings", "preis_historie", "gemini_usage",
                  "pokemon_sets", "tcgdex_catalog"):
        assert table in payload["tables"], f"Tabelle {table} fehlt im Backup"
    assert len(payload["tables"]["pokemon_cards"]) == cards_before

    # ── Daten mutieren: Karte + Sammlung löschen, Bild wegwerfen ────────────
    client.delete(f"/api/v1/collections/{roundtrip_data['collection_id']}")
    client.delete(f"/api/v1/cards/{roundtrip_data['card_id']}")
    roundtrip_data["image"].unlink()
    assert _card_count(client) < cards_before

    # ── Restore ──────────────────────────────────────────────────────────────
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", backup_bytes, "application/zip")},
        data={"confirm": "JA_WIRKLICH"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["restored"]["pokemon_cards"] == cards_before
    assert body["images"] >= 1

    # Zählstände überleben
    assert _card_count(client) == cards_before
    collections_after = client.get("/api/v1/collections").json()
    assert {c["id"] for c in collections_after} == {c["id"] for c in collections_before}
    ours = [c for c in collections_after if c["id"] == roundtrip_data["collection_id"]]
    assert ours and ours[0]["karten_anzahl"] == 1, "n:m-Zuordnung hat den Roundtrip nicht überlebt"

    # Karte inkl. Umlauten wieder da
    r = client.get(f"/api/v1/cards/{roundtrip_data['card_id']}")
    assert r.status_code == 200
    assert r.json()["kartenname"] == "Glumanda Jubiläums-Röntgenkarte ß"

    # Bilddatei überlebt byte-identisch
    assert roundtrip_data["image"].read_bytes() == image_bytes

    # Sequenzen nachgezogen: neuer INSERT kollidiert nicht mit Restore-IDs
    r = client.post("/api/v1/cards", json={"kartenname": "Nach-Restore-Karte"})
    assert r.status_code == 201, f"INSERT nach Restore schlug fehl (Sequenz?): {r.text}"
    client.delete(f"/api/v1/cards/{r.json()['id']}")


def test_restore_without_confirm_returns_400(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.json", json.dumps({"format": 1, "app_version": "x", "tables": {}}))
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
    )
    assert r.status_code == 400
    assert "JA_WIRKLICH" in r.json()["detail"]

    # Auch mit falschem Wert → 400, DB bleibt unangetastet
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        data={"confirm": "ja eh"},
    )
    assert r.status_code == 400


def test_restore_rejects_invalid_zip_and_structure(client):
    # Kein ZIP
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", b"das ist kein zip", "application/zip")},
        data={"confirm": "JA_WIRKLICH"},
    )
    assert r.status_code == 400

    # ZIP ohne data.json
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "leer")
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        data={"confirm": "JA_WIRKLICH"},
    )
    assert r.status_code == 400

    # data.json ohne Versionsfeld
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data.json", json.dumps({"tables": {}}))
    r = client.post(
        "/api/v1/data/restore",
        files={"file": ("backup.zip", buf.getvalue(), "application/zip")},
        data={"confirm": "JA_WIRKLICH"},
    )
    assert r.status_code == 400


def test_data_endpoints_require_auth(anon_client):
    assert anon_client.get("/api/v1/data/export.csv").status_code == 401
    assert anon_client.get("/api/v1/data/backup").status_code == 401
    assert anon_client.post("/api/v1/data/restore").status_code == 401
