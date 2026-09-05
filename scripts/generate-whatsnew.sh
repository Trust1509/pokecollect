#!/bin/sh
# "Was ist neu"-Notizen generieren (Issue #99) — Teil des Release-Rituals.
#   DE kommt automatisch aus CHANGELOG.md (Abschnitt der aktuellen APP_VERSION).
#   EN kommt aus der handgepflegten web/src/lib/whatsnew.en.json und wird nur
#   übernommen, wenn deren "version" zur aktuellen passt — sonst bleibt EN
#   bewusst leer (web/scripts/check-whatsnew.mjs schlägt dann in den Gates an).
# Läuft in einem Wegwerf-Node-Container — kein lokales npm/node auf diesem PC.
# Aufruf: sh scripts/generate-whatsnew.sh
set -eu

# Git-Bash/MSYS: Pfad-Mangling aus, wie in gates.sh/smoke.sh/teststand.sh.
export MSYS_NO_PATHCONV=1

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

host_path() {
  if command -v cygpath >/dev/null 2>&1; then cygpath -w "$1"; else printf '%s' "$1"; fi
}

# Repo-Wurzel mounten (der Generator braucht CHANGELOG.md eine Ebene über
# web/), Arbeitsverzeichnis auf web/ setzen — dieselbe Node-Version wie
# web/Dockerfile (node:20-alpine).
docker run --rm \
  -v "$(host_path "$ROOT")":/w \
  -w /w/web \
  node:20-alpine \
  node scripts/generate-whatsnew.mjs
