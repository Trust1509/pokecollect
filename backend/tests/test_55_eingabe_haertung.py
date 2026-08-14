"""
#55: Ungültige Eingaben werden abgelehnt (4xx) statt einen Serverfehler
auszulösen — die Befunde des Schemathesis-Erstlaufs.

Zwei Fehlerklassen, beide am laufenden Teststand reproduziert (2026-08-14):
  A) Steuerzeichen (NUL) im Text → PostgreSQL kann sie nicht speichern → 500.
  B) Ausdrückliches `null` auf einem Pflichtfeld → IntegrityError bzw.
     int("None") → 500.
"""

import pytest

from app.schemas._validators import (
    reject_control_chars, reject_explicit_null, strip_control_chars,
)

NUL = "A" + chr(0) + "B"     # nie als Literal ins Skript — Werkzeuge stolpern


# ── Reine Validator-Ebene ────────────────────────────────────────────────────

def test_reject_control_chars():
    for schlecht in (NUL, "x" + chr(1), "y" + chr(127), chr(27) + "[31m"):
        with pytest.raises(ValueError):
            reject_control_chars(schlecht)


def test_reject_control_chars_laesst_normales_durch():
    for gut in ("Glurak-ex", "Weiße Flammen (WHT)", "メガライボルトex",
                "Zeile1\nZeile2\tTab", "", None, 42, 1.5):
        assert reject_control_chars(gut) == gut


def test_reject_control_chars_prueft_listen():
    assert reject_control_chars(["OBF", "PAF"]) == ["OBF", "PAF"]
    with pytest.raises(ValueError):
        reject_control_chars(["OBF", NUL])


def test_reject_control_chars_begrenzt_tiefe_und_laenge():
    """Ohne Grenzen wäre die Prüfung selbst die 500-Quelle (RecursionError)
    bzw. liefe erst durch Millionen Elemente (Panel-Funde)."""
    tief = ["x"]
    for _ in range(30):
        tief = [tief]
    with pytest.raises(ValueError):
        reject_control_chars(tief)
    with pytest.raises(ValueError):
        reject_control_chars(["x"] * 10_001)


def test_strip_control_chars_entfernt_statt_abzulehnen():
    """Serverseitige Texte (OCR/LLM) werden gesäubert — Ablehnen wäre dort ein
    Absturz ohne Client, den man korrigieren könnte."""
    assert strip_control_chars("Seiten" + chr(12) + "vorschub") == "Seitenvorschub"
    assert strip_control_chars("Glurak-ex") == "Glurak-ex"
    assert strip_control_chars(None) is None
    assert strip_control_chars(42) == 42


def test_scan_liest_modellantwort_mit_steuerzeichen(monkeypatch):
    """Panel-MAJOR: ScanRawRead wird auch SERVERSEITIG aus LLM-/OCR-Text
    gebaut. Ein Steuerzeichen darf den Scan nicht sprengen — es wird
    entfernt, die Karte bleibt lesbar."""
    from app.services.scan import vlm

    reads = vlm.reads_from_json([{
        "name": "Glurak" + chr(7) + "-ex",
        "set_code": "OBF" + chr(12),
        "number": "125/197",
    }])
    assert reads is not None and len(reads) == 1
    assert reads[0].name == "Glurak-ex"     # gesäubert, kein Absturz
    assert reads[0].set_code == "OBF"


def test_ocr_parse_saeubert_steuerzeichen():
    from app.services.scan.ocr import _parse

    parsed = _parse("Glurak" + chr(12) + "\nOBF 125/197")
    assert parsed["name"] is None or chr(12) not in parsed["name"]


def test_reject_explicit_null():
    with pytest.raises(ValueError):
        reject_explicit_null(None)
    assert reject_explicit_null(False) is False   # False ist ein gültiger Wert!
    assert reject_explicit_null(0) == 0
    assert reject_explicit_null("") == ""


# ── API-Ebene: die konkreten Schemathesis-Befunde ───────────────────────────

@pytest.fixture()
def karte(client):
    r = client.post("/api/v1/cards", json={"kartenname": "H55-Testkarte",
                                           "besessen": True})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    yield cid
    # besessen zurücksetzen — DELETE lehnt nicht-besessene Karten ab, die
    # Testkarte bliebe sonst liegen (Panel-Fund).
    client.put(f"/api/v1/cards/{cid}", json={"besessen": True})
    assert client.delete(f"/api/v1/cards/{cid}").status_code == 204


@pytest.fixture()
def sammlung(client):
    r = client.post("/api/v1/collections", json={"name": "H55-Sammlung"})
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    yield cid
    client.delete(f"/api/v1/collections/{cid}")


def test_post_cards_mit_steuerzeichen_ist_422(client):
    r = client.post("/api/v1/cards", json={"kartenname": NUL, "besessen": True})
    assert r.status_code == 422, r.text


def test_post_sealed_mit_steuerzeichen_ist_422(client):
    r = client.post("/api/v1/sealed", json={"name": NUL})
    assert r.status_code == 422, r.text


def test_post_sets_mit_steuerzeichen_ist_422(client):
    r = client.post("/api/v1/sets", json={"code": NUL, "name": NUL})
    assert r.status_code == 422, r.text


def test_post_sets_mit_leerem_namen_ist_422(client):
    assert client.post("/api/v1/sets", json={"code": "H55", "name": "   "}).status_code == 422
    assert client.post("/api/v1/sets", json={"code": "", "name": "X"}).status_code == 422


@pytest.mark.parametrize("feld", ["kartenname", "besessen", "wunschliste",
                                  "im_pokedex", "erste_edition"])
def test_put_cards_mit_explizitem_null_ist_422(client, karte, feld):
    r = client.put(f"/api/v1/cards/{karte}", json={feld: None})
    assert r.status_code == 422, f"{feld}: {r.status_code} {r.text[:200]}"


def test_put_collections_mit_null_name_ist_422(client, sammlung):
    r = client.put(f"/api/v1/collections/{sammlung}", json={"name": None})
    assert r.status_code == 422, r.text


def test_put_settings_mit_explizitem_null_ist_422(client):
    r = client.put("/api/v1/settings", json={"gemini_daily_limit": None})
    assert r.status_code == 422, r.text


def test_put_settings_mit_steuerzeichen_ist_422(client):
    r = client.put("/api/v1/settings", json={"openrouter_model": NUL})
    assert r.status_code == 422, r.text


# ── Gegenprobe: legitime Requests bleiben unberührt ─────────────────────────

def test_weglassen_bleibt_unveraendert(client, karte):
    """„Weglassen = unverändert" darf die Null-Sperre NICHT brechen."""
    r = client.put(f"/api/v1/cards/{karte}", json={"notizen": "nur Notiz"})
    assert r.status_code == 200, r.text
    assert r.json()["besessen"] is True          # unangetastet
    assert r.json()["notizen"] == "nur Notiz"


def test_nullable_felder_duerfen_weiter_null_sein(client, karte):
    r = client.put(f"/api/v1/cards/{karte}", json={"notizen": None, "zustand": None})
    assert r.status_code == 200, r.text
    assert r.json()["notizen"] is None


def test_false_wird_nicht_als_null_missverstanden(client, karte):
    r = client.put(f"/api/v1/cards/{karte}", json={"besessen": False})
    assert r.status_code == 200, r.text
    assert r.json()["besessen"] is False


def test_bestandsdaten_mit_steuerzeichen_bleiben_lesbar(client, karte):
    """Panel-MAJOR: die Sperre gehört auf den SCHREIB-Weg. Hing sie an der
    gemeinsamen Basisklasse, prüfte sie auch Antworten — eine Karte, die (aus
    Alt-Bestand oder Restore) ein Steuerzeichen trägt, war dann nicht mehr
    lesbar (GET lieferte 500)."""
    from app.database import SessionLocal
    from app.models.card import PokemonCard

    db = SessionLocal()
    try:
        card = db.get(PokemonCard, karte)
        card.notizen = "Seite1" + chr(11) + "Seite2"
        db.commit()
    finally:
        db.close()

    r = client.get(f"/api/v1/cards/{karte}")
    assert r.status_code == 200, r.text        # vorher: 500
    assert chr(11) in r.json()["notizen"]
    assert client.get("/api/v1/cards", params={"limit": 200}).status_code == 200


def test_passwortwechsel_erlaubt_exotische_zeichen(client, test_password):
    """Passwörter landen nur als Hash in der DB — die Steuerzeichen-Sperre
    darf hier nicht greifen (sie würde ein bestehendes Passwort unänderbar
    machen). Falsches aktuelles Passwort → 400, NICHT 422 (Panel-Fund)."""
    r = client.post("/api/v1/settings/change-password", json={
        "current_password": "falsch" + chr(1), "new_password": "neuespasswort1"})
    assert r.status_code == 400, r.text


def test_secret_laesst_sich_weiter_mit_leerstring_leeren(client):
    """Der Wildcard-Null-Riegel darf das Leeren eines Keys nicht verbauen
    (leerer String bleibt der Lösch-Weg, Panel-Testlücke)."""
    assert client.put("/api/v1/settings",
                      json={"openai_api_key": "sk-test-1234"}).status_code == 200
    assert client.get("/api/v1/settings").json()["openai_api_key_set"] is True
    assert client.put("/api/v1/settings",
                      json={"openai_api_key": ""}).status_code == 200
    assert client.get("/api/v1/settings").json()["openai_api_key_set"] is False


def test_settings_grenzen_schuetzen_die_kartenliste(client):
    """Ein unbegrenztes cards_per_page hätte jede Kartenliste dauerhaft auf
    422 gelegt (Panel-Fund)."""
    assert client.put("/api/v1/settings", json={"cards_per_page": 999999}).status_code == 422
    assert client.put("/api/v1/settings", json={"cards_per_page": 0}).status_code == 422
    assert client.put("/api/v1/settings", json={"price_update_hour": 99}).status_code == 422
    assert client.put("/api/v1/settings", json={"cards_per_page": 48}).status_code == 200


def test_sealed_verknuepfung_loesen_bleibt_moeglich(client):
    """Gegenprobe zum Wildcard-Validator: `tcgplayer_product_id: null` muss
    weiterhin entkoppeln (SealedProductUpdate hat bewusst KEINEN Null-Riegel)."""
    r = client.post("/api/v1/sealed", json={"name": "H55-Sealed"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    try:
        r = client.put(f"/api/v1/sealed/{pid}", json={"tcgplayer_product_id": None})
        assert r.status_code == 200, r.text
        assert r.json()["tcgplayer_product_id"] is None
    finally:
        client.delete(f"/api/v1/sealed/{pid}")


def test_settings_ueberleben_muell_in_der_datenbank(client):
    """Schreib-Sperren helfen nicht gegen Müll, der SCHON in der DB liegt
    (Alt-Backup-Restore, manueller Eingriff, früherer 500er-Pfad). Am
    Teststand real passiert: ein „None" in gemini_daily_limit legte JEDEN
    Settings-Aufruf lahm — inklusive der Einstellungs-Seite (#55)."""
    from app.database import SessionLocal
    from app.models.setting import AppSetting

    db = SessionLocal()
    try:
        vorher = db.get(AppSetting, "gemini_daily_limit")
        alt = vorher.value if vorher else None
        if vorher:
            vorher.value = "None"
        else:
            db.add(AppSetting(key="gemini_daily_limit", value="None"))
        db.commit()
    finally:
        db.close()

    try:
        r = client.get("/api/v1/settings")
        assert r.status_code == 200, r.text          # vorher: 500
        assert r.json()["gemini_daily_limit"] == 0   # Default statt Absturz
    finally:
        db = SessionLocal()
        try:
            row = db.get(AppSetting, "gemini_daily_limit")
            if row is not None:
                row.value = alt if alt is not None else "0"
                db.commit()
        finally:
            db.close()
