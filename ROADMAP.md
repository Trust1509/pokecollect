# PokéCollect – Roadmap

## ✅ v0.1.0-pre — Grundfunktionen
- 1025 Karten aus Notion importiert
- Pokédex-Raster mit Filtern (Status, Generation, Set, Seltenheit, Sprache)
- Suche nach Name oder Pokédex-Nr.
- Statistiken-Dashboard
- Karten-Detailansicht mit Bearbeitung

## ✅ v0.1.1 — Bilder & Filter
- Pokédex-Platzhalterbilder (pokemon.com) für alle 1025 Karten
- Bild-URL manuell hinterlegen (z.B. Cardmarket-Scan)
- Foto hochladen und löschen
- Bild-Filter: Eigenes Foto / Externe URL / Nur Platzhalter
- Typo-Fix: "Besossen" → "Besessen"

## ✅ v0.1.2 — Git-Deploy
- Git-basiertes Deployment via `deploy.sh`
- Deploy-Dokumentation mit Rebuild-Regeln
- NEXT_PUBLIC_API_URL korrekt als Docker Build-Arg

## ✅ v0.2.0 — Settings-Seite
- `/settings`-Seite mit 5 Sektionen (Anzeige, Preise, Sammlung, API-Keys, Konto)
- Versionsanzeige in der Navbar
- Settings in PostgreSQL gespeichert (key/value)

## ✅ v0.2.2 — Auth-Architektur: Authelia
- In-App-Auth entfernt; Authelia-Config vorbereitet
- Intern offen, extern via Caddy + Authelia geschützt

## ✅ v0.3.1 — Automatische Kartenbilder (pokemon.com)
- SV-Era Sets automatisch mit korrekten Kartenbildern (80/96 besessene Karten = 83%)
- Backfill-Endpoint + Auto-Fetch bei Anlage
- Löschen nur für besessene Karten
- SWSH/XY DE-Subsets deaktiviert (Nummerierung weicht ab → würden falsche Bilder zeigen)

## ✅ v0.4.0 — Set-Stammdaten, Pokédex-Integrität, i18n, Seltenheits-Symbole

### Set-Stammdaten
- Backend: `pokemon_sets`-Tabelle (code PK, name, max_card_nr)
- 70+ Sets als Seed-Daten mit Upsert (XY, Sonne & Mond, Schwert & Schild, Karmesin & Purpur, MEG-Generation)
- REST-Endpunkte: `GET/POST /api/v1/sets`, `PUT /api/v1/sets/{code}`

### Karte anlegen & bearbeiten
- `SetPicker`: Searchable Dropdown (Kürzel + auto-befüllter Name), Option „Neues Set anlegen"
- set_edition-Format in DB: `"Paldeas Schicksale (PAF)"`
- Karten-Nr. Feld mit Format-Hinweis (`NNN/MAX`) und Validierung; Secret Rares > MAX ausdrücklich erlaubt
- Auto-Name via PokéAPI: Pokédex-Nr. eingeben → DE + EN Name automatisch befüllt (500ms debounced, manuelle Eingaben werden nicht überschrieben, Reset bei Leerung)

### Pokédex-Integrität
- `POST /cards` mit `besessen=true` + `pokedex_nr` → vorhandener Platzhalter wird übernommen statt Duplikat
- `DELETE /cards/{id}` → wenn letzte Karte einer Pokédex-Nr., wird automatisch neuer Platzhalter angelegt
- Karten ohne `pokedex_nr` (Trainer, Energie) nicht betroffen

### Sprach-Toggle DE/EN
- `I18nProvider` (React Context) mit vollständigen DE/EN Dictionaries
- Toggle in der Navbar, Sprachpräferenz in `localStorage`
- Alle Seiten und Komponenten übersetzt

### Seltenheits-Symbole
- Offizielle Symbole nach TCG-Standard: ●◆★☆✦ + PROMO-SVG-Stern
- JP/CN-Karten zeigen Text-Codes: C/U/R/RR/SR/AR/SAR/UR/MUR/ACE/S/SSR/PROMO
- `RarityBadge`: Symbol auf Kacheln + Detailseite
- `RaritySelect`: Custom Dropdown mit großem Symbol pro Option (kein nativer `<select>`)
- Enums aktualisiert: `Holo Rare` + `Full Art` entfernt, neu: `Mega Hyper Rare`, `ACE SPEC Rare`, `Shiny Rare`, `Shiny Ultra Rare`

---

## 🔲 v0.5.0 — Karten-Grid Verbesserungen
> **Ziel:** Mehr Information auf einen Blick, physischen Binder vergleichbar machen.

- [ ] Pokédex-Nummer auf jeder Kachel anzeigen (klein, unter dem Kartennamen)
- [ ] **Binder-Ansicht** als eigene Seite `/binder`:
  - Konfigurierbar: Karten pro Reihe (3er = 9/Seite, 4er = 12/Seite, 5er = 15/Seite)
  - Seitenweise durchblättern (‹ / ›) — entspricht physischem Binder
  - Filter: nur besessene Karten, nur bestimmtes Set
  - Ideal zum Vergleich mit physischem Binder
- [ ] Karten pro Seite in Settings: Binder-freundliche Voreinstellungen
  (9 = 3×3, 12 = 3×4, 18 = 3×6, 20 = 4×5, 24 = 4×6)

## 🔲 v0.6.0 — Authelia + Externer Zugriff
- [ ] Authelia als Portainer-Stack deployen (siehe `deploy/README.md`)
- [ ] DNS-Einträge `auth.yourdomain.com` + `pokecollect.yourdomain.com` setzen
- [ ] Caddy-Config mit Authelia `forward_auth` aktivieren
- [ ] Externen Zugriff testen (Web + Android)

## 🔲 v0.7.0 — Android App
- [ ] App auf Gerät testen
- [ ] Typo "Besossen" fixen (CardDetailScreen.kt Zeile 64, ScanScreen.kt)
- [ ] API-URL konfigurierbar (intern vs. extern)
- [ ] Seltenheits-Symbole im Scan-Ergebnis anzeigen (RarityBadge-Logik übertragen)
- [ ] Set-Dropdown aus Stammdaten (`GET /api/v1/sets`) befüllen

## 🔲 v0.8.0 — Wunschkarten
- [ ] DB-Tabelle `wunschkarten`
- [ ] `/wishlist`-Seite: gewünschte Karten eintragen, filtern, Preise anzeigen
- [ ] "Erhalten" → automatisch in Sammlung übertragen (Pokédex-Integrität greift)
- [ ] CSV-Export für Cardmarket-Suche

## 🔲 v0.9.0 — PokémonTCG.io Integration
- [ ] API-Key aus Settings verwenden
- [ ] Korrekte Bilder für SWSH/XY DE-Sets (ASC, PFL, BLK, BRS, WHT, MEG)
- [ ] Fallback-Kette: eigenes Foto → manuelle URL → pokemon.com → PokémonTCG.io → Pokédex-Artwork
- [ ] Seltenheits-Daten aus API abgleichen

## 🔲 v1.0.0 — Cardmarket + Daten
- [ ] Cardmarket OAuth 1.0a (Keys aus Settings)
- [ ] Preisabruf + Preishistorie
- [ ] CSV-Export/Import
- [ ] Statistiken: Wert-Entwicklung, Set-Vollständigkeit

## 🔲 v1.1.0 — Production Release
- [ ] Docker Images auf ghcr.io
- [ ] `image:` statt `build:` in docker-compose.yml
- [ ] Öffentliche Dokumentation
