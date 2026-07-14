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

# Auth-Zwang (Issue #1): Die Suite loggt sich mit diesem Passwort ein.
# Bewusst FEST gesetzt (kein setdefault) — so passen Hash und TEST_PASSWORD
# garantiert zusammen, egal was CI/gates.sh zusätzlich in die Env legen.
from passlib.context import CryptContext  # noqa: E402 — vor app-Import nötig

TEST_PASSWORD = "gates-test-passwort"
os.environ["APP_PASSWORD_HASH"] = CryptContext(schemes=["bcrypt"]).hash(TEST_PASSWORD)

import pytest
from fastapi.testclient import TestClient

import app.api.v1.cards as cards_api
import app.services.card_creation as card_creation
from app.main import app


@pytest.fixture(scope="session")
def client():
    """
    TestClient als Context-Manager → lifespan läuft: create_all +
    Light-Migrations + Passwort-Guard + Set-Seed. Damit testen wir genau den
    Migrationspfad, den auch ein frischer Install durchläuft.
    Loggt sich ein und schickt das JWT als Default-Header mit (Issue #1).
    """
    with TestClient(app) as c:
        r = c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": TEST_PASSWORD},
        )
        assert r.status_code == 200, f"Test-Login fehlgeschlagen: {r.text}"
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield c


@pytest.fixture(scope="session")
def anon_client(client):
    """
    Client OHNE Token — für 401-Tests. Hängt am client-Fixture, damit die
    App (lifespan/Seed) sicher initialisiert ist; eigener TestClient ohne
    Context-Manager, damit kein zweiter lifespan-Lauf nötig ist.
    """
    return TestClient(app)


@pytest.fixture(scope="session")
def test_password():
    """Klartext-Testpasswort passend zum in conftest gesetzten Hash."""
    return TEST_PASSWORD


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
