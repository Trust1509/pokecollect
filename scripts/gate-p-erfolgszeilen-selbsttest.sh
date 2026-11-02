#!/bin/sh
# Selbstprobe von scripts/gate-p-erfolgszeilen.sh (#106), läuft in Gate P.
# Verstümmelt ein Muster-Protokoll, dessen Zahlen genau auf den Untergrenzen
# stehen, und verlangt den passenden Exit-Code. Die Muster-Zeilen sind ein
# Nachbau: Ob die Zählung zu den ECHTEN Zeilen passt, zeigt der CI-Job, der sie
# auf das echte Protokoll anwendet.
set -eu

HIER=$(cd "$(dirname "$0")" && pwd)
ZAEHLER="$HIER/gate-p-erfolgszeilen.sh"
MINDEST=60
FAELLE=0
TMP=$(mktemp -d "${TMPDIR:-/tmp}/gate-p-probe.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/gut" <<'EOF'
── Kopfzeile ──
commit-msg-Selbstprobe gruen: 43 Faelle (mindestens 43) mit echten git-commit-Aufrufen (-m, -F), gespeicherte Nachricht verglichen, gegen /w/.githooks/commit-msg
commit-msg-Hook in Index und HEAD ausführbar (100755)
ci.yml faehrt Gate P und die Zaehlung
Selbstprobe gruen: 201 Laeufe. Gegen den Muster-Brief gemeldet (Kodierungen: utf8 cp1252 crlf).
Zaehl-Selbstprobe gruen: 60 Faelle.
Waechter-Selbstprobe gruen: 597 Erwartungen = Nicht geprueft: Vollstaendigkeit der Werkzeugliste.
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
ANFAENGE='^commit-msg-Selbstprobe ^commit-msg-Hook ^ci\.yml ^Selbstprobe.gruen:.[0-9]+.Laeufe ^Zaehl-Selbstprobe ^Waechter-Selbstprobe ^ast-gleich ^Selbstprobe.gruen:.[0-9]+.Erwartungen ^Verweise'
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
verstuemmelt "Zähl-Probe 59"     1 's/gruen: 60 Faelle/gruen: 59 Faelle/'
verstuemmelt "Wächter 596"       1 's/gruen: 597 Erw/gruen: 596 Erw/'
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

if [ "$FAELLE" -lt "$MINDEST" ]; then
    echo "FEHLER: nur $FAELLE Fälle, mindestens $MINDEST verlangt"
    exit 1
fi
echo "Zaehl-Selbstprobe gruen: $FAELLE Faelle."
