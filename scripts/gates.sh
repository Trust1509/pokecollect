#!/bin/sh
# Lokale Gates — alles läuft in Docker, kein Node/Python lokal nötig.
#   Backend: Image bauen + pytest gegen Wegwerf-Postgres (echter Migrationspfad)
#   Web:     Image bauen = npm ci + tsc + next build (wie Prod)
# Aufruf:  sh scripts/gates.sh [backend|web|all]     (Default: all)
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
  docker run --rm --network pokecollect-gate \
    -v "$(host_path "$ROOT/backend/tests"):/app/tests" \
    -e DATABASE_URL=postgresql://pokecollect:pokecollect@pokecollect-gate-db:5432/pokecollect_test \
    -e JWT_SECRET=gate-secret \
    -e IMAGES_DIR=/tmp/test-images \
    pokecollect-api-gate \
    sh -c "mkdir -p /tmp/test-images && pip install --quiet pytest==8.3.2 && python -m pytest tests -q" \
    || status=$?

  docker rm -f pokecollect-gate-db >/dev/null
  return "$status"
}

web_gate() {
  echo "── Gate 2/2: Web (Docker-Build: npm ci + tsc + next build) ──"
  docker build -t pokecollect-web-gate "$(host_path "$ROOT/web")"
}

# Wichtig: KEIN `backend_gate && web_gate` — links von && greift set -e nicht,
# ein roter Backend-Gate liefe sonst still in das Erfolgs-Echo durch.
case "$TARGET" in
  backend) backend_gate ;;
  web)     web_gate ;;
  all)
    backend_gate
    web_gate
    ;;
  *) echo "Nutzung: sh scripts/gates.sh [backend|web|all]"; exit 2 ;;
esac

echo "✓ Gates grün ($TARGET)"
