#!/bin/sh
# Lokale Gates — alles läuft in Docker, kein Node/Python lokal nötig.
#   Backend: Image bauen + pytest gegen Wegwerf-Postgres (echter Migrationspfad)
#   Web:     Image bauen = npm ci + tsc + next build (wie Prod) + Lint (Builder-Stage)
# Aufruf:  sh scripts/gates.sh [backend|web|prozess|all]     (Default: all)
set -eu

# Git-Bash/MSYS: Pfad-Mangling aus, wir konvertieren selbst via cygpath
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${1:-all}"

host_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

backend_gate() {
  echo "── Gate 1/2: Backend (Docker-Build + pytest gegen Wegwerf-Postgres) ──"
  docker build -t pokecollect-api-gate "$(host_path "$ROOT/backend")"
  docker network inspect pokecollect-gate >/dev/null 2>&1 || docker network create pokecollect-gate >/dev/null
  docker rm -f pokecollect-gate-db >/dev/null 2>&1 || true
  docker run -d --name pokecollect-gate-db --network pokecollect-gate \
    -e POSTGRES_USER=pokecollect -e POSTGRES_PASSWORD=pokecollect \
    -e POSTGRES_DB=pokecollect_test postgres:16-alpine >/dev/null

  i=0
  until docker exec pokecollect-gate-db pg_isready -U pokecollect >/dev/null 2>&1; do
    i=$((i + 1))
    [ "$i" -gt 60 ] && { echo "FEHLER: Postgres kam nicht hoch"; docker rm -f pokecollect-gate-db >/dev/null; exit 1; }
    sleep 1
  done

  status=0
  # APP_PASSWORD_HASH: bcrypt("teststand") — Start-Guard verlangt ein Passwort
  # (Issue #1). conftest.py überschreibt den Wert ohnehin deterministisch.
  docker run --rm --network pokecollect-gate \
    -v "$(host_path "$ROOT/backend/tests"):/app/tests" \
    -v "$(host_path "$ROOT/backend/requirements-dev.txt"):/app/requirements-dev.txt" \
    -v "$(host_path "$ROOT/backend/requirements.txt"):/app/requirements.txt" \
    -e DATABASE_URL=postgresql://pokecollect:pokecollect@pokecollect-gate-db:5432/pokecollect_test \
    -e JWT_SECRET=gate-secret \
    -e APP_PASSWORD_HASH='$2b$12$DeEohIVnaJLbl/RfAGZYjONLbnSdt4h0PByR61DSe87ZU3tmaJb9G' \
    -e IMAGES_DIR=/tmp/test-images \
    pokecollect-api-gate \
    sh -c "mkdir -p /tmp/test-images && pip install --quiet -r requirements-dev.txt && python -m pytest tests -q" \
    || status=$?

  docker rm -f pokecollect-gate-db >/dev/null
  return "$status"
}

# Panel-Nacharbeit #99 (BLOCKER der Zweitstimme): `npm run check:whatsnew` läuft
# IM Web-Build-Image — dort gibt es CHANGELOG.md gar nicht, der Wächter kann die
# generierte Datei also nur gegen sich selbst prüfen. Eine von Hand hineinge-
# schriebene oder nach einer CHANGELOG-Änderung veraltete Datei bliebe grün —
# genau die "zweite Wahrheit", die Issue #99 vermeiden wollte. Deshalb hier, auf
# REPO-Ebene mit CHANGELOG.md in Reichweite: neu erzeugen und vergleichen.
whatsnew_paritaet_gate() {
  echo "── Gate 0/2: Was-ist-neu-Notizen stammen wirklich aus den Quellen ──"
  MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$ROOT")":/w -w //w node:20-alpine     node web/scripts/generate-whatsnew.mjs --check
}

# Abgleich v1.17.2: die Prozess-Werkzeuge der Vorlage — Brief-Prüfskript samt
# Selbstprobe, Wächter-Gate-Probe-Selbstprobe und der Lehren-Verweis-Wächter;
# seit Abgleich v1.18.13 dazu die Selbstprobe von ast-gleich.py (sein Urteil
# entscheidet über die Größe eines Panels; ohne Gate-Zeile liefe die Probe nur,
# wenn jemand daran denkt).
# Sie laufen im Linux-Container, nicht auf dem Host, aus zwei gemessenen Gründen
# (28.09.2026):
#   1. Nacktes `python` hing damals auf diesem Rechner für immer
#      (Windows-Store-Stub). Seit dem Python Install Manager läuft es (gemessen
#      19.10.2026) — ein Alias, der still wechselt, ist trotzdem keine
#      Gate-Umgebung; das Gate nimmt einen absoluten Interpreter.
#   2. Die Brief-Selbstprobe braucht unter Git Bash 166 s, unter dash im
#      Container 9 s (201 Läufe des Prüfskripts; fork ist unter Linux billig).
# Ein dritter Grund ist entfallen: Bis Vorlage v1.18.10 war die
# Wächter-Selbstprobe über den Symlink /usr/local/bin/python3 rot (Fall
# "Hardlink des Interpreters"); gemessen 19.10.2026 ist sie auch darüber grün.
# Wir rufen weiter python3.12 direkt auf. -I -S ist Pflicht (Vorlage
# abgleich.md 2h); seit Vorlage v1.18.0 verweigern die Werkzeuge den Lauf ohne.
# Alle vier Python-Aufrufe laufen mit -I -S, nicht nur der Wächter: Ohne -I
# steht das Skriptverzeichnis docs/vorlagen/ vorn auf sys.path, und eine
# gleichnamige Datei dort (tempfile.py, re.py) überschattet die
# Standardbibliothek — das Verweis-Werkzeug endete dann mit Exit 0, ohne zu
# prüfen, und das Gate meldete grün (Gegenprüfer, Abgleich v1.17.2; nachgestellt).
# Keine gepinnte Erwartungszahl: Die Summe der Wächter-Selbstprobe hängt an der
# Python-Version, nicht an der Plattform (gemessen 28.09.2026: 3.14 → 518,
# 3.12 → 521, bei 490 festen; 19.10.2026 hier 628 = 597 feste + 30
# umgebungsbedingte + die Schlusszeile). Die feste Zahl prüft die Selbstprobe selbst als
# Untergrenze (Vorlage v1.18.0). Die Werkzeuge melden ihr Ergebnis selbst über
# den Exit-Code; `sh -eu` bricht beim ersten roten ab und reicht ihn durch.
# Beleg eines Laufs sind die Erfolgszeilen der Werkzeuge selbst (Brief-Läufe,
# Wächter-Erwartungen, ast-gleich, Verweise) — nicht Exit 0 allein und nicht
# die Zeile "✓ Gates grün (...)": Die druckt gates.sh nach jedem Ziel, auch
# wenn prozess_gate nichts mehr prüft. GRENZE, gemessen im Abgleich v1.18.13:
# Eine gestrichene Werkzeug-Zeile, ein `sh -u -c` statt `sh -eu -c` (dann zählt
# nur der Exit der letzten Zeile) oder ein Ziel `all` ohne prozess_gate macht
# nichts rot; dagegen hilft nur das Lesen der Erfolgszeilen (#106).
# Die Vorlagen-CI fährt diese Prüfungen nicht (0 Treffer in docs/vorlagen/ci.yml)
# — sie gehören ins lokale Gate, deshalb hier keine Paritäts-Zeile für ci.yml.
prozess_gate() {
  echo "── Gate P: Prozess-Werkzeuge (Brief-Prüfskript, Wächter-Selbstprobe, ast-gleich, Lehren-Verweise) ──"
  MSYS_NO_PATHCONV=1 docker run --rm -v "$(host_path "$ROOT")":/w -w //w python:3.12-slim sh -eu -c '
    sh scripts/bau-brief-pruefen-selbsttest.sh
    /usr/local/bin/python3.12 -I -S docs/vorlagen/waechter-gate-probe-selbsttest.py
    /usr/local/bin/python3.12 -I -S docs/vorlagen/ast-gleich.py --selbstprobe
    /usr/local/bin/python3.12 -I -S docs/vorlagen/lehren-verweise-pruefen.py --selbstprobe
    /usr/local/bin/python3.12 -I -S docs/vorlagen/lehren-verweise-pruefen.py --lehren docs/agents/lehren.md docs/agents/*.md CLAUDE.md
  '
}

web_gate() {
  echo "── Gate 2/2: Web (Docker-Build: npm ci + tsc + next build; danach Lint) ──"
  # Paritäts-Wächter (lehren.md §5, Panel #72): Gate und CI müssen denselben
  # Lint-Schritt tragen — fehlt er in ci.yml, ist das Gate rot, nicht nur die Doku.
  grep -q "npm run lint" "$ROOT/.github/workflows/ci.yml" || { echo "FEHLER: ci.yml Web-Job ohne 'npm run lint' — Parität Gate <-> CI verletzt"; exit 1; }
  # Derselbe Paritäts-Wächter für den neuen "Was ist neu"-Wächter (Issue #99):
  # ohne diese Zeile könnte der CI-Schritt unbemerkt verschwinden, während das
  # lokale Gate weiter grün bliebe (lehren.md §13: Wächter-Code selbst
  # prüfen, nicht nur "läuft durch").
  grep -q "npm run check:whatsnew" "$ROOT/.github/workflows/ci.yml" || { echo "FEHLER: ci.yml Web-Job ohne 'npm run check:whatsnew' — Parität Gate <-> CI verletzt"; exit 1; }
  docker build -t pokecollect-web-gate "$(host_path "$ROOT/web")"
  # Lint separat gegen die Builder-Stage (Prod-Image lintet nicht — next.config.js
  # eslint.ignoreDuringBuilds, Panel-Nacharbeit #72):
  # Cache trifft, da dieselbe Stage gerade eben Teil des Builds oben war.
  # Kein `&&`-Verkettung nötig — set -eu oben lässt jede Zeile einzeln reißen.
  echo "── Lint (Builder-Stage: npm run lint --max-warnings 0) ──"
  docker build --target builder -t pokecollect-web-lint "$(host_path "$ROOT/web")"
  docker run --rm pokecollect-web-lint npm run lint
  # "Was ist neu"-Wächter (Issue #99): der Generierungsschritt darf nicht
  # lautlos ausfallen — prüft die COMMITTETE whatsnew.generated.ts gegen die
  # aktuelle APP_VERSION, DE/EN nicht leer. Läuft gegen dieselbe Builder-Stage
  # (Cache trifft, kostet praktisch nichts extra).
  echo "── Was-ist-neu-Notizen prüfen (npm run check:whatsnew) ──"
  docker run --rm pokecollect-web-lint npm run check:whatsnew
}

# Wichtig: KEIN `backend_gate && web_gate` — links von && greift set -e nicht,
# ein roter Backend-Gate liefe sonst still in das Erfolgs-Echo durch.
case "$TARGET" in
  backend) backend_gate ;;
  web)
    whatsnew_paritaet_gate
    web_gate
    ;;
  prozess) prozess_gate ;;
  all)
    whatsnew_paritaet_gate
    prozess_gate
    backend_gate
    web_gate
    ;;
  *) echo "Nutzung: sh scripts/gates.sh [backend|web|prozess|all]"; exit 2 ;;
esac

echo "✓ Gates grün ($TARGET)"
