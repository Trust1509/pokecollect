#!/bin/sh
# Zählt die Erfolgszeilen der Werkzeuge in einem Protokoll von
# `sh scripts/gates.sh prozess` — für den CI-Job „Prozess (Gate P)" (#106).
#
#   sh scripts/gate-p-erfolgszeilen.sh <protokoll>
#
# Exit 0: jede Zeile genau einmal, Zahlen mindestens auf der Untergrenze.
# Exit 1: eine Zeile fehlt, steht mehrfach, ist verändert oder zählt zu wenig.
# Exit 2: Aufruf- oder Werkzeugfehler (Protokoll fehlt, grep/sed scheitern).
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
# Werkzeug zu Gate P dazu, gehört seine Erfolgszeile hierher; nichts erzwingt
# das. Die Untergrenzen sind am 02.11.2026 gemessene Werte; nur die Verweise haben
# Luft, weil Doku Verweise verlieren darf. Von der Wächter-Selbstprobe zählt der
# feste Anteil, der Rest hängt von der Umgebung ab. Ändert sich ein Werkzeug, das
# legitim weniger prüft, wird hier bewusst nachgezogen. Getauschte Dateien im
# Verweis-Lauf fängt die Dateizahl nicht, nur fehlende.
#
# GRENZEN: Die Zählung liest ein Protokoll; sie sieht nicht, wer es schrieb.
# Ein `echo` der erwarteten Zeile statt des Werkzeugs bleibt grün (Fremdprüfer
# #106, gemessen). Das geht nur mit Absicht; gegen Absicht schützt hier nichts.
# Ein Werkzeug, das NACH seiner Erfolgszeile scheitert, fängt sie nur zusammen
# mit dem `-e` in gates.sh, im Container wie auf dem Host (gemessen 25.10.2026: mit `sh -u` und angehängtem
# `exit 1` bleiben Gate und Zählung grün; ein rotes Werkzeug ohne Erfolgszeile
# macht die Zählung rot, auch unter `sh -u`).

set -u
LOG=${1:?Aufruf: sh scripts/gate-p-erfolgszeilen.sh <protokoll>}
[ -f "$LOG" ] && [ -r "$LOG" ] || { echo "Aufruffehler: $LOG fehlt oder ist nicht lesbar" >&2; exit 2; }

FEHLER=0
ZEILEN=0

werkzeugfehler() {
    echo "Werkzeugfehler: $1" >&2
    exit 2
}

# Vergleiche positiv formuliert: Eine leere oder unsinnige Zahl lässt `[` scheitern,
# und das darf nie als „in Ordnung“ gelten (Blindprüfer #106, gemessen).
mindestens() {  # $1 = Werkzeug, $2 = Wert, $3 = Untergrenze
    case "$2" in ''|*[!0-9]*) werkzeugfehler "$1: Zahl '$2' nicht lesbar" ;; esac
    if [ "$2" -ge "$3" ]; then return 0; fi
    echo "ZU WENIG: $1 meldet $2, mindestens $3 verlangt"
    FEHLER=$((FEHLER + 1))
}

# $1 = Werkzeug, $2 = Muster (ERE, Anfang und Ende verankert, Zahlen als
# Gruppen, ohne #), $3/$4 = Untergrenzen der Gruppen 1/2 (optional)
erwarte() {
    ZEILEN=$((ZEILEN + 1))
    n=$(grep -cE -- "$2" "$LOG")
    rc=$?
    if [ "$rc" -gt 1 ]; then werkzeugfehler "grep rc=$rc bei $1"; fi
    case "$n" in ''|*[!0-9]*) werkzeugfehler "grep lieferte '$n' bei $1" ;; esac
    if [ "$n" -ne 1 ]; then
        echo "FEHLT: Erfolgszeile von $1 ${n}-mal statt einmal (Muster: $2)"
        FEHLER=$((FEHLER + 1))
        return 0
    fi
    if [ "$#" -ge 3 ]; then
        wert=$(sed -nE "s#$2#\\1#p" "$LOG") || werkzeugfehler "sed bei $1"
        mindestens "$1" "$wert" "$3"
    fi
    if [ "$#" -ge 4 ]; then
        wert=$(sed -nE "s#$2#\\2#p" "$LOG") || werkzeugfehler "sed bei $1"
        mindestens "$1" "$wert" "$4"
    fi
}

erwarte "commit-msg-Selbstprobe"        '^commit-msg-Selbstprobe gruen: ([0-9]+) Faelle \(mindestens [0-9]+\) mit echten git-commit-Aufrufen .* gegen (.*/)?\.githooks/commit-msg$' 43
erwarte "Modus des commit-msg-Hooks"    '^commit-msg-Hook in Index und HEAD ausführbar \(100755\)$'
erwarte "Parität ci.yml"                '^ci\.yml faehrt Gate P und die Zaehlung$'
erwarte "Brief-Selbstprobe"             '^Selbstprobe gruen: ([0-9]+) Laeufe\. .*\(Kodierungen: utf8 cp1252 crlf\)\.$' 201
erwarte "Zähl-Selbstprobe"              '^Zaehl-Selbstprobe gruen: ([0-9]+) Faelle\.$' 85
erwarte "Wächter-Selbstprobe"           '^Waechter-Selbstprobe gruen: [0-9]+ Erwartungen = ([0-9]+) feste .*Vollstaendigkeit der Werkzeugliste\.$' 597
erwarte "ast-gleich --selbstprobe"      '^ast-gleich Selbstprobe gruen: ([0-9]+) Erwartungen .*Nicht geprueft: ob ein Kopftext WAHR ist\.$' 38
erwarte "Lehren-Verweise --selbstprobe" '^Selbstprobe gruen: ([0-9]+) Erwartungen \(Abschnitts- .*das kann dieses Skript nicht\.$' 242
erwarte "Lehren-Verweise über die Doku" '^Verweise gruen: ([0-9]+) Verweise in ([0-9]+) Datei\(en\), .*Nicht geprueft: ob ein Verweis die GEMEINTE Lehre trifft\.$' 30 10
erwarte "Schlusszeile von gates.sh"     '^✓ Gates grün \(prozess\)$'

if [ "$FEHLER" -ne 0 ]; then
    echo "Gate P ROT: $FEHLER Abweichung(en) bei $ZEILEN erwarteten Erfolgszeilen in $LOG"
    exit 1
fi
echo "Gate P belegt: alle $ZEILEN Erfolgszeilen je einmal in $LOG"
