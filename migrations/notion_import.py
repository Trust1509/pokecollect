#!/usr/bin/env python3
"""
Einmaliger Import von Pokémon-Karten aus Notion in PostgreSQL.

Verwendung:
    NOTION_API_KEY=... NOTION_DATABASE_ID=... \
    DATABASE_URL=postgresql://... \
    python migrations/notion_import.py [--dry-run]

Voraussetzungen:
    pip install notion-client psycopg2-binary python-dotenv
"""

import argparse
import logging
import os
import sys
from datetime import datetime

import psycopg2
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Notion → DB Feld-Mapping
# Passe die Schlüssel auf die tatsächlichen Notion-Spaltennamen an.
# ---------------------------------------------------------------------------
FIELD_MAP = {
    "kartenname":       ("title",    "Kartenname"),
    "pokedex_nr":       ("number",   "Pokédex-Nr."),
    "englischer_name":  ("rich_text","Englischer Name"),
    "set_edition":      ("select",   "Set/Edition"),
    "karten_nr":        ("rich_text","Karten-Nr."),
    "seltenheit":       ("select",   "Seltenheit"),
    "kartenversion":    ("select",   "Kartenversion"),
    "folierung":        ("select",   "Folierung"),
    "sprache":          ("select",   "Sprache"),
    "besessen":         ("checkbox", "Besossen"),
    "wert_eur":         ("number",   "Wert (€)"),
    "notizen":          ("rich_text","Notizen"),
    "zustand":          ("select",   "Zustand"),
    "bild_pokedex_url": ("url",      "Bild-URL"),
}

# Seltenheits-Werte normalisieren (Notion kann leicht abweichen)
SELTENHEIT_NORM = {
    "common":                       "Common",
    "uncommon":                     "Uncommon",
    "rare":                         "Rare",
    "holo rare":                    "Holo Rare",
    "double rare":                  "Double Rare",
    "ultra rare":                   "Ultra Rare",
    "secret rare":                  "Secret Rare",
    "full art":                     "Full Art",
    "illustration rare":            "Illustration Rare",
    "special illustration rare":    "Special Illustration Rare",
    "rainbow rare":                 "Rainbow Rare",
    "hyper rare":                   "Hyper Rare",
    "promo":                        "Promo",
}

FOLIERUNG_NORM = {
    "normal":                       "Normal",
    "holo":                         "Holo",
    "cosmos holo":                  "Cosmos Holo",
    "reverse holo":                 "Reverse Holo",
    "reverse holo – sterne":        "Reverse Holo – Sterne",
    "reverse holo – energie":       "Reverse Holo – Energie",
    "reverse holo – pokéball":      "Reverse Holo – Pokéball",
    "reverse holo – masterball":    "Reverse Holo – Masterball",
    "reverse holo – team rocket r": "Reverse Holo – Team Rocket R",
    "reverse holo – muster":        "Reverse Holo – Muster",
    "etched holo":                  "Etched Holo",
    "bubble holo":                  "Bubble Holo",
}


def extract_prop(properties: dict, field_type: str, field_name: str):
    prop = properties.get(field_name)
    if not prop:
        return None
    t = field_type
    try:
        if t == "title":
            return prop["title"][0]["plain_text"] if prop["title"] else None
        if t == "rich_text":
            return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else None
        if t == "number":
            return prop["number"]
        if t == "select":
            return prop["select"]["name"] if prop["select"] else None
        if t == "checkbox":
            return prop["checkbox"]
        if t == "url":
            return prop["url"]
    except (KeyError, IndexError, TypeError):
        return None
    return None


def notion_page_to_row(page: dict) -> dict:
    props = page["properties"]
    row = {}
    for db_field, (ftype, notion_field) in FIELD_MAP.items():
        row[db_field] = extract_prop(props, ftype, notion_field)

    # Normalisierung
    if row.get("seltenheit"):
        row["seltenheit"] = SELTENHEIT_NORM.get(
            row["seltenheit"].lower(), row["seltenheit"]
        )
    if row.get("folierung"):
        row["folierung"] = FOLIERUNG_NORM.get(
            row["folierung"].lower(), row["folierung"]
        )
    if not row.get("sprache"):
        row["sprache"] = "DE"

    return row


INSERT_SQL = """
INSERT INTO pokemon_cards (
    kartenname, pokedex_nr, englischer_name, set_edition, karten_nr,
    seltenheit, kartenversion, folierung, sprache, besessen,
    wert_eur, notizen, zustand, bild_pokedex_url
) VALUES (
    %(kartenname)s, %(pokedex_nr)s, %(englischer_name)s, %(set_edition)s,
    %(karten_nr)s, %(seltenheit)s, %(kartenversion)s, %(folierung)s,
    %(sprache)s, %(besessen)s, %(wert_eur)s, %(notizen)s, %(zustand)s,
    %(bild_pokedex_url)s
)
"""


def run(dry_run: bool):
    notion_key = os.environ["NOTION_API_KEY"]
    database_id = os.environ["NOTION_DATABASE_ID"]
    db_url = os.environ["DATABASE_URL"]

    notion = Client(auth=notion_key)

    log.info("Lade Notion-Datenbank %s …", database_id)
    pages = []
    cursor = None
    while True:
        kwargs = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        result = notion.databases.query(**kwargs)
        pages.extend(result["results"])
        if not result.get("has_more"):
            break
        cursor = result["next_cursor"]

    log.info("%d Einträge gefunden.", len(pages))

    rows = [notion_page_to_row(p) for p in pages]
    # Zeilen ohne Kartenname überspringen
    valid = [r for r in rows if r.get("kartenname")]
    skipped = len(rows) - len(valid)
    if skipped:
        log.warning("%d Einträge ohne Kartenname übersprungen.", skipped)

    if dry_run:
        log.info("DRY RUN – kein DB-Schreibzugriff. Erste 3 Zeilen:")
        for r in valid[:3]:
            log.info("  %s", r)
        return

    conn = psycopg2.connect(db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for row in valid:
                    cur.execute(INSERT_SQL, row)
        log.info("Import abgeschlossen: %d Karten eingefügt.", len(valid))
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Notion → PostgreSQL Import")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("DRY_RUN", "true").lower() == "true",
        help="Nur lesen, nichts schreiben (Default: True)",
    )
    args = parser.parse_args()

    if args.dry_run:
        log.info("Modus: DRY RUN (--dry-run gesetzt oder DRY_RUN=True)")
    else:
        log.info("Modus: SCHARF – schreibe in DB!")

    try:
        run(dry_run=args.dry_run)
    except KeyError as e:
        log.error("Fehlende Umgebungsvariable: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
