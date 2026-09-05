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

**Autonomes Release ist freigegeben** für Slices **ohne R4-Auslöser**, wenn
alle Gates grün sind und der Stand real im Teststand verifiziert ist. **R4
(Tabelle in `CLAUDE.md`) braucht Owner-OK vor dem Tag.** Die Auslöser stehen
NUR dort — hier bewusst keine Aufzählung (eine Schwelle hat genau einen
Eigentümer, v1.9.0).

## Ablauf

1. **Alles gelandet**, CI grün auf dem gelandeten Endstand — **EIN
   `workflow_dispatch` je Slice** (CI-Dauerregel 02.09.2026, CLAUDE.md), den Lauf
   **run-id-gepinnt** beobachten (`gh run watch <id> --exit-status`), nie über
   eine Listenposition.
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
8. Tag + `gh release create`, Notizen aus dem CHANGELOG-Abschnitt.
9. **Deploy-Anweisung an den Owner** — deployen macht immer er.

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

**Rückstands-Check** (Vorlage v1.13.0, bei uns vertagt auf #54): Sobald die
Betriebs-Überwachung steht, vergleicht die ohnehin laufende
Erreichbarkeitsprüfung die Version aus `/health` mit dem letzten Git-Tag —
**null zusätzliche Läufe**. Beleg aus der Vorlage: Eine Site antwortete vier
Wochen tadellos und war nicht der aktuelle Stand; alle Prüfungen grün, das
Monitoring stumm. Bis #54 gebaut ist, ist der `curl` oben der manuelle
Ersatz — und die Reihenfolge Tag (Schritt 8) vor Ausliefern (Schritt 9) ist
genau deshalb Pflicht: Ohne Tag hat der Check nichts zu vergleichen.
