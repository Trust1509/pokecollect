# CLAUDE.md — PokéCollect

**Prozess-Stand: v1.9.1** — Stand der Vorlage `Trust1509/agent-projekt-template`,
gegen die dieses Projekt zuletzt abgeglichen wurde (Abgleich-Issue im Repo,
Titel `Abgleich v1.9.1`). Bei einer neueren Vorlagen-Version nach
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
4. **Riskant-Gate:** Datenverlust-/Migrations-/Security-/Auth-Änderungen →
   bauen + grüner Report + **Owner-OK vor Release**. Gefahrloses + alle Gates
   grün + real im Teststand verifiziert → Release autonom.
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
  `scripts/gates.sh` (tsc + next build + pytest). package-locks nur im
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
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) läuft bei jedem Push auf
  main: Backend-pytest + Frontend tsc/build. Actions sind SHA-gepinnt, jeder
  Workflow hat einen `permissions:`-Block (Least Privilege). **Kein
  `pull_request`-Trigger** (Minuten-Notbremse 14.08.2026) — es gibt keine
  menschlichen PRs. Dependabot (`.github/dependabot.yml`) ist bis zum 01.09.
  stillgelegt; Rücksetz-Anweisung steht in der Datei.
- **Ein Push kostet Minuten.** Reine Doku-/Konfigurations-Commits, die keine
  Prüfung beweisen können, mit `[skip ci]` pushen; Verifikation einmal per
  `workflow_dispatch`, nicht durch wiederholtes Pushen.
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

## Review-Panel — verbindlich nach jedem nicht-trivialen Slice

Ablauf, Prüfaufträge und die abschließende Trivial-Liste: `docs/agents/panel.md`.
Die **Form des Ergebnisses**: `docs/agents/panel-kommentar.md` — drei feste
Überschriften, eine je Stimme, **auch bei „keine Funde"**. Ein Slice ohne
vollständiges oder vermerkt-verkürztes Panel gilt als **nicht geprüft**.

1. **Subagenten sind für dieses Projekt freigegeben** (Owner, 15.08.2026).
   Reviewer-Subagenten **immer** — ohne sie gibt es keine blinde Erststimme.
   Bau-Subagenten nach Ermessen des Hauptagenten; **baut der Hauptagent selbst,
   ist die blinde Erststimme zwingend ein frischer Subagent**, der weder
   Bau-Brief noch den Bericht des Bauers sieht.
2. **Tiering:** Read-only-Scans/Mechanik → `haiku`, Bau-Slices → `sonnet`,
   Review/Verifikation → `opus`; bei Unsicherheit erben lassen.
3. **Drittstimme (DeepSeek) bis 2 $/Monat ohne Rückfrage** (Owner, 15.08.2026),
   darüber melden. Bei `402` zweistimmig weiterarbeiten, im Panel-Kommentar
   vermerken **und** den Owner informieren.
4. **Wann ein Panel Pflicht ist — abschließend, hier und nicht nebenan**
   (v1.8.2: Verfahren verweisen, Schwellen stehen dort, wo entschieden wird):

   **Ohne Panel nur:** reine Testinfrastruktur *ohne* Verhaltensänderung
   (Läufer, Konfiguration, Hilfsmittel), Doku, Typisierung ohne
   Verhaltensänderung. **Ein neuer Test gehört NICHT dazu** — er behauptet
   etwas über das Verhalten und kann falsch behaupten.

   **Immer volles Panel** bei: Migrationen, Auth/Berechtigungen, allem was
   Werte berechnet, allem was nach außen geht — **und allem, was Herkunft
   hat** (Code, den niemand aus diesem Projekt gebaut hat).

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
