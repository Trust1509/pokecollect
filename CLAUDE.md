# CLAUDE.md — PokéCollect

Self-hosted Pokémon-TCG-Sammlungs-App. FastAPI (Python 3.12) + PostgreSQL 16 +
Next.js 14 (einzige Client-Plattform, mobile-first/PWA — ADR-0002). ~1.025
Karten, Scan per Handy-Browser (Gemini-Ecken + manueller CornerEditor),
Preise via TCGdex/Cardmarket.

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
  main: Backend-pytest + Frontend tsc/build. Actions sind SHA-gepinnt, jeder
  Workflow hat einen `permissions:`-Block (Least Privilege), Dependabot
  (`.github/dependabot.yml`) ist die einzige tolerierte Bot-PR-Quelle (Merge nur
  nach grünen Gates; npm nur monatlich+gruppiert wegen des Lock-Rituals).
- **Wöchentlicher Security-Scan** (`.github/workflows/security-scan.yml`, Montag +
  `workflow_dispatch`, **kein** Push-Gate): `pip-audit` + `npm audit` +
  **Schemathesis**-API-Fuzzing (nur 5xx zählen, Check `not_a_server_error` in
  Schemathesis 4.x; ausgehende Netz-Endpunkte ausgeschlossen). Bewusst
  nicht-blockierend: ein fremdes Upstream-CVE oder eine Fuzz-Welle darf den
  Trunk nicht blocken → Funde triagieren wie Panel-Funde.
- **Kein Alembic → kein `alembic heads`-Gate / Migrations-Roundtrip** (das
  Wagner-Muster): Schema-Änderungen sind additive Light-Migrations (Fallstrick 5),
  der Rückweg ist Backup + altes Image, Alt-Downgrades sind nie begangener Pfad.
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
   Owner-OK). **Expand-Contract ist Pflicht für Schema-Semantik-Änderungen**
   (Welle-2-Abgleich 2026-08): erst erweitern (neue Spalte/neuer Wertebereich,
   beide Formen lesbar, Alt-Zeilen bekommen einen Default — vgl. `region`
   DEFAULT 'west'), Konsumenten umstellen, erst in einem SPÄTEREN Release
   verengen/entfernen — nie Expand und Contract im selben Release. Bei
   Semantik-/Typwechsel eines bestehenden Feldes alle Konsumenten auf Alt-Werte
   absichern, sonst Prod-Crash beim ersten unpassenden Bestandswert.
6. **SECURITY (seit Issue #1, ADR-0003):** Alle Fach-Router erzwingen ein
   JWT (`require_auth` via `include_router`-dependencies); auth-frei sind nur
   `/auth/login`, `/health` und der `/images`-Mount. `GET /settings` liefert
   Secrets nur maskiert (`*_set`/`*_masked`). Ohne `APP_PASSWORD_HASH`
   startet die App nicht (kein Default-Passwort mehr). Neue Router IMMER
   unter den Auth-Zwang in `api/v1/__init__.py` hängen; Secrets nie im
   Klartext ausgeben.

## Multi-LLM-Arbeitsmodus (Review-Panel)

Werkzeuge + Fallstricke: `C:\Users\manue\.claude\Immich\model-panel\README.md`.
Zweck ist **Diversität im Urteil**, nicht Token-Ersparnis.

1. **Subagenten-Tiering:** Read-only-Scans/Mechanik → `model: haiku`, Bau-Slices →
   `sonnet`, Review/Verifikation → `opus`; bei Unsicherheit erben lassen.
2. **Review-Panel nach jedem nicht-trivialen Slice — DREI Stimmen:**
   1. **Claude-Reviewer (opus, empirisch — darf Sonden/Tests ausführen).**
      **Seit 2026-08-06 als BLINDE Erststimme** (Welle-2-Abgleich A5,
      Studienbefund Kontext-Bias): ein FRISCHER Reviewer-Subagent, der nur
      Diff + Repo bekommt — NICHT den Bau-Brief/Bauer-Bericht. Der Hauptagent,
      der den Bau orchestriert hat, läse sonst die Absicht statt des Codes und
      übersähe Silent Bugs. Der Hauptagent arbitriert DANACH mit vollem Kontext.
   2. **GPT über Codex-CLI** (`model-panel/codex.sh exec --sandbox read-only -c
      'model_reasoning_effort="high"' "…"`; Login im Volume `codex-home`;
      Strenge-Bias — findet Echtes, braucht Arbitrierung). Der GitHub-Connector
      liest aus dem privaten Repo — Quellcode ist ok (PokéCollect ist
      Single-User ohne Kunden-PII; anders als bei Wagner keine PII-Sperre nötig).
   3. **DeepSeek V4 Pro als günstige Drittstimme** (Diff per stdin an
      `python model-panel/ask-api.py --model deepseek/deepseek-v4-pro
      --max-tokens 32768 --stdin-anhang "<Prüfauftrag>"`; irrt nur
      Richtung zu-streng). Braucht OpenRouter-Guthaben (`model-panel/.env`);
      bei 402/leer Panel auf zwei Stimmen und den Owner informieren.
   **Arbitrierung (die wichtigste Regel):** Der Hauptagent REPRODUZIERT jeden
   Blocker am Code / an der laufenden App, bevor er ihn übernimmt oder verwirft —
   Prüfer-Konvergenz ersetzt keine Reproduktion, Mehrheit entscheidet nie allein.
   Sonden-Falle: Erwartungswerte VOR der Sonde fixieren (eine Sonde kann ihre
   eigenen Befunde erzeugen).
   **Bauauftrags-Checkliste:** In jeden Bau-Prompt gehört „Wer ruft den geänderten
   Code auf?" — Konsumenten der berührten Stellen (Frontend-Bodies,
   Service-Aufrufer) ins Material.
3. **Trivial-Slices** (reine Test-Infra, Doku, Typisierung ohne
   Verhaltensänderung) nur Arbiter-Review, kein volles Panel.
4. **Kein PreToolUse-Guardrail-Hook nötig** (anders als Wagners
   `wagner_prod_readonly.py`): PokéCollect hat keinen eigenen MCP-Server und
   keine schreibenden Prod-Tools, die ein Agent erreichen könnte — Deploy läuft
   owner-seitig, SSH zum Server ist für Agenten geblockt.

## Agent skills

### Issue tracker

Issues leben in GitHub Issues (Repo Trust1509/pokecollect, `gh`-CLI); externe
PRs sind keine Triage-Oberfläche. See `docs/agents/issue-tracker.md`.

### Triage labels

Kanonisches Vokabular ohne Overrides: `needs-triage` / `needs-info` /
`ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` am Repo-Root + `docs/adr/`. See `docs/agents/domain.md`.
