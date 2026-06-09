# Changelog

## [v0.9.8] – 2026-06-09 (Eck-Editor mit Lupe/Zoom, Detailseiten-Zuschnitt, Dex-Nr.-Fix)

### Fixes (Feedback zu v0.9.7)
- **Eck-Editor verbessert:** Beim Ziehen erscheint jetzt eine **Lupe** (der
  Finger verdeckt den Eckpunkt nicht mehr – man sieht genau, wo man platziert).
  Zusätzlich **Zoom (+/−, Mausrad) und Verschieben (Pan)**, damit bei mehreren
  Karten auf einem Foto präzise gearbeitet werden kann.
- **Zuschnitt auf der Detailseite:** Nach „Foto aufnehmen/hochladen" öffnet sich
  derselbe Eck-Editor – das Foto kann vor dem Speichern zugeschnitten/entzerrt
  werden (vorher wurde es direkt unbearbeitet hochgeladen).
- **Pokédex-Nr. bei Karten ohne eigene dexId:** Manche (neue) Sets – z.B. die
  Mega-Evolution-Reihe (ASC „Erhabene Helden", `me02.5`) – führen an der Karte
  selbst **keine** National-Dex-Nr. (TCGdex liefert `dexId: null`). Der Scan zieht
  die Spezies-Dex-Nr. jetzt aus einer Schwesterkarte gleichen Namens → die Karte
  bekommt wieder eine Pokédex-Nr. (im Beispiel Traunfugil → #0200).

### Intern
- Crop-/Entzerrungs-Logik nach `web/src/lib/cardCrop.ts` ausgelagert; `CornerEditor`
  ist jetzt eine eigene, wiederverwendbare Komponente (Scan + Detailseite).

### Noch offen
- Automatischer Erst-Zuschnitt (Gemini-Ecken) ist bei mehreren/schrägen Karten
  noch nicht immer ideal – die manuelle Eck-Korrektur gleicht das aus.

## [v0.9.7] – 2026-06-09 (Foto-Entzerrung, Bild-Fallback per Name, EXIF-Orientierung)

### Fixes (Known Issues)
- **Foto-Zuschnitt/Perspektive (Issue 1):** Eigene Scan-Fotos werden jetzt mit
  einer echten **Homographie** entzerrt (feines Gitter statt grobem
  2-Dreieck-Affin) – auch stark schräge Karten werden sauber rechteckig.
  Querformat-Zuschnitte (gekippte Karte) werden automatisch ins Hochformat
  gedreht.
- **Manuelle Eck-Korrektur (Issue 1):** Im Scan-Review gibt es pro Karte
  „✥ Ecken anpassen" – die 4 Kartenecken lassen sich per Drag exakt setzen,
  danach wird das Foto perspektivisch neu entzerrt (auch bei mehreren/schrägen
  Karten auf einem Bild).
- **Bild ohne Kartennummer (Issue 2):** Fehlt die aufgedruckte Nummer (oder
  scheitert die exakte Auflösung), wird das Kartenbild jetzt über die
  **Namenssuche** gezogen (wahrscheinliches Bild der gleichen Spezies,
  bevorzugt aus dem bekannten Set). Ohne Set werden nur Bild + Pokédex-Nr.
  gesetzt, um keine falsche konkrete Karte zu erzwingen.
- **Ausrichtung in Raster/Binder (Issue 3):** Hochgeladene Fotos werden
  serverseitig anhand ihrer **EXIF-Orientierung** aufrecht gespeichert (inkl.
  Thumbnail) – Handy-/Galerie-Uploads liegen nicht mehr quer/verdreht.

### Intern
- **Backend-Version zentralisiert:** `settings.app_version` (config.py, per Env
  `APP_VERSION` überschreibbar) statt hart `1.0.0` in main.py; an FastAPI
  durchgereicht und in `/health` ausgegeben. Eine Projektversion pro Dev-Stand –
  beim Release nur `web/src/lib/version.ts` + `backend/app/config.py` hochzählen.

## [v0.9.6] – 2026-06-07 (Erster öffentlicher Release)

### Fixes
- **Detailseite**: Illustrator wird jetzt angezeigt.
- **Datenverlust behoben**: „Im Pokédex" anklicken überschreibt nicht mehr die
  nicht gespeicherten Formular-Eingaben (nur das Flag wird synchronisiert).

### Doku
- ROADMAP: Known-Issues-Abschnitt (Foto-Zuschnitt/Entzerrung, Bild erst mit
  Kartennummer) + neuer Backlog-Punkt „Sealed-Produkte sammeln".

> Erster öffentlicher Release. Es bestehen bekannte Einschränkungen (siehe
> ROADMAP → Known Issues), die zeitnah behoben werden.

## [v0.9.5] – 2026-06-07 (Set-Sortierung, Binder-Dimmen, Sticky-Header, Mobile-Lupe)

- **Sortierung „Set + Nr."** in cards-API + Filter (Pokédex/Owned) – sortiert nach
  Set und aufgedruckter Kartennummer.
- **Binder: Filter dimmt statt zu entfernen.** In der Binder-Ansicht (Pokédex)
  bleiben alle Karten an ihrem festen Platz; nicht passende werden ausgegraut
  (Suche, Set, Seltenheit, Sprache, Illustrator, Generation …). Im Raster wird
  weiter klassisch gefiltert.
- **Sticky-Header:** Statistik + Filter + Steuerung bleiben oben fixiert, nur die
  Karten/der Binder scrollen (Pokédex, „Alle besessenen", Katalog).
- **Mobile-Filter-Lupe:** Der Filter wird über eine 🔍-Lupe in der Anzahl/Wert-Zeile
  auf-/zugeklappt (spart eine Zeile); FilterSidebar ist dafür steuerbar gemacht.

## [v0.9.4] – 2026-06-07 (Illustrator-Filter, Filter angeglichen, Binder-⚙ in Navizeile)

- **Illustrator an Karten**: neues Feld `illustrator`, automatisch aus TCGdex
  befüllt (Bild-Backfill, Katalog-Übernahme). Filter `illustrator` in der cards-API.
- **Illustrator-Filter** jetzt auch in Pokédex + „Alle besessenen" (durchsuchbares
  Dropdown) → gleiche Felder wie im Katalog.
- **Katalog-Filterleiste einklappbar** („🔍 Filter") wie überall → einheitliche Optik.
- **Binder-⚙** sitzt jetzt in der Navigationszeile (‹ Seite › ⚙) statt in einer
  eigenen Zeile; Optionen klappen darüber auf.

### Hinweis
- Illustrator füllt sich bei neuen/aktualisierten Karten. Für bestehende besessene
  Karten einmal Bild-Backfill laufen lassen:
  `curl -X POST "…/api/v1/cards/meta/backfill-images?force=true"`

## [v0.9.3] – 2026-06-07 (UI-Vereinheitlichung: Katalog-Punkte, Owned ohne Binder, Set-Filter mit Logos)

- **Katalog-Karten** zeigen jetzt grünen (besessen) / roten (im Pokédex) Punkt.
- **„Alle besessenen Karten"**: kein Binder mehr (nur Raster) + Anzahl/Wert-Header
  (mobil in einer Zeile, wie im Pokédex).
- **Einheitlicher Set-Filter** überall: durchsuchbares Dropdown, nach Serie
  geclustert, mit Set-Logo (Pokédex + Owned nutzen denselben wie der Katalog).
- **Binder-Steuerung kompakt**: Seiten-Raster + Größe hinter einem ⚙-Schalter
  (spart Platz, v.a. mobil).

### Noch offen (nächste Runde)
- Sticky-Header (UI fix, nur Karten/Binder scrollen)
- Mobile: Filter-Lupe direkt in die Anzahl/Wert-Zeile integrieren
- Illustrator-Filter auch im Pokédex/Owned (braucht Illustrator-Feld an Karten)

## [v0.9.2] – 2026-06-07 (Filter horizontal, Pokédex-Header schlanker)

- **Filter horizontal über den Karten** (Pokédex + „Alle besessenen") statt
  linker Sidebar – wie im Katalog. Weiterhin ein-/ausklappbar.
- **Katalog: „Filter zurücksetzen"** ergänzt.
- **Pokédex-Header:** „Gesammelt x/y"-Karte entfernt (steht in den Statistiken).
  Auf Mobile stehen Pokédex-Fortschritt und Gesamtwert in einer Zeile.

## [v0.9.1] – 2026-06-07 (Katalog: Filter, Detail, Auto-Enrichment)

- **Enrichment automatisiert:** `POST /catalog/enrich-all` läuft selbstständig
  durch, bis alle Karten angereichert sind (einmal aufrufen). Täglicher Cron
  ergänzt Neues. Kein wiederholtes curl mehr nötig.
- **Set-Filter** als durchsuchbares Dropdown, **nach Serie geclustert**
  (Schwert & Schild, Karmesin & Purpur …) mit **Set-Logo** je Eintrag.
- **Illustrator-Filter** als eigenes durchsuchbares Dropdown (`GET /catalog/illustrators`).
- **Katalog-Karten anklickbar** → Detail-Dialog mit Großbild + Infos und Aktionen
  „Zur Wunschliste" sowie „Zu Sammlung hinzufügen".

## [v0.9.0] – 2026-06-07 (Lokaler TCGdex-Katalog + Voll-Set-Sync)

### Sets vollständig
- **Set-Sync übernimmt jetzt ALLE TCGdex-Sets** in `pokemon_sets` (Code =
  offizielle Abkürzung). Kein manuelles Pflegen mehr – fehlende Sets wie
  **POR** (Perfect Order / me03) sind nach Sync automatisch da.

### Katalog (alle Karten)
- Neue Tabelle `tcgdex_catalog` (Spiegel aller ~23.000 Karten: Name DE/EN, Set,
  Nr., Bild; Illustrator/Rarity/dexId/Varianten werden angereichert).
- `POST /catalog/sync` (Sets + Katalog-Basis), `POST /catalog/enrich`
  (Volldetails in Etappen), `GET /catalog` (Suche/Filter/Sortierung),
  `GET /catalog/meta`.
- **Seite „Alle Karten"** (`/catalog`, verlinkt unter Sammlungen): durchsuchbar
  nach Name/Nr./Illustrator, filterbar nach Set/Generation, sortierbar nach
  Set+Nr./Name/Pokédex-Nr.; **Stern-Button** legt die Karte auf die Wunschliste.
- Katalog-Karten zählen **nicht** zu besessenen/Pokédex-Karten und in keine
  Statistik; sie sind read-only, aber per Stern auf die Wunschliste (und per API
  in Sammlungen) übernehmbar. Ohne TCGdex-Bild (z. B. MEP) → Platzhalter.
- Täglicher Cron 04:00: Set-/Katalog-Sync + Anreicherung in Etappen.

### Hinweis
- Illustrator-Daten füllen sich schrittweise (Enrichment) bzw. sofort beim
  Übernehmen einer Karte. Der Illustrator-**Filter** folgt als eigenes Feature (🅲).

## [v0.8.1] – 2026-06-07 (Mobile-Detail, Binder-Swipe, Gemini-Limits)

- **Detailseite mobil**: Bild + Felder stapeln am Handy (flex-col), Felder
  einspaltig auf kleinen Screens.
- **Binder blättern per Wisch** (links/rechts) auf Mobile.
- **Filter ein-/ausklappbar auch am Desktop** (auf Desktop offen voreingestellt).
- **Gemini Free-Tier-Anzeige**: Limits je Modell (Flash 1500 RPD/15 RPM/1M TPM,
  Pro 50 RPD/2 RPM/2M TPM) – „heute X / RPD" mit Balken + „Scans übrig",
  Ø Tokens/Scan, RPM/TPM-Info.

## [v0.8.0] – 2026-06-07 (Teil 3: Mobile-First + PWA)

### Mobile
- **Bottom-Navigation** auf dem Smartphone (Pokédex / Sammlungen / Scan /
  Wunschliste / Einstellungen) mit Icons; Scan-Button hervorgehoben. Desktop-Nav
  unverändert (Links blenden auf Mobile aus → keine abgeschnittene Top-Leiste mehr).
- **Filter als ein-/ausklappbares Sheet** auf Mobile (mit Anzahl aktiver Filter);
  Pokédex- und „Alle besessenen"-Seite stapeln Filter/Inhalt sauber (flex-col).
- Layout-Abstand für die Bottom-Nav, Safe-Area berücksichtigt.

### PWA
- **Installierbar:** Web-App-Manifest + App-Icons (Pokéball), Theme-Color,
  Standalone-Anzeige → „Zum Startbildschirm hinzufügen".
- **Service Worker** (`/sw.js`): App-Shell-Cache + stale-while-revalidate für
  GET/API/Bilder → Offline-Lesezugriff auf die zuletzt geladene Sammlung.
  Nicht-GET-Anfragen werden nie abgefangen.

### Hinweis
- Installation + Offline + (Live-Kamera) brauchen **HTTPS**. Über HTTP im LAN
  läuft die App normal, aber ohne Installier-/Offline-Funktion und ohne
  Live-Webcam. → Caddy-TLS einrichten, dann ist alles aktiv.

## [v0.7.11] – 2026-06-07 (Scan-Review: Pokédex-Nr. editierbar, Crop-Ausrichtung)

### Scan-Review
- **Pokédex-Nr. ist jetzt editierbar** – auch wenn die Erkennung keine findet
  (z. B. „Team Rockets Kramurx"), kann man sie manuell eintragen; danach wird die
  Karte dem Pokédex zuweisbar (Schalter erscheint). Manuelle Nr. überlebt das
  Neu-Auflösen.
- **Crop-Ausrichtung:** quer fotografierte Karten werden vor der Entzerrung auf
  Hochformat gedreht (längere Kante = Höhe) → kein seitwärts liegender Zuschnitt mehr.

### Hinweis
- Promo-Rarität wird erkannt, sobald die Karte einen Treffer hat. Bei unsicheren
  Karten (kein Set erkannt) erst Set wählen → Rarität/Pokédex-Nr. füllen sich.

## [v0.7.10] – 2026-06-07 (SVP-Promo-Set)

- Set **SVP** (Karmesin & Purpur Black Star Promos → TCGdex `svp`) in Seed +
  Brücke ergänzt. Nach Deploy im Set-Picker verfügbar; Bilder/Preise lösen auf.

## [v0.7.9] – 2026-06-07 (Foto-Entzerrung, Foto-Löschen-Fix, Gemini-Limit)

### Scan
- **Perspektivische Entzerrung:** Gemini liefert die vier Kartenecken; das eigene
  Foto wird damit auf ein sauberes Karten-Rechteck (63:88) entzerrt – auch bei
  schräg fotografierten Karten / mehreren Karten auf einem Bild. Fällt ohne
  Ecken auf bbox-Zuschnitt zurück.

### Fix
- **Foto löschen:** Nach dem Löschen eines eigenen Fotos wird automatisch das
  TCGdex-Kartenbild nachgeladen (statt Platzhalter), sofern keine manuelle URL
  gesetzt ist.

### Gemini-Tracking
- **Tageslimit konfigurierbar** (Einstellungen): Anzeige „heute X / Limit" mit
  Fortschrittsbalken + „übrig", da Google das Restkontingent nicht per API meldet.

## [v0.7.8] – 2026-06-07 (Pokédex-Dublette, Foto aufnehmen, Gemini-Tracking)

### Fix
- **Pokédex-Dublette behoben:** Besitzt man eine Karte einer Spezies (auch ohne
  „Im Pokédex"-Flag), wurde zusätzlich noch der graue Platzhalter derselben
  Nummer angezeigt. Platzhalter erscheinen jetzt nur noch für Spezies, die weder
  geflaggt noch besessen sind.

### Features
- **Kartenfoto neu aufnehmen:** Auf der Kartenseite gibt es jetzt „Foto
  aufnehmen" (Kamera) zusätzlich zu „Foto austauschen/hochladen" (Galerie).
- **Gemini-Nutzungs-Tracking:** Requests + Tokens werden pro Tag gezählt
  (`gemini_usage`), Anzeige in den Einstellungen (heute / gesamt) mit Hinweis
  zum täglichen Free-Tier-Reset. Endpoint `GET /scan/usage`.

### Hinweis (Verhalten, kein Bug)
- Eine **besessene** Karte erscheint immer im Pokédex (eine je Spezies). Das
  „Im Pokédex"-Flag wählt nur aus, **welche** Karte erscheint, wenn man mehrere
  derselben Spezies besitzt.

## [v0.7.7] – 2026-06-07 (Scan-Review: Zuschnitt-Fix, Pokédex je Karte, Wunschkarte)

### Scan
- **Zuschnitt korrekt:** Gemini-Bounding-Box wird jetzt im nativen Format
  `[ymin,xmin,ymax,xmax]` (0–1000) interpretiert → das eigene Foto sitzt sauber
  auf der Karte (vorher daneben).
- **Pokédex je Karte:** Pokédex-Nr. wird in der Review angezeigt; „Im Pokédex"
  ist jetzt **pro Karte nach dem Scan** umschaltbar (Setup-Häkchen bleibt als
  Standard für alle).
- **Wunschkarte scannen:** neues Ziel „Wunschliste" (mit Priorität) – Karte
  wird als nicht besessen auf die Wunschliste gelegt.
- **Mobile Review:** Karten-Layout stapelt am Handy (Bild oben, Felder darunter),
  Set-Auswahl/Felder laufen nicht mehr aus der Box (min-w-0).

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
