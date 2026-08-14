#!/bin/sh
# Rauchtest (#52) — Playwright gegen einen frisch gebauten Wegwerf-Stapel.
# Nutzung: sh scripts/smoke.sh [run|keep|down]     (Default: run)
#
# BEWUSST KEIN Push-Gate: der Lauf baut zwei Images und startet vier Container
# (~3–5 min). Er gehört vor ein Release und in den Wochen-Job — nicht in die
# Schleife nach jedem Commit. Die schnellen Gates bleiben `scripts/gates.sh`.
#
# Der Stapel ist vom Teststand getrennt (eigenes Compose-Projekt, eigene DB) —
# der Teststand trägt die echte Sammlung des Owners.
set -eu

export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if command -v cygpath >/dev/null 2>&1; then ROOT="$(cygpath -w "$ROOT")"; fi
COMPOSE="docker compose -p pokecollect-smoke -f $ROOT/docker-compose.smoke.yml"

CMD="${1:-run}"

lauf() {
  status=0
  # --abort-on-container-exit: sobald der Rauchtest fertig ist, fallen auch
  # Web/API/DB; --exit-code-from reicht sein Ergebnis nach außen.
  $COMPOSE up --build --abort-on-container-exit --exit-code-from smoke || status=$?
  return "$status"
}

case "$CMD" in
  run)
    status=0
    lauf || status=$?
    $COMPOSE down -v --remove-orphans >/dev/null 2>&1 || true
    if [ "$status" -eq 0 ]; then
      echo "✓ Rauchtest grün"
    else
      echo "✗ Rauchtest rot — Bericht: e2e/playwright-report/index.html"
    fi
    exit "$status"
    ;;
  keep)
    # Stapel nach dem Lauf stehen lassen (zum Nachsehen im Browser).
    status=0
    lauf || status=$?
    echo "Stapel läuft weiter — Abriss: sh scripts/smoke.sh down"
    exit "$status"
    ;;
  down)
    $COMPOSE down -v --remove-orphans
    ;;
  *)
    echo "Nutzung: sh scripts/smoke.sh [run|keep|down]"
    exit 2
    ;;
esac
