# Review-Panel: drei Stimmen über denselben Diff

Verbindlich nach **jedem nicht-trivialen Slice**, vor dem Landen. Zweck ist
**Diversität im Urteil**, nicht Token-Ersparnis.

> Die **Werkzeuge** (Skripte, Docker-Image, OpenRouter-Zugang) liegen bewusst
> **außerhalb dieses Repos** unter `model-panel/` neben dem Projektordner —
> dort liegen Zugangsdaten, und die haben in einem Repo nichts verloren. Diese
> Datei ist die **Anleitung**: Sie muss auch dann gelten, wenn die Werkzeuge
> einmal anders heißen.

## Die drei Stimmen

**Stimme 1 — blinde Erststimme (Claude, Subagent, `model: opus`).**
Ein **frischer** Reviewer-Subagent, der **nur Diff und Repo** bekommt: nicht den
Bau-Brief, nicht den Bericht des Bauers, nicht die Diskussion. Er darf Sonden
fahren (Tests, Messungen), aber nichts ändern.

Das ist die wichtigste Regel des Verfahrens. Wer den Bau begleitet hat — auch
der Hauptagent — liest die **Absicht** statt des Codes.

**Baut der Hauptagent ausnahmsweise selbst, ist die blinde Erststimme
zwingend** (Owner-Freigabe 15.08.2026): Ohne sie gibt es keine unabhängige
Prüfung, nur eine Selbstbestätigung.

**Stimme 2 — GPT über die Codex-CLI**, read-only, `model_reasoning_effort=high`.
Strenge-Bias: findet Echtes, braucht Arbitrierung. Sieht den lokalen Arbeitsbaum
nicht — **erst einen Prüf-Zweig pushen**, dann über den GitHub-Connector
reviewen lassen:

```bash
git push -f origin HEAD:review/<issue>-<kurzname>
```

Im Prompt den Zweignamen nennen **und** ausdrücklich schreiben, dass lokaler
Dateizugriff nicht funktioniert und nur der Connector zu benutzen ist — sonst
verbrennt Codex Züge an `git`-Aufrufen, die an der Namespace-Sperre scheitern.
Der Zweig ist Wegwerfware und wird nach dem Landen gelöscht.

**Stimme 3 — DeepSeek V4 Pro**, diff-only, günstig. Irrt Richtung zu-streng und
liest gelegentlich die Vorher-Seite eines Diffs; die Treffer sind echt.
**Budget: bis 2 $/Monat ohne Rückfrage** (Owner-Freigabe 15.08.2026), darüber
melden. Bei `402` (Guthaben leer) gilt der Ausfall-Weg unten.

## Ablauf

1. Prüf-Zweig pushen (Stimme 2 braucht ihn).
2. **Alle drei parallel starten**, nicht nacheinander — zusammen 20–40 Minuten,
   sequenziell ein Vielfaches.
3. **Arbitrieren.** Jeden Blocker **am Code oder an der laufenden App
   reproduzieren**. Prüfer-Konvergenz ersetzt keine Reproduktion; Mehrheit
   entscheidet nie allein.
4. **Nacharbeit** an denselben Subagenten, der gebaut hat (Kontext bleibt) — mit
   dem, was **bestätigt** wurde, und mit ausdrücklich **abgeräumten**
   Fehlbefunden.
5. **Panel-Kommentar** am Issue, Form nach `panel-kommentar.md`.

**Sonden-Falle:** Erwartungswerte **vor** der Sonde fixieren. Eine Sonde kann
ihre eigenen Befunde erzeugen — am Teststand ist das schon passiert (ein
Probe-`PUT` schrieb Unsinn in die Einstellungen und legte danach jeden
Settings-Aufruf lahm).

## Prüfaufträge, die sich bewährt haben

Nicht „prüfe den Diff", sondern **eine Behauptung zum Widerlegen**:

> Die Behauptung lautet: ⟨X⟩. Versuche das zu WIDERLEGEN. Denk an Umwege: ⟨konkrete Kandidaten⟩.

Dazu:

- **Nennen, was schon geprüft und ohne Befund ist** — sonst laufen alle drei
  dieselben Wege ab.
- **Ausdrücklich erlauben, nichts zu finden.** Sonst wird etwas erfunden.
- **Je Fund: Schwere (BLOCKER/WICHTIG/KLEIN), Datei:Zeile, Nachweis.** Kein
  Nachweis, kein Fund.
- Abschluss: **ein Satz Gesamturteil** (landen ja/nein).

Fragen, die hier überdurchschnittlich oft etwas gefunden haben:

- „Wer ruft den geänderten Code auf? Prüfe **jeden** Aufrufer."
- „Bricht die neue Strenge einen legitimen Ablauf?" (fand den #55-Blocker)
- „Welche einzelne Zeile könnte ich löschen, ohne dass ein Test rot wird?"
- „Enthalten die Testdaten den Fall überhaupt, um den es geht?"
- „Wird der geänderte Code auch **serverseitig** aufgerufen, nicht nur vom
  Client?" (fand den #55-MAJOR: der Scan baut dasselbe Schema aus OCR-Text)

## Verhältnismäßigkeit — abschließende Liste

**Ohne Panel nur:** reine Testinfrastruktur **ohne Verhaltensänderung**, Doku,
Typisierung ohne Verhaltensänderung. **Alles andere bekommt das Panel; im
Zweifel das Panel.**

Die Liste ist abschließend, nicht beispielhaft: „Ist das trivial?" ist genau die
Frage, bei der man sich unter Zeitdruck selbst überzeugt.

**Immer volles Panel** bei: Migrationen, Auth/Berechtigungen, allem, was Geld
oder Werte berechnet, und allem, was nach außen geht.

**Sonderfall:** Eine Testinfrastruktur-Scheibe, die als **Sicherheitsnetz**
gemeldet wird, ist nicht trivial — sie braucht mindestens den Rot-Beweis über
die ganze Suite (`bau-brief.md`).

## Wenn eine Stimme ausfällt

Werkzeug nicht verfügbar, kein Guthaben, Dienst down: **mit zweien weitermachen,
im Kommentar vermerken und es dem Owner sagen.** Nicht stillschweigend
reduzieren, und die fehlende Stimme nachholen, solange der Slice nicht
ausgeliefert ist.

Ein Slice ohne vollständiges oder ausdrücklich vermerkt-verkürztes Panel gilt
als **nicht geprüft** und wird nicht ausgeliefert.
