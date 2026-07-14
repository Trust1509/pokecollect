# CONTEXT.md — PokéCollect

Self-hosted Pokémon-TCG-Sammlungs-App (MIT). Ein Nutzer, LAN-Deployment,
FastAPI + PostgreSQL + Next.js. Dieses Dokument hält Grundsätze und
Domänensprache fest — Pflichtlektüre vor Architektur-/Feature-Arbeit
(siehe docs/agents/domain.md).

## Grundsätze (Kredo, ADR-0001)

1. **DRY — eine Routine je Sache.** Invarianten (Platzhalter-Adoption,
   Pokédex-Exklusivität, Bild-Priorität, Set-Code-Extraktion) leben in genau
   einer Routine, nie dupliziert in Routern oder Seiten.
2. **Mobile-First-Web.** Die Web-App IST die Mobile-App: sie muss im
   Handy-Browser vollständig funktionieren und skalieren (PWA). Es gibt keine
   nativen Apps (ADR-0002: Android ausgemustert).
3. **Testbar by default.** Services nehmen `db: Session` als Parameter und
   erzeugen keine `SessionLocal` selbst; pure Parser/Mapper haben Unit-Tests
   ohne Container; jede Verhaltensänderung läuft durch `scripts/gates.sh`.
4. **Secrets nie im Klartext an Clients.** *(Zielzustand — heute durch
   Issue #1/P0 verletzt: `GET /settings` liefert Keys klartext. Bis der Fix
   released ist, gilt: keine neuen Endpunkte, die Secrets ausgeben.)*
5. **Additive Light-Migrations.** Schema-Änderungen als idempotente
   Statements in `main.py::_run_light_migrations`; destruktive Statements
   (DROP/DELETE) nur mit Owner-OK und im Code als solche markiert.
6. **i18n DE/EN konsequent.** Jeder UI-Text läuft über `web/src/lib/i18n.tsx`
   (DE+EN, `typeof DE`-Parität); echte Umlaute; interne ASCII-Werte nie roh
   ins UI (Label-Maps).

## Glossar (Ubiquitous Language)

- **Karte** (`pokemon_cards`): eine physische Karte ODER ein Platzhalter.
  Unterscheidung über `besessen`.
- **Platzhalter**: nicht-besessene Karten-Zeile, die eine Pokédex-Nummer im
  Raster vertritt (zeigt offizielles Artwork). Wird beim Anlegen einer
  besessenen Karte derselben Nummer **adoptiert** (übernommen statt
  dupliziert); beim Löschen der letzten Karte einer Nummer neu erzeugt.
- **Im Pokédex** (`im_pokedex`): genau eine Karte je Pokédex-Nummer ist der
  Vertreter im Pokédex-Raster (Exklusivitäts-Invariante).
- **Sammlung** (`collections`): frei benannter Binder, n:m zu Karten, mit
  Layout (`binder_layout`) und Slot-Reihenfolge (`position`).
- **Wunschliste** (`wunschliste`-Flag): gewünschte Karten mit Priorität
  (Chase/Hoch/Mittel/Niedrig).
- **Katalog** (`tcgdex_catalog`): lokaler Spiegel aller ~23.000
  TCGdex-Karten; reine Referenzdaten, zählt nicht zur Sammlung.
- **Set** (`pokemon_sets`): Stammdaten je Set; `code` = aufgedrucktes Kürzel
  (z. B. OBF), `set_id` = stabile TCGdex-Id (z. B. sv03).
- **Scan**: Foto → Erkennung (Gemini oder lokale OCR) → **Resolver**
  (Set + Nummer gegen TCGdex/Katalog) → Bestätigungs-Dialog → Commit.
- **Light-Migration**: idempotentes SQL-Statement im App-Start (kein Alembic).

## Leitplanken

- Preise/Karten/Bilder kommen primär von **TCGdex** (kein Key nötig);
  Cardmarket-OAuth ist optionaler Fallback.
- Vergleichsprojekt Git-Romer/pokecollector ist **AGPL** — Ideen ja, Code nie.
- Deploy macht der Owner (TrueNAS, `deploy.sh`); Agenten liefern getaggte,
  getestete Stände (Details in CLAUDE.md).
