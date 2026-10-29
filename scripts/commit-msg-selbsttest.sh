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
# ab. In jedem Fall hier schreibt git selbst die Datei, die der Hook liest
# (bei -m und -F aus dem vorgegebenen Text, bei -v samt Schere und Diff).
#
# WAS SIE PRUEFT, je Fall in einem Wegwerf-Repo unter $TMPDIR:
#   "ab": git commit scheitert, es entsteht kein Commit, die Meldung des Hooks
#         steht in der Ausgabe;
#   "an": git commit gelingt, es entsteht genau ein Commit, und die
#         GESPEICHERTE Nachricht ist genau die erwartete (ein Hook, der die
#         Nachricht umschreibt, faellt so auf).
# Dazu eine Mindestzahl ausgefuehrter Faelle: Fehlen Faelle, ist sie rot.
# Der Marker wird im Skript zusammengesetzt, damit diese Datei ihn nicht
# woertlich traegt.
#
# GRENZE: die des Hooks (siehe dort) — wer die drei Scheren-Zeilen von git
# selbst in die Nachricht schreibt, umgeht ihn. Kein Fall hier prueft das, mit
# Absicht: Er wuerde die Grenze als erwuenschtes Verhalten festschreiben.

set -u
LC_ALL=C
export LC_ALL
# gates.sh exportiert MSYS_NO_PATHCONV=1; dann bekommt das native git unter
# Git Bash "/c/..." woertlich und legt das Wegwerf-Repo unter C:\c\ an, die
# Probe bricht ab (gemessen 24.10.2026). Hier braucht git die Umsetzung.
unset MSYS_NO_PATHCONV MSYS2_ARG_CONV_EXCL
# Abschottung: kein fremdes Repo ueber die Umgebung (mit gesetztem GIT_DIR
# schrieb die Probe sonst Commits und Konfiguration in ein fremdes Repo und
# meldete gruen; Panel #112), keine Nutzer- oder System-Konfiguration
# (commit.verbose, commit.cleanup, commit.template verschoeben die Faelle).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
      GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT \
      GIT_CEILING_DIRECTORIES GIT_EDITOR GIT_TEMPLATE_DIR
GIT_CONFIG_GLOBAL=/dev/null
GIT_CONFIG_NOSYSTEM=1
export GIT_CONFIG_GLOBAL GIT_CONFIG_NOSYSTEM

MINDEST=36

HIER=$(cd "$(dirname "$0")/.." && pwd)
HOOKS=${1:-$HIER/.githooks}
[ -f "$HOOKS/commit-msg" ] || { echo "Aufruffehler: $HOOKS/commit-msg fehlt" >&2; exit 2; }
HOOKS=$(cd "$HOOKS" && pwd)

BASIS=${TMPDIR:-/tmp}
W=$(mktemp -d "$BASIS/commit-msg-probe.XXXXXX") || exit 2
trap 'rm -rf "$W"' EXIT INT TERM
case $W in *"'"*) echo "Aufruffehler: Hochkomma in \$TMPDIR" >&2; exit 2 ;; esac

M="[skip"" ci]"          # der Ueberspring-Marker, zusammengesetzt
git init -q "$W/repo" || exit 2
cd "$W/repo" || exit 2
git config user.email probe@example.invalid
git config user.name Probe
git config core.hooksPath "$HOOKS"
git config core.autocrlf false
git config commit.gpgsign false
printf 'start\n' > datei.txt
printf 'start\n' > zweite.txt
git add datei.txt zweite.txt
git -c core.hooksPath=/dev/null commit -q -m "Start" || exit 2
[ "$(git rev-list --count HEAD)" -eq 1 ] || { echo "Aufruffehler: Wegwerf-Repo nicht frisch" >&2; exit 2; }

# Editor-Ersatz: setzt $W/nachricht.txt VOR die Vorlage, die git anlegt;
# Scheren-Zeile und Diff schreibt git selbst.
{
    echo '#!/bin/sh'
    echo "cat '$W/nachricht.txt' \"\$1\" > \"\$1.neu\" && mv \"\$1.neu\" \"\$1\""
} > "$W/editor.sh"
nachricht() { printf "$1" "$M" > "$W/nachricht.txt"; }   # %s = Marker

FEHLER=0
FAELLE=0
# fall <Name> an|ab <erwartete gespeicherte Nachricht, nur bei "an"> <git-commit-Argumente>
fall() {
    name=$1; erwartet=$2; soll=$3; shift 3
    FAELLE=$((FAELLE + 1))
    printf 'zeile %s\n' "$FAELLE" >> datei.txt
    [ "${INHALT_MIT_MARKER:-}" = ja ] && printf 'Inhalt %s\n' "$M" >> datei.txt
    git add datei.txt
    vorher=$(git rev-list --count HEAD)
    GIT_EDITOR="sh '$W/editor.sh'" git commit -q "$@" > "$W/aus.txt" 2>&1
    rc=$?
    nachher=$(git rev-list --count HEAD)
    if [ "$erwartet" = an ]; then
        ist=$(git log -1 --format=%B)
        [ "$rc" -eq 0 ] && [ "$nachher" -eq $((vorher + 1)) ] && [ "$ist" = "$soll" ] && return 0
        [ "$ist" = "$soll" ] || printf '    gespeichert: %s\n    erwartet:    %s\n' "$ist" "$soll" >> "$W/aus.txt"
    else
        [ "$rc" -ne 0 ] && [ "$nachher" -eq "$vorher" ] && grep -q "Ueberspring-Marker" "$W/aus.txt" && return 0
    fi
    echo "  FALSCH: $name — erwartet '$erwartet', git commit rc=$rc, Commits $vorher -> $nachher"
    sed 's/^/    | /' "$W/aus.txt"
    FEHLER=$((FEHLER + 1))
}

NL='
'
# -m: Betreff erlaubt, ohne Marker erlaubt, jede Stelle ab Zeile 2 verboten
fall "-m, ohne Marker"                        an "Betreff${NL}${NL}Rumpf ohne Marker." -m "Betreff" -m "Rumpf ohne Marker."
fall "-m, Marker im Betreff"                  an "$M Betreff${NL}${NL}Rumpf ohne Marker." -m "$M Betreff" -m "Rumpf ohne Marker."
fall "-m, Marker im Rumpf"                    ab "" -m "Betreff" -m "Rumpf mit $M."
fall "-m, Marker in Zeile 2 (ohne Leerzeile)" ab "" -m "Betreff${NL}Zweite Zeile $M"
fall "-m, Marker in Zeile 9"                  ab "" -m "Betreff" -m "a${NL}b${NL}c${NL}d${NL}e${NL}f${NL}Spaet $M"
# #116: je ein Fall für die Hook-Varianten, die die Probe vorher grün ließ
# (gemessen vom Blindprüfer zu #112): Ablehnung reiner Betreff-Nachrichten,
# Prüfung nur bis Zeile 9 bzw. nur des ersten Absatzes, grep -w, Muster ohne
# eckige Klammern.
fall "-m, nur Betreff"                        an "Betreff" -m "Betreff"
VIELE=$(i=0; while [ $i -lt 30 ]; do printf 'zeile %s\n' $i; i=$((i + 1)); done)
fall "-m, Marker in Zeile 40, dritter Absatz" ab "" -m "Betreff" -m "Absatz eins" -m "Absatz zwei${NL}${VIELE}${NL}Spaet $M"
fall "-m, Marker direkt an einem Wort"        ab "" -m "Betreff" -m "foo$M bar"
fall "-m, die Woerter ohne Klammern"          an "Betreff${NL}${NL}Rumpf mit skip ci ohne Klammern." -m "Betreff" -m "Rumpf mit skip ci ohne Klammern."
# jede Form des Musters, auch gross geschrieben
for v in "skip ci" "skip-ci" "ci skip" "ci-skip" "no ci" "no-ci" \
         "skip actions" "skip-actions" "actions skip" "actions-skip" "SKIP CI" "No-Ci"; do
    fall "-m, Form [$v] im Rumpf"             ab "" -m "Betreff" -m "Rumpf mit [$v]."
done
# -F: git laesst Kommentar- und Scheren-Zeilen stehen, der Hook prueft sie mit
printf 'Betreff\n\nRumpf mit %s.\n' "$M" > "$W/f.txt"
fall "-F, Marker im Rumpf"                    ab "" -F "$W/f.txt"
printf 'Betreff\n\n# Kommentar\n# Kommentar\n# Kommentar mit %s\n' "$M" > "$W/f.txt"
fall "-F, Marker hinter Kommentarzeilen (bleiben bei -F stehen)" ab "" -F "$W/f.txt"
printf 'Betreff\n\nRumpf.\n# ------------------------ >8 ------------------------\nnach der Schere %s\n' "$M" > "$W/f.txt"
fall "-F, eigene Scheren-Zeile, Marker danach (git behaelt ihn)" ab "" -F "$W/f.txt"
printf 'Betreff\n\n# ------------------------ >8 ------------------------\n# Do not modify or remove the line above.\nnach zwei Scheren-Zeilen %s\n' "$M" > "$W/f.txt"
fall "-F, nur zwei der drei Scheren-Zeilen, Marker danach" ab "" -F "$W/f.txt"
printf 'Betreff\n\nZitat:\ndiff --git a/x b/x\n+%s\n-alt\n+neu\n' "$M" > "$W/f.txt"
fall "-F, zitierter Diff im Rumpf"            ab "" -F "$W/f.txt"
# #116: Schnitt nur an einem Teil der drei Scheren-Zeilen, an anderen
# Kommentarzeilen von git, und Zitatzeilen — überall bleibt der Marker in der
# gespeicherten Nachricht stehen, der Hook muss ablehnen. Hinter dem Marker
# stehen noch zwei Zeilen: Der Hook sucht die Schere nur, solange danach zwei
# Zeilen folgen — ohne sie erreichte ein Schnitt-Mutant die Stelle nie
# (gemessen beim Bau, Mutant „nur letzte Hinweiszeile" blieb grün).
printf 'Betreff\n\nRumpf.\n# Do not modify or remove the line above.\n# Everything below it will be ignored.\nnach zwei Hinweiszeilen %s\nweiter\nweiter\n' "$M" > "$W/f.txt"
fall "-F, nur die zwei Hinweiszeilen ohne Schere" ab "" -F "$W/f.txt"
printf 'Betreff\n\nRumpf.\n# Everything below it will be ignored.\nnach einer Hinweiszeile %s\nweiter\nweiter\n' "$M" > "$W/f.txt"
fall "-F, nur die letzte Hinweiszeile"        ab "" -F "$W/f.txt"
printf 'Betreff\n\n# Please enter the commit message for your changes.\nnach dem Vorlagentext %s\nweiter\nweiter\n' "$M" > "$W/f.txt"
fall "-F, Vorlagentext von git, Marker danach" ab "" -F "$W/f.txt"
printf 'Betreff\n\n> Zitat mit %s\n' "$M" > "$W/f.txt"
fall "-F, Marker in einer Zitatzeile"         ab "" -F "$W/f.txt"
# -v: git haengt Schere und Diff an und schneidet sie nach dem Hook ab
nachricht 'Betreff\n'
fall "-v, nur Betreff (#116)"                 an "Betreff" -v
nachricht 'Betreff\n\nRumpf ohne Marker.\n'
INHALT_MIT_MARKER=ja
fall "-v, Marker nur im gestagten Inhalt"     an "Betreff${NL}${NL}Rumpf ohne Marker." -v
INHALT_MIT_MARKER=
nachricht 'Betreff\n\nRumpf mit %s.\n'
fall "-v, Marker im Rumpf"                    ab "" -v
nachricht '%s Betreff\n\nRumpf ohne Marker.\n'
INHALT_MIT_MARKER=ja
fall "-v, Marker im Betreff und im Inhalt"    an "$M Betreff${NL}${NL}Rumpf ohne Marker." -v
INHALT_MIT_MARKER=
# -v -v: zweiter Diff mit der UNGESTAGTEN Aenderung, Marker nur darin
printf 'Ungestagt %s\n' "$M" >> zweite.txt
nachricht 'Betreff\n\nRumpf ohne Marker.\n'
fall "-v -v, Marker nur im ungestagten Diff"  an "Betreff${NL}${NL}Rumpf ohne Marker." -v -v
git diff --quiet zweite.txt && { echo "  FALSCH: -v -v-Fall ohne ungestagte Aenderung"; FEHLER=$((FEHLER + 1)); }

# awk scheitert: der Hook muss ablehnen, nicht ungeprueft durchlassen
mkdir "$W/kaputt" && printf '#!/bin/sh\nexit 2\n' > "$W/kaputt/awk" && chmod +x "$W/kaputt/awk" || exit 2
FAELLE=$((FAELLE + 1))
printf 'zeile %s\n' "$FAELLE" >> datei.txt
git add datei.txt
vorher=$(git rev-list --count HEAD)
PATH="$W/kaputt:$PATH" git commit -q -m "Betreff" -m "Rumpf ohne Marker." > "$W/aus.txt" 2>&1
rc=$?
if [ "$rc" -eq 0 ] || [ "$(git rev-list --count HEAD)" -ne "$vorher" ] || ! grep -q "nicht lesen" "$W/aus.txt"; then
    echo "  FALSCH: awk scheitert — erwartet 'ab' mit Lesefehler, git commit rc=$rc"
    sed 's/^/    | /' "$W/aus.txt"
    FEHLER=$((FEHLER + 1))
fi

if [ "$FAELLE" -lt "$MINDEST" ]; then
    echo "commit-msg-Selbstprobe ROT: nur $FAELLE Faelle ausgefuehrt, mindestens $MINDEST erwartet"
    exit 1
fi
if [ "$FEHLER" -ne 0 ]; then
    echo "commit-msg-Selbstprobe ROT: $FEHLER von $FAELLE Faellen falsch ($HOOKS/commit-msg)"
    exit 1
fi
echo "commit-msg-Selbstprobe gruen: $FAELLE Faelle (mindestens $MINDEST) mit echten git-commit-Aufrufen (-m, -F, -v, -v -v), gespeicherte Nachricht je angenommenem Fall verglichen, gegen $HOOKS/commit-msg"
