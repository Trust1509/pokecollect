# CLAUDE.md — PokéCollect

Self-hosted Pokémon-TCG-Sammlungs-App. FastAPI (Python 3.12) + PostgreSQL 16 +
Next.js 14 + Kotlin/Compose-Android-App (`android/`). ~1.025 Karten, Scan per
Handy (Gemini-Ecken + manueller CornerEditor), Preise via TCGdex/Cardmarket.

Lies vor Architektur-/Feature-Arbeit `CONTEXT.md` (Grundsätze + Glossar) und
passende ADRs unter `docs/adr/`.

## Arbeitsregeln

1. **Nichts aus dem Gedächtnis:** jede Behauptung am echten Code verifizieren,
   bevor du sie triffst oder darauf baust.
2. **Direkt-Push auf `main` ist autorisiert** (Trunk-Workflow, Pipeline ersetzt
   PRs). Releases nur per Tag, Tags erst nach Owner-Test-OK.
3. **Je Issue ein Commit; Gates je Commit:** Tests + Typecheck + Build lokal
   grün (`scripts/gates.sh`), CI auf main grün. Bei Datei-Überlappung mehrerer
   Arbeitspakete sequenziell statt parallel arbeiten (Git-Race).
4. **Riskant-Gate:** Datenverlust-/Migrations-/Security-/Auth-Änderungen →
   bauen + grüner Report + **Owner-OK vor Release**. Gefahrloses + alle Gates
   grün + real im Teststand verifiziert → Release autonom.
5. **Verifikation real, nicht nur Tests:** Änderungen in der laufenden App
   prüfen (lokaler Teststand, siehe unten), bevor „fertig" gemeldet wird.
6. **Grilling vor großen/riskanten Designs;** Lock-Spec als Issue-Kommentar.
7. **Echte Umlaute** (ä/ö/ü/ß) in allen deutschen Texten; interne ASCII-Werte
   nie roh ins UI (Label-Maps). UI ist zweisprachig DE/EN (`web/src/lib/i18n.tsx`)
   — neue UI-Texte immer in beiden Sprachen pflegen.
8. **Lehren verankern:** Erkenntnisse in CONTEXT.md/ADRs/CLAUDE.md festhalten.
9. **Versionierung:** eine Projektversion je Dev-Stand, an ZWEI Stellen bumpen:
   `web/src/lib/version.ts` (`APP_VERSION`) + `backend/app/config.py`
   (`app_version`). Sichtbare Auslieferungen bekommen einen CHANGELOG-Eintrag.

## Build, Gates, Teststand

- **Kein Node/npm lokal auf diesem PC.** Frontend-Gates laufen im Docker-Container:
  `scripts/gates.sh` (tsc + next build + pytest). package-locks nur im
  Node-Container erzeugen — der lokale npm-Wrapper („allow-scripts") schreibt
  inkompatible Locks.
- **Backend-Tests:** `pytest` unter `backend/tests/` (Container oder lokales
  Python; DB-lose Tests bevorzugt, sonst Teststand-Postgres).
- **Lokaler Teststand:** Compose-Projekt `pokecollect-test`
  (`docker-compose.test.yml`), Web http://localhost:3021, API http://localhost:3020.
  `scripts/teststand.sh up` — für Browser-Verifikation vor jedem Release.
- **CI:** GitHub Actions (`.github/workflows/ci.yml`) läuft bei jedem Push auf
  main: Backend-pytest + Frontend tsc/build.
- **Android-Build:** `cd android` und
  `JAVA_HOME="C:\Program Files\Android\Android Studio\jbr" ./gradlew.bat assembleDebug`.
  gradlew nie durch `tail`/Pipe schicken — verschluckt den Exit-Code.

## Deploy (macht immer der Owner)

- TrueNAS `<server-ip>` — **GETEILTER Server, nie `docker system prune -a`**.
  Repo dort: `/mnt/HDDs/Applications/pokecollect/app`, `deploy.sh` = git pull +
  Build beider Images. Ports API 3010 / Web 3011, UID:GID 3010:3010.
- SSH zum Server ist für Agenten geblockt; API/Web sind per HTTP testbar:
  `curl <server-ip>:3010/health`.
- Du lieferst getestete, getaggte Stände + klare Deploy-Anweisung; der Owner
  deployt selbst.

## Fallstricke (teuer gelernt)

1. **Deutsche Typo-Quotes in JS-Strings:** ein `„` in einem `"…"`-String,
   geschlossen mit ASCII-`"` → „Unterminated string constant". Nie mischen;
   innere Quotes weglassen oder Backtick-Template.
2. **Next-Hooks nullable:** `useSearchParams()`/`useParams()` brauchen
   Optional-Chaining; `useSearchParams()` braucht `<Suspense>`.
3. **Keine echten IPs committen** — die LAN-IP wurde per filter-branch aus der
   History gescrubbt. Platzhalter `<server-ip>` verwenden.
4. **Vergleichs-Repo Git-Romer/pokecollector ist AGPL** — niemals Code
   übernehmen, nur Ideen (PokéCollect ist MIT).
5. **DB-Migrationen: KEIN Alembic.** `create_all` legt nur neue Tabellen an;
   Spaltenänderungen als idempotente Light-Migrations in
   `backend/app/main.py::_run_light_migrations`
   (`ALTER TABLE … ADD COLUMN IF NOT EXISTS`, additiv, nie destruktiv ohne
   Owner-OK).
6. **⚠️ SECURITY (offen, ROADMAP v1.0):** Die API erzwingt keine Auth —
   `require_auth` (backend/app/api/deps.py) ist unverdrahtet, `GET /settings`
   liefert API-Keys im Klartext ins LAN. Extern schützt Authelia. Bei jeder
   Arbeit an Settings/Auth mitdenken; Fix ist als P0 vorgesehen.

## Agent skills

### Issue tracker

Issues leben in GitHub Issues (Repo Trust1509/pokecollect, `gh`-CLI); externe
PRs sind keine Triage-Oberfläche. See `docs/agents/issue-tracker.md`.

### Triage labels

Kanonisches Vokabular ohne Overrides: `needs-triage` / `needs-info` /
`ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` am Repo-Root + `docs/adr/`. See `docs/agents/domain.md`.
