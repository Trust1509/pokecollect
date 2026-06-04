# Changelog

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
