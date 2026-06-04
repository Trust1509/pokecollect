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

---

## 🔄 v0.4.0 — Set-Stammdaten + Karte anlegen/bearbeiten (in Arbeit)
> **Ziel:** Set/Edition als strukturierte Daten statt Freitext — verhindert Tippfehler,
> ermöglicht korrekte Kartenbilder und Nummernvalidierung.

- [x] Backend: `pokemon_sets` Tabelle (code, name, max_card_nr, pokemon_com_code)
- [x] Backend: `GET/POST/PUT /api/v1/sets` Endpunkte
- [x] Frontend: `PokemonSet` Typ + `setsApi` in api.ts
- [ ] Frontend: Karte anlegen (`/cards/new`) — Set-Dropdown mit Suche (Kürzel + Name)
- [ ] Frontend: Karte bearbeiten (`/cards/[id]`) — gleiches Dropdown
- [ ] Frontend: Karten-Nr. Feld mit Format-Hinweis (`001/132`) und Max-Validierung aus Set
- [ ] Option: neues Set direkt im Dropdown anlegen ("+")
- [ ] FilterSidebar: Set-Filter ebenfalls auf Stammdaten umstellen

## 🔄 v0.4.1 — Sprach-Toggle DE/EN
> **Ziel:** Komplette UI auf Deutsch und Englisch umschaltbar.

- [x] i18n-Context (`I18nProvider`) und `Navbar`-Komponente angelegt
- [ ] Übersetzungs-Dictionary DE/EN für alle Labels, Buttons, Statusmeldungen
- [ ] Toggle in Navbar, Präferenz in localStorage
- [ ] Alle bestehenden Seiten auf i18n umstellen

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

> **Empfehlung:** Binder-Ansicht als separate Seite ist besser als nur "Karten pro Seite" ändern —
> so bleibt die Hauptübersicht flexibel und die Binder-Ansicht ist für den physischen Vergleich optimiert.

## 🔲 v0.6.0 — Authelia + Externer Zugriff
- [ ] Authelia als Portainer-Stack deployen (siehe `deploy/README.md`)
- [ ] DNS-Einträge `auth.yourdomain.com` + `pokecollect.yourdomain.com` setzen
- [ ] Caddy-Config mit Authelia `forward_auth` aktivieren
- [ ] Externen Zugriff testen (Web + Android)

## 🔲 v0.7.0 — Android App
- [ ] App auf Gerät testen
- [ ] Typo "Besossen" fixen (CardDetailScreen.kt Zeile 64, ScanScreen.kt)
- [ ] API-URL konfigurierbar (intern vs. extern)

## 🔲 v0.8.0 — Wunschkarten
- [ ] DB-Tabelle `wunschkarten`
- [ ] `/wishlist`-Seite: gewünschte Karten eintragen, filtern, Preise anzeigen
- [ ] "Erhalten" → automatisch in Sammlung übertragen
- [ ] CSV-Export für Cardmarket-Suche

## 🔲 v0.9.0 — PokémonTCG.io Integration
- [ ] API-Key aus Settings verwenden
- [ ] Korrekte Bilder für SWSH/XY DE-Sets (ASC, PFL, BLK, BRS, WHT, MEG)
- [ ] Fallback-Kette: eigenes Foto → manuelle URL → pokemon.com → PokémonTCG.io → Pokédex-Artwork

## 🔲 v1.0.0 — Cardmarket + Daten
- [ ] Cardmarket OAuth 1.0a (Keys aus Settings)
- [ ] Preisabruf + Preishistorie
- [ ] CSV-Export/Import
- [ ] Statistiken: Wert-Entwicklung, Set-Vollständigkeit

## 🔲 v1.1.0 — Production Release
- [ ] Docker Images auf ghcr.io
- [ ] `image:` statt `build:` in docker-compose.yml
- [ ] Öffentliche Dokumentation
