# Release-Ritual

## Grundsätze

**Version und Notizen im selben Commit.** Ein Tag ohne gepflegten
CHANGELOG-Eintrag zeigt dem Nutzer die Angaben der Vorversion — inklusive
falscher Risiko-Kennzeichnung.

**Die Version steht an ZWEI Stellen** und wird gemeinsam gezogen:
`web/src/lib/version.ts` (`APP_VERSION`) und `backend/app/config.py`
(`app_version`). Der Rauchtest prüft den Gleichstand selbst („API und Oberfläche
melden dieselbe Version") — der häufigste Deploy-Fehler ist, dass nur eines der
beiden Images neu ist.

**Risiko ehrlich kennzeichnen** — als Zusatz in der CHANGELOG-Überschrift:

| Stufe | Bedeutung |
|---|---|
| `gefahrlos` | nur Code, keine Migration |
| `backup` | Light-Migration im Spiel — Backup vor dem Deploy empfohlen |
| `breaking` | Hinweise beachten, Backup zwingend |

**Im Zweifel die vorsichtigere Stufe.** Auch eine reine Index-Migration ändert
keine Daten und bekommt trotzdem `backup`, damit die Kennzeichnung verlässlich
bleibt. Ein Flag, das mal so und mal so gemeint ist, wird ignoriert.

> Diese Kennzeichnung war bis v1.4.0 gepflegt und ist danach eingeschlafen,
> obwohl seither fast jede Auslieferung eine Light-Migration mitbringt
> (Abgleich 15.08.2026). Sie ist wieder verbindlich.

**Autonomes Release ist freigegeben**, wo das Release-Gate keine
Owner-Freigabe verlangt, alle Gates grün sind und der Stand real im
Teststand verifiziert ist. **Wann das Release-Gate eine Freigabe verlangt,
steht NUR im Schwellen-Inventar der `CLAUDE.md`** (Zeile „Release-Gate“) —
hier bewusst keine Aufzählung (eine Schwelle hat genau einen Eigentümer,
v1.9.0).

**Vor jeder Release-Serie den letzten Lauf jedes Zeitplan-Workflows lesen**
(aus der Vorlage, Abgleich v1.17.2) — bei uns `security-scan.yml` und
`smoke.yml`, je eine Zeile, Exit ohne Pipe:

    gh run list --workflow <workflow> --limit 1 --json conclusion,createdAt,headSha

Ein roter Zeitplan-Lauf wird ein Issue, bevor getaggt wird. Hausbeleg (#105):
Der Security-Scan war seit seiner Einrichtung in 9 von 9 Läufen rot, und
niemand hatte einen gelesen — kein Release hing davon ab. Das ist die dritte
Wächterfrage (`lehren.md` §10) als Schritt; ein Wächter ist es nicht, solange
kein Skript ihn erzwingt.

## Ablauf

1. **Alles gelandet**, CI grün auf dem gelandeten Endstand — **EIN
   `workflow_dispatch`**, run-id-gepinnt beobachtet.

   **„Kein Lauf zum `headSha` gefunden“ ist ROT, nicht „noch nicht da“**
   (v1.14.0/v1.14.1). Der Nachweis lautet: Es gibt einen grünen Lauf ZU DIESEM
   Commit — nicht „oben in der Liste steht etwas Grünes“. Ein Lauf, den es nie
   gab, hinterlässt nichts; der grüne Lauf des Vorgängers steht dann ganz oben
   und wird als der eigene gelesen. Probe:

       gh run list --repo <repo> --limit 5 --json headSha,conclusion,databaseId

   **Owner-Skripte werden auf dem Owner-Host geprobt** (`lehren.md` §18)
   — mit dem Kommando aus dem Ritual, Exit-Code ohne Pipe **und Hash der
   Zieldatei vorher und nachher**; der Exit-Code allein ist als Kriterium
   widerlegt. `deploy.sh` läuft auf dem Server des Owners; wir können es hier
   nur nachstellen. Jede Aussage über den Deploy wird als Nachstellung
   benannt, und Kommandos, die der Owner auf dem Server tippt, stehen in der
   Deploy-Anweisung in genau der Form, in der sie geprobt wurden — eine nicht
   geprobte Zeile steht dort als Einschränkung.
2. **Version an beiden Stellen** ziehen.
3. **CHANGELOG-Eintrag** ganz oben: Titel, Risiko-Stufe, was der Nutzer merkt.
   In seiner Sprache, nicht in der des Codes: *was er merkt*, nicht welche
   Funktion umgebaut wurde.
4. **„Was ist neu"-Notizen generieren** (Issue #99): `sh
   scripts/generate-whatsnew.sh` — liest Version + den gerade geschriebenen
   CHANGELOG-Abschnitt (Schritte 2+3 müssen also VOR diesem Schritt stehen)
   und schreibt `web/src/lib/whatsnew.generated.ts` neu. **Englisch dazu von
   Hand pflegen:** `web/src/lib/whatsnew.en.json` auf die neue Version
   bringen und den Text schreiben — der CHANGELOG ist nur deutsch, maschinell
   übersetzen wollen wir nicht. Ohne diesen Schritt (oder ohne den
   EN-Nachtrag) schlägt `npm run check:whatsnew` in Schritt 5 an.
5. **Gates**: `sh scripts/gates.sh all` — darin hängt seit #99 auch der
   Wächter für den vorigen Schritt.
6. **Rauchtest**: `sh scripts/smoke.sh` — frischer Stapel, damit nicht ein
   veralteter Stand geprüft wird.
7. **Teststand**: `sh scripts/teststand.sh up` und die geänderten Stellen im
   Browser ansehen. Bei UI-Änderungen **mobil** mitprüfen (Mobile-First-PWA).
8. **Keine Datei geht still verloren** (Vorlage v1.15.2/v1.15.4, bei uns
   `lehren.md` §21). Vor dem Tag:

       liste=$(git -c core.quotepath=off log -m --no-renames --diff-filter=D --name-only --format= <letzter-tag>..HEAD) || exit 1
       printf '%s\n' "$liste" | sort -u

   Die **Zuweisung** trägt den Exit von `git log` — eine Pipe verschluckte ihn,
   und ein falscher Tag-Name sähe aus wie „nichts verloren“. `log` statt `diff`
   (sieht auch eine Datei, die nach dem Tag angelegt und wieder gelöscht wurde),
   `-m` (Löschungen in einer Merge-Konfliktauflösung; bringt auch Löschungen
   früherer Releases mit, wenn ein Merge-Elternteil älter ist als der Tag),
   `--no-renames` (verschobene Dateien) und `core.quotepath=off` (Namen mit
   Umlaut) sind Pflicht. Je Pfad, der in `HEAD` fehlt (`git cat-file -e
   HEAD:<pfad>`; fehlte er schon vor dem Tag: `git cat-file -e
   <letzter-tag>:<pfad>`), eine eigene Zeile ohne Pipe:

       git grep -n -i -F "<dateiname>" -- . ":!CHANGELOG.md"

   Enthält der Name ein Nicht-ASCII-Zeichen oder ein Leerzeichen, zusätzlich
   eine Zeile mit der **URL-kodierten Form**; verschwindet ein ganzes
   Verzeichnis, zusätzlich der Verzeichnisname **ohne** abschließendes `/`.
   Exit 0 heißt: Es gibt noch Verweise — **ROT**, außer der Verweis ist gewollt
   und im CHANGELOG begründet; Exit 1: kein Verweis; alles andere: Kommando
   kaputt, ROT. Jede gelöschte oder verschobene Datei steht mit Grund im
   CHANGELOG — ohne Eintrag ROT. **Grenzen:** Verweise, die per Variable
   zusammengesetzt sind oder außerhalb des Repos stehen, findet die Suche
   nicht. **Das ist ein Ritualschritt, kein Wächter** — wir haben kein
   Release-Skript, also macht sein Auslassen nichts rot (`lehren.md` §10).
   **Teilstring-Rauschen:** Die Suche nach dem Dateinamen trifft Namen mit
   demselben Ende. Gemessen am Stand `2417912` für die gelöschte
   `backend/app/api/v1/images.py`, mit dem Kommando oben: 14 Treffer in 9
   Dateien, jeder ein Verweis auf `card_images.py`, `catalog_images.py` oder
   `sealed_images.py`; mit `-w` 0 Treffer (Exit 1). Einen Verweis mit Pfad
   (`v1/images.py`) findet auch `-w`, weil `/` kein Wortzeichen ist. Treffer
   trotzdem einzeln ansehen, nicht zählen.
   Einmal rückwirkend gefahren am 28.09.2026: 98 gelöschte Pfade seit
   `v0.1.0-pre`, **0 ungewollte Verweise** (zwei gewollte Nennungen mit dem Satz
   „Datei inzwischen entfernt“ bzw. „toter Code“).
9. **CI für den Release-COMMIT, dann Tag.** Der Versionssprung aus Schritt 2
   entsteht NACH dem Lauf aus Schritt 1 — vor dem Tag deshalb genau ein
   `workflow_dispatch` auf dem Release-Commit, nachgewiesen für dessen
   `headSha` („kein Lauf gefunden“ ist ROT, Schritt 1). **Nach dem Warten wird
   das ERGEBNIS abgefragt, nicht der Exit des Wartens gelesen:**
   `gh run watch <id> --exit-status` endet mit 0, wenn der Lauf
   **abgebrochen** wurde; maßgeblich ist `gh run view <id> --json
   status,conclusion`, und dieser Wert gehört in den Bericht, nicht das Wort
   „grün“ (`lehren.md` §5). **Eine Regel, die nur eine Einstellung einhält,
   die man nicht im Blick hat, ist nicht eingehalten:** Fällt beim
   Zusammenfassen von Commits der Überspring-Marker heraus, löst der Push einen
   zweiten Lauf aus — dass am Ende trotzdem nur einer läuft, verdankt sich dann
   `concurrency`, nicht der Regel. **Jede Zahl in Commit-Nachricht oder
   CHANGELOG kommt aus einem Kommando** (Testzahlen aus der Ausgabe des
   Läufers, an beiden Ständen), nie aus einer Addition im Kopf; eine Zusage
   über einen Wächter vor seinem Rot-Beweis heißt „soll fangen“, nicht
   „fängt“. Verlangt das Release-Gate eine Owner-Freigabe (Schwellen-Inventar
   der `CLAUDE.md`), vorher fragen. Dann Tag + `gh release create`, Notizen
   aus dem CHANGELOG-Abschnitt.
10. **Deploy-Anweisung an den Owner** — deployen macht immer er.

## Notizen schreiben

Was der Nutzer merkt, nicht was umgebaut wurde:

> ❌ „`variant_usd` liefert jetzt zusätzlich den Varianten-Schlüssel"
> ✅ „Der angezeigte TCGplayer-Preis war der Basispreis der Karte, nicht der der
> besessenen Variante — bei einer Pokéball-Karte stand $0.25 neben einem Wert,
> der aus $0.60 kam."

**Nach einem Folge-Slice gegenlesen.** Ein Eintrag kann durch den nächsten Slice
unwahr werden.

## Nach dem Ausliefern

**Prüfen, ob es wirklich läuft** — `curl <server-ip>:3010/health` sagt mehr als
eine Versionsanzeige: Es liefert die Backend-Version, die mit der Oberfläche
übereinstimmen muss.

**Rückstands-Check: „läuft es?“ beantwortet nicht „ist das Laufende
aktuell?“** (Vorlage v1.13.0/v1.14.0). Nach jedem Deploy und bei jedem
Abgleich einmal: `curl <server-ip>:3010/health` nennt die laufende Version —
sie muss dem letzten Tag entsprechen. Eine laufende alte Version ist kein
Ausfall und fällt deshalb niemandem auf (anderswo gemessen: 17 Tage stiller
Rückstand; eine Site antwortete vier Wochen tadellos und war nicht der
aktuelle Stand). Das ist eine **Nachstellung** im Sinn von `lehren.md` §18:
Wir sehen die Version über HTTP, nicht den Server. Automatisch wird der Check
erst mit der Betriebs-Überwachung (#54) — die ohnehin laufende
Erreichbarkeitsprüfung vergleicht dann die Version aus `/health` mit dem
letzten Git-Tag, null zusätzliche Läufe. Bis dahin ist der `curl` der
manuelle Ersatz, und die Reihenfolge Tag (Schritt 9) vor Ausliefern
(Schritt 10) ist genau deshalb Pflicht: Ohne Tag hat der Check nichts zu
vergleichen.
