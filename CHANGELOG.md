# Changelog

## [v0.7.6] – 2026-06-07 (Scan: Foto-Zuschnitt, Tempo, Pokédex-Nr.)

### Scan
- **Schneller:** Gemini-„Thinking" abgeschaltet (thinkingBudget 0) und Bild vor
  dem Upload auf max. 1600 px verkleinert → deutlich kürzere Analyse, gleiche
  Erkennungsqualität.
- **Bounding-Box-Zuschnitt:** Gemini liefert jetzt die Position jeder Karte im
  Bild. Das eigene Foto wird damit **genau auf die Karte zugeschnitten** (statt
  mittig-grob) – funktioniert auch je Karte bei Binder/Multi.
- **Bildquelle wählbar:** je Karte „Eigenes Foto" vs. API-Bild umschaltbar.
- **Einzelkarten-Scan** behält nur die Hauptkarte (größte Box), falls eine Karte
  darunter mit aufs Bild geriet.
- **Pokédex-Nr. immer ermittelt:** auch ohne exakten Set-Treffer wird die
  National-Pokédex-Nr. über den Namen bestimmt → die Karte erscheint im Pokédex
  und bekommt den „Im Pokédex"-Schalter (vorher fehlte beides bei unsicheren).

## [v0.7.5] – 2026-06-07 (Binder zeigt jetzt den ganzen Pokédex)

### Fix
- Binder-Ansicht im Pokédex zeigte nur ~11 Seiten: Das Frontend lädt im Binder
  `limit=2000`, der API-Endpunkt deckelte `limit` aber bei 1100 → 422, der
  Ladevorgang schlug fehl und es blieben die alten ~96 Rasterkarten stehen.
  Limit-Obergrenze auf 5000 angehoben → alle ~1025 Pokédex-Slots / ~114 Seiten.

## [v0.7.4] – 2026-06-07 (Scan-Review & Pokédex-Binder)

### Scan-Review
- **Set per Dropdown** (wie beim manuellen Anlegen) statt Freitext – inkl.
  „Neues Set anlegen". Auswahl löst die Karte live neu auf.
- **Seltenheit mit Symbol** (RaritySelect) im Review; in der Kartenübersicht
  werden die Symbole bereits angezeigt.
- **Folierung**: alle Möglichkeiten wählbar (laut Karte mögliche zuerst).
- **Live-Bild**: ändert man Set, Nummer oder Sprache, wird die Karte über
  `POST /scan/resolve` neu aufgelöst und das Trefferbild aktualisiert – so sieht
  man sofort, ob die richtige Karte getroffen wurde.

### Pokédex-Binder
- **Nur noch ein Seitenwechsler:** In der Binder-Ansicht werden jetzt alle
  Karten geladen, der zusätzliche Daten-Pager oben ist ausgeblendet. Damit
  erscheinen auch neu hinzugefügte Karten auf den richtigen Seiten.

### Hinweis
- Unsicher erkannte Karten ohne Treffer bekommen keine Pokédex-Nr. und tauchen
  daher nicht in der Pokédex-Ansicht auf – im Review jetzt einfach das Set
  wählen, dann wird die Karte korrekt aufgelöst (inkl. Pokédex-Nr.).

## [v0.7.3] – 2026-06-07 (Scan- & Binder-Fixes)

### Fixes
- **Binder-Seite merkt sich die Position:** Beim Öffnen einer Detailansicht aus
  dem Binder (Pokédex oder Sammlung) und Zurück landet man wieder auf derselben
  Seite statt auf Seite 1 (`BinderView` persistiert die Seite je Ansicht).
- **Live-Webcam zeigt jetzt das Bild:** Stream wird erst nach dem Rendern des
  Video-Elements angehängt (vorher schwarz). Höhere Auflösung angefragt.

### Scan
- **Auto-Aufnahme:** Hält man die Karte ruhig, scharf und hell im Rahmen,
  löst die Kamera automatisch aus (abschaltbar). Manuelles „Aufnehmen" bleibt.
- **Seltenheit** wird erkannt: Resolver mappt die (englische) TCGdex-Rarity auf
  unser Seltenheits-Enum und füllt sie im Bestätigungs-Dialog vor (editierbar).
- Bei unklarem/falschem Set-Kürzel zusätzlicher Fallback über Namenssuche
  gefiltert nach Kartennummer.
- Vorschaubild im Review größer + klickbar (Originalgröße zur Kontrolle).

### Hinweis
- Live-Webcam/PWA brauchen HTTPS – siehe Teil 3 (geplant): Caddy-TLS löst den
  Chrome-Flag-Workaround dauerhaft, auch am Smartphone.

## [v0.7.2] – 2026-06-07 (Scan-Feinschliff: Gemini, Webcam, Foto)

### Scan
- **Gemini-Key über die Einstellungsseite** pflegbar (DB-Setting, Fallback .env).
  Ist der Key gesetzt, nutzt der Scan automatisch Gemini statt OCR – inkl.
  konfigurierbarem Modell. `GET /scan/status` spiegelt den DB-Key wider.
- **Desktop-Webcam:** „Kamera starten" immer verfügbar; bei unsicherem Kontext
  (HTTP über LAN) erscheint eine klare Anleitung (Chrome-Flag bzw. HTTPS).
- **Aufgenommenes Foto wird genutzt:** Vorschau im Review zeigt das gescannte
  Bild; bei Einzelkarten wird die Aufnahme zugeschnitten (Karten-Format 63:88)
  + skaliert und direkt als Kartenfoto hochgeladen (Anzeige-Vorrang).

### Set-Korrekturen
- `MEP` (Mega-Promos → `mep`) und `151C` (chinesische 151er → `sv03.5`,
  Bild via EN/DE-Sprachfallback) in Brücke + Seed ergänzt.
  Bild-Auflösung greift jetzt auch ohne eigene Set-Zeile auf die Brücke zurück.

## [v0.7.1] – 2026-06-07 (Karten-Scan)

### Features – Scan (Web + Android teilen dieselbe API)
- **POST /api/v1/scan**: Foto → erkannte Karten. Hybrid-Engine:
  Gemini (REST über httpx, kein SDK) wenn `GEMINI_API_KEY` gesetzt, sonst
  lokale **OCR** (Tesseract) als Fallback. `GET /scan/status` zeigt die aktive Engine.
- **Drei Modi**: `single` (Einzelkarte), `multi` (mehrere lose Karten),
  `binder` (ganze Mappenseite – wird am bekannten Raster rows×cols zerlegt).
- **Resolver** löst jede Erkennung gegen TCGdex auf (set_code→set_id-Brücke +
  Nummer → exakte Karte; bei Unschärfe Namenssuche). Liefert Kandidaten mit
  **Confidence + Liste unsicherer Felder** und vorbefülltem Bestätigungs-Dialog,
  Folierungs-Optionen nur laut `variants`.
- **POST /api/v1/scan/commit**: bestätigte Karten ablegen – Ziel Pokédex oder
  Sammlung (mit Binder-Slot über `position`), optional Pokédex-Vertreter setzen.
- **Web-Scan-UI** (`/scan`): Modus-/Ziel-/Raster-Auswahl, Kamera (getUserMedia,
  Rückkamera) **oder** Foto-Upload-Fallback (funktioniert auch über HTTP/LAN),
  Review-Liste mit Hervorhebung unsicherer Treffer, Stapel-Speichern.
  Scan-Button in der Navbar.

### Geplant für v0.7.x / 0.8.0
- Teil 3: Mobile-First-Refactor + PWA (manifest, service worker)
- OCR-Feintuning / optionale Bildvorverarbeitung
- Offene Bild-Lücken (MEP-Promos, CN-151-Set-Codes) nach Rückmeldung der Labels

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
