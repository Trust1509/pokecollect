#!/bin/sh
# Selbstprobe von scripts/gate-p-erfolgszeilen.sh (#106), läuft in Gate P.
# Verstümmelt ein Muster-Protokoll, dessen Zahlen genau auf den Untergrenzen
# stehen, und verlangt den passenden Exit-Code. Die Muster-Zeilen sind ein
# Nachbau: Ob die Zählung zu den ECHTEN Zeilen passt, zeigt der CI-Job, der sie
# auf das echte Protokoll anwendet.
set -eu

HIER=$(cd "$(dirname "$0")" && pwd)
ZAEHLER="$HIER/gate-p-erfolgszeilen.sh"
MINDEST=85
FAELLE=0
TMP=$(mktemp -d "${TMPDIR:-/tmp}/gate-p-probe.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/gut" <<'EOF'
── Kopfzeile ──
commit-msg-Selbstprobe gruen: 43 Faelle (mindestens 43) mit echten git-commit-Aufrufen (-m, -F), gespeicherte Nachricht verglichen, gegen /w/.githooks/commit-msg
commit-msg-Hook in Index und HEAD ausführbar (100755)
ci.yml faehrt Gate P und die Zaehlung
Selbstprobe gruen: 201 Laeufe. Gegen den Muster-Brief gemeldet (Kodierungen: utf8 cp1252 crlf).
Zaehl-Selbstprobe gruen: 85 Faelle.
Waechter-Selbstprobe gruen: 628 Erwartungen = 597 feste + 31. Nicht geprueft: Vollstaendigkeit der Werkzeugliste.
ast-gleich Selbstprobe gruen: 38 Erwartungen (GLEICH). Nicht geprueft: ob ein Kopftext WAHR ist.
Selbstprobe gruen: 242 Erwartungen (Abschnitts- und Verweise). Nicht geprueft: das kann dieses Skript nicht.
Verweise gruen: 30 Verweise in 10 Datei(en), alle treffen. Nicht geprueft: ob ein Verweis die GEMEINTE Lehre trifft.
✓ Gates grün (prozess)
EOF

# $1 = Fallname, $2 = erwarteter Exit, $3 = Protokoll
pruefe() {
    FAELLE=$((FAELLE + 1))
    if sh "$ZAEHLER" "$3" > "$TMP/aus" 2>&1; then rc=0; else rc=$?; fi
    if [ "$rc" -ne "$2" ]; then
        echo "FEHLER: $1: Exit $rc statt $2"
        cat "$TMP/aus"
        exit 1
    fi
}

# $1 = Fallname, $2 = erwarteter Exit, $3 = sed-Ausdruck auf das Muster-Protokoll
verstuemmelt() {
    sed -E "$3" "$TMP/gut" > "$TMP/log"
    if cmp -s "$TMP/gut" "$TMP/log"; then
        echo "FEHLER: $1: Der Ausdruck ändert nichts, der Fall prüft nichts"
        exit 1
    fi
    pruefe "$1" "$2" "$TMP/log"
}

pruefe "Muster-Protokoll auf den Untergrenzen" 0 "$TMP/gut"

# Jede Erfolgszeile: gestrichen, doppelt, eingerückt, mit Anhang, mit Vorsatz
ANFAENGE='^commit-msg-Selbstprobe ^commit-msg-Hook ^ci\.yml ^Selbstprobe.gruen:.[0-9]+.Laeufe ^Zaehl-Selbstprobe ^Waechter-Selbstprobe ^ast-gleich ^Selbstprobe.gruen:.[0-9]+.Erwartungen ^Verweise ^✓'
for a in $ANFAENGE; do
    verstuemmelt "gestrichen: $a" 1 "/$a/d"
    verstuemmelt "doppelt: $a" 1 "/$a/p"
    verstuemmelt "eingerückt: $a" 1 "/$a/s/^/  /"
    verstuemmelt "Anhang: $a" 1 "/$a/s/\$/ ERFUNDEN/"
    verstuemmelt "Vorsatz: $a" 1 "/$a/s/^/x/"
done

# Jede Zahl: eins unter der Untergrenze, null, unsinnig groß bleibt zulässig
verstuemmelt "commit-msg 42"     1 's/gruen: 43 Faelle/gruen: 42 Faelle/'
verstuemmelt "commit-msg 0"      1 's/gruen: 43 Faelle/gruen: 0 Faelle/'
verstuemmelt "Brief 200"         1 's/gruen: 201 Laeufe/gruen: 200 Laeufe/'
verstuemmelt "Zähl-Probe 84"     1 's/gruen: 85 Faelle/gruen: 84 Faelle/'
verstuemmelt "Wächter 596 feste" 1 's/= 597 feste/= 596 feste/'
verstuemmelt "ast-gleich 37"     1 's/gruen: 38 Erw/gruen: 37 Erw/'
verstuemmelt "Lehren-Probe 241"  1 's/gruen: 242 Erw/gruen: 241 Erw/'
verstuemmelt "Verweise 29"       1 's/gruen: 30 Verweise/gruen: 29 Verweise/'
verstuemmelt "Dateien 9"         1 's/in 10 Datei/in 9 Datei/'
verstuemmelt "0 Verweise, 0 Dat" 1 's/gruen: 30 Verweise in 10/gruen: 0 Verweise in 0/'
verstuemmelt "Verweise höher"    0 's/gruen: 30 Verweise in 10/gruen: 31 Verweise in 11/'

# Andere Hook-Datei als Argument der commit-msg-Probe
verstuemmelt "fremder Hook" 1 's#/w/\.githooks/commit-msg$#/w/anderer-hook#'
# Übersprungene Modus-Prüfung (git-archive-Auszug) belegt nichts
verstuemmelt "Modus nicht geprüft" 1 's/^commit-msg-Hook in Index.*/Modus des commit-msg-Hooks NICHT geprueft: kein Git-Arbeitsbaum/'

: > "$TMP/leer"
pruefe "leeres Protokoll" 1 "$TMP/leer"
pruefe "Protokoll fehlt" 2 "$TMP/gibt-es-nicht"

# Scheitern grep oder sed, darf das nie als grün gelten (Blindprüfer #106: leeres
# Ergebnis ließ `[` scheitern, und das Skript meldete „belegt“).
mkdir "$TMP/stumm"
for w in grep sed; do
    printf '#!/bin/sh\nexit 2\n' > "$TMP/stumm/$w"
    chmod +x "$TMP/stumm/$w"
    FAELLE=$((FAELLE + 1))
    if PATH="$TMP/stumm:$PATH" sh "$ZAEHLER" "$TMP/gut" > "$TMP/aus" 2>&1; then rc=0; else rc=$?; fi
    if [ "$rc" -ne 2 ]; then
        echo "FEHLER: $w scheitert: Exit $rc statt 2"
        cat "$TMP/aus"
        exit 1
    fi
    rm "$TMP/stumm/$w"
done

# ci-gate-p-pruefen.sh gegen das echte ci.yml und seine Umbauten
PRUEFER="$HIER/ci-gate-p-pruefen.sh"
CI="$HIER/../.github/workflows/ci.yml"

pruefe_ci() {  # $1 = Fallname, $2 = erwarteter Exit, $3 = Datei
    FAELLE=$((FAELLE + 1))
    if sh "$PRUEFER" "$3" > "$TMP/aus" 2>&1; then rc=0; else rc=$?; fi
    if [ "$rc" -ne "$2" ]; then
        echo "FEHLER: ci.yml, $1: Exit $rc statt $2"
        cat "$TMP/aus"
        exit 1
    fi
    if [ "$rc" -eq 0 ]; then erwartet=1; else erwartet=0; fi
    if [ "$(grep -c '^ci\.yml faehrt Gate P und die Zaehlung$' "$TMP/aus")" -ne "$erwartet" ]; then
        echo "FEHLER: ci.yml, $1: Erfolgszeile trotz Exit $rc falsch"
        exit 1
    fi
}

umbau() {  # $1 = Fallname, $2 = sed-Ausdruck
    sed -E "$2" "$CI" > "$TMP/ci.yml"
    if cmp -s "$CI" "$TMP/ci.yml"; then
        echo "FEHLER: ci.yml, $1: Der Ausdruck ändert nichts, der Fall prüft nichts"
        exit 1
    fi
    pruefe_ci "$1" 1 "$TMP/ci.yml"
}

pruefe_ci "echtes ci.yml" 0 "$CI"
pruefe_ci "ci.yml fehlt" 2 "$TMP/gibt-es-nicht"
umbau "Zählschritt weg"          '/run: sh scripts\/gate-p-erfolgszeilen/d'
umbau "Lauf weg"                 '/sh scripts\/gates\.sh prozess >/d'
umbau "Exit nicht weitergereicht" '/gates\.sh prozess: Exit/d'
umbau "Exit auf 0"               '/gates\.sh prozess: Exit/s/exit "\$rc"/exit 0/'
umbau "Zugangsdaten gespeichert" '/persist-credentials: false/d'
umbau "Job umbenannt"            's/^  prozess:$/  prozess2:/'
umbau "if am Job"                's/^  prozess:$/  prozess:\n    if: false/'
umbau "if am Schritt"            's/^      - name: Gate P$/      - if: false\n        name: Gate P/'
umbau "if in Anführungszeichen"  's/^  prozess:$/  prozess:\n    "if": false/'
umbau "continue-on-error am Job" 's/^  prozess:$/  prozess:\n    continue-on-error: true/'
umbau "continue-on-error quotiert" 's/^  prozess:$/  prozess:\n    "continue-on-error": true/'
umbau "continue-on-error fremder Job" 's/^  web:$/  web:\n    continue-on-error: true/'
umbau "Auslöser weg"             '/^  workflow_dispatch:/d'

mkdir "$TMP/stumm2"
for w in grep awk; do
    printf '#!/bin/sh\nexit 2\n' > "$TMP/stumm2/$w"
    chmod +x "$TMP/stumm2/$w"
    FAELLE=$((FAELLE + 1))
    if PATH="$TMP/stumm2:$PATH" sh "$PRUEFER" "$CI" > "$TMP/aus" 2>&1; then rc=0; else rc=$?; fi
    rm "$TMP/stumm2/$w"
    if [ "$rc" -ne 2 ]; then
        echo "FEHLER: ci.yml, $w scheitert: Exit $rc statt 2"
        cat "$TMP/aus"
        exit 1
    fi
done

if [ "$FAELLE" -lt "$MINDEST" ]; then
    echo "FEHLER: nur $FAELLE Fälle, mindestens $MINDEST verlangt"
    exit 1
fi
echo "Zaehl-Selbstprobe gruen: $FAELLE Faelle."
