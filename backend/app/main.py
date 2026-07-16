import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from sqlalchemy import text

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.api.v1 import router as v1_router
from app.services.cron import start_scheduler

logging.basicConfig(level=logging.INFO)

# Set-Stammdaten (code, name, max_card_nr)
# max_card_nr = reguläre Kartennummer-Obergrenze (ohne Secret Rares)
# Secret Rares / Full Arts können höhere Nummern haben – das ist korrekt
_SET_SEED = [
    # ── MEG-Generation (parallel zu SV) ──────────────────────────────────────
    ("MEG",  "Mega-Entwicklung",                   132),
    ("MEP",  "Mega-Promos",                        None),  # TCGdex: mep (ohne Bilder)
    ("PFL",  "Fatale Flammen",                     109),
    ("ASC",  "Erhabene Helden",                   None),  # ~130, noch nicht final
    ("OCH",  "Optimale Ordnung",                  None),  # ~130, noch nicht final
    ("WCH",  "Wachsendes Chaos",                  None),  # ~130, noch nicht final
    ("DNK",  "Dunkelnacht",                       None),  # unbekannt
    # ── Karmesin & Purpur / Scarlet & Violet ─────────────────────────────────
    ("SVI",  "Karmesin & Purpur",                  198),
    ("PAL",  "Entwicklungen in Paldea",            193),
    ("OBF",  "Obsidianflammen",                    197),
    ("MEW",  "Pokémon 151",                        165),
    ("151",  "Pokémon 151",                        165),
    ("151C", "Pokémon 151 (Chinesisch)",           165),  # TCGdex: sv03.5 (Bild via EN/DE-Fallback)
    ("PAR",  "Paradoxrift",                        182),
    ("PAF",  "Paldeas Schicksale",                  91),
    ("TEF",  "Gewalten der Zeit",                  162),
    ("TWM",  "Maskerade im Zwielicht",             167),
    ("SFA",  "Nebel der Sagen",                     64),
    ("SCR",  "Stellarkrone",                       142),
    ("SSP",  "Stürmische Funken",                  191),
    ("PRE",  "Prismatische Entwicklungen",         131),
    ("JTG",  "Reisegefährten",                    168),
    ("DRI",  "Ewige Rivalen",                      131),
    ("WHT",  "Weiße Flammen",                     None),  # ~100, noch nicht final
    ("BLK",  "Schwarze Blitze",                   None),  # ~100, noch nicht final
    ("SVE",  "SV Energie-Karten",                   30),
    ("SVP",  "Karmesin & Purpur Promos",          None),  # TCGdex: svp
    # ── Schwert & Schild / Sword & Shield ────────────────────────────────────
    ("SSH",  "Schwert & Schild",                   202),
    ("RCL",  "Clash der Rebellen",                 192),
    ("DAA",  "Flammende Finsternis",               189),
    ("CPA",  "Weg des Champs",                      73),
    ("VIV",  "Farbenschock",                       185),
    ("SHF",  "Glänzendes Schicksal",                73),
    ("BST",  "Kampfstile",                         163),
    ("CRE",  "Schaurige Herrschaft",               198),
    ("EVS",  "Drachenwandel",                      203),
    ("CEL",  "Celebrations",                        25),
    ("FST",  "Fusionsangriff",                     264),
    ("BRS",  "Strahlende Sterne",                  172),
    ("ASR",  "Astralglanz",                        189),
    ("PGO",  "Pokémon GO",                          78),
    ("LOR",  "Verlorener Ursprung",                196),
    ("SIT",  "Silberne Sturmwinde",                195),
    ("CRZ",  "Zenit der Könige",                   159),
    # ── Sonne & Mond / Sun & Moon ─────────────────────────────────────────────
    ("SUM",  "Sonne & Mond",                       149),
    ("GRI",  "Stunde der Wächter",                 145),
    ("BUS",  "Nacht in Flammen",                   147),
    ("SLG",  "Schimmernde Legenden",                73),
    ("CIN",  "Aufziehen der Sturmröte",            147),
    ("UPR",  "Ultra Prisma",                       173),
    ("FLI",  "Grauen der Lichtfinsternis",         131),
    ("CES",  "Sturm am Firmament",                 168),
    ("DRM",  "Majestät der Drachen",                70),
    ("LOT",  "Echo des Donners",                   214),
    ("TEU",  "Teams sind Trumpf",                  181),
    ("DET",  "Meisterdetektiv Pikachu",             18),
    ("UNB",  "Kräfte im Einklang",                 214),
    ("UNM",  "Bund der Gleichgesinnten",           236),
    ("HIF",  "Verborgenes Schicksal",               68),
    ("COS",  "Welten im Wandel",                   236),
    # ── X & Y ────────────────────────────────────────────────────────────────
    ("XY",   "X & Y",                              146),
    ("FLF",  "Flammenmeer",                        106),
    ("FFI",  "Fliegende Fäuste",                   111),
    ("PHF",  "Phantomkräfte",                      119),
    ("PRC",  "Protoschock",                        160),
    ("ROS",  "Drachenleuchten",                    108),
    ("AOR",  "Ewiger Anfang",                       98),
    ("BKT",  "Turbostart",                         162),
    ("BKP",  "Turbofieber",                        122),
    ("FCO",  "Schicksalsschmiede",                 124),
    ("STS",  "Dampfkessel",                        114),
    ("EVO",  "Evolution",                          113),
]


def _seed_sets():
    """Upsert: neuen Sets anlegen, bei bestehenden name+max_card_nr aktualisieren."""
    from app.models.pokemon_set import PokemonSet
    db = SessionLocal()
    try:
        for code, name, max_nr in _SET_SEED:
            existing = db.get(PokemonSet, code)
            if existing:
                existing.name = name
                existing.max_card_nr = max_nr
            else:
                db.add(PokemonSet(code=code, name=name, max_card_nr=max_nr))
        db.commit()
    finally:
        db.close()


def _run_light_migrations():
    """
    Fügt neue Spalten zu bestehenden Tabellen hinzu (kein Alembic im Einsatz).
    create_all legt nur fehlende Tabellen an, ändert aber keine bestehenden.
    Idempotent dank ADD COLUMN IF NOT EXISTS (PostgreSQL).
    """
    stmts = [
        # bild_karte_url kam historisch per SQL-Migration – hier abgesichert,
        # damit auch Alt-Installationen vollständig sind (create_all + diese
        # Light-Migrations sind die Quelle der Wahrheit, Issue #12).
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS bild_karte_url TEXT",
        # CHECK-Constraints der früheren migrations/001_initial.sql (Datei
        # inzwischen entfernt) auf Alt-Installationen droppen: Die gültigen Werte
        # pflegt die API (schemas/card.py). Die alten Constraints kennen neuere
        # Werte nicht (z.B. "ACE SPEC Rare", "Shiny Rare", "Mega Hyper Rare")
        # und würden Inserts/Updates ablehnen.
        "ALTER TABLE pokemon_cards DROP CONSTRAINT IF EXISTS seltenheit_check",
        "ALTER TABLE pokemon_cards DROP CONSTRAINT IF EXISTS kartenversion_check",
        "ALTER TABLE pokemon_cards DROP CONSTRAINT IF EXISTS folierung_check",
        "ALTER TABLE pokemon_cards DROP CONSTRAINT IF EXISTS sprache_check",
        "ALTER TABLE pokemon_cards DROP CONSTRAINT IF EXISTS zustand_check",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS wunschliste BOOLEAN DEFAULT FALSE",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS prioritaet TEXT",
        "CREATE INDEX IF NOT EXISTS ix_pokemon_cards_wunschliste ON pokemon_cards (wunschliste)",
        "ALTER TABLE collection_cards ADD COLUMN IF NOT EXISTS position INTEGER",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS binder_layout TEXT DEFAULT '3x3'",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS binder_slots INTEGER",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS im_pokedex BOOLEAN NOT NULL DEFAULT FALSE",
        "CREATE INDEX IF NOT EXISTS ix_pokemon_cards_im_pokedex ON pokemon_cards (im_pokedex)",
        # ── TCGdex-Integration (v0.7.0) ──────────────────────────────────────
        # Set-Anreicherung
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS set_id TEXT",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS name_en TEXT",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS series_id TEXT",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS card_count_official INTEGER",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS card_count_total INTEGER",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS logo_url TEXT",
        "ALTER TABLE pokemon_sets ADD COLUMN IF NOT EXISTS symbol_url TEXT",
        "CREATE INDEX IF NOT EXISTS ix_pokemon_sets_set_id ON pokemon_sets (set_id)",
        # Karten-Anreicherung (stabile TCGdex-Referenz + Varianten)
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS tcgdex_card_id TEXT",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS set_id TEXT",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS dex_id INTEGER",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS illustrator TEXT",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS variants_normal BOOLEAN",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS variants_reverse BOOLEAN",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS variants_holo BOOLEAN",
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS variants_firstedition BOOLEAN",
        "CREATE INDEX IF NOT EXISTS ix_pokemon_cards_tcgdex_card_id ON pokemon_cards (tcgdex_card_id)",
        # Originalfoto (ungeschnitten) zusätzlich zum Zuschnitt aufbewahren (v0.9.10)
        "ALTER TABLE pokemon_cards ADD COLUMN IF NOT EXISTS bild_original_pfad TEXT",
        # ── Set-Sammlungen / Sammelziele (Issue #16) ─────────────────────────
        # Die neue Tabelle collection_soll legt create_all an (models/collection.py);
        # hier nur die additiven Spalten auf der bestehenden collections-Tabelle.
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS typ TEXT DEFAULT 'frei'",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS ziel_set_id TEXT",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS ziel_folierung TEXT",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS ziel_sprache TEXT",
        "ALTER TABLE collections ADD COLUMN IF NOT EXISTS ziel_master_set BOOLEAN DEFAULT FALSE",
        # Pokémon TCG Pocket (serie 'tcgp') ist rein digital → aus Katalog & Sets
        # entfernen, falls früher synchronisiert. Reihenfolge: erst Katalog (die
        # Subquery braucht die Set-Zeilen), dann die Sets selbst. Der Sync legt
        # sie danach nicht mehr an (services/tcgdex.EXCLUDED_SERIES).
        "DELETE FROM tcgdex_catalog WHERE set_id IN (SELECT set_id FROM pokemon_sets WHERE series_id = 'tcgp')",
        "DELETE FROM pokemon_sets WHERE series_id = 'tcgp'",
        # Einmalmigration: erste besessene Karte je Pokédex-Nr. automatisch als Pokédex-Vertreter setzen
        """
        UPDATE pokemon_cards
        SET im_pokedex = TRUE
        WHERE id IN (
            SELECT MIN(id)
            FROM pokemon_cards
            WHERE besessen = TRUE AND pokedex_nr IS NOT NULL
            GROUP BY pokedex_nr
            HAVING SUM(CASE WHEN im_pokedex = TRUE THEN 1 ELSE 0 END) = 0
        )
        """,
    ]
    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(text(stmt))


def _ensure_password_configured():
    """
    Start-Guard (Issue #1): Ohne Login-Passwort startet die App nicht.
    Der frühere eingebaute Default-Hash ("secret") ist entfernt — ein Deploy
    ohne APP_PASSWORD_HASH wäre sonst mit bekanntem Passwort offen.
    Gültig ist entweder die Env-Var APP_PASSWORD_HASH oder ein per
    In-App-Passwortwechsel gesetzter Hash in der Datenbank.
    """
    if os.getenv("APP_PASSWORD_HASH", "").strip():
        return
    from app.models.setting import AppSetting
    db = SessionLocal()
    try:
        row = db.get(AppSetting, "app_password_hash")
        if row and row.value:
            return
    finally:
        db.close()
    raise RuntimeError(
        "APP_PASSWORD_HASH ist nicht gesetzt (und in der Datenbank liegt kein "
        "Passwort-Hash). Die App startet aus Sicherheitsgründen nicht ohne "
        "Login-Passwort. Abhilfe: bcrypt-Hash erzeugen mit\n"
        "  python -c \"import bcrypt; print(bcrypt.hashpw(b'DEIN_PASSWORT', bcrypt.gensalt()).decode())\"\n"
        "oder ohne lokales Python via Docker:\n"
        "  docker run --rm python:3.12-slim sh -c \"pip -q install bcrypt==4.0.1 && python -c \\\"import bcrypt; print(bcrypt.hashpw(b'DEIN_PASSWORT', bcrypt.gensalt()).decode())\\\"\"\n"
        "und den Hash als APP_PASSWORD_HASH in die .env eintragen "
        "(siehe .env.example bzw. deploy/README.md)."
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_light_migrations()
    _ensure_password_configured()
    _seed_sets()
    # TCGdex-Brücke offline anwenden (set_id auf bekannten Sets setzen).
    # Der eigentliche Set-Sync (Netzzugriff) läuft täglich im Katalog-Cron
    # bzw. auf Anfrage via POST /catalog/sync (macht Sets mit).
    try:
        from app.services.set_sync import apply_bridge_to_seed
        apply_bridge_to_seed()
    except Exception as exc:  # niemals den Start blockieren
        logging.getLogger(__name__).warning("Bridge-Anwendung fehlgeschlagen: %s", exc)
    start_scheduler()
    yield


app = FastAPI(
    title="PokéCollect API",
    version=settings.app_version,
    lifespan=lifespan,
)

# allow_credentials=False: Auth läuft über den Authorization-Header, nicht
# über Cookies. Origins kommen aus CORS_ORIGINS (kommagetrennt); ohne Env
# greifen die Defaults für Prod-Web (3011) + Teststand (3021) — Details in
# config.py::cors_origins_list. Kein "*" mehr (Issue #1).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

# Serve uploaded card images
app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")


@app.get("/health")
def health():
    return {"status": "ok", "version": settings.app_version}
