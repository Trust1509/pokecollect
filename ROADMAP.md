# PokéCollect – Roadmap

Stand: **v0.9.11** · Aufräum-/Konsistenz-Release (Repo-Hygiene, DB-Robustheit, Settings wirksam)

---

## ⚠️ Known Issues
- Automatischer Erst-Zuschnitt (Gemini-Ecken) bei mehreren/schräg liegenden
  Karten auf einem Foto noch nicht immer ideal – die manuelle Eck-Korrektur
  (Lupe/Zoom/Flip/Rotate) gleicht das aus.

---

## ✅ Erledigt

### Grundlagen (v0.1.x – v0.4.0)
- Import 1025 Karten, Pokédex-Raster, Filter (Status/Generation/Set/Seltenheit/Sprache), Suche
- Statistiken-Dashboard, Detailansicht mit Bearbeitung
- Foto-Upload/-Löschen, manuelle Bild-URL, Bild-Filter
- Git-Deploy (`deploy.sh`), Settings-Seite (Anzeige/Preise/Sammlung/API-Keys/Konto)
- `pokemon_sets`-Stammdaten + `SetPicker`, set_edition-Format, Karten-Nr.-Validierung
- Pokédex-Integrität (Platzhalter-Übernahme, Auto-Platzhalter bei Löschung)
- DE/EN-Sprach-Toggle, Seltenheits-Symbole (`RarityBadge`/`RaritySelect`)

### v0.5.x – v0.6.0 — Binder, Sammlungen, Wunschliste, Pokédex-Modus
- Binder-Ansicht (konfigurierbares Raster, Blättern, Drag&Drop, Seiten verwalten)
- Pokédex-Nr. auf jeder Kachel; Pokédex-Modus (`im_pokedex`, dedupliziert)
- Freie Sammlungen (`collections` + `collection_cards`, n:m), Sammlungs-Detailseite
- Wunschliste (`/wishlist`) mit Priorität

### v0.7.0 — TCGdex als zentrale Datenquelle
- `services/tcgdex.py` (Karten/Sets/Preise, kein Key), Bild-URLs `high.webp`
- Set-Sync (`/sets/sync`) inkl. Auto-Auflösung über `abbreviation.official` + ptcgo-Brücke
- Preise aus `pricing.cardmarket` (avg30 + Holo-Logik), Preis-Cron, `preis_historie`
- Bild-Proxy/-Cache mit Host-Allowlist; additive DB-Felder (tcgdex_card_id, set_id, dex_id, variants)

### v0.7.1 – v0.7.11 — Karten-Scan (Web + gemeinsame API)
- `POST /scan` (Hybrid: Gemini per REST, sonst Tesseract-OCR), 3 Modi (Einzel/Multi/Binder)
- Resolver: Set→set_id + Nummer, Namens-/Nummer-Fallback, Pokédex-Nr. immer über Name
- Bestätigungs-Dialog: Set-Dropdown, Seltenheit-Symbol, alle Folierungen, Live-Bild (`/scan/resolve`)
- Ziele Pokédex / Sammlung (Binder-Slot) / Wunschliste; Gemini-Nutzungs-Tracking

### v0.8.0 – v0.8.1 — Mobile-First + PWA
- Bottom-Navigation, responsive Top-Nav, Filter als ein-/ausklappbares Sheet
- PWA: Manifest + Icons + Service Worker (App-Shell + SWR, Offline-Lesen)
- Gemini Free-Tier-Anzeige (RPD/RPM/TPM je Modell)

### v0.9.0 – v0.9.5 — Lokaler Katalog, Illustrator, UI-Vereinheitlichung
- Tabelle `tcgdex_catalog` (Spiegel aller ~23.000 Karten) + Voll-Set-Sync + Cron-Enrichment
- Seite `/catalog`: Suche/Filter/Sortierung, Stern → Wunschliste, Detail-Dialog
  mit „Zur Wunschliste" und „Zu Sammlung hinzufügen"
- Illustrator-Feld + -Filter überall (Pokédex/Owned/Katalog)
- Einheitliche Filterleisten, Set-Filter mit Logos (nach Serie geclustert),
  Sticky-Header, Binder-Dimmen statt Filtern, Sortierung „Set + Nr."

### v0.9.6 – v0.9.10 — Foto-Pipeline
- Homographie-Entzerrung + manuelle Eck-Korrektur (Lupe, Zoom/Pan, Gesten)
- EXIF-Normalisierung (Editor-Anzeige == gespeicherter Zuschnitt), Cache-Busting
- Originalfotos werden aufbewahrt → großzügiges Neu-Zuschneiden auf der Detailseite
- Bild-Fallback per Namenssuche, Promo-Erkennung (Seltenheit + Nummernformat)

### v0.9.11 — Aufräumen & Robustheit
- Repo-Hygiene: toter Code (auth.ts, authApi, ungenutzte i18n-Keys, Duplikate),
  obsolete Migrationen, ungenutzte Abhängigkeiten (Redis, Alembic, notion-client)
- DB-Robustheit: Light-Migrations decken frische Installs vollständig ab;
  veraltete CHECK-Constraints (blockierten z.B. „ACE SPEC Rare") entfernt
- Einstellungen wirksam verdrahtet: Standard-Sprache/-Zustand (Formular + Scan),
  Preis-Update-Uhrzeit (Cron)
- CORS korrigiert; Doku (README/Deploy/.env.example) auf Ist-Stand

---

## 🔲 Backlog (priorisierbar)

### 🅰 Katalog-Restpunkte
- [ ] Scan-Resolver/Set-Picker offline aus dem lokalen Katalog bedienen
      (weniger TCGdex-Roundtrips beim Scannen)

### 🅱 Detailseite: Navigation + Bild-Zoom/3D
- [ ] Vor/Zurück zwischen Pokémon: Wisch (Mobile) + Buttons (Desktop)
- [ ] Klick/Hover aufs Kartenbild → Großansicht
- [ ] 3D-Neige-/Holo-Lichteffekt (Maus am Desktop, Geräte-/Touch am Handy) wie TCGdex

### 🅲 Foto-Zuschnitt
- [ ] Auto-Zuschnitt vor dem manuellen Schritt weiter verbessern (Multi-Karten,
      gemischte Ausrichtungen)

### 🅳 HTTPS via Caddy
> Schaltet PWA-Installation, Offline **und** Live-Webcam (ohne Chrome-Flag) frei.
- [ ] Caddy-TLS (eigene Domain mit Let's Encrypt **oder** lokales `tls internal`)
- [ ] Doku im Deploy

### 🅴 Preise & Statistiken
- [ ] Wert-Entwicklung über Zeit (Charts), Set-Vollständigkeit
- [ ] Setting `price_source` (30-Tage-Ø vs. Tagespreis) im Preis-Update auswerten

### 🅵 Android-App verschlanken
- [ ] Auf „nativer Kamerazugriff + dünner Wrapper" reduzieren, sobald Web mobil alles kann
- [ ] Scan-API teilen (kein doppelter Code), Set-Dropdown/Seltenheit aus Backend

### 🅶 Kleinkram / Politur
- [ ] Settings-Seite auf i18n umstellen (aktuell nur Deutsch, Rest der App DE/EN)
- [ ] Gemini RPM/TPM auch pro Minute live tracken (aktuell nur Tageslimit)
- [ ] „Gesammelt"-Gesamtnenner: Wunschliste/Platzhalter optional ausblenden
- [ ] Foto-Upload: Datei-Endung serverseitig auf Bildformate beschränken

### 🅷 Sealed-Produkte sammeln
> Auch versiegelte Produkte (Booster, Displays, ETBs, Tins, Kollektionen) tracken,
> damit die gesamte Sammlung in einem Tool ist.
- [ ] Eigener Produkttyp „Sealed" (Name, Set/Serie, Typ, Menge, Zustand)
- [ ] Foto + Wert (manuell und/oder via Preisquelle) + Wertverlauf
- [ ] Eigene Ansicht/Filter; fließt in Gesamtwert-Statistik ein, getrennt von Karten

### 🔲 v1.0 — Production
- [x] Erster öffentlicher Release (v0.9.6) mit dokumentierten Known Issues
- [ ] **Auth durchsetzen:** Login-Seite im Web + `require_auth` auf den API-Routern
      (Bild-Routen ausgenommen). Aktuell ist die API bewusst LAN-offen, extern
      schützt Authelia – `/settings` liefert API-Keys daher jedem im LAN.
- [ ] Docker-Images auf ghcr.io, `image:` statt `build:` in docker-compose
- [ ] Authelia/externer Zugriff finalisieren, öffentliche Doku
