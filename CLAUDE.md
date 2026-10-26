# CLAUDE.md — PokéCollect

**Prozess-Stand: v1.18.13** — Stand der Vorlage `Trust1509/agent-projekt-template`,
gegen die dieses Projekt zuletzt abgeglichen wurde (Abgleich-Issue im Repo,
Titel `Abgleich v1.18.13`). Bei einer neueren Vorlagen-Version nach
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
Next.js 15 (einzige Client-Plattform, mobile-first/PWA — ADR-0002). ~1.025
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
   er einen eigenen `git worktree` mit eigenem Branch (wie der Fremdprüfer;
   Blind- und Gegenprüfer bekommen einen `git archive`-Auszug — der
   Gegenprüfer seit Vorlage v1.15.0, der Blindprüfer seit v1.18.0) — dann
   kann kein fremder Push ihn mitnehmen, und der Hauptbaum bleibt frei.
3. **In einer Commit-Nachricht steht der Überspring-Marker NUR als Marker.**
   Nie erklärt, zitiert oder verneint — die Plattform liest die ganze
   Nachricht, nicht nur die Betreffzeile, und ein Satz ÜBER den Marker
   enthält ihn. Der Commit löst dann null Läufe aus: keinen roten, keinen
   abgebrochenen, gar keinen. Wer im Rumpf darüber schreiben muss,
   umschreibt ihn („der Überspring-Marker“). In Dateien und Issue-Texten
   ist die wörtliche Nennung unbedenklich. Mechanisch erzwungen durch
   `.githooks/commit-msg` — **einmalig je Arbeitskopie aktivieren:**
   `git config core.hooksPath .githooks`. Hintergrund und Vorfall:
   `docs/agents/lehren.md` §19.
4. **Je Issue ein Commit; Gates je CODE-Commit:** Tests + Typecheck + Build
   lokal grün (`scripts/gates.sh`), CI auf main grün. Reine Doku-Commits
   brauchen die Code-Gates nicht — **wohl aber Gate P, sobald sie `CLAUDE.md`
   oder `docs/agents/` berühren**: Der Verweis-Wächter prüft genau diese
   Dateien, und ein Doku-Commit kann ihn brechen (`sh scripts/gates.sh
   prozess`, ~35 s (gemessen 24.10.2026), unter der Rechner-Sperre; Gegenprüfer, Abgleich v1.17.2).
   Gate P fährt dabei auch die Brief-Selbstprobe, die ein Doku-Commit an den
   Prüffragen, den „Randbedingungen, die immer mitmüssen" oder den „Typischen
   Fallen" in `bau-brief.md` bricht (Vorlage v1.18.1). Die CI fährt Gate P nicht
   — was es rot macht, ohne dass jemand daran denkt, ist bisher nichts
   (erste Wächterfrage, `docs/agents/lehren.md` §10; offen in #106). Die Prüfungen
   laufen **einmal auf dem finalen Baumzustand**, egal von wem: dieselbe Suite
   von Bauer, Arbiter und CI dreimal zu fahren ist Leerlauf. Bei Datei-
   Überlappung mehrerer Arbeitspakete sequenziell statt parallel (Git-Race).
   Jeder Bau-Commit trägt den Modell-Stempel, mehrteilig, wenn mehrere Modelle
   beteiligt waren: `Built-With: bau=<m>; nacharbeit=<m>; arbitriert=<m>
   (<datum>)`. Ohne ihn ist nach vier Wochen nicht feststellbar, wer was gebaut
   hat — und jede Aussage über Modellverhalten bleibt Anekdote.
   **Den Stempel setzt der HAUPTAGENT, nie der Bauer** (v1.14.0): Ein Bauer
   kennt seine eigene Modell-Kennung nicht; im Vorlagen-Benchmark trugen vier
   von vier Erstbauten einen erfundenen Stempel, auch nach ausdrücklicher
   Auflage. Bau-Briefe geben `bau=<vom Orchestrator gesetzt>` vor.
5. **Die Tabelle besitzt die PRÜFTIEFE** (wer prüft, wie tief) — sie ist der
   einzige Eigentümer der Auslöser. **Das RELEASE-GATE (wer vor Release
   freigibt) ist eine eigene Größe:** Seine Untergrenze hat der Owner für alle
   Projekte gesetzt, darüber darf das Projekt weitere Auslöser haben (Vorlage
   v1.18.2). Unsere Entscheidung dazu hat zwei Stufen: Im
   v1.11.3-Abgleich wurde das frühere breitere Gate („jede Migration →
   Owner-OK") **bewusst und Owner-gebilligt** auf die R4-Auslöser verengt
   (#78, veto-fähig vorgelegt, kein Veto); die **Owner-Dauerregel vom
   02.09.2026** (für alle Repos) hat es wieder erweitert, Punkt
   „Release-Stau“: „wo das projekteigene Release-Gate ein Owner-Gate verlangt (Migrationen, Geld-Slices auf jeden Fall), VORHER fragen“.
   **Der gültige Wert steht nur im Schwellen-Inventar** (Zeile
   „Release-Gate"); alle anderen Stellen zeigen darauf. Wo das Gate keine
   Freigabe verlangt, gilt: Gates grün + Teststand verifiziert → Release
   autonom.
6. **Verifikation real, nicht nur Tests:** Änderungen in der laufenden App
   prüfen (lokaler Teststand, siehe unten), bevor „fertig" gemeldet wird.
7. **Grilling vor großen/riskanten Designs;** Lock-Spec als Issue-Kommentar.
8. **Echte Umlaute** (ä/ö/ü/ß) in allen deutschen Texten; interne ASCII-Werte
   nie roh ins UI (Label-Maps). UI ist zweisprachig DE/EN (`web/src/lib/i18n.tsx`)
   — neue UI-Texte immer in beiden Sprachen pflegen.
9. **Lehren verankern:** Fehlerklassen nach `docs/agents/lehren.md`, Fachliches
   nach `CONTEXT.md`/ADRs. Ist die Lehre **übertragbar** (klebt nicht am Stack),
   zusätzlich als Issue in die Vorlage.
10. **Versionierung und Auslieferung:** `docs/agents/release-ritual.md` — dort
   stehen die zwei Versionsstellen, die Risiko-Stufen und der Ablauf. Hier
   bewusst kein Auszug: Die Doppelpflege Kurzfassung/Langfassung war in zwei
   Projekten die Ursache, dass eine Pflichtregel unwirksam blieb (v1.8.0).
11. **Auch der Orchestrator führt Buch über seine Läufe** (Vorlage v1.15.3).
   Der Bauer bekommt „Vordergrund, keine Hintergrundprozesse" als Auflage;
   wer den Brief schreibt, startet dagegen bewusst welche — Panel-Stimmen
   laufen parallel im Hintergrund. Verboten ist nicht der Hintergrundlauf,
   sondern der **unbemerkte**: Ein Lauf, den ein Zeitlimit oder ein Abbruch
   ins Hintergrundfach verschoben hat, wird **gestoppt und im Ergebnis
   genannt**, bevor die nächste Messung startet — samt seinen Kindprozessen,
   über seine Prozessnummer mit `sh docs/vorlagen/baum-stoppen.sh <pid>` (die
   Prozessnummer allein trifft unter Git Bash die Kinder nicht; Vorlage
   v1.18.12), nie über den Programmnamen (auf diesem Rechner laufen parallele
   Sitzungen anderer Projekte). Hält der Lauf die Rechner-Sperre, wird sie erst
   nach dem Exit 0 des Werkzeugs und dem Blick auf `docker ps` und `ps -W`
   freigegeben (`docs/agents/bau-brief.md`, Randbedingung „Parallelität").
   Jeder Bau- und Panel-Bericht endet
   mit der Zeile **„Eigene Läufe am Ende: …"** (`docs/agents/lehren.md` §22,
   Form in `docs/agents/panel-kommentar.md`).

## Wie eine Regel wirksam wird

**Regeln in diesem Repo erreichen keinen Bau-Subagenten** — er arbeitet den
Bau-Brief ab, nicht `docs/agents/` (aus der Vorlage, Abgleich v1.17.2):

    Regel  →  Bau-Brief (Pflicht-Gerüst)  →  Bauer
    Regel  →  Gate / Hook / Skript        →  erzwungen
    Regel  →  Panel-Form                  →  im Ergebnis sichtbar

Was in keiner dieser drei Ketten steht, ist eine Absichtserklärung. Und auch
innerhalb der Ketten gibt es Stufen — **wie stark eine Regel wirkt, sagt die
Stufe, nicht die Formulierung**:

| Stufe | Beispiel | Hält, wenn niemand daran denkt? |
|---|---|---|
| Disziplin | Satz in einem Dokument; ein Ritualschritt ohne Skript | nein |
| advisory | Hinweis eines Skripts, Warnung eines Hooks | nur, wenn jemand liest |
| Gate | Prüfung, die rot macht und das Landen blockiert | ja, solange sie läuft |
| strukturelle Sperre | Recht fehlt, Verzeichnis nicht eingehängt, Aufruf unmöglich | ja |

Doku oder Konfiguration begründen keine höhere Stufe. Und eine Option, die
„nie falsch" ist, wird unter Druck selten gewählt — was unter Druck gelten
muss, ist deshalb Standard, nicht Option. Konkret:

- **Für den Bauer verbindlich** ist nur, was im Brief steht.
  `sh scripts/bau-brief-pruefen.sh <brief>` zeigt, wo die zehn Pflicht-Themen
  stehen könnten — ein fehlendes Thema ist ein starkes Signal, kein Beweis
  (fester Wortschatz), ein Treffer nur ein Kandidat (Grenzen im Skriptkopf).
- **Verfahren verweisen, SCHWELLEN hier** — und jede Schwelle hat genau einen
  Eigentümer (Schwellen-Inventar unten). Ansonsten dupliziert diese Datei
  keine Regeln, sie verweist (Arbeitsregel 10).
- **Vor jedem Slice** die fünf Fragen aus `docs/agents/lehren.md` — nicht alle
  Abschnitte. Ein Dokument zu haben ist nicht, es gelesen zu haben.

## Build, Gates, Teststand

- **Frontend-Gates und Sperrdateien laufen im Container, nicht auf dem Host.**
  Node und npm SIND lokal installiert — die frühere Aussage „kein Node/npm
  lokal" war falsch (gemessen 28.09.2026, wiederholt 19.10.2026:
  `node --version` Exit 0, v24.18.0; `npm --version` Exit 0, 11.16.0). Der
  Grund für die Regel ist ein anderer: Container und CI laufen auf npm
  **10** (seit #117 `node:22-alpine`, im Abbild gemessen 26.10.2026: node
  v22.23.4, npm 10.9.9; die CI setzt `node-version: 22`; vorher Node 20, das
  keine Unterstützung mehr hat), und ein Lock aus npm 11 kann in der CI
  scheitern.
  `scripts/gates.sh` fährt pytest, tsc, lint und next build in Docker;
  `package-lock.json` nur im Node-Container erzeugen (Kommando in
  `docs/agents/bau-brief.md`, Projektabschnitt).
- **Python im Gate ist ein absoluter Interpreter im Container**, nie ein Alias:
  `/usr/local/bin/python3.12` in `python:3.12-slim`. Nacktes `python` hing auf
  diesem Rechner bis Oktober 2026 für immer (Windows-Store-Stub); seit der
  Alias auf den Python Install Manager zeigt (Alias vom 10.10.2026), läuft es
  (gemessen 19.10.2026: `python -c`, `python <skript>` und `python --version`
  je Exit 0 unter 20 s, Python 3.14.5). Ein Alias, der still wechseln kann,
  bleibt trotzdem keine Gate-Umgebung (`docs/agents/lehren.md` §5). Über den
  Symlink `python3` ist die Wächter-Selbstprobe seit Vorlage v1.18.10 ebenfalls
  grün (bis dahin rot, Fall „Hardlink des Interpreters"; beides gemessen,
  28.09. und 19.10.2026).
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
  Workflow hat einen `permissions:`-Block (Least Privilege). **Nur lokal**
  laufen drei Teile von `gates.sh`: die Was-ist-neu-Parität (Gate 0), die
  Paritäts-Prüfungen Gate ↔ CI im Web-Gate (`grep` auf `ci.yml`) und die
  Prozess-Werkzeuge (Gate P: Selbstprobe des commit-msg-Hooks, Brief-Selbstprobe,
  Wächter-Selbstprobe, Selbstprobe von `ast-gleich.py`, Lehren-Verweise) — die
  CI ruft `gates.sh` nicht auf. Wer sie auslässt, macht nichts rot
  (`docs/agents/lehren.md` §10).
- **Rechner-Sperre für jeden schweren Lauf** — was als schwer gilt (auch
  `gates.sh prozess`: es startet einen Container) und der Wert: Schwellen-Inventar
  unten, Zeile „Schwere Läufe auf dem Rechner". Die zwei Blöcke zum Nehmen und
  Freigeben und der Abbruch über `docs/vorlagen/baum-stoppen.sh` stehen in
  `docs/agents/bau-brief.md`, Randbedingung „Parallelität". Die Skripte nehmen
  die Sperre NICHT selbst — wer sie startet, nimmt sie im selben Aufruf.
- **CI-DAUERREGEL: EIN Lauf je Slice, nicht je Push (Owner, 02.09.2026 — ersetzt
  die Quota-Notbremse vom 14./20.08.).** Das Actions-Kontingent (3000 Min/Monat)
  teilen sich alle Repos; Tagesbudget und übliche Laufdauer stehen im
  Schwellen-Inventar unten. Deshalb:
  - **Alle Commits tragen `[skip ci]`** — Bau, Panel, Nacharbeit, Doku. Die
    **lokalen Gates auf dem finalen Baum sind die Verifikation** (Pflicht,
    Arbeitsregel 4); im Issue steht `Gates lokal grün auf <SHA>`.
  - **Nach der Landung eines Slices genau EIN `workflow_dispatch` auf dem HEAD**
    (`gh workflow run ci.yml`, dann die Lauf-ID zum gelandeten Commit holen und
    das Ergebnis mit `gh run view <id> --json status,conclusion` LESEN — nicht den
    Exit von `gh run watch` auswerten, und nie `gh run list --limit 1` direkt nach
    einem Push: Der eigene Lauf existiert dann oft noch nicht, und man erwischt
    den des Vorgänger-Commits; Vorlage §6) — die CI ist die **Gegenprobe**, nicht die Prüfung. Wird sie
    rot: normaler Fix-Slice, kein Drama; ein Unterschied zwischen lokalen Gates
    und CI ist selbst ein Befund und gehört ins Rückmeldungs-Issue der Vorlage.
    Nie zum Prüfen pushen.
  - **Dauerhaft, weil sie keine Qualität kosten:** ein pytest-Job, **kein
    `pull_request`-Trigger** (es gibt keine menschlichen PRs), `concurrency` mit
    `cancel-in-progress` (in `ci.yml` Tag-Refs ausgenommen), `paths-ignore`
    für reine Doku.
  - **Dependabot** (`.github/dependabot.yml`): `interval` bleibt `monthly`,
    `open-pull-requests-limit: 1` — Sicherheits-Updates unberührt. Kein
    „weekly/limit 5" mehr; die frühere Rücksetz-Notiz war falsch.
  - **Releases:** nach grüner CI-Gegenprobe erlaubt; verlangt das Release-Gate
    eine Owner-Freigabe, **vorher fragen** — diese Dauerregel nennt
    Migrationen und Geld-Slices „auf jeden Fall“; der Wert steht im
    Schwellen-Inventar unten.
    Zeitplan-Läufe (Security-Scan) laufen wieder normal.
  - Kostet ein Lauf deutlich mehr als die übliche Laufdauer
    (Schwellen-Inventar): im Rückmeldungs-Issue der
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
- **Der Agenten-Schlüssel gilt nicht für den Server** (Owner-Auskunft vom
  24.10.2026, nicht gemessen). Ein auf diesem Rechner angelegter
  Agenten-Schlüssel gilt für andere Systeme im Heimnetz. In den
  Agenten-Einstellungen steht keine SSH-Regel (gemessen 19.10.2026). Ein Verbindungsversuch zum Server gehört
  nicht zu den Aufgaben eines Agenten.
  API/Web sind per HTTP testbar: `curl <server-ip>:3010/health`.
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
     `secret_scanning_push_protection: enabled`, 0 offene Alerts). Nach der
     Probe der Vorlage erkennen sie nur die Formate der Partner-Anbieter;
     deshalb kommt ein eigener Scanner dazu (Punkt 1 der vier Regeln unten,
     Bau in #115). Push Protection
     blockiert einen erkannten Schlüssel schon beim Push; wird ein Push
     deshalb abgelehnt: **nicht umgehen**, sondern den Wert aus der Änderung
     nehmen und dem Owner melden.
  Historien-Prüfung 04.09.2026 über alle 233 Commits (API-Key-Muster, private
  Schlüssel, `192.168.*`/`10.*`, Passwort-Zuweisungen, `.env`-Dateien,
  E-Mail-Adressen): gemeldet **ohne Befund** — die einzigen Passwort-Treffer
  sind Wegwerf-Werte für Gate-Postgres und Teststand. **Berichtigt am
  19.10.2026:** Eine Zeile hat sie übersehen. `deploy/README.md` nannte seit dem
  04.06.2026 (`67175b4`) das Heimnetz als Adressbereich (gefunden 28.09.2026);
  die Zeile sagt jetzt „im Heimnetz". Private Adressen, die Historie bleibt
  stehen.

  **Nachgemessen am 19.10.2026** (Abgleich v1.18.13; zuvor 06.09.2026):
  `secret_scanning: enabled`, `secret_scanning_push_protection: enabled`,
  Sichtbarkeit `public`, **0 offene Alerts**. `secret_scanning_validity_checks`
  steht auf `disabled` — das ist eine Owner-Entscheidung, kein Mangel.

- **Vier Regeln liegen bei öffentlichen Repos anders** (Vorlage v1.14.0,
  Owner-Entscheid):
  1. **Geheimnis-Scan: Plattform UND eigener Scanner** (Owner, 24.10.2026;
     ersetzt den Entscheid „nur Plattform" vom 06.09.2026). Die gewählte
     Form steht in #115; bis der Scanner steht, gilt nur die Plattform. Hintergrund: Die Vorlage führt seit v1.15.0 „Plattform UND
     eigener Scanner" — der Plattform-Scan kennt nur die Muster seiner
     Partner-Anbieter (selbst vergebene Schlüssel fand in einer Probe mit
     sechs Fixtures nur ein eigener Scanner). Ihr zweiter Grund, öffentliche
     Repos verbrauchten keine abgerechneten Minuten, begründet sie mit
     `billable = 0` aus `actions/runs/<id>/timing`; dieselbe Schnittstelle meldet 0
     aber auch für private Repos (gemessen 28.09.2026 an zwei privaten Läufen
     desselben Kontos), als Kostenbeleg taugt sie also nicht.
  2. **Die PII-Grenze ist für Code gegenstandslos, für DATEN scharf.** Unser
     Code enthält keine Personendaten. Was zählt, sind Fixtures und
     Beispieldaten — **die Fixtures-Regel ist hier die eigentliche
     Schutzlinie, keine Hygiene**: Testdaten werden ERFUNDEN, nie aus dem
     echten Bestand übernommen. Ein Fixture aus der echten Sammlung ist in
     einem privaten Repo eine Unsauberkeit und hier eine Veröffentlichung.
  3. **Das Suchverbot für Panel-Stimmen ist Integritätsschutz, nicht
     Sparsamkeit.** In einem öffentlichen Repo kann eine Stimme den eigenen
     Code im Netz finden und ihre „unabhängige“ Prüfung daran ausrichten.
  4. **Test-Zugänge stehen nie im Repo.** Auch keine Wegwerf-Passwörter für
     den Teststand in Dateien, die jeder lesen kann — dazu #96.
  Bei einem Sichtbarkeitswechsel wird die Historie einmal vollständig
  geprüft (bei uns am 04.09. geschehen; die eine übersehene Zeile ist oben
  berichtigt).

- **Auth-Zwang (Issue #1, ADR-0003):** Alle Fach-Router erzwingen ein JWT
  (`require_auth` via `include_router`-dependencies); auth-frei sind nur
  `/auth/login`, `/health` und der `/images`-Mount. Neue Router IMMER unter den
  Auth-Zwang in `api/v1/__init__.py` hängen.
- **Secrets nie im Klartext ausgeben.** `GET /settings` liefert sie nur maskiert
  (`*_set` / `*_masked`). Ohne `APP_PASSWORD_HASH` startet die App nicht.
- **Der Agent trägt keine Schlüssel ein** — Details, Ablageorte und der
  Wiederruf-Weg in `docs/SECRETS.md`.
- **Kein Produktiv-Wächter nötig — solange die Bedingung hält.** Es gibt
  keinen MCP-Server für dieses Projekt und keine schreibenden
  Prod-Werkzeuge, und der Agenten-Schlüssel gilt nicht für den Server
  (Owner-Auskunft, „Deploy").
  **Grenze, bewusst akzeptiert (Owner, 24.10.2026):** Agenten laufen unter dem
  Windows-Benutzer des Owners; was dieser Benutzer gespeichert hat, ist für sie
  erreichbar. Alle Anwendungen laufen lokal und sind von außen nicht
  erreichbar. **Wird einem Agenten ein Prod-Token oder das Prod-Passwort
  übergeben (Konfiguration, Umgebungsvariable, Prüfauftrag), kommt ein
  MCP-Server mit schreibenden Werkzeugen oder ein SSH-Zugang zum Server für
  Agenten dazu, wird der Wächter sofort nötig**
  (Vorlage und Echtprobe: `docs/SECRETS.md`; der Wächter der Vorlage
  entscheidet nur über MCP-Werkzeuge, nicht über Shell-Aufrufe).

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
| *R1* | **keine frei vergebbare Klasse** — seit v1.15.0 in der Zeile „Nacharbeit“ aufgegangen, die für JEDE Nacharbeit gilt, nicht nur für mechanische Auflagen | siehe „Nacharbeit“ |
| **R2** | alles ohne R0-, R3- oder R4-Auslöser (der Normalfall) | Blindprüfer + Fremdprüfer |
| **R3** | **Datenmigration — der VORGANG zählt, nicht das Werkzeug** (v1.12.0, framework-frei): bestehende Daten werden unumkehrbar umgewandelt — auch eine Light-Migration, die Werte aufteilt/umschreibt, auch eine selbstheilende Wanderung beim Start (bei uns real: #103). Eine rein ADDITIVE Spalte ohne Datenumwandlung ist KEINE Datenmigration (→ R2); Berechtigungs-/Datenschutzlogik (Auth, Secrets); Geld/Werte (Preise, Bewertung); Außenwirkung über eine Schnittstelle; **Fremdcode** — Produktionscode, den ein FREMDES System beigesteuert hat (Patch eines Anbietermodells, zugelieferter Zweig, übernommener Schnipsel) — **und fremde Werkzeug-Mechanik, die in den eigenen Prozess übernommen wird** (Hooks, Agenten-Definitionen, Skills eines anderen Frameworks: je Zusicherung wie „nur lesend“ oder „schlägt geschlossen fehl“ eine negative Probe); **kritische Dateien** — Wächter, Gate-Probe, Selbstprobe, Hook-Einträge, Gate-, Release- und Prüfskripte (Liste in `docs/agents/panel.md`, „Kritische Dateien“), unabhängig von der Diffgröße — **zwei Ausnahmen, beide nur für das Panel, die Probe durch die echte Tür bleibt in beiden Fällen:** (a) byte-identische Übernahme aus der Vorlage beim Abgleich (`abgleich.md` der Vorlage, Absatz „Panel für den Abgleich-Commit“); (b) **reine Kopftext-Änderung** — nur Kommentare oder Docstrings, Syntaxbaum nachweislich gleich (`docs/vorlagen/ast-gleich.py`); dann R2. Bedingungen und Beleg: `docs/agents/panel.md`, „Kritische Dateien“. **NICHT gemeint: der eigene Bau-Subagent** — sonst wäre der Auslöser hier immer erfüllt und R2 leer | volles Panel mit Gegenprüfer + risikospezifische Probe durch die echte Tür |
| *Nacharbeit* | jede Nacharbeitsrunde nach einem Panel, gleich welcher Klasse; **höchstens zwei** (gezählt: Erstrunde, Nacharbeit 1, Nacharbeit 2; Owner 17.09.2026) | Blindprüfer; Gegenprüfer nur bei neuer Tür; bei R3 und R4 zusätzlich die risikospezifische Probe durch den Arbiter. **Nach Nacharbeit 2 wird nicht weiter gebaut:** offene oder neue BLOCKER → anhalten, Owner fragen; nur noch Nicht-Blocker → landen, die Funde werden ein eigenes Issue mit Beleg |
| **R4** | irreversible Daten-/Prod-Wirkung; fachlich nicht rückholbare Entscheidung | R3 + ausdrückliche Owner-Freigabe. **Das Release-Gate bleibt davon unberührt** — diese Spalte sagt, ab wann die PRÜFTIEFE eine Freigabe verlangt; das Release-Gate (Schwellen-Inventar) verlangt sie zusätzlich bei Auslösern unterhalb von R4 (Vorlage v1.18.2) |

„Klein" und „gut rückrollbar" sind **Urteile, keine Auslöser** — und Urteile
sind der Punkt, an dem sich der Ausführende unter Druck freispricht.
**Prüftiefe ≠ Release-Gate (v1.12.1, Fassung v1.18.2):** Die Tabelle besitzt
die Prüftiefe; das Release-Gate ist eine eigene Größe mit eigener Zeile im
Schwellen-Inventar. Seine **Untergrenze** hat der Owner für alle Projekte
gesetzt (Migrationen, Geld — beides R3-Auslöser, also unterhalb von R4), und
ein Projekt darf weitere Auslöser haben. Wer eigene Auslöser über der
Untergrenze aufgibt, tut das als ausdrückliche, veto-fähige
Owner-Entscheidung, nie als Nebenwirkung der Übernahme; **unter die
Untergrenze führt kein Entscheid auf Projektebene**. **Hier geschehen:**
verengt im v1.11.3-Abgleich (#78) und bei der v1.12.0-Schärfung (#81), beide
Male veto-fähig vorgelegt, kein Veto; von der Owner-Dauerregel vom
02.09.2026 für Migrationen und Geld wieder erweitert. Der gültige Wert steht
im Schwellen-Inventar, Zeile „Release-Gate".

## Schwellen-Inventar

**Jede Schwelle hat hier eine Zeile, und ihr WERT steht genau einmal:** in
dieser Tabelle oder bei dem Eigentümer, den die Zeile nennt (dann steht hier
der Zeiger, nicht die Zahl). **Portfolio** = vom Owner für alle Projekte
entschieden, hier übernommen; **Projekt** = hier gewählt;
**Portfolio-Untergrenze** = der Owner hat eine Mindestschwelle für alle
Projekte gesetzt, das Projekt darf strenger sein, nie lockerer (Vorlage
v1.18.2). Eine Schwelle, die hier fehlt, hat keinen Eigentümer — das ist ein
Fund (Vorlage v1.17.0).

| Schwelle | Wert | entschieden von |
|---|---|---|
| Nacharbeitsrunden nach einem Panel | Risiko-Tabelle oben, Zeile „Nacharbeit“ | **Portfolio** (2026-09-17) |
| CI-Läufe je Slice | **einer**, auf dem gelandeten Endstand — Verfahren im Block „CI-DAUERREGEL“ oben | **Portfolio** (2026-09-02) |
| Kostenschwelle je Panel-Lauf (Ersatzstimme) | **keine** — Kosten pauschal freigegeben (ersetzt die frühere Grenze „2 $/Monat“). Was bei Guthabenende geschieht, ist Verfahren: `docs/agents/panel.md`, Klumpenrisiko Punkt 4 | **Portfolio** (2026-09-19) |
| Panel-Untergrenze beim Verkürzen | Abschnitt „Review-Panel“ unten, Absatz „Verkürzen“ | **Portfolio** |
| Prüftiefe je Risikoklasse | Risiko-Tabelle oben, Auslöser abschließend | **Portfolio** |
| Release-Gate (ab wann eine Freigabe nötig ist) | **mindestens jedes Release mit Migration oder Geld-Logik** (Untergrenze, Owner-Dauerregel vom 02.09.2026: „wo das projekteigene Release-Gate ein Owner-Gate verlangt (Migrationen, Geld-Slices auf jeden Fall), VORHER fragen“); **dazu bei uns: R4-Auslöser** → vorher den Owner fragen. Geschichte: im v1.11.3-Abgleich auf R4 verengt (#78, veto-fähig vorgelegt, kein Veto), von der Dauerregel wieder erweitert | **Portfolio-Untergrenze** (2026-09-02), darüber **Projekt** |
| Zeitlimit einzelner Befehle im Prüfauftrag | **15 Minuten** — dieselbe Grenze wie `timeout-minutes` beider CI-Jobs (`.github/workflows/ci.yml`) | **Projekt** |
| CI-Nebenläufigkeit (`concurrency`, `cancel-in-progress`) | **an** — `group: ci-${{ github.ref }}`, `cancel-in-progress` für alles außer Tag-Refs (`ci.yml`). Ausgenommen sind nach der Vorlage auch Läufe, die ausliefern — solche gibt es bei uns nicht (Deploy macht der Owner). Alle drei Workflows tragen sie (`security-scan.yml` und `smoke.yml` seit Abgleich v1.18.13, Gruppe je Workflow und Ref; vorher nur `ci.yml`). Sie hält die Zahl der Läufe unten, **ohne** dass jemand die Regel „ein Lauf je Slice“ einhält — ein abgebrochener Lauf ist kein eingesparter | **Portfolio** (Owner-Dauerregel 2026-09-02: Notbremse-Maßnahmen bleiben dauerhaft) |
| CI-Tagesbudget über alle Repos | **100 Minuten** je Tag (Kontingent 3000 Min/Monat, geteilt) | **Portfolio** (2026-09-02) |
| Übliche Dauer eines CI-Laufs (Meldeschwelle) | **2–4 Minuten** — ein Lauf deutlich darüber wird im Rückmeldungs-Issue der Vorlage gemeldet | **Portfolio** (Owner-Dauerregel 2026-09-02, Punkt „Budget“) |
| Schwellen der Wochen-Scans (`security-scan.yml`) | `npm audit` ab **high** (Owner-Entscheid #91 — moderate/low mit reinem Major-Fix bleiben ohne Signal, Kommentar in `.github/dependabot.yml`); `pip-audit --strict` meldet jede bekannte Lücke; Schemathesis zählt nur 5xx | **Projekt** (npm-Schwelle: Owner, #91) |
| Turnus des Abhängigkeits-Bots | `interval: monthly`, `open-pull-requests-limit: 1` je Ökosystem (`github-actions`, `pip`, `npm`; `.github/dependabot.yml`) | **Portfolio** (Owner-Dauerregel 2026-09-02) |
| Schwere Läufe auf dem Rechner — alles, was eine volle Testsuite, einen Browser oder einen Container startet (bei uns jedes Ziel von `scripts/gates.sh`, `scripts/smoke.sh`, `scripts/teststand.sh up`, jeder Container-Build, ein Mutationslauf über die ganze Suite); im Zweifel schwer | **höchstens einer gleichzeitig auf dem ganzen Rechner**, über alle Sitzungen, Projekte und Rollen; leichte Läufe (eine Testdatei, Lint) sind frei. Eingehalten über EINE Sperre mit festem Pfad für alle Projekte, `$HOME/.sperre-schwerer-lauf`; Kommandos: `docs/agents/bau-brief.md`, Randbedingung „Parallelität" | **Portfolio** (2026-10-18) |
| Parallelität innerhalb eines Laufs (Worker je Testlauf, Browser) | **pytest: 1 Prozess** (kein `pytest-xdist` in `backend/requirements-dev.txt`); **Playwright: 1 Worker**, also ein Browser zugleich (`workers: 1`, `e2e/playwright.config.ts`) — gemessen 19.10.2026 | **Projekt** |

Panel-INTERNE Schwellen (Wiederholungen einer ausgefallenen Stimme,
Antwortbudget) besitzt `docs/agents/panel.md` — die ausdrückliche Ausnahme
von „Schwellen hier“.

## Review-Panel

Das Verfahren je Klasse: `docs/agents/panel.md`. Die **Form des Ergebnisses**:
`docs/agents/panel-kommentar.md` — feste Überschriften je Stimme, **auch bei
„keine Funde“**. Ein Slice ohne vollständiges oder vermerkt-verkürztes Panel
gilt als **nicht geprüft**.

Bis zu drei Stimmen mit festen Namen (v1.15.0) — wie viele ein Slice bekommt,
sagt die Risiko-Tabelle oben:

1. **Blindprüfer** — frischer Reviewer-Subagent (nie ein Fork der Sitzung),
   bekommt **nur Diff und Repo** als `git archive`-Auszug außerhalb jedes
   Repos, nicht den Bau-Brief. Früher „blinde Erststimme“.
2. **Fremdprüfer** — Modell eines anderen Anbieters über denselben Diff
   (Codex; ist dessen Kontingent erschöpft, sofort die agentische
   OpenRouter-Stimme — nie warten, Owner 19.09.2026). Früher „unabhängige
   Zweitstimme“.
3. **Gegenprüfer** — zweite frische Claude-Stimme mit Widerlegungsauftrag (auch
   sie nie als Fork, Unterlagen als Dateien im eigenen `git archive`-Baum);
   Pflicht bei R3, optional bei R2. Früher „Drittstimme bei R3“ bzw.
   „Zweitblind-Stimme“.

Die Überschriften im Panel-Kommentar bleiben nummeriert (`Stimme 1 —
Blindprüfer`), damit ältere Kommentare vergleichbar bleiben.

**Verkürzen** (eine Stimme bewusst weglassen) nur mit Grund unter der
Überschrift der weggelassenen Stimme — und nie unter die **Untergrenze**: bei
R2 der Blindprüfer (bei der Kopftext-R2 an einer kritischen Datei dazu die
Tür-Probe, `docs/agents/panel.md`); bei R3 und R4 zusätzlich nie ohne
Gegenprüfer und Tür-Probe. **Ein AUSFALL einer Pflichtstimme ist keine
Verkürzung:** Sie wird vor der Auslieferung nachgeholt, oder der Owner gibt die
Auslieferung ohne sie ausdrücklich frei. **Dasselbe gilt für eine teilweise
ausgefallene Tür-Probe** bei R3, R4 und der Kopftext-R2 an einer kritischen
Datei (Überschrift „Tür-Probe“ in `docs/agents/panel-kommentar.md`). Die
Schritte bei einem Ausfall stehen nur in `docs/agents/panel.md`.

**Kostenschwelle:** Wert im Schwellen-Inventar oben. Meldet die Ersatzleitung
des Fremdprüfers Guthabenende, gilt `docs/agents/panel.md`, Klumpenrisiko
Punkt 4 (Owner fragen, nicht ohne Panel ausliefern); die Form eines
geordneten Abbruchs steht dort unter „Ein Kostenstopp steht fest, BEVOR die
Serie beginnt".

Projektregeln zur Besetzung:

- **Subagenten sind für dieses Projekt freigegeben** (Owner, 15.08.2026).
  Reviewer-Subagenten **immer** — ohne sie gibt es keinen Blindprüfer.
  Bau-Subagenten nach Ermessen des Hauptagenten; **baut der Hauptagent selbst,
  ist der Blindprüfer zwingend ein frischer Subagent**, der weder Bau-Brief
  noch den Bericht des Bauers sieht.
- **Tiering:** Read-only-Scans/Mechanik → `haiku`, Bau-Slices → `sonnet`,
  Review/Verifikation → `opus`; bei Unsicherheit erben lassen.
- **Bau-Briefe** nach `docs/agents/bau-brief.md`: Pflicht-Gerüst aus Block 0
  plus neun Blöcken. Vor dem Absenden: `sh scripts/bau-brief-pruefen.sh
  <brief.md>`. Ein Brief ohne Block 3 (Konsumenten) ist die teuerste
  Auslassung.

Im Zweifel Panel. Ablauf, Prüfaufträge und Begründungen: `panel.md`.

## Agent skills

### Issue tracker

Issues leben in GitHub Issues (Repo Trust1509/pokecollect, `gh`-CLI); externe
PRs sind keine Triage-Oberfläche. See `docs/agents/issue-tracker.md`.

### Triage labels

Kanonisches Vokabular ohne Overrides: `needs-triage` / `needs-info` /
`ready-for-agent` / `ready-for-human` / `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` am Repo-Root + `docs/adr/`. See `docs/agents/domain.md`.
