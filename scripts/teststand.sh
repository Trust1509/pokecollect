#!/bin/sh
# Teststand-Verwaltung (Compose-Projekt pokecollect-test, siehe docker-compose.test.yml)
# Nutzung: sh scripts/teststand.sh [up|down|reset|seed|logs|status]
set -eu
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if command -v cygpath >/dev/null 2>&1; then ROOT="$(cygpath -w "$ROOT")"; fi
COMPOSE="docker compose -p pokecollect-test -f $ROOT/docker-compose.test.yml"
API="http://localhost:3020"

CMD="${1:-up}"

case "$CMD" in
  up)
    $COMPOSE up -d --build
    echo "Warte auf API …"
    i=0
    until curl -sf "$API/health" >/dev/null 2>&1; do
      i=$((i + 1))
      [ "$i" -gt 90 ] && { echo "FEHLER: API kam nicht hoch — $COMPOSE logs api"; exit 1; }
      sleep 2
    done
    echo "✓ Teststand läuft — Web: http://localhost:3021 · API: $API"
    ;;
  down)
    $COMPOSE down
    ;;
  reset)
    $COMPOSE down -v
    echo "✓ Teststand samt Daten entfernt"
    ;;
  seed)
    # Ein paar besessene Karten + eine Wunschlisten-Karte für den UX-Durchklick
    seed_card() {
      curl -sf -X POST "$API/api/v1/cards" -H "Content-Type: application/json" -d "$1" >/dev/null \
        && echo "  + $2" || echo "  ! Seed fehlgeschlagen: $2"
    }
    seed_card '{"kartenname":"Pikachu","englischer_name":"Pikachu","pokedex_nr":25,"set_edition":"SVI","karten_nr":"063","seltenheit":"Common","sprache":"DE","besessen":true,"zustand":"Near Mint"}' "Pikachu (SVI 063)"
    seed_card '{"kartenname":"Glurak-ex","englischer_name":"Charizard ex","pokedex_nr":6,"set_edition":"OBF","karten_nr":"125","seltenheit":"Double Rare","sprache":"DE","besessen":true,"folierung":"Holo","zustand":"Mint"}' "Glurak-ex (OBF 125)"
    seed_card '{"kartenname":"Mew-ex","englischer_name":"Mew ex","pokedex_nr":151,"set_edition":"MEW","karten_nr":"151","seltenheit":"Double Rare","sprache":"EN","besessen":true}' "Mew-ex (MEW 151)"
    seed_card '{"kartenname":"Nachtara","englischer_name":"Umbreon","pokedex_nr":197,"set_edition":"PRE","karten_nr":"059","seltenheit":"Common","sprache":"DE","wunschliste":true,"prioritaet":"Chase"}' "Nachtara (Wunschliste)"
    echo "✓ Seed fertig"
    ;;
  logs)
    $COMPOSE logs -f --tail 100
    ;;
  status)
    $COMPOSE ps
    ;;
  *)
    echo "Nutzung: sh scripts/teststand.sh [up|down|reset|seed|logs|status]"
    exit 2
    ;;
esac
