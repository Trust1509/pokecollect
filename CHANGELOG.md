# Changelog

## [v0.7.0] – 2026-06-07 (TCGdex-Integration)

### Features – Backend
- **TCGdex als zentrale Datenquelle** (`services/tcgdex.py`): kostenlose offene
  REST-API ohne Key – liefert Kartendaten, Bilder und Preise. Typisierte
  Pydantic-Modelle, Sprach-Mapping (DE/EN/CN→zh-tw/JP→ja/…), Fallback-Sprachen.
- **Bild-URLs aus TCGdex** (`high.webp`): ersetzt die komplette pokemon.com-Logik
  (Set-Code-Mapping, HEAD-Probing, Nummern-Mismatch entfallen). Eigenes Foto /
  manuelle URL behalten weiterhin Vorrang, Pokédex-Artwork bleibt Platzhalter.
- **Set-Sync** (`POST /api/v1/sets/sync`): reichert die Set-Tabelle aus
  `/en/sets` + `/de/sets` an (Name EN/DE, Kartenzahlen, Logo, Symbol, Serie),
  Merge über die stabile `set_id`. Offline-Brücke `ptcgo_code → set_id`
  (inkl. aufgelöster Fälle MEG→me01, PFL→me02, ASC→me02.5, WHT→sv10.5w, BLK→sv10.5b).
- **Preise via TCGdex** (`services/pricing.py`): Cardmarket EUR mit Holo-Logik
  (avg30 / avg30-holo + Fallbacks), Preisverlauf in `preis_historie`.
  zh-tw ohne Preis bleibt unverändert (kein 0-Wert). Cardmarket-OAuth nur noch
  optionaler Fallback.
- **Bild-Proxy/Cache** (`GET /api/v1/images/proxy`): holt Bilder einmal
  serverseitig (Offline-Fähigkeit + Datenschutz), Host-Allowlist (assets.tcgdex.net),
  nur https.
- Additive DB-Felder: `pokemon_sets` (set_id, name_en, series_id, card_count_*,
  logo_url, symbol_url) und `pokemon_cards` (tcgdex_card_id, set_id, dex_id,
  variants_normal/reverse/holo/firstedition). Keine bestehenden Daten verändert.

### Geplant für v0.7.x / 0.8.0
- Teil 2: Karten-Scan im Web (Webcam) + serverseitige Erkennung (`POST /api/v1/scan`)
- Teil 3: Mobile-First-Refactor + PWA (manifest, service worker)
- Optional: Gemini-Scan (Variante B) hinter `GEMINI_API_KEY`

## [v0.1.0-pre] – 2026-06-04 (Pre-Release)

### Features
- Vollständiges Datenbankschema (PostgreSQL 16) mit allen Pokémon TCG Feldern
- FastAPI Backend mit CRUD-Endpoints für Karten, Preise, Statistiken
- JWT-Authentifizierung (Single-User)
- CSV-Import aus Notion-Export (`migrations/csv_import.py`)
- Web-Frontend (Next.js 14 + Tailwind) — Pokédex-Raster, Filter, Detailansicht
- Statistiken-Dashboard mit Donut-Charts und Preishistorie
- Foto-Upload mit automatischer Thumbnail-Erstellung
- Cardmarket OAuth 1.0a Preisanbindung (Grundstruktur)
- Täglicher Preis-Cron-Job (03:00 Uhr)
- Android-App Grundstruktur (Kotlin + Compose + ML Kit OCR)
- Docker Compose Stack (lokaler Build)
- ZFS POSIX-ACL kompatibles Volume-Setup

### Bekannte Einschränkungen / Noch nicht getestet
- Karten manuell hinzufügen (Web-Formular) – noch nicht vollständig getestet
- Cardmarket API-Keys noch nicht über UI konfigurierbar (nur via .env)
- PokémonTCG.io Platzhalterbilder noch nicht aktiviert
- Android-App noch nicht auf Gerät getestet
- Externe Erreichbarkeit via Caddy noch nicht konfiguriert

### Geplant für v0.2.0
- Settings-Seite im Web für API-Keys (Cardmarket, PokémonTCG)
- Platzhalterbilder für alle Kacheln (ein/ausschaltbar)
- Android-App: Scan-Feature vollständig testen
- Karten hinzufügen/bearbeiten vollständig testen
