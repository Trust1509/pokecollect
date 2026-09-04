# CLAUDE.md — PokéCollect

**Prozess-Stand: v1.13.0** — Stand der Vorlage `Trust1509/agent-projekt-template`,
gegen die dieses Projekt zuletzt abgeglichen wurde (Abgleich-Issue im Repo,
Titel `Abgleich v1.12.1`). Bei einer neueren Vorlagen-Version nach
`docs/agents/abgleich.md` der Vorlage abgleichen und diese Zeile hochsetzen.
**Prozess-Erkenntnisse gehen in die Vorlage, nicht in einen Alleingang hier:**
Fall + Vorschlag als Issue (Label `prozess-vorschlag` / `prozess-lehre`), bloße
Beobachtung/Reibung/Messzahl/Bestätigung als Kommentar im Rückmeldungs-Issue
der jeweiligen Version. Im Zweifel Kommentar. **Jede Meldung beginnt mit der
Kennung dieses Projekts: `P2 · Anwendung mit Datenbank`** — alle Projekte
melden unter demselben Konto, ohne Kennung ist nicht unterscheidbar, ob drei
Projekte dieselbe Lücke fanden oder eines sie dreimal meldete. Die Kennung
ersetzt die Anonymisierung nicht: kein Repo-Name, keine Kundendaten.
**Kennungen gelten beidseitig** (seit 20.08.2026): Eine Rückfrage aus dem
Vorlagen-Repo trägt `[Prozess-Agent]` (kollegiale Frage) oder `[Owner]`
(Entscheidungsanfrage) — beides läuft über dasselbe Konto, ohne Kennung ist es
nicht unterscheidbar.

**Profil: Anwendung mit Datenbank.** Bestimmt, welcher Teil der Vorlage beim
Abgleich zu prüfen ist: Der **Prozess-Kern** (Panel, Bau-Brief, Lehren,
Release-Ritual, Betrieb, Rückkanal) gilt immer; die **Stack-Maschine**
(Migrations-Prüfungen, Schnittstellen-Fuzzing, Sperrdateien,
Abhängigkeits-Scans) nur, wo sie hier einen Gegenstand hat — ohne
Migrations-Framework entfällt z. B. der Rückwärts-Roundtrip, **nicht** die
Datenerhalt-Probe.

Self-hosted Pokémon-TCG-Sammlungs-App. FastAPI (Python 3.12) + PostgreSQL 16 +
Next.js 14 (einzige Client-Plattform, mobile-first/PWA — ADR-0002). ~1.025
Karten, Scan per Handy-Browser (Gemini-Ecken + manueller CornerEditor),
Preise via TCGdex/Cardmarket.

**Vor dem ersten Slice `docs/agents/lehren.md` lesen** — Fehlerklassen, die hier
real getroffen haben. Kostet fünf Minuten und hat schon mehrfach einen Fund in
Produktion verhindert. Vor Architektur-/Feature-Arbeit zusätzlich `CONTEXT.md`
(Grundsätze + Glossar) und die passenden ADRs unter `docs/adr/`.

## Skills

Für die meisten Schritte gibt es fertige Methoden-Anleitungen (Herkunft
`mattpocock/skills`, global unter `~/.claude/skills/`): `docs/agents/skills.md`
sagt, welche wann passt. **Skills liegen pro Rechner, nicht im Repo** — auf
einem frischen Rechner erst `/setup-matt-pocock-skills`. Nur Skills nennen, die
dort wirklich existieren. Ein Skill ist eine *Methode*, der Prozess ist die
*Verbindlichkeit*: Wo beide etwas zum selben Thema sagen, gilt der Prozess.

## Arbeitsregeln

1. **Nichts aus dem Gedächtnis:** jede Behauptung am echten Code verifizieren,
   bevor du sie triffst oder darauf baust.
2. **Direkt-Push auf `main` ist autorisiert** (Trunk-Workflow, Pipeline ersetzt
   PRs). Releases nur per Tag — Ritual und Risiko-Stufen in
   `docs/agents/release-ritual.md`.
   **Ein Push landet ALLE lokalen Commits, nicht nur den eigenen letzten.**
   Vor jedem `git push` deshalb `git log --oneline @{u}..HEAD` lesen und
   jeden Commit darin verantworten — steht dort ungepanelter Code, wird er
   mit gelandet. Real passiert (04.09.2026): Ein Doku-Push nahm die vier
   ungepanelten Commits eines parallel arbeitenden Bau-Subagenten mit.
   **Deshalb:** Arbeitet ein Bau-Subagent parallel zum Hauptagenten, bekommt
   er einen eigenen `git worktree` mit eigenem Branch (wie die Panel-Stimmen
   seit v1.13.0) — dann kann kein fremder Push ihn mitnehmen, und der
   Hauptbaum bleibt frei.
3. **Je Issue ein Commit; Gates je CODE-Commit:** Tests + Typecheck + Build
   lokal grün (`scripts/gates.sh`), CI auf main grün. Reine Doku-Commits
   brauchen kein Gate — sie können keines bestehen (`[skip ci]`). Die Prüfungen
   laufen **einmal auf dem finalen Baumzustand**, egal von wem: dieselbe Suite
   von Bauer, Arbiter und CI dreimal zu fahren ist Leerlauf. Bei Datei-
   Überlappung mehrerer Arbeitspakete sequenziell statt parallel (Git-Race).
   Jeder Bau-Commit trägt den Modell-Stempel, mehrteilig, wenn mehrere Modelle
   beteiligt waren: `Built-With: bau=<m>; nacharbeit=<m>; arbitriert=<m>
   (<datum>)`. Ohne ihn ist nach vier Wochen nicht feststellbar, wer was gebaut
   hat — und jede Aussage über Modellverhalten bleibt Anekdote.
4. **Die Tabelle besitzt die PRÜFTIEFE** (wer prüft, wie tief) — sie ist der
   einzige Eigentümer der Auslöser. **Das RELEASE-GATE (wer vor Release
   freigibt) ist eine eigene, projekteigene Größe** und darf breiter sein als
   R4 (v1.12.1). Unsere Entscheidung dazu: Das frühere breitere Gate („jede
   Migration → Owner-OK") wurde im v1.11.3-Abgleich **bewusst und
   Owner-gebilligt** auf die R4-Auslöser verengt (#78, veto-fähig vorgelegt,
   kein Veto) — sie bleibt gültig. Unverändert: Gefahrloses (R0/R2) + Gates
   grün + Teststand verifiziert → Release autonom.
5. **Verifikation real, nicht nur Tests:** Änderungen in der laufenden App
   prüfen (lokaler Teststand, siehe unten), bevor „fertig" gemeldet wird.
6. **Grilling vor großen/riskanten Designs;** Lock-Spec als Issue-Kommentar.
7. **Echte Umlaute** (ä/ö/ü/ß) in allen deutschen Texten; interne ASCII-Werte
   nie roh ins UI (Label-Maps). UI ist zweisprachig DE/EN (`web/src/lib/i18n.tsx`)
   — neue UI-Texte immer in beiden Sprachen pflegen.
8. **Lehren verankern:** Fehlerklassen nach `docs/agents/lehren.md`, Fachliches
   nach `CONTEXT.md`/ADRs. Ist die Lehre **übertragbar** (klebt nicht am Stack),
   zusätzlich als Issue in die Vorlage.
9. **Versionierung und Auslieferung:** `docs/agents/release-ritual.md` — dort
   stehen die zwei Versionsstellen, die Risiko-Stufen und der Ablauf. Hier
   bewusst kein Auszug: Die Doppelpflege Kurzfassung/Langfassung war in zwei
   Projekten die Ursache, dass eine Pflichtregel unwirksam blieb (v1.8.0).

## Build, Gates, Teststand

- **Kein Node/npm lokal auf diesem PC.** Frontend-Gates laufen im Docker-Container:
  `scripts/gates.sh` (pytest + tsc + lint + next build). package-locks nur im
  Node-Container erzeugen — der lokale npm-Wrapper („allow-scripts") schreibt
  inkompatible Locks.
- **Backend-Tests:** `pytest` unter `backend/tests/`, gegen echtes Postgres
  (`conftest.py` schließt SQLite aus). Prüf-Abhängigkeiten stehen in
  `backend/requirements-dev.txt` — **Gate und CI installieren aus derselben
  Datei**, nie hartkodiert im Aufruf.
- **Lokaler Teststand:** Compose-Projekt `pokecollect-test`
  (`docker-compose.test.yml`), Web http://localhost:3021, API http://localhost:3020.
  `scripts/teststand.sh up` — für Browser-Verifikation vor jedem Release.
  **Trägt den echten Bestand des Owners samt Schlüssel** — nichts, was schreibt
  und aufräumt, läuft dort; `reset` löscht ihn samt Schlüssel.
- **CI:** GitHub Actions (`.github/workflows/ci.yml`): Backend-pytest + Frontend
  tsc/lint/build, gespiegelt in `scripts/gates.sh`. Actions sind SHA-gepinnt, jeder
  Workflow hat einen `permissions:`-Block (Least Privilege).
- **CI-DAUERREGEL: EIN Lauf je Slice, nicht je Push (Owner, 02.09.2026 — ersetzt
  die Quota-Notbremse vom 14./20.08.).** Das Actions-Kontingent (3000 Min/Monat)
  teilen sich alle Repos; das Portfolio-Tagesbudget ist 100 Min, ein Lauf hier
  kostet 2–4 Min. Deshalb:
  - **Alle Commits tragen `[skip ci]`** — Bau, Panel, Nacharbeit, Doku. Die
    **lokalen Gates auf dem finalen Baum sind die Verifikation** (Pflicht,
    Arbeitsregel 3); im Issue steht `Gates lokal grün auf <SHA>`.
  - **Nach der Landung eines Slices genau EIN `workflow_dispatch` auf dem HEAD**
    (`gh workflow run ci.yml`, dann `gh run watch <id> --exit-status`,
    run-id-gepinnt) — die CI ist die **Gegenprobe**, nicht die Prüfung. Wird sie
    rot: normaler Fix-Slice, kein Drama; ein Unterschied zwischen lokalen Gates
    und CI ist selbst ein Befund und gehört ins Rückmeldungs-Issue der Vorlage.
    Nie zum Prüfen pushen.
  - **Dauerhaft, weil sie keine Qualität kosten:** ein pytest-Job, **kein
    `pull_request`-Trigger** (es gibt keine menschlichen PRs), `concurrency` mit
    `cancel-in-progress` (Tag-Refs ausgenommen), `paths-ignore` für reine Doku.
  - **Dependabot** (`.github/dependabot.yml`): `interval` bleibt `monthly`,
    `open-pull-requests-limit: 1` — Sicherheits-Updates unberührt. Kein
    „weekly/limit 5" mehr; die frühere Rücksetz-Notiz war falsch.
  - **Releases:** nach grüner CI-Gegenprobe erlaubt; wo unser Release-Gate ein
    Owner-Gate verlangt (Migrationen, Geld — Arbeitsregel 4), **vorher fragen**.
    Zeitplan-Läufe (Security-Scan) laufen wieder normal.
  - Kostet ein Lauf deutlich mehr als 2–4 Min: im Rückmeldungs-Issue der
    Vorlage melden (der Owner fährt einen Budget-Wächter über alle Repos).
- **Wöchentlicher Security-Scan** (`.github/workflows/security-scan.yml`, Montag +
  `workflow_dispatch`, **kein** Push-Gate): `pip-audit` + `npm audit` +
  **Schemathesis**-API-Fuzzing (nur 5xx zählen). Bewusst nicht-blockierend: ein
  fremdes Upstream-CVE darf den Trunk nicht blocken → Funde triagieren wie
  Panel-Funde.
- **Rauchtest** (`sh scripts/smoke.sh`, #52): Playwright fährt 12 kritische
  Flows gegen einen **eigenen Wegwerf-Stapel** (`docker-compose.smoke.yml`,
  eigene DB, keine veröffentlichten Ports — läuft parallel zum Teststand und
  rührt dessen Daten nie an). **Kein Push-Gate** (~3–5 min, zwei Image-Builds):
  vor jedem Release lokal und im Wochen-Job (`.github/workflows/smoke.yml`).
  Bericht bei Rot: `e2e/playwright-report/index.html`. Test-Texte gebündelt in
  `e2e/tests/helfer.ts` (`T`).
- **Kein Alembic:** Schema-Änderungen sind additive, idempotente
  Light-Migrations in `backend/app/main.py::_run_light_migrations`. Was daraus
  folgt — Datenerhalt-Probe statt Roundtrip, Expand–Contract, die
  Transaktions-Falle beim Testen — steht in `docs/agents/lehren.md` §2.
- **Android:** ausgemustert (ADR-0002) — keine native App mehr; `android-dev`
  bleibt als Archiv-Branch.

## Deploy (macht immer der Owner)

- TrueNAS `<server-ip>` — **GETEILTER Server, nie `docker system prune -a`**.
  Repo dort: `/mnt/HDDs/Applications/pokecollect/app`, `deploy.sh` = git pull +
  Build beider Images. Ports API 3010 / Web 3011, UID:GID 3010:3010.
- SSH zum Server ist für Agenten geblockt; API/Web sind per HTTP testbar:
  `curl <server-ip>:3010/health`.
- Du lieferst getestete, getaggte Stände + klare Deploy-Anweisung; der Owner
  deployt selbst.
- **Betrieb** (Sicherung mit Rückspiel-Probe, Totmann-Schalter,
  Erreichbarkeits-Wächter) ist noch **offen** — er läuft am Server und gehört in
  die Infra-Welle. Bis dahin gibt es keinen automatischen Auszug: `GET
  /data/backup` muss von Hand gezogen werden.

## Sicherheit

- **DAS REPO IST ÖFFENTLICH** (Owner-Hinweis 04.09.2026). Zwei Folgen:
  1. **Alles, was committet wird, ist weltweit lesbar — auch die Historie.**
     Kein Geheimnis, keine echte IP (`<server-ip>` schreiben), keine echten
     Namen/Adressen in Beispieldaten, keine Kundendaten. Auch in Commit-Texten,
     Issue-Kommentaren und Panel-Berichten.
  2. **GitHub Secret Scanning und Push Protection sind aktiv** (gratis für
     öffentliche Repos, verifiziert 04.09.: `secret_scanning: enabled`,
     `secret_scanning_push_protection: enabled`, 0 offene Alerts) — ein
     eigener gitleaks-Job wäre doppelt und wird NICHT gebaut. Push Protection
     blockiert einen erkannten Schlüssel schon beim Push; wird ein Push
     deshalb abgelehnt: **nicht umgehen**, sondern den Wert aus der Änderung
     nehmen und dem Owner melden.
  Historien-Prüfung 04.09.2026 über alle 233 Commits (API-Key-Muster, private
  Schlüssel, `192.168.*`/`10.*`, Passwort-Zuweisungen, `.env`-Dateien,
  E-Mail-Adressen): **ohne Befund** — die einzigen Passwort-Treffer sind
  Wegwerf-Werte für Gate-Postgres und Teststand.

- **Auth-Zwang (Issue #1, ADR-0003):** Alle Fach-Router erzwingen ein JWT
  (`require_auth` via `include_router`-dependencies); auth-frei sind nur
  `/auth/login`, `/health` und der `/images`-Mount. Neue Router IMMER unter den
  Auth-Zwang in `api/v1/__init__.py` hängen.
- **Secrets nie im Klartext ausgeben.** `GET /settings` liefert sie nur maskiert
  (`*_set` / `*_masked`). Ohne `APP_PASSWORD_HASH` startet die App nicht.
- **Der Agent trägt keine Schlüssel ein** — Details, Ablageorte und der
  Wiederruf-Weg in `docs/SECRETS.md`.
- **Kein Produktiv-Wächter nötig — solange die Bedingung hält:** Es gibt keinen
  MCP-Server und keine schreibenden Prod-Werkzeuge; SSH ist geblockt. Die
  Prod-API ist per HTTP aber erreichbar, Schreiben scheitert heute **nur** daran,
  dass der Agent das Passwort nicht kennt. Das ist eine Umstands-Sperre, keine
  strukturelle. **Gerät ein Prod-Token oder das Prod-Passwort je in den Kontext
  eines Agenten, wird der Wächter sofort nötig** (Vorlage + Echtprobe siehe
  `docs/SECRETS.md`).

## Risikoklasse je Slice — hier wird entschieden, was geprüft wird

Jeder Slice bekommt im Bau-Brief eine Risikoklasse mit Auslöser
(`Risiko: R<n> — Auslöser: …`, Block 0). **Die Klasse wird aus Auslösern
abgeleitet, nicht frei vergeben** — kleine Diff-Größe stuft einen R3-Auslöser
nie herunter (sechs Zeilen an einer Berechtigungsgrenze sind R3). Im Zweifel
gilt die höhere Klasse; **die Abstufung nach unten braucht die Begründung,
nicht die nach oben.** Diese Tabelle ERSETZT die frühere Trivial-Liste und
die Pflichtfälle (v1.11.0) — sie ist der einzige Eigentümer der Auslöser.

| Klasse | Auslöser (abschließend) | Mindestprüfung |
|---|---|---|
| **R0** | reine Testinfrastruktur ohne Verhaltensänderung (**ein neuer Test ist das NICHT**); Doku-Korrektur ohne ausgelieferten Inhalt; Typisierung ohne Verhaltensänderung | lokale Gates |
| *R1* | **keine frei vergebbare Klasse** — benannte Verkürzung innerhalb von R2 für genau einen Fall: Nacharbeit mit ausschließlich mechanischen Auflagen | blinde Erststimme allein; Begründung unter den ausgelassenen Stimmen |
| **R2** | alles ohne R0-, R3- oder R4-Auslöser (der Normalfall) | blinde Erststimme + unabhängige Zweitstimme |
| **R3** | **Datenmigration — der VORGANG zählt, nicht das Werkzeug** (v1.12.0, framework-frei): bestehende Daten werden unumkehrbar umgewandelt — auch eine Light-Migration, die Werte aufteilt/umschreibt, auch eine selbstheilende Wanderung beim Start. Eine rein ADDITIVE Spalte ohne Datenumwandlung ist KEINE Datenmigration (→ R2); Berechtigungs-/Datenschutzlogik (Auth, Secrets); Geld/Werte (Preise, Bewertung); Außenwirkung über eine Schnittstelle; **Fremdcode** — Produktionscode, den ein FREMDES System beigesteuert hat (Patch eines Anbietermodells, zugelieferter Zweig, übernommener Schnipsel). **NICHT gemeint: der eigene Bau-Subagent** — sonst wäre der Auslöser hier immer erfüllt und R2 leer | volles Panel + risikospezifische Probe durch die echte Tür |
| **R4** | irreversible Daten-/Prod-Wirkung; fachlich nicht rückholbare Entscheidung | R3 + ausdrückliche Owner-Freigabe. **Ein projekteigenes Release-Gate mit breiteren Auslösern bleibt davon unberührt** — diese Spalte sagt, ab wann die Vorlage eine Freigabe verlangt, nicht, ab wann das Projekt sie verlangen darf (v1.12.1) |

„Klein" und „gut rückrollbar" sind **Urteile, keine Auslöser** — und Urteile
sind der Punkt, an dem sich der Ausführende unter Druck freispricht.
**Prüftiefe ≠ Release-Gate (v1.12.1):** Die Tabelle besitzt die Prüftiefe;
das Release-Gate ist projekteigen und darf breiter sein — wer ein breiteres
Gate zugunsten der R4-Zeile aufgibt, tut das als ausdrückliche, veto-fähige
Owner-Entscheidung, nie als Nebenwirkung der Übernahme. **Hier geschehen und
gültig:** verengt im v1.11.3-Abgleich (#78) und bei der v1.12.0-Schärfung
(#81), beide Male veto-fähig vorgelegt, kein Veto.

## Review-Panel

Das Verfahren je Klasse: `docs/agents/panel.md`. Die **Form des Ergebnisses**:
`docs/agents/panel-kommentar.md` — feste Überschriften je Stimme, **auch bei
„keine Funde"**. Ein Slice ohne vollständiges oder vermerkt-verkürztes Panel
gilt als **nicht geprüft**.

1. **Subagenten sind für dieses Projekt freigegeben** (Owner, 15.08.2026).
   Reviewer-Subagenten **immer** — ohne sie gibt es keine blinde Erststimme.
   Bau-Subagenten nach Ermessen des Hauptagenten; **baut der Hauptagent selbst,
   ist die blinde Erststimme zwingend ein frischer Subagent**, der weder
   Bau-Brief noch den Bericht des Bauers sieht.
2. **Tiering:** Read-only-Scans/Mechanik → `haiku`, Bau-Slices → `sonnet`,
   Review/Verifikation → `opus`; bei Unsicherheit erben lassen.
3. **Drittstimme bei R3: zweite blinde Claude-Repo-Stimme, adversarial**
   (Regelfassung v1.12.0 — vier R3-Runden Messbasis, in jeder exklusive
   Blocker-Funde). DeepSeek ist **keine Panel-Stimme mehr** (diff-only
   konvergierte nur); das Werkzeug bleibt als Ad-hoc-Zweitmeinung, Budget bis
   2 $/Monat ohne Rückfrage (Owner, 15.08.2026). Besetzung nach Diff-Typ und
   Ausfallregeln: `panel.md`.

   Im Zweifel Panel. Ablauf, Prüfaufträge und Begründungen: `panel.md`.
5. **Bau-Briefe** nach `docs/agents/bau-brief.md`, Pflicht-Gerüst aus acht
   Blöcken. Vor dem Absenden: `sh scripts/bau-brief-pruefen.sh <brief.md>`.
   Ein Brief ohne Block 3 (Konsumenten) ist die teuerste Auslassung.

## Agent skills

### Issue tracker

Issues leben in GitHub Issues (Repo Trust1509/pokecollect, `gh`-CLI); externe
PRs sind keine Triage-Oberfläche. See `docs/agents/issue-tracker.md`.

### Triage labels

Kanonisches Vokabular ohne Overrides: `needs-triage` / `needs-info` /
`ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` am Repo-Root + `docs/adr/`. See `docs/agents/domain.md`.
