#!/usr/bin/env python3
"""
Einmaliger Import aus Notion CSV-Export in PostgreSQL.

Verwendung:
    DATABASE_URL=postgresql://... python migrations/csv_import.py notion_export.csv [--dry-run]

Voraussetzungen (bereits in requirements.txt):
    psycopg2-binary, python-dotenv
"""

import argparse
import csv
import logging
import os
import re
import sys
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Notion-Spalte → DB-Feld
COLUMN_MAP = {
    "Kartenname":            "kartenname",
    "Besessen":              "besessen",
    "Bild URL":              "bild_pokedex_url",
    "Englischer Name":       "englischer_name",
    "Folierung":             "folierung",
    "Geschätzter Wert (€)": "wert_eur",
    "Karten-Nr. im Set":     "karten_nr",
    "Kartenversion":         "kartenversion",
    "Notizen":               "notizen",
    "Pokédex Nr.":           "pokedex_nr",
    "Seltenheit":            "seltenheit",
    "Set / Edition":         "set_edition",
    "Sprache":               "sprache",
    "Zustand":               "zustand",
}

# Erlaubte DB-Werte – Zeilen mit ungültigem Wert werden korrigiert oder gewarnt
SELTENHEIT_OK = {
    "Common", "Uncommon", "Rare", "Holo Rare", "Double Rare",
    "Ultra Rare", "Secret Rare", "Full Art", "Illustration Rare",
    "Special Illustration Rare", "Rainbow Rare", "Hyper Rare", "Promo",
}
FOLIERUNG_OK = {
    "Normal", "Holo", "Cosmos Holo", "Reverse Holo",
    "Reverse Holo – Sterne", "Reverse Holo – Energie",
    "Reverse Holo – Pokéball", "Reverse Holo – Masterball",
    "Reverse Holo – Team Rocket R", "Reverse Holo – Muster",
    "Etched Holo", "Bubble Holo",
}
KARTENVERSION_OK = {
    "Normal", "Full Art", "Special Art", "Rainbow", "Gold",
    "Shiny", "Illustration Rare", "Special Illustration Rare",
}
SPRACHE_OK = {"DE", "EN", "CN", "JP", "FR", "ES", "IT"}
ZUSTAND_OK  = {"Mint", "Near Mint", "Excellent", "Good", "Played"}


def parse_wert(raw: str) -> Decimal | None:
    """'8,00 €' oder '0.10' → Decimal"""
    if not raw:
        return None
    clean = raw.replace("€", "").replace(" ", "").strip()
    clean = clean.replace(",", ".")
    try:
        return Decimal(clean)
    except InvalidOperation:
        return None


def parse_bool(raw: str) -> bool:
    return raw.strip().lower() in ("yes", "true", "ja", "1")


def parse_int(raw: str) -> int | None:
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return None


def clean_row(raw: dict) -> dict | None:
    row = {}
    for notion_col, db_field in COLUMN_MAP.items():
        row[db_field] = raw.get(notion_col, "").strip() or None

    if not row.get("kartenname"):
        return None  # Pflichtfeld

    row["besessen"]  = parse_bool(raw.get("Besossen", ""))
    row["wert_eur"]  = parse_wert(raw.get("Geschätzter Wert (€)", ""))
    row["pokedex_nr"] = parse_int(raw.get("Pokédex Nr.", ""))

    # Sprache normalisieren
    sprache = (row.get("sprache") or "DE").upper()
    row["sprache"] = sprache if sprache in SPRACHE_OK else "DE"

    # Optionale Felder validieren (ungültige → None + Warnung)
    for field, valid_set in [
        ("seltenheit",   SELTENHEIT_OK),
        ("folierung",    FOLIERUNG_OK),
        ("kartenversion", KARTENVERSION_OK),
        ("zustand",      ZUSTAND_OK),
    ]:
        val = row.get(field)
        if val and val not in valid_set:
            log.warning("Unbekannter Wert für %s: %r → wird als NULL importiert", field, val)
            row[field] = None

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


def run(csv_path: str, dry_run: bool):
    import psycopg2

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows_raw = list(reader)

    log.info("CSV gelesen: %d Zeilen", len(rows_raw))

    rows = []
    skipped = 0
    for r in rows_raw:
        cleaned = clean_row(r)
        if cleaned:
            rows.append(cleaned)
        else:
            skipped += 1

    log.info("Gültig: %d | Übersprungen (kein Name): %d", len(rows), skipped)

    if dry_run:
        log.info("DRY RUN – erste 5 Zeilen:")
        for r in rows[:5]:
            log.info("  %s", r)
        return

    db_url = os.environ["DATABASE_URL"]
    conn = psycopg2.connect(db_url)
    try:
        with conn:
            with conn.cursor() as cur:
                for row in rows:
                    cur.execute(INSERT_SQL, row)
        log.info("Import abgeschlossen: %d Karten eingefügt.", len(rows))
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="Notion CSV → PostgreSQL Import")
    parser.add_argument("csv", help="Pfad zur CSV-Datei")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=os.getenv("DRY_RUN", "true").lower() == "true",
        help="Nur lesen, nichts schreiben (Default: True)",
    )
    args = parser.parse_args()

    if args.dry_run:
        log.info("Modus: DRY RUN")
    else:
        log.info("Modus: SCHARF – schreibe in DB!")

    run(args.csv, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
