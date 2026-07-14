"""
Test-Setup: läuft gegen ein echtes PostgreSQL (kein SQLite — SQLite erzwingt
keine FKs und kennt die Light-Migrations-Syntax nicht). DATABASE_URL kommt aus
der Umgebung (CI-Service bzw. scripts/gates.sh); der Default passt zum
Wegwerf-Postgres, das gates.sh startet.

Wichtig: Env-Variablen MÜSSEN vor dem Import von app.* gesetzt sein, weil
app.config.Settings() beim Import instanziiert wird.
"""

import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://pokecollect:pokecollect@localhost:5440/pokecollect_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret")
# StaticFiles verlangt ein existierendes Verzeichnis
os.environ.setdefault("IMAGES_DIR", tempfile.mkdtemp(prefix="pokecollect-test-images-"))

import pytest
from fastapi.testclient import TestClient

import app.api.v1.cards as cards_api
import app.services.card_creation as card_creation
from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    TestClient als Context-Manager → lifespan läuft: create_all +
    Light-Migrations + Set-Seed. Damit testen wir genau den Migrationspfad,
    den auch ein frischer Install durchläuft.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def no_external_fetch(monkeypatch):
    """Hintergrund-Task würde TCGdex übers Netz befragen — in Tests abklemmen."""

    async def _noop(card_id: int):
        return None

    monkeypatch.setattr(cards_api, "_trigger_image_fetch", _noop)
    monkeypatch.setattr(card_creation, "_trigger_image_fetch", _noop)


@pytest.fixture()
def png_bytes() -> bytes:
    """Ein kleines, echtes PNG für Upload-/Scan-Tests."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (10, 14), color=(200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()
