# Changelog

## [v1.2.0] – 2026-07-18 (Quick-Wins: Kurzcode-Suche, besserer Scan) — gefahrlos

### Suche & Scan
- **Kurzcode-Suche „PFL 001":** In Katalog- und Kartensuche löst ein
  `KÜRZEL NUMMER` direkt auf Set + Kartennummer auf — spart am Handy das
  Filtern über zwei Felder. Unbekannte Kürzel fallen automatisch auf die
  normale Volltextsuche zurück (#19).
- **Treffsichererer Scan:** Findet die Namenssuche nichts, sucht der Resolver
  einmal ohne Karten-Suffix (ex/GX/V/VSTAR/VMAX) erneut — breitere
  TCGdex-Treffer, ohne echte Namen wie „Iksbat" zu verstümmeln (#20).

## [v1.1.0] – 2026-07-18 (Set-Sammlungen, Export/Backup, HTTPS) — ⚠️ enthält Migration

### ⚠️ Deploy-Hinweis
- **Additive Migration** (neue Tabelle `collection_soll` + 5 Spalten an
  `collections`) — läuft automatisch beim Start, kein manueller Schritt.
  Backup vor dem Deploy trotzdem empfohlen (jetzt per Knopf, siehe unten).

### Set-Sammlungen (Issue #16)
- **Sammlungen können jetzt Sammelziele sein:** beim Anlegen ein Set wählen,
  optional nach **Folierung** (z. B. nur Holo) und **Sprache** einschränken,
  Umschalter „inkl. Secret Rares" (Master-Set). Dasselbe Set lässt sich
  mehrfach mit verschiedenen Regeln sammeln.
- **Automatisch vorbefüllte, aber kuratierbare Soll-Liste:** Startvorschlag aus
  dem TCGdex-Katalog (bei Folierungs-Zielen die passenden Varianten), danach
  Karten hinzufügen/entfernen und die Folierung je Slot anpassen.
- **Fortschritt** je Ziel („X / Soll" + Balken) in Liste und Detail; fehlende
  Karten per Klick auf die Wunschliste. Binder- und Rasteransicht zeigen
  erfüllte Karten echt, fehlende als gedimmte Katalog-Platzhalter.
- Eine Karte zählt für alle passenden Ziele gleichzeitig.

### Daten: Export & Backup (Issue #17)
- Neuer Abschnitt „Daten" in den Einstellungen: **CSV-Export** der Sammlung
  (Excel-tauglich mit BOM), **Backup als ZIP** (Datenbank + eigene Fotos,
  self-contained inkl. Katalog) und **Wiederherstellen** per Upload mit
  doppelter Sicherheitsabfrage.

### HTTPS im LAN (Issue #18)
- Doku + Caddyfile-Snippet für HTTPS via `tls internal` — für einen
  bestehenden externen Caddy oder als optionalen In-Stack-Service. Schaltet
  PWA-Installation und Kamera-Scan am Handy ohne Browser-Flag frei.
  (Owner-Schritt: Snippet einbinden + CA-Zertifikat am Handy installieren.)

## [v1.0.0] – 2026-07-14 (Auth: Login-Pflicht, maskierte Secrets) — ⚠️ Deploy nur mit vorbereiteter .env!

### ⚠️ Breaking / Deploy-Checkliste
- **`APP_PASSWORD_HASH` ist jetzt Pflicht** — ohne gesetzten Hash (Env oder
  In-App-Passwort) verweigert die API den Start. Das eingebaute
  Default-Passwort (`secret`) ist entfernt. Hash erzeugen: siehe
  `.env.example` / `deploy/README.md`.
- **`CORS_ORIGINS` neu** (kommagetrennt) — Wildcard `*` ist abgeschafft.
  Prod-.env: `CORS_ORIGINS=http://<server-ip>:3011`.
- `GET /images/proxy` entfernt (war unbenutzt).

### Sicherheit (Issue #1, ADR-0003)
- **Alle Fach-Router verlangen ein JWT** (`require_auth`); frei bleiben nur
  `/auth/login`, `/health` und der `/images`-Mount (eigene Fotos für `<img>`).
- **Login-Seite im Web** (DE/EN), Auth-Guard, 401-Redirect, Abmelden in den
  Einstellungen; Token in localStorage, Laufzeit 30 Tage.
- **API-Keys verlassen das Backend nie mehr im Klartext**: `GET /settings`
  liefert je Secret nur noch „gesetzt" + Maske (`•••• XXXX`); Ändern durch
  Neueingabe.
- Global gemounteter Toast-Container (Fehlermeldungen erscheinen jetzt
  überall zuverlässig).

## [v0.9.15] – 2026-07-14 (Bauwelle 2a: Settings wirken, Admin-Buttons, Architektur-Schnitt)

### Einstellungen, die jetzt wirklich wirken (#12)
- **Preisquelle** (30-Tage-Durchschnitt vs. Tagespreis) wird beim Preisupdate
  tatsächlich ausgewertet (Tagespreis = TCGdex `avg1`, Fallback avg30-Kette).
- **Cardmarket-Keys aus den Einstellungen werden benutzt** (DB vor .env) —
  wer Keys hat, kann sie nutzen; TCGdex bleibt Primärquelle.
- **Zwei Admin-Buttons:** „Preise jetzt aktualisieren" und „Katalog jetzt
  synchronisieren" (mit Status-Toast) — vorher nur per curl erreichbar.
- Entfernt: `POST /sets/sync`, `/catalog/enrich`, `/catalog/enrich-all`
  (Cron erledigt das täglich), `migrations/001_initial.sql` (create_all +
  Light-Migrations sind die Quelle der Wahrheit).

### Architektur-Schnitt (#14, keine Funktionsänderung)
- Backend: Bild-Verarbeitung (`services/card_images.py`) und Statistik
  (`services/stats.py`) aus dem cards-Router gelöst (477→314 Zeilen).
- Web: geteilte Daten-Hooks (`useEnums`/`useSets`/`useSettings`, ein Fetch
  pro Sitzung statt je Seite), zentrale `API_BASE`, Kartendetail-Seite in
  Panels geschnitten (759→300 Zeilen), `setTimeout`-Nachladen durch echten
  Refetch ersetzt.

### Kleinigkeiten
- Formular-Placeholder folgen der Sprache; Formular behält manuell
  getippte Namen auch bei langsam eingegebener Pokédex-Nr. (Altbug).
- `deploy.sh`/`scripts/*.sh` tragen jetzt Execute-Bits.

## [v0.9.14] – 2026-07-14 (Bauwelle 1: Härtung, DRY, i18n, Android-Aus)

### Entscheidungen
- **Android-App ausgemustert (ADR-0002):** `android/` von main entfernt; die
  Web-App ist die einzige Client-Plattform und muss am Handy-Browser voll
  skalieren. Branch `android-dev` bleibt als Archiv.
- **Kredo verankert (ADR-0001):** CONTEXT.md mit sechs Grundsätzen + Glossar.

### Härtung
- **Foto-Upload:** Suffix-Allowlist (jpg/jpeg/png/webp), Content-Type-Prüfung,
  12-MB-Limit, Aufräumen bei Verarbeitungsfehler (#2).
- **Gemini-Tageslimit wird durchgesetzt** statt nur angezeigt — bei Erreichen
  fällt der Scan auf lokale OCR zurück, das UI zeigt einen Hinweis (#3).

### DRY / Architektur
- **Ein Domain-Service fürs Karten-Anlegen** (`create_owned_card`):
  Platzhalter-Adoption + Pokédex-Exklusivität + Bild-Fetch gelten jetzt auf
  allen drei Wegen (Formular, Scan-Commit, Katalog-Übernahme) — vorher
  erzeugte der Scan Duplikate neben Platzhaltern (#4).
- Karten-Formulare (Neuanlage + Detail-Edit) teilen sich `useCardForm` +
  Feld-Komponenten (#5); Listen-Kopf-UI als `ListPageHeader` + Hooks (#8);
  Set-Code-Extraktion und Generationstabelle zentralisiert (#7);
  Bild-Prioritätskette als eine Funktion mit thumb/full-Variante (#10).
- **Services testbar:** DB-Session wird injiziert statt selbst erzeugt; 37
  neue Unit-Tests für pure Parser/Mapper, Suite jetzt 64 Tests (#9).

### UI / i18n
- **Settings-Seite komplett DE/EN** (~45 neue Keys), Tooltips/Streuner
  nachgezogen, Datums- und Zahlformate folgen der aktiven Sprache (#6).
- **Statistik-Seite mobiltauglich** (Breakpoints, scrollbare Tabelle) (#10).
- **A11y:** Labels mit Feldern verknüpft, Buttons explizit typisiert (#15).

### Aufräumen
- Tote Endpoints (`/auth/refresh`, `/cards/pokedex/{nr}`, `/cards/meta/sets`,
  `PUT /sets/{code}`), `pokemontcg_api_key` (nie benutzt), tote api.ts-Wrapper,
  `react-query`, `migrations/csv_import.py` + `python-dotenv` entfernt (#11).
- `scripts/gates.sh`: `all`-Ziel brach bei rotem Backend-Gate nicht ab (Fix).

## [v0.9.13] – 2026-07-14 (Fundament: Tests, CI, Teststand + bcrypt-Fix)

### Fix
- **Login-Endpoint repariert:** `passlib 1.7.4` ist mit `bcrypt >= 4.1`
  inkompatibel — ohne Pin zog der Image-Build bcrypt 5.x, wodurch
  `POST /auth/login` und der Passwortwechsel in den Einstellungen mit 500
  abbrachen. Jetzt `bcrypt==4.0.1` gepinnt. (Gefunden von der neuen Test-Suite
  bei ihrem allerersten Lauf.)
- Irreführender Kommentar korrigiert: das eingebaute Default-Passwort ist
  `secret`, nicht `changeme` (Hash war schon immer der für `secret`).

### Entwicklungs-Fundament (keine Funktionsänderung)
- **Backend-Test-Suite:** 12 Smoke-Tests (`backend/tests/`) gegen echtes
  PostgreSQL — Health, Set-Seed, Karten-CRUD, Platzhalter-Invarianten,
  Settings, Auth. Läuft über den echten Migrationspfad (create_all +
  Light-Migrations), kein SQLite.
- **Lokale Gates ohne Node/Python:** `scripts/gates.sh` baut beide Images und
  fährt pytest gegen ein Wegwerf-Postgres — alles in Docker.
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) bei jedem Push —
  Backend-pytest (Postgres-Service) + Web `tsc --noEmit` + `next build`.
- **Lokaler Teststand:** Compose-Projekt `pokecollect-test`
  (`scripts/teststand.sh`, Web :3021 / API :3020) mit Seed-Befehl für
  Browser-Verifikation ohne Prod-Runden.
- **Reproduzierbare Web-Builds:** `package-lock.json` committed (im
  Node-Container erzeugt), Dockerfile nutzt `npm ci`.
- **Agent-/Prozess-Setup:** `CLAUDE.md` (jetzt versioniert), `docs/agents/`
  (Issue-Tracker-, Triage-Label-, Domain-Doc-Konventionen), Triage-Labels im
  GitHub-Repo angelegt.

## [v0.9.12] – 2026-06-13 (Pokémon TCG Pocket ausschließen)

### Fix
- **Rein digitale Pocket-Sets fliegen raus:** TCGdex liefert die Serie „Pokémon
  TCG Pocket" (`tcgp`, ~15 Sets wie A1/A2/B1 …, tausende Karten) mit. Diese
  Karten existieren **nicht physisch** und haben in einem Sammlungs-Tracker für
  echte Karten nichts verloren – sie blähten den Katalog auf, verlängerten den
  Sync und erzeugten eine sinnlose „TCGP"-Gruppe in den Set-Filtern.
  - Set- und Katalog-Sync übernehmen die Serie `tcgp` jetzt **gar nicht mehr**
    (zentral über `services/tcgdex.EXCLUDED_SERIES`).
  - **Self-Healing:** vorhandene Pocket-Daten werden bereinigt – sofort beim
    Deploy (Light-Migration löscht `tcgdex_catalog`/`pokemon_sets` der Serie
    `tcgp`) und zusätzlich bei jedem Sync.
- Hintergrund: Idee aus dem Funktionsvergleich (dortiges Issue/PR zu Pocket-Sets);
  hier bewusst **ohne** Settings-Schalter umgesetzt (hart ausgeschlossen), da
  PokéCollect ein reiner Tracker für physische Karten ist.

### Hygiene
- Git-History von einer versehentlich committeten privaten LAN-IP bereinigt
  (`history rewrite` + force-push; betraf nur Doku-Strings in `i18n.tsx`).

## [v0.9.11] – 2026-06-10 (Aufräum-Release: Repo-Hygiene, DB-Robustheit, Settings wirksam)

### Repo-/Code-Hygiene (keine Funktionsänderung)
- **Toter Code entfernt:** `web/src/lib/auth.ts` + `authApi` (kein Login-Flow im
  UI vorhanden), 15 ungenutzte i18n-Keys (DE+EN), ungenutzte
  `refresh_prices_for_cards` in `cardmarket.py`, ungenutzte `ResolvedCard`-Klasse.
- **Duplikate konsolidiert:** `SERIES_LABEL`/`seriesLabel` und `extractSetCode`
  existieren nur noch einmal in `lib/utils.ts`.
- **Veraltete Texte korrigiert:** „pokemon.com" → TCGdex (Settings-Sektion,
  Detailseiten-Badge, Backfill-Beschreibung); die falsche Behauptung
  „Keys werden verschlüsselt gespeichert" entfernt (sie liegen im Klartext in
  der DB – siehe Security-Hinweis unten).
- **IP-Scrub:** echte LAN-IP aus dem Webcam-HTTPS-Hinweis entfernt
  (generischer Platzhalter). Hinweis: in der Git-History ist sie weiterhin
  vorhanden (kein History-Rewrite durchgeführt).
- **Obsolete Dateien:** `migrations/002` + `003` (einmalige Skripte der
  pokemon.com-Ära) entfernt; `bild_karte_url` wird jetzt von den
  Light-Migrations abgedeckt.

### Robustheit / kleine Verhaltensänderungen
- **DB-Schema selbstheilend:** Light-Migrations ergänzen `bild_karte_url`
  (frische Installs über `001_initial.sql` waren sonst unvollständig) und
  entfernen die veralteten CHECK-Constraints aus 001 – diese kannten neuere
  Seltenheiten (z.B. **ACE SPEC Rare**, **Shiny Rare**, **Mega Hyper Rare**)
  nicht und hätten das Speichern solcher Karten mit einem DB-Fehler blockiert.
- **Einstellungen wirken jetzt wirklich:**
  - *Standard-Sprache/-Zustand* befüllen das „Neue Karte"-Formular vor;
  - der *Scan* nutzt die Standard-Sprache (vorher hart „DE");
  - *Uhrzeit der Preisaktualisierung* steuert den Cron (nach API-Neustart,
    wie im UI-Hinweis beschrieben – vorher fix 03:00).
  - Sprach-/Zustandslisten der Settings-Seite an die Backend-Enums angeglichen.
- **CORS korrigiert:** `allow_credentials=False` – die Kombination
  Wildcard-Origin + Credentials ist ungültig; Auth läuft (wenn genutzt) über
  den Authorization-Header.
- **Redis entfernt** (Compose-Service, Env, pip-Paket): wurde nirgends im Code
  verwendet – ein Container weniger, kleineres Image. Ebenso die ungenutzten
  Pakete `alembic` und `notion-client` entfernt. Das ZFS-Dataset `cache` wird
  nicht mehr gebraucht.
- `POST /prices/refresh` lädt nur noch Karten-IDs statt kompletter Objekte.

### Doku
- **README komplett neu** (war auf v0.4.1-Stand): Features, Architektur,
  Konfiguration, Ports, Deploy-Verweis.
- ROADMAP aufgeräumt: erledigte Punkte (Illustrator, Homographie,
  „Zu Sammlung hinzufügen" im Katalog) abgehakt, Backlog neu nummeriert.
- `.env.example` auf Ist-Stand (NEXT_PUBLIC_API_URL, APP_USERNAME/HASH,
  GEMINI_API_KEY; Redis-/Notion-Reste raus).

### Security-Hinweis (offen, bewusst nicht „mal eben" geändert)
- Die API erzwingt aktuell **keine Authentifizierung** (`require_auth`
  existiert, ist aber nicht verdrahtet; es gibt keine Login-Seite). Im LAN ist
  damit u.a. `GET /settings` inkl. Gemini-/Cardmarket-Keys für jeden erreichbar.
  Extern schützt Authelia. Auth-Durchsetzung ist als v1.0-Punkt in der ROADMAP
  dokumentiert (Login-UI + Router-Dependencies, Bild-Routen ausgenommen).

## [v0.9.10] – 2026-06-09 (Originalfotos, EXIF-Konsistenz, Live-Flip/Rotate, Cache-Busting, Promo)

### Fixes (Feedback-Runde)
- **Bild im Editor richtig, in der Übersicht gespiegelt/gedreht (Kern-Bug):** Foto
  wird beim Aufnehmen/Hochladen jetzt **EXIF-normalisiert** (Orientierung fest in
  die Pixel gebacken). Dadurch zeigen Editor-Anzeige und gespeicherter Zuschnitt
  IMMER dieselbe Ausrichtung – kein „im Bearbeiten korrekt, in der Übersicht
  geflippt" mehr.
- **Änderung erst nach Seiten-Neuladen sichtbar:** Bild-URLs haben jetzt
  **Cache-Busting** (`?v=aktualisiert_am`) – nach Zuschnitt/Drehen/Spiegeln wird
  das neue Bild sofort angezeigt (Raster, Binder, Detail).
- **Flip/Drehen ohne Live-Reaktion:** Drehen (90°) und horizontal/vertikal
  spiegeln wirken jetzt **live im Editor** (Bild + Eckpunkte drehen/spiegeln
  sichtbar mit); das Ergebnis entspricht der Vorschau.
- **Originalfotos werden gespeichert:** Zusätzlich zum Zuschnitt wird das
  ungeschnittene Originalfoto aufbewahrt. „Foto bearbeiten" auf der Detailseite
  öffnet das **Original** → man kann großzügiger neu zuschneiden statt nur den
  vorhandenen Ausschnitt.
- **Promo-Karten:** Seltenheit wird für Promo-Sets (z.B. „SVP Black Star Promos")
  als **Promo** gesetzt und die Nummer ohne Nenner (z.B. `061` statt `061/225`).

### Hinweise
- Eck-Editor: Pinch/Zoom + Verschieben am Handy, Mausrad + Linksklick-halten am
  Desktop, ganzes Foto sichtbar (Feedback war positiv – bleibt so).
- Multi-Scan mit mehreren/gemischt ausgerichteten Karten kann die Erkennung
  (Gemini) noch falsch zuschneiden – Einzelscan oder manuelle Eck-Korrektur hilft.

## [v0.9.9] – 2026-06-09 (Eck-Editor: Gesten/Flip/Rotate, Auto-Ausrichtung, Detail-Bearbeiten)

### Fixes (Feedback zu v0.9.8)
- **Bild stand auf dem Kopf / gespiegelt (Auto-Zuschnitt):** Die Ecken aus der
  Erkennung werden jetzt **nach Bildposition sortiert** (TL,TR,BR,BL) – verhindert
  gespiegelte/kopfstehende und gestauchte Zuschnitte beim automatischen Zuschnitt.
- **Eck-Editor – Bedienung am Smartphone:** Das Foto ist jetzt komplett sichtbar
  (alle 4 Ecken erreichbar), **Zoom & Verschieben per Fingergesten** (Pinch-Zoom,
  1-Finger-Verschieben) und am Desktop **Mausrad-Zoom + Linksklick-halten zum
  Verschieben**. Layout für kleine Screens überarbeitet.
- **Manuelle Ausrichtungs-Korrektur:** Im Eck-Editor neu **⟳ 90° drehen**,
  **horizontal/vertikal spiegeln** – falls ein Foto doch mal falsch herum ist,
  kann es per Hand korrigiert werden.
- **Foto nachträglich bearbeiten (Detailseite):** Für eigene Fotos gibt es jetzt
  zusätzlich zu Aufnehmen/Austauschen/URL die Option **„Foto bearbeiten
  (Zuschnitt/Drehen)"** – das gespeicherte Bild wird erneut im Eck-Editor geöffnet
  (Zuschnitt/Flip/Drehen) und ersetzt.

### Hinweise
- Fotos werden **nur als zugeschnittene Karte** gespeichert (nicht das ganze
  Originalfoto). Nachträgliches Bearbeiten arbeitet auf dem gespeicherten Zuschnitt.
- Multi-Scan mit gemischten Ausrichtungen (Hoch-/Querformat) kann je nach Foto noch
  unzuverlässig erkennen – Einzelscan bzw. manuelle Nacharbeit hilft.

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
