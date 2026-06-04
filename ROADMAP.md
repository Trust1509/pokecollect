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
- `/settings`-Seite mit 5 Sektionen:
  - 🖼️ Anzeige (Platzhalter-Toggle, Karten/Seite, Sortierung)
  - 💰 Preise (Auto-Update, Uhrzeit, Quelle)
  - 📦 Sammlung (Standard-Sprache & -Zustand)
  - 🔑 API-Keys (Cardmarket OAuth, PokémonTCG.io)
  - 👤 Konto (Passwort ändern)
- Versionsanzeige in der Navbar (v0.x.x)
- Settings in PostgreSQL gespeichert (key/value)

## ✅ v0.2.1 — Auth (zurückgenommen)
- Login-Seite, Middleware, Backend-Absicherung gebaut
- Entschieden: Auth wird von Authelia übernommen, nicht in-app

## ✅ v0.2.2 — Auth-Architektur: Authelia
- In-App-Auth vollständig entfernt (kein Login, kein Middleware)
- Authelia-Konfiguration vorbereitet (`deploy/authelia/`)
- Caddy-Snippet mit `forward_auth` für externen Zugriff
- Intern (192.168.2.x): offen
- Extern (yourdomain.com): Authelia-Login erzwungen

---

## ✅ v0.3.0 — Automatische Kartenbilder (pokemon.com)

> **Ziel:** Für jede gesammelte Karte automatisch das exakte Kartenbild laden —
> kein eigenes Foto nötig, solange Set + Kartennummer + Sprache bekannt sind.

### URL-System (verifiziert)
```
https://www.pokemon.com/static-assets/content-assets/cms2-{locale}/img/cards/web/{SET_CODE}/{SET_CODE}_{LANG}_{NR}.png
```

- `{locale}` → z.B. `de-de`, `en-us`
- `{SET_CODE}` → pokemon.com interner Code (≠ unser Kürzel, Mapping nötig)
- `{NR}` → Kartennummer ohne führende Nullen, ohne `/XXX`-Suffix (z.B. `"007/091"` → `"7"`)

### Set-Code Mapping (manuell verifiziert)
| Unser Kürzel | pokemon.com Code | Set |
|---|---|---|
| PAF | SV4PT5 | Paldeas Schicksale |
| SVI | SV01 | Scharlachrot & Violett Basis |
| OBF | SV03 | Obsidian Flames |
| TEF | SV05 | Temporal Forces |
| 151 | SV3PT5 | Pokémon 151 |
| PRE | SV8PT5 | Prismatische Entwicklungen |
| MEG | XY8 | Mega-Entwicklung |
| ASC | SWSH10 | Erhabene Helden |
| … | … | (weitere nach Bedarf ergänzen) |

> PAL, PAR und weitere → auf pokemon.com DE nicht verfügbar → Fallback PokémonTCG.io

### Bild-Priorität in der App
1. **Eigenes Scan-Foto** (`bild_karte_pfad`) — immer bevorzugt
2. **pokemon.com** — automatisch aus Set + Nr. + Sprache konstruiert, HEAD-Check ob vorhanden
3. **PokémonTCG.io API** — Fallback für fehlende Sets
4. **Pokédex-Artwork** — letzter Fallback, immer verfügbar für alle 1025 Pokémon

### Aufgaben
- [x] Backend-Service `card_image_service.py` mit HEAD-verifizierter URL-Konstruktion
- [x] Set-Code-Mapping (50+ Sets, alle manuell verifiziert)
- [x] `bild_karte_url` Feld in DB (Migration 002)
- [x] Backfill-Endpoint `/api/v1/cards/meta/backfill-images` (nur besessene Karten)
- [x] Auto-Fetch bei Karte anlegen/bearbeiten (Background Task)
- [x] Frontend: Bildpriorität eigenes Foto → manuelle URL → pokemon.com → Pokédex-Artwork
- [x] "pokemon.com"-Label in Detailansicht
- [x] Backfill-Buttons in Settings-Seite
- **Ergebnis: 80/96 besessener Karten mit Kartenbild (83%)**
- Nicht verfügbar: chinesische 151C, Mega Promos (MEP), japanische Sets → Pokédex-Artwork als Fallback
- [ ] PokémonTCG.io als Fallback für fehlende Sets (v0.7.0)

---

## 🔲 v0.4.0 — Authelia + Externer Zugriff
- [ ] Authelia als Portainer-Stack deployen (siehe `deploy/README.md`)
- [ ] DNS-Eintrag `auth.yourdomain.com` setzen
- [ ] DNS-Eintrag `pokecollect.yourdomain.com` setzen
- [ ] Caddy-Config mit Authelia `forward_auth` aktivieren
- [ ] Authelia-User anlegen, Hash generieren
- [ ] Externen Zugriff testen (Web + Android)

## 🔲 v0.5.0 — Android App
- [ ] Android-App auf Gerät testen
- [ ] Typo "Besossen" in Android-Code fixen (CardDetailScreen.kt Zeile 64, ScanScreen.kt)
- [ ] API-URL in App konfigurierbar machen (intern vs. extern via Authelia)
- [ ] Basis-Funktionen testen: Karten scannen, Status setzen, Detailansicht

## 🔲 v0.6.0 — Wunschkarten
> **Ziel:** Eigene Wunschliste führen — welche exakten Karten (Set + Nr. + Version) will ich noch sammeln?

- [ ] Neue DB-Tabelle `wunschkarten` (verknüpft mit `pokemon_cards` oder eigenständig)
- [ ] `/wishlist`-Seite im Web: Liste der gewünschten Karten
- [ ] Karte aus Sammlung zur Wunschliste hinzufügen (Button in Detailansicht)
- [ ] Karte manuell zur Wunschliste hinzufügen (Set + Nr. + Version + Sprache)
- [ ] Wunschkarte als "erhalten" markieren → automatisch in Sammlung übertragen
- [ ] Filter: besessen / nicht besessen / auf Wunschliste
- [ ] Preis-Anzeige auf Wunschliste (Cardmarket-Wert der gewünschten Karte)
- [ ] Export Wunschliste als CSV (für Cardmarket-Suche)

## 🔲 v0.7.0 — Cardmarket-Integration
- [ ] Cardmarket OAuth 1.0a testen (Keys via Settings-Seite eintragen)
- [ ] Preisabruf für einzelne Karte manuell triggern
- [ ] Preishistorie-Anzeige verbessern
- [ ] Preis-Quelle (30-Tage-Ø vs. Tagespreis) aktivieren
- [ ] Wunschlisten-Preise automatisch abrufen

## 🔲 v0.8.0 — Daten & Qualität
- [ ] CSV-Export (vollständige Sammlung als Backup)
- [ ] CSV-Import mit Duplikat-Erkennung
- [ ] Massenhafte Bild-URL-Zuweisung (alle Karten eines Sets auf einmal)
- [ ] Statistiken erweitern: Wert-Entwicklung, Set-Vollständigkeit

## 🔲 v1.0.0 — Production Release
- [ ] Docker Images auf ghcr.io pushen
- [ ] `docker-compose.yml`: `image:` statt `build:` verwenden
- [ ] Vollständige Test-Abdeckung kritischer Endpunkte
- [ ] Öffentliche Dokumentation
