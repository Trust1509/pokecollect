#!/bin/sh
# Selbstprobe fuer .githooks/commit-msg — mit ECHTEN git-commit-Aufrufen.
#
#   sh scripts/commit-msg-selbsttest.sh [<hook-verzeichnis>]
#
# Ohne Argument prueft sie .githooks/ dieses Repos. Mit Argument ein anderes
# Verzeichnis (fuer den Rot-Beweis gegen eine alte Fassung).
#
# WARUM ECHT: Eine Selbstprobe, deren Eingabe das Format von git nachbaut,
# prueft die Annahme mit, statt sie zu pruefen (lehren.md §1). Gemessen
# (#112): Bei `git commit -v` haengt git den Diff hinter einer Scheren-Zeile an
# die Nachrichtendatei; der Hook las ihn als Rumpf und lehnte saubere Commits
# ab. Jeder Fall hier laesst git selbst die Datei schreiben, die der Hook liest.
#
# WAS SIE PRUEFT: je Fall den Exit von `git commit`, ob ein Commit entstanden
# ist (Zahl der Commits davor und danach) und bei Ablehnung die Meldung des
# Hooks — in einem Wegwerf-Repo unter $TMPDIR. Der Marker wird im Skript
# zusammengesetzt, damit diese Datei ihn nicht woertlich traegt.
#
# GRENZE: Wer in einer -F-Datei die Scheren-Zeile von git samt der Zeile
# darunter von Hand nachbaut, umgeht den Hook. Gegen eine versehentlich
# falsche Nachricht reicht das; gegen Absicht schuetzt kein Hook.

set -u
LC_ALL=C
export LC_ALL
# gates.sh exportiert MSYS_NO_PATHCONV=1; dann bekommt das native git unter
# Git Bash "/c/..." wörtlich und legt das Wegwerf-Repo unter C:\c\ an, die
# Probe bricht ab (gemessen 24.10.2026). Hier braucht git die Umsetzung.
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL

HIER=$(cd "$(dirname "$0")/.." && pwd)
HOOKS=${1:-$HIER/.githooks}
[ -f "$HOOKS/commit-msg" ] || { echo "Aufruffehler: $HOOKS/commit-msg fehlt" >&2; exit 2; }
HOOKS=$(cd "$HOOKS" && pwd)

BASIS=${TMPDIR:-/tmp}
W=$(mktemp -d "$BASIS/commit-msg-probe.XXXXXX") || exit 2
trap 'rm -rf "$W"' EXIT INT TERM

M="[skip"" ci]"          # der Ueberspring-Marker, zusammengesetzt
git init -q "$W/repo" || exit 2
cd "$W/repo" || exit 2
git config user.email probe@example.invalid
git config user.name Probe
git config core.hooksPath "$HOOKS"
git config core.autocrlf false
git config core.commentChar '#'
printf 'start\n' > datei.txt
git add datei.txt
git -c core.hooksPath=/dev/null commit -q -m "Start" || exit 2

# Editor-Ersatz: setzt $W/nachricht.txt VOR die Vorlage, die git anlegt;
# Scheren-Zeile und Diff schreibt git selbst.
{
    echo '#!/bin/sh'
    echo "cat \"$W/nachricht.txt\" \"\$1\" > \"\$1.neu\" && mv \"\$1.neu\" \"\$1\""
} > "$W/editor.sh"
nachricht() { printf "$1" "$M" > "$W/nachricht.txt"; }   # %s = Marker

FEHLER=0
FAELLE=0
fall() {  # $1 = Name, $2 = erwartet (an|ab), Rest = git-commit-Argumente
    name=$1; erwartet=$2; shift 2
    FAELLE=$((FAELLE + 1))
    printf 'zeile %s\n' "$FAELLE" >> datei.txt
    [ "${INHALT_MIT_MARKER:-}" = ja ] && printf 'Inhalt %s\n' "$M" >> datei.txt
    git add datei.txt
    vorher=$(git rev-list --count HEAD)
    GIT_EDITOR="sh $W/editor.sh" git commit -q "$@" > "$W/aus.txt" 2>&1
    rc=$?
    nachher=$(git rev-list --count HEAD)
    if [ "$erwartet" = an ]; then
        [ "$rc" -eq 0 ] && [ "$nachher" -eq $((vorher + 1)) ] && return 0
    else
        [ "$rc" -ne 0 ] && [ "$nachher" -eq "$vorher" ] && grep -q "Ueberspring-Marker" "$W/aus.txt" && return 0
    fi
    echo "  FALSCH: $name — erwartet '$erwartet', git commit rc=$rc, Commits $vorher -> $nachher"
    sed 's/^/    | /' "$W/aus.txt"
    FEHLER=$((FEHLER + 1))
}

fall "-m, Marker im Betreff"                  an -m "$M Betreff" -m "Rumpf ohne Marker."
fall "-m, Marker im Rumpf"                    ab -m "Betreff" -m "Rumpf mit $M."
printf 'Betreff\n\nRumpf mit %s.\n' "$M" > "$W/f.txt"
fall "-F, Marker im Rumpf"                    ab -F "$W/f.txt"
printf 'Betreff\n\n# Kommentar mit %s\n' "$M" > "$W/f.txt"
fall "-F, Marker in Kommentarzeile (bleibt bei -F stehen)" ab -F "$W/f.txt"
printf 'Betreff\n\nRumpf.\n# ------------------------ >8 ------------------------\nnach der Schere %s\n' "$M" > "$W/f.txt"
fall "-F, eigene Scheren-Zeile, Marker danach (git behaelt ihn)" ab -F "$W/f.txt"
nachricht 'Betreff\n\nRumpf ohne Marker.\n'
INHALT_MIT_MARKER=ja
fall "-v, Marker nur im gestagten Inhalt"     an -v
fall "-v -v, Marker nur im Inhalt (zwei Diffs)" an -v -v
INHALT_MIT_MARKER=
nachricht 'Betreff\n\nRumpf mit %s.\n'
fall "-v, Marker im Rumpf"                    ab -v
nachricht '%s Betreff\n\nRumpf ohne Marker.\n'
INHALT_MIT_MARKER=ja
fall "-v, Marker im Betreff und im Inhalt"    an -v
INHALT_MIT_MARKER=

if [ "$FEHLER" -ne 0 ]; then
    echo "commit-msg-Selbstprobe ROT: $FEHLER von $FAELLE Faellen falsch ($HOOKS/commit-msg)"
    exit 1
fi
echo "commit-msg-Selbstprobe gruen: $FAELLE Faelle mit echten git-commit-Aufrufen (-m, -F, -v, -v -v) gegen $HOOKS/commit-msg"
