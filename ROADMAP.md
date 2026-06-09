# PokéCollect – Roadmap

Stand: **v0.9.6** · erster öffentlicher Release

---

## ⚠️ Known Issues (bekannt, Fix in Arbeit)
- **Foto-Aufnahme**: Zuschnitt/Skalierung nicht immer korrekt, keine echte
  perspektivische Entzerrung; im Raster/Binder stimmt die Ausrichtung nicht immer.
  → geplant: manuelle Eck-Korrektur (🅳) + echte Homographie.
- **Kartenbild** wird erst geladen, wenn eine **Kartennummer** eingetragen ist
  (Set + Nr. nötig zur eindeutigen Auflösung). → geplant: Namens-basierter Fallback.
- Vereinzelt uneinheitliche Filter-Felder je Kontext (kontextbedingt).

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
- Set-Korrekturen: MEP, 151C, COS, SVP

### v0.7.1 – v0.7.11 — Karten-Scan (Web + gemeinsame API)
- `POST /scan` (Hybrid: Gemini per REST, sonst Tesseract-OCR), 3 Modi (Einzel/Multi/Binder)
- Resolver: Set→set_id + Nummer, Namens-/Nummer-Fallback, Pokédex-Nr. immer über Name
- Bestätigungs-Dialog: Set-Dropdown, Seltenheit-Symbol, alle Folierungen, Live-Bild (`/scan/resolve`)
- Foto: bbox-Crop + Perspektiv-Entzerrung (4 Ecken), Auto-Rotation Hochformat, eigenes Foto vs. API-Bild
- Ziele Pokédex / Sammlung (Binder-Slot) / Wunschliste; Pokédex je Karte; editierbare Pokédex-Nr.
- Gemini-Nutzungs-Tracking (`gemini_usage`)

### v0.8.0 – v0.8.1 — Mobile-First + PWA
- Bottom-Navigation (Mobile), responsive Top-Nav, Filter als ein-/ausklappbares Sheet (Mobile + Desktop)
- PWA: Manifest + Icons + Service Worker (App-Shell + SWR, Offline-Lesen)
- Detailseite responsiv, Binder blättern per Wisch
- Gemini Free-Tier-Anzeige (RPD/RPM/TPM je Modell, „heute X/RPD", Ø Tokens/Scan)

---

## 🔲 Backlog (priorisierbar)

### ✅ 🅰 Lokale Karten-DB (TCGdex-Katalog) + globale Suche — v0.9.0
- [x] Tabelle `tcgdex_catalog` (alle Karten: Name DE/EN, Set, Nr., Bild; Illustrator/Rarity/dexId/Varianten via Enrichment)
- [x] Voll-Set-Sync: alle TCGdex-Sets in `pokemon_sets` (POR etc. automatisch)
- [x] Sync + Enrichment per Cron (04:00) in Etappen; `POST /catalog/sync` + `/enrich`
- [x] Globale Suche/Filter/Sortierung (`GET /catalog`), Seite `/catalog` „Alle Karten"
- [x] Stern → Wunschliste; Katalog zählt NICHT zu besessen/Pokédex/Statistik
- [ ] Offene Punkte: „zu Sammlung hinzufügen" aus dem Katalog-UI (API steht: `POST /catalog/{id}/collection`); Scan-Resolver/Set-Picker offline aus Katalog bedienen

### 🅱 Detailseite: Navigation + Bild-Zoom/3D
- [ ] Vor/Zurück zwischen Pokémon: Wisch (Mobile) + Buttons (Desktop)
- [ ] Klick/Hover aufs Kartenbild → Großansicht
- [ ] 3D-Neige-/Holo-Lichteffekt (Maus am Desktop, Geräte-/Touch am Handy) wie TCGdex

### 🅲 Illustrator
- [ ] Feld `illustrator` je Karte aus TCGdex (auto bei Anlage/Scan/Backfill)
- [ ] Illustrator als Filter (für Künstler-Sammler)

### 🅳 Foto-Zuschnitt: manuelle Eck-Korrektur
- [ ] Grober Auto-Zuschnitt + Ecken per Hand verschieben → perspektivische Entzerrung
- [ ] Löst schlechte Multi-Karten-Zuschnitte ohne teure Gemini-Rechnung

### 🅴 HTTPS via Caddy
> Schaltet PWA-Installation, Offline **und** Live-Webcam (Desktop + Handy, ohne Chrome-Flag) frei.
- [ ] Caddy-TLS (eigene Domain mit Let's Encrypt **oder** lokales `tls internal`)
- [ ] Doku im Deploy

### 🅵 Preise & Statistiken
- [ ] Wert-Entwicklung über Zeit (Charts), Set-Vollständigkeit
- [ ] Preis-Quelle/-Intervall in Settings nutzen; optional Cardmarket-OAuth als Fallback

### 🅶 Android-App verschlanken
- [ ] Auf „nativer Kamerazugriff + dünner Wrapper" reduzieren, sobald Web mobil alles kann
- [ ] Scan-API teilen (kein doppelter Code), Set-Dropdown/Seltenheit aus Backend

### 🅷 Kleinkram / Politur
- [ ] Gemini RPM/TPM auch pro Minute live tracken (aktuell nur Tageslimit)
- [ ] „Gesammelt"-Gesamtnenner: Wunschliste/Platzhalter optional ausblenden
- [ ] Deskew: echte Homographie statt 2-Dreieck-Affin (falls bei starkem Winkel nötig)

### 🅸 Sealed-Produkte sammeln
> Auch versiegelte Produkte (Booster, Displays, ETBs, Tins, Kollektionen) tracken,
> damit die gesamte Sammlung in einem Tool ist.
- [ ] Eigener Produkttyp „Sealed" (Name, Set/Serie, Typ, Menge, Zustand)
- [ ] Foto + Wert (manuell und/oder via Preisquelle) + Wertverlauf
- [ ] Eigene Ansicht/Filter; fließt in Gesamtwert-Statistik ein, getrennt von Karten

### 🔲 v1.0 — Production
- [x] Erster öffentlicher Release (v0.9.6) mit dokumentierten Known Issues
- [ ] Docker-Images auf ghcr.io, `image:` statt `build:` in docker-compose
- [ ] Authelia/externer Zugriff finalisieren, öffentliche Doku
