#!/bin/sh
# Prüft, dass ci.yml den Job „Prozess (Gate P)" wirklich fährt (#106), für Gate P.
#
#   sh scripts/ci-gate-p-pruefen.sh <ci.yml>
#
# Exit 0: Job, Lauf und Zählung stehen da, nichts schaltet sie ab.
# Exit 1: eine Stelle fehlt oder schaltet den Job ab.
# Exit 2: Aufruf- oder Werkzeugfehler.
#
# Die Erfolgszeile steht NUR am Ende: Eine Meldung, die das Gate nicht rot macht,
# ließe sie stehen, und gate-p-erfolgszeilen.sh sähe nichts (Blindprüfer #106,
# gemessen, darum eigenes Skript mit Selbstprobe statt Zeilen in gates.sh).
#
# GRENZE: Das ist Textvergleich, kein YAML-Parser. Abgedeckt sind die Umbauten,
# die in der Selbstprobe stehen (gate-p-erfolgszeilen-selbsttest.sh); ein Lauf
# nur für bestimmte Zweige oder ein geänderter Auslöser anderer Form nicht.

set -u
CI=${1:?Aufruf: sh scripts/ci-gate-p-pruefen.sh <ci.yml>}
[ -f "$CI" ] && [ -r "$CI" ] || { echo "Aufruffehler: $CI fehlt oder ist nicht lesbar" >&2; exit 2; }

# Nur der Job selbst: von „  prozess:" bis zum nächsten Job
if ! BLOCK=$(awk '/^  prozess:$/ { f = 1; next } f && /^  [^ #]/ { f = 0 } f' "$CI"); then
    echo "Werkzeugfehler: awk" >&2
    exit 2
fi
[ -n "$BLOCK" ] || { echo "FEHLER: ci.yml hat keinen Job prozess"; exit 1; }

# $1 = Muster, $2 = Text; Exit 0/1 wie grep, alles andere bricht ab
im_text() {
    printf '%s\n' "$2" | grep -qE -- "$1"
    rc=$?
    if [ "$rc" -gt 1 ]; then echo "Werkzeugfehler: grep rc=$rc" >&2; exit 2; fi
    return "$rc"
}

verlangt() {  # $1 = Muster, $2 = Meldung
    im_text "$1" "$BLOCK" || { echo "FEHLER: $2"; exit 1; }
}
verboten() {  # $1 = Muster, $2 = Text, $3 = Meldung
    if im_text "$1" "$2"; then echo "FEHLER: $3"; exit 1; fi
}

verlangt '^ +sh scripts/gates\.sh prozess > "\$RUNNER_TEMP/gate-p\.log" 2>&1$' "Job fährt 'gates.sh prozess' nicht mehr ins Protokoll"
verlangt '^ +run: sh scripts/gate-p-erfolgszeilen\.sh "\$RUNNER_TEMP/gate-p\.log"$' "Job zählt die Erfolgszeilen nicht mehr"
verlangt '^ +if \[ "\$rc" -ne 0 \]; then echo "gates\.sh prozess: Exit \$rc"; exit "\$rc"; fi$' "Job reicht den Exit von gates.sh nicht mehr weiter"
verlangt '^ +persist-credentials: false( |$)' "Checkout des Jobs speichert Zugangsdaten"
verboten '^[ -]*["'"'"']?if["'"'"']?:' "$BLOCK" "if: im Job, er liefe vielleicht gar nicht"
verboten '^[ -]*["'"'"']?continue-on-error["'"'"']?:' "$(cat "$CI")" "continue-on-error in ci.yml: ein roter Job bliebe folgenlos"
im_text '^  workflow_dispatch:' "$(cat "$CI")" || { echo "FEHLER: ci.yml hat keinen workflow_dispatch mehr, der Lauf nach der Landung fiele weg"; exit 1; }

echo "ci.yml faehrt Gate P und die Zaehlung"
