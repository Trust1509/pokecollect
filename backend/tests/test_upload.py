"""
Upload-Härtung (Issue #2): Suffix-Allowlist, Content-Type image/*,
12-MB-Limit, Rohdatei-Cleanup bei kaputten Bildern.
"""

import io
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings


@pytest.fixture()
def card_id(client):
    r = client.post(
        "/api/v1/cards",
        json={"kartenname": "Uploadmon", "besessen": True},
    )
    assert r.status_code == 201
    cid = r.json()["id"]
    yield cid
    client.delete(f"/api/v1/cards/{cid}")


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 14), color=(200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def test_upload_rejects_forbidden_suffix(client, card_id):
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("boese.svg", b"<svg xmlns='x'/>", "image/svg+xml")},
    )
    assert r.status_code == 400
    assert ".svg" in r.json()["detail"]


def test_upload_rejects_non_image_content_type(client, card_id):
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("harmlos.png", b"<html></html>", "text/html")},
    )
    assert r.status_code == 400


def test_upload_rejects_oversize(client, card_id):
    big = b"\x00" * (12 * 1024 * 1024 + 1)
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("gross.jpg", big, "image/jpeg")},
    )
    assert r.status_code == 413


def test_upload_cleans_up_broken_image(client, card_id):
    """Erlaubtes Suffix + image/*, aber kaputte Bytes → 400 UND keine Rohdatei."""
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("kaputt.png", b"definitiv-kein-png", "image/png")},
    )
    assert r.status_code == 400
    leftovers = [
        p for p in Path(settings.images_dir).glob(f"card_{card_id}*")
    ]
    assert leftovers == [], f"Rohdatei blieb liegen: {leftovers}"


def test_upload_accepts_valid_png(client, card_id):
    r = client.post(
        f"/api/v1/cards/{card_id}/image",
        files={"file": ("gut.png", _png_bytes(), "image/png")},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["bild_karte_pfad"]
    assert body["bild_thumbnail_pfad"]
    full = Path(settings.images_dir).parent / body["bild_karte_pfad"]
    assert full.exists()
    # Aufräumen fürs nächste Testfile
    client.delete(f"/api/v1/cards/{card_id}/image")
