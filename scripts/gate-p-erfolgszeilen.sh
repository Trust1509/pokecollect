#!/bin/sh
# Zählt die Erfolgszeilen der Werkzeuge in einem Protokoll von
# `sh scripts/gates.sh prozess` — für den CI-Job „Prozess (Gate P)" (#106).
#
#   sh scripts/gate-p-erfolgszeilen.sh <protokoll>
#
# WARUM: Exit 0 von gates.sh beweist nicht, dass Gate P geprüft hat. Gemessen
# im Abgleich v1.18.13: Eine gestrichene Werkzeug-Zeile in prozess_gate oder
# ein `sh -u -c` statt `sh -eu -c` (dann zählt nur der Exit der letzten Zeile)
# lässt Gate P grün, und "✓ Gates grün (prozess)" druckt gates.sh nach jedem
# Ziel. Jedes Werkzeug druckt bei Erfolg genau eine eigene Zeile — fehlt eine,
# hat es nicht oder nicht grün geprüft.
#
# Die Erwartungen stehen HIER, nicht in gates.sh: Wer dort eine Werkzeug-Zeile
# streicht, muss sie auch hier streichen, sonst wird die CI rot. Kommt ein
# Werkzeug zu Gate P dazu, gehört seine Erfolgszeile hierher.
#
# GRENZE: Die Zahlen in den Zeilen prüft dieses Skript nicht — Untergrenzen
# prüfen die Werkzeuge selbst (Wächter-Selbstprobe, commit-msg-Selbstprobe).
# Ein Werkzeug, das grün druckt, ohne zu prüfen, fängt es nicht — und eines,
# das NACH seiner Erfolgszeile scheitert, nur zusammen mit `sh -eu` in
# gates.sh (gemessen 25.10.2026: mit `sh -u` und angehängtem `exit 1` bleiben
# Gate und Zählung grün; ein rotes Werkzeug ohne Erfolgszeile macht die
# Zählung rot, auch unter `sh -u`).

set -u
LOG=${1:?Aufruf: sh scripts/gate-p-erfolgszeilen.sh <protokoll>}
[ -f "$LOG" ] || { echo "Aufruffehler: $LOG fehlt" >&2; exit 2; }

FEHLER=0
ZEILEN=0
erwarte() {  # $1 = Werkzeug, $2 = Muster (ERE, am Zeilenanfang verankert)
    ZEILEN=$((ZEILEN + 1))
    n=$(grep -cE "^$2" "$LOG")
    if [ "$n" -ne 1 ]; then
        echo "FEHLT: Erfolgszeile von $1 ${n}-mal statt einmal (Muster: ^$2)"
        FEHLER=$((FEHLER + 1))
    fi
}

erwarte "commit-msg-Selbstprobe"           'commit-msg-Selbstprobe gruen: [0-9]+ Faelle'
erwarte "Brief-Selbstprobe"                'Selbstprobe gruen: [0-9]+ Laeufe\.'
erwarte "Wächter-Selbstprobe"              'Waechter-Selbstprobe gruen: [0-9]+ Erwartungen'
erwarte "ast-gleich --selbstprobe"         'ast-gleich Selbstprobe gruen: [0-9]+ Erwartungen'
erwarte "Lehren-Verweise --selbstprobe"    'Selbstprobe gruen: [0-9]+ Erwartungen \(Abschnitts-'
erwarte "Lehren-Verweise über die Doku"    'Verweise gruen: [0-9]+ Verweise in [0-9]+ Datei'

if [ "$FEHLER" -ne 0 ]; then
    echo "Gate P ROT: $FEHLER von $ZEILEN Erfolgszeilen fehlen oder stehen mehrfach in $LOG"
    exit 1
fi
echo "Gate P belegt: alle $ZEILEN Erfolgszeilen je einmal in $LOG"
