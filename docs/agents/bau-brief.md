# Bau-Brief: Vorlage für Aufträge an Bau-Subagenten

> **Der Bau-Brief ist die einzige Leitplanke, die den Bauer erreicht.**
> Regeln im Repo erreichen ihn nicht: Ein Bau-Subagent arbeitet den Brief ab,
> nicht `docs/agents/`. In fünf Projekten gemeldet, zweimal ist genau daran
> eine Pflichtregel gescheitert — sie stand im Repo und fehlte im Brief.
>
> Deshalb hat der Brief ein **Pflicht-Gerüst**. Fehlt ein Block, ist der Brief
> nicht fertig. `scripts/bau-brief-pruefen.sh` hilft dabei: Es sucht die zehn
> Themen im ganzen Brief — ein fehlendes Thema ist ein starkes Signal, kein
> Beweis (der Wortschatz ist fest), ein Treffer nur ein Kandidat.

## Pflicht-Gerüst (Block 0 plus neun Blöcke, keiner leer)

```markdown
## 0 Risiko            Risiko: R<n> — Auslöser: ⟨bei R3/R4 der Auslöser aus
                        der Tabelle in CLAUDE.md; bei R0 der R0-Auslöser; bei
                        R2 „Normalfall, gegen die Auslöser-Tabelle geprüft"⟩
                        Basis: ⟨Repo-Pfad, Zweig, erwarteter Commit⟩ —
                        erster Schritt des Bauers ist, den eigenen Stand
                        gegen diesen Commit und den aktuellen Hauptzweig
                        abzugleichen
```

## Pflicht-Gerüst (Fortsetzung: die neun Themen-Blöcke)

```markdown
## 1 Auftrag            ⟨Issue-Nummer; was gebaut wird, in zwei Sätzen, bei
                          mehreren Teilen Reihenfolge und warum; darunter die
                          Abnahme als prüfbare Punkte, je Punkt womit belegt,
                          kein Fließtext⟩
## 2 Befund             ⟨bereits verifiziert — NICHT neu recherchieren; je
                          Punkt mit Datei:Zeile⟩
## 3 Konsumenten        ⟨WER RUFT DEN GEÄNDERTEN CODE AUF? Jeden nennen.
                          VORWÄRTS: welche Türen bekommt das Neue (Oberfläche,
                          Schnittstelle, Werkzeug, Export)? Und welche KNAPPE
                          GRÖSSE beansprucht der Slice (CI-Minuten, Guthaben,
                          Ports, Owner-Zeit), wer greift parallel danach?⟩
## 4 Sichtbares         ⟨ändert der Slice sichtbares Verhalten? Doku-Folge?⟩
## 5 Nachweis           ⟨Rot-Beweis je neuem Test, inkl. Verdrahtung, UND
                          Gegenprobe (der richtige Fall bleibt grün);
                          bei ganzen Suiten zwei Mutationen; je neuer
                          Bedingung/Verzweigung die gemessene TREFFERZAHL⟩
## 6 Prüf-Kommandos     ⟨ALLE, die die CI fährt — nicht nur die naheliegenden⟩
## 7 Fixtures           ⟨erfunden, nie aus dem Kontext übernommen⟩
## 8 Randbedingungen    ⟨Vordergrund, Zeitlimits, lokal committen, nicht pushen,
                          Umfang nicht erweitern; Einrichtung (Abhängigkeiten,
                          Dienste, Env-Werte) ist in einer LEEREN Umgebung
                          ausprobiert⟩
## 9 Prüffragen         ⟨ALLE Fragen unten: je Frage der FETT gesetzte
                          Fragesatz, WÖRTLICH — nicht der Erklärtext darunter —,
                          jede Frage BEGINNT EINE EIGENE ZEILE (nummeriert oder
                          als Aufzählung); JE EINE ZEILE Antwort — „trifft
                          nicht zu" ist eine gültige Antwort, Weglassen ist
                          keine, Umformulieren auch nicht⟩
```

**Die Form ist Teil der Regel, weil nur sie maschinell auffindbar ist.** Block 0
heißt wörtlich `Risiko: R<n> — Auslöser: …` (nicht `**R2** — Auslöser`), und
Block-Überschriften stehen nicht in Versalien. Gemessen in zwei Projekten: Ein
Brief mit inhaltlich vollständigem Block 0 fiel im Prüfskript als
`[KEIN TREFFER] Risiko` durch, weil das Risiko fett gesetzt war; ein Brief mit
`## 9 PRÜFFRAGEN` fiel durch, weil `grep -i` ohne passende Locale kein `Ü`
faltet. Das Skript entfernt Markdown-Auszeichnung vor der Suche, setzt seit
v1.15.0 die Locale selbst und hält jedes Umlaut-Muster auch byteweise
(`..?` statt `.`) — die v1.14.0-Fassung hatte das nur für 2 von 7 Mustern
geschafft, obwohl ihr Kommentar „analog" sagte (Rot-Beweis im CHANGELOG). Die
Form bleibt trotzdem die Regel, weil der nächste Leser des Briefs ein Skript
sein kann.

**Warum Block 9 existiert und nicht nur die Fragenliste:** Ein Projekt hat die
Prüffragen einen ganzen Slice lang nicht angewendet — sie standen seit dem
Abgleich in der eigenen `bau-brief.md`. Die Diagnose des Projekts trifft es:
*Das Prüfskript prüft Themen, nicht Fragen — und was das Skript nicht anmahnt,
fällt durch.* Als eigener Block fehlt er auffällig; als Liste im Fließtext
verschwindet er lautlos. Das ist §10 auf unsere eigene Neuerung angewandt:
Eine Regel, deren Auslassung nichts rot macht, ist eine Notiz.

**Block 3 ist der teuerste, wenn er fehlt** — in vier von fünf Projekten kam
darüber ein Fund, den sonst niemand hatte.

**Der Hauptagent baut in der Regel nicht selbst; baut er ausnahmsweise selbst
(kleiner Slice, kein Bauer verfügbar), gelten Gerüst und Panel unverändert —
es entfällt nur der Empfänger.** Die
zehn Themen (Block 0 bis 9) werden dann vor dem ersten Commit durchgegangen. Gemessen in einem
Projekt ohne Bau-Subagenten: Drei Themen (Konsumenten, Sichtbares,
Prüf-Kommandos) fehlten in allen drei realen Aufträgen — **obwohl der
Ausführende die Regeln kannte, teils selbst formuliert hatte.** Wissen war nie
das Problem; es fehlte der Moment, sie einzeln durchzugehen.

Eine gekürzte Eigenliste („nur die drei, die mir fehlen") ist dabei die falsche
Antwort: Sie schreibt den nächsten blinden Fleck fest — derselbe
Kurzfassung/Langfassung-Fehler eine Ebene tiefer. Ein gegenstandsloses Thema
kostet eine Zeile Begründung, und die ist billiger als eine selbst
zurechtgeschnittene Liste.

**Die Gliederung ist ein Vorschlag, die zehn THEMEN sind die Pflicht.** Ein
Brief, der sie als Aufzählung unter einer gemeinsamen Überschrift trägt, ist
vollständig — gemessen an einem echten Brief, den der Bauer gelesen und befolgt
hat. `scripts/bau-brief-pruefen.sh` sucht deshalb im ganzen Dokument.

**Das Skript beruht auf einer Asymmetrie — die ist der ganze Trick:**

- **Kein Treffer → starkes Signal, kein Beweis.** Keines der Suchwörter des
  Themas kommt vor. Der Wortschatz ist fest; bei `[KEIN TREFFER]` sucht der
  Arbiter das seltenste Einzelwort des eigenen Briefs zu diesem Thema nach.
- **Ein Treffer → unbelastbar.** Es kann Behandlung sein, Erwähnung, Verneinung,
  Nachbarwort oder wiederverwendete Floskel.

Deshalb behauptet es kein „vorhanden", sondern nennt **Kandidaten mit der
Fundzeile**. Du urteilst in Sekunden, statt den Brief zu lesen.

**Prüffragen werden gezählt, und zwar am Zeilenanfang.** Eine Frage zählt,
wenn eine Zeile — nach Leerraum, Nummer, Aufzählungszeichen und entfernter
Auszeichnung — mit den ersten zwei bis drei Wörtern ihres fetten Fragesatzes
beginnt („Schreibt dieser Fix", „Welchen Pfad benutzt"). **Deshalb beginnt im
Brief jede Frage auf einer eigenen Zeile**, nummeriert oder als Aufzählung;
eine Frage mitten in einer Zeile zählt als fehlend. Das Skript meldet
`Prüffragen: k von N`, die Fundzeile je Frage und bei `0 < k < N` die
fehlenden Nummern als `[UNVOLLSTAENDIG]` (Exit 1). **N ist die Zahl der Muster
in `FRAGEN`, nicht fest elf:** Eine projekteigene Frage (Nummer ab N+1,
`abgleich.md` der Vorlage, 2e) braucht **zwei Stellen**: eine Zeile in `FRAGEN` **und** die
Frage selbst hier unten — die Selbstprobe hält beide Zahlen gegeneinander,
prüft die eigene Frage mit und bricht ab, solange sie auseinanderlaufen. Vorher machte eine einzige
zitierte Frage das Thema zum Kandidaten, obwohl zehn fehlten; danach zählte je
Frage ein Einzelwort irgendwo im Brief, und Alltagsprosa („der Wert, der wahr
ist", „liest seine Daten") hielt fehlende Fragen für vorhanden (gemessen,
v1.15.2).

**Sieben Grenzen, alle gemessen; dieselbe Liste in derselben Reihenfolge steht
im Skriptkopf:**

- **Verneinungen** (aus fünf Projekten). „Einen Rot-Beweis brauchst du hier
  eher nicht" traf als Thema *Nachweis*. Schlimmer: Bei *Fixtures* traf
  ausgerechnet die Zeile, die die Regel **verletzt** („nimm die Testdaten aus
  dem, was da ist"). Das Skript markiert Verneinungswörter — als Hinweis,
  nicht als Urteil.
- **Nachbarwörter** (aus fünf Projekten). In deutscher Prosa trifft „doku"
  das Wort „dokumentieren", ein Dateipfad in einer Beschreibung liest sich wie
  ein Kommando.
- **Mehrwortige Muster am Zeilenumbruch** (eigene Messung, 08/2026). grep
  arbeitet zeilenweise; eine zweiwortige Alternative („sichtbares verhalten")
  über einem harten Umbruch trifft nicht. Die Einzelwort-Alternativen
  desselben Themas fangen das meist.
- **Floskel-Sättigung** (aus fünf Projekten). Eine Standard-Regelzeile
  („Fixtures erfunden, Rot-Beweis je Test, Gates im Vordergrund") sättigt
  **drei Themen auf einer Zeile**, ohne dass eines für *diesen* Slice
  durchdacht wäre. Dagegen hilft keine Verschärfung — jede liefe wieder auf
  Gliederungs-Urteile hinaus. Es bleibt eine Grenze, die man kennen muss.
- **Fester Wortschatz** (eigene Messung, v1.15.2). Ein Thema, das der Brief
  mit Wörtern behandelt, die das Skript nicht kennt, meldet `[KEIN TREFFER]` —
  bis v1.15.1 etwa ein Brief mit `cargo test && go vet` beim Thema
  *Kommandos*.
- **Wörtliche Pflichttexte** (eigene Messung, v1.15.2). Ein Suchwort, das in
  den elf Prüffragen oder in einem Satz steht, den jeder Brief trägt, erfüllt
  sein Thema in *jedem* Brief. Gemessen: „belegt" (Frage 6, Abnahme) und
  „gemessen" (Frage 10) hielten das Thema *Befund* in einem Brief ohne
  Befund-Block grün; mit dem Erklärtext der Fragen hielten „Prüfauftrag",
  „Befund", „Konsumenten", „Mutation", „Rot-Beweis" und „Testdatenbank" fünf
  Themen grün; in den Pflicht-Randbedingungen unten hielten „Prüf-Kommandos"
  und „endet mit einem Nachweis" *Kommandos* und *Nachweis* ohne Block 5 und 6
  grün (beide Sätze sind seitdem umformuliert); und drei Absätze unter
  „Typische Fallen" hielten *Sichtbares*, *Nachweis* und *Fixtures* ohne den
  jeweiligen Block grün, schon mit einer einzigen kopierten Falle (auch diese
  drei sind umformuliert). In den Brief gehört nur der
  fette Fragesatz; die Suchwörter sind trotzdem so gewählt, dass auch der
  Erklärtext kein Thema erfüllt. Das hält
  **`sh scripts/bau-brief-pruefen-selbsttest.sh`** — für ihren eingebauten
  Muster-Brief, nicht für jeden denkbaren Brief: Sie liest die Prüffragen,
  die Pflicht-Randbedingungen und die Fallen aus dieser Datei, ergänzt
  Alltagsprosa mit
  Nachbarwörtern, baut Briefe mit je einem fehlenden Thema oder einer
  fehlenden Frage und wird rot, wenn eines nicht gemeldet wird — nach jeder
  Änderung an Skript, Prüffragen, Pflicht-Randbedingungen oder Fallen laufen
  lassen (im Kind-Repo im lokalen Gate).
- **Prüffragen nur am Zeilenanfang** (eigene Messung, v1.15.2). Geprüft
  werden nur die ersten zwei bis drei Wörter jeder Frage am Zeilenanfang. Eine
  Frage, deren Rest umformuliert ist, zählt als vorhanden; eine Frage mitten
  in einer Zeile oder mit anderem Anfang zählt als fehlend (Fehlalarm); eine
  Prosazeile, die zufällig mit einem Fragenanfang beginnt, zählt als Frage
  (Durchlass — gegen `bau-brief.md` und `lehren.md` gemessen: kein solcher
  Treffer).

Ein sauberer Lauf heißt „nichts vergessen", nicht „Brief ist gut".

**Verbot aus Urteil vs. Grenze aus Umfang — der Unterschied ist wichtig:**

- **Schädlich: ein Verbot aus Urteil.** „Ich habe entschieden, dass das in
  Ordnung ist, sieh nicht hin." Real passiert: Der Brief verbot, eine bestimmte
  Funktion anzufassen — genau dort saß die Ein-Zeilen-Behebung eines Panel-Funds.
- **Legitim: eine Grenze aus Umfang oder Rechten.** „Außerhalb dieses Slices",
  „dafür fehlt dem Bauer der Token-Scope, ein Zugriff lässt den Push scheitern".
  Das gehört sachlich in **Block 8 (Randbedingungen)**, nicht in eine Warnung.

Beides teilt sich leicht dieselbe Formulierung. Wenn ein Brief regelmäßig eine
berechtigte Warnung erzeugt, gewöhnt man sich an sie — dieselbe Erosion, die
rote Läufe zum Wegklicken erzieht.


Ein Bau-Brief ist der Unterschied zwischen einem Slice, der beim ersten Panel
durchgeht, und einem, der drei Runden braucht. Die Punkte unten stehen alle,
weil ihr Fehlen einmal Geld gekostet hat.

---

## Es gibt genau ein Gerüst

Das **Pflicht-Gerüst oben** (Block 0 bis 9) ist das einzige. Bis v1.15.0 stand
an dieser Stelle zusätzlich ein älteres, kürzeres Muster unter der Überschrift
„Gerüst". Ihm fehlten unter anderem Risikoklasse, der Abgleich des eigenen Stands gegen den
erwarteten Commit, Nachweis, Fixtures und die Prüffragen. Wer es kopierte,
schrieb einen Brief, der nach der eigenen Definition unfertig war (Fremdprüfer
im v1.15.0-Panel). Jeder seiner Teile hat seit v1.15.1 diesen Platz:

| Altes Muster | Pflicht-Gerüst |
|---|---|
| Kopfzeile: Repo, Branch, HEAD | Block 0, Zeile „Basis" |
| Kopfzeile: „Baue Issue #…" | Block 1 |
| Befund (bereits verifiziert, nicht neu recherchieren — mit Datei:Zeile) | Block 2 |
| Auftrag, bei mehreren Teilen Reihenfolge und warum | Block 1 |
| Fallen, die ich kenne | **kein eigener Block** — jede Falle in den Block, den sie betrifft (eine Test-Falle in Block 5, eine Umgebungs-Falle in Block 8); Vorrat unter „Typische Fallen" unten |
| Pflichtfragen „Wer ruft den geänderten Code auf?" und „Ändert der Slice sichtbares Verhalten?" | Block 3 und Block 4 |
| Abnahme: prüfbare Punkte, kein Fließtext, je Punkt womit belegt | Block 1 |
| Randbedingungen: Test-Kommandos vollständig | Block 6 |
| Randbedingungen: Zeitlimits, Vordergrund, nicht pushen | Block 8 |

---

## Blöcke 3, 4 und 5 — warum sie drinstehen

**„Wer ruft den geänderten Code auf?"**
Die teuersten Fehler entstanden durch ungesehene Aufrufer: vier Auswahlfelder,
die nach einer Listen-Umstellung leer blieben; ein Frontend, das ein Feld noch
erwartete; ein Cockpit, dessen Hauptablauf durch eine neue Sperre starb. Der
Bauer soll die Konsumenten **auflisten**, nicht behaupten, es gäbe keine.

**„Ändert der Slice sichtbares Verhalten?"**
Wenn ja, gehört die Doku in denselben Slice. Sonst driftet sie, und der nächste
Agent glaubt ihr.

**„Rot-Beweis für jeden neuen Test."**
Den Fix sabotieren und zeigen, dass der Test fällt. **Auch die Verdrahtung
sabotieren** — die Frage lautet: „Welche einzelne Zeile könnte ich löschen, ohne
dass etwas rot wird?" Drei reale Fälle, in denen ein grüner Test nichts bewies,
stehen in `lehren.md`.

---

## Randbedingungen, die immer mitmüssen

*Diese Punkte stehen wörtlich in Block 8 jedes Briefs. Deshalb enthalten sie
kein Suchwort eines anderen Themas des Prüfskripts — sonst erfüllten sie jenes
Thema in jedem Brief (gemessen: zwei Suchwörter anderer Themen standen hier
bis v1.15.2, siehe Grenze „Wörtliche Pflichttexte"). Wer hier ändert, lässt
die Selbstprobe laufen; sie liest diesen Abschnitt.*

- **Der Bericht endet mit der Zeile „Eigene Läufe am Ende: …"** — keiner, oder
  welcher Lauf noch offen ist, was er hält und ob er gestoppt wurde. Ein Lauf,
  den ein Zeitlimit ins Hintergrundfach verschoben hat, wird gestoppt, bevor es
  weitergeht (`lehren.md` §22).
- **Alle** Prüfläufe nennen, die die CI fährt — vollständig in Block 6.
  (Reales Beispiel: Die CI fuhr
  *zwei* Typprüfungen, im Brief stand nur eine — der neue Test war lokal grün
  und im CI rot.)
- **Jede Option, die der Brief anbietet, nennt die Umgebung, in der sie läuft.**
  Gemessen: Ein Nacharbeits-Brief bot „die Version per Dateizugriff lesen" an —
  im Test-Abbild existierte die Datei nicht (das Abbild kopiert nur den
  Test-Ordner). Alle 27 Tests fielen aus, keine von drei Stimmen sah es, der
  Brief hatte den Ausfall bestellt. Wer eine Option vorschlägt, hat sie gegen
  das Abbild geprüft, in dem sie laufen soll — nicht gegen den Arbeitsbaum.
- **Was der Orchestrator selbst schreibt und ausliefert** (Release-Notiz,
  Meldung, Beschriftung, Kommentar im Code), unterliegt denselben Stilregeln
  wie Code aus dem Bau und geht durch dieselbe Prüfung. Gemessen: Acht von zehn
  Release-Notizen eines Releases trugen ASCII-Umschreibungen statt Umlauten —
  vom Orchestrator geschrieben, fünf Slices lang von niemandem geprüft, weil
  Panel und Gates nur den Bauer sehen.
- **Lange Befehlszeilen und Pfade in Listenpunkten gehören in einen Zaun-Block**,
  nie in einen Inline-Code-Span: Ein Formatierer wirft die Fortsetzungszeile
  auf Spalte 0 und zerreißt den Span — und `--check` ist danach grün, weil der
  Formatierer den Zustand selbst hergestellt hat (dreimal in einem Slice).
- Läufe im **Vordergrund**, Zeitlimits explizit. Keine Hintergrundprozesse, keine
  eigenen Subagenten.
- **Lokal committen, nicht pushen.** Landen entscheidet der Hauptagent nach dem Panel.
- Bei neuen Datenbank-Tests: Engine im `tearDown` entsorgen, gegen eine echt
  migrierte DB testen statt gegen ein frisch erzeugtes Schema.
- **Parallelität: innerhalb eines Laufs höchstens ⟨n⟩ Worker und ⟨n⟩ Browser;
  jeden schweren Lauf nur unter der Rechner-Sperre** — die Zahlen aus dem
  Schwellen-Inventar der `CLAUDE.md` stehen HIER, im Brief; ein Zeiger auf die
  `CLAUDE.md` erreicht den Bauer nicht. Hier stehen NUR die Zahlen; wie das
  Werkzeug sie setzt (eine Option des Testlaufs), gehört in Block 6 — sonst
  erfüllt dieser Punkt ein anderes Thema des Prüfskripts, sobald das Werkzeug
  in dessen Wortschatz steht (gemessen, Blindprüfer v1.18.9).
  Auf einem geteilten Rechner halten Shards eines Testlaufs das Mehrfache an
  Speicher (gemessen: mehrere Interpreter mit je rund 350 MB), ohne schneller
  fertig zu sein. Gemessen in einem Kind-Repo: Ein Rechner mit 64 GB lief auf
  94 %, als drei Sitzungen gleichzeitig bauten; der Anteil der Agenten daran lag
  grob bei 7 GB, die Hauptlast kam aus dem Betriebssystem — der Agenten-Anteil
  war aber vermeidbar, und eine Zahl hatte niemand verlangt. **Die
  Rechner-Sperre** gilt für jeden schweren Lauf (volle Suite, Gate-Skript,
  Browser, Container, Mutationslauf über die ganze Suite; im Zweifel schwer) und
  hat für alle Projekte denselben Pfad, sonst sperren zwei Projekte einander
  nicht aus. **Nehmen, Lauf und Freigeben stehen in EINEM Aufruf**, und die
  Sperre nimmt, wer den Lauf startet — nie ein Skript darin:

  ```sh
  S="$HOME/.sperre-schwerer-lauf"; until mkdir "$S" 2>/dev/null; do sleep 30; done
  echo "⟨Projekt⟩ ⟨Rolle⟩ $(date +%FT%T)" > "$S/wer"; cat "$S/wer"
  ```

  Im selben Aufruf folgt der schwere Lauf aus Block 6, danach:

  ```sh
  rc=$?; rm -f "$HOME/.sperre-schwerer-lauf/wer"; rmdir "$HOME/.sperre-schwerer-lauf"; exit $rc
  ```

  Der Lauf selbst steht nicht in diesem Punkt: Diese Randbedingung steht
  wörtlich in Block 8, und ein hier eingesetzter Lauf erfüllte das Thema zu
  Block 6 im Prüfskript, sobald sein Werkzeug in dessen Wortschatz steht — ein
  Brief ohne Block 6 kam dann als vollständig durch (gemessen, Blindprüfer
  v1.18.6 und v1.18.9). Deshalb nennt dieser Satz weder ein Werkzeug noch das
  Thema beim Namen.

  Der Pfad steht beim Freigeben ausgeschrieben: Claude Code blockiert ein `rm`
  auf eine Variable, deren Ziel es nicht auflösen kann — gemessen in einer
  Sitzung, in einer anderen nicht; es hängt vermutlich am Berechtigungsmodus.
  `$HOME` löst es in beiden auf.

  Ein Skript, das die Sperre selbst nähme, wartete auf den, der es startete. Ein
  Nehmen in einem eigenen Aufruf hielte sie fest, wenn dieser Aufruf in den
  Hintergrund wandert und niemand mehr arbeitet. Und ein `trap`, der freigibt,
  löschte beim Abbruch während des Wartens die FREMDE Sperre (alle drei
  gemessen, Blindprüfer v1.18.6). Wandert der Aufruf in den Hintergrund, gilt
  die Regel zum Bericht oben: Er wird gestoppt, bevor es weitergeht; bis dahin
  hält er die Sperre zu Recht. Gestoppt wird der ganze Prozessbaum des schweren
  Laufs, nicht nur dessen Prozessnummer: Ein Gate-Skript, ein Testlauf mit
  Workern oder ein Browser startet Kindprozesse, und die liefen sonst als Waisen
  weiter, während die Shell die Sperre schon freigibt (gemessen, Blindprüfer
  v1.18.9). Unter Git Bash erfasst `taskkill //T` die Kinder nicht, die die
  Shell per Fork gestartet hat, und eine eigene Prozessgruppe legt eine Shell
  ohne Aufforderung nicht an (beides gemessen). Das leistet
  `sh docs/vorlagen/baum-stoppen.sh <pid>`: Es hält den Baum an, beendet ihn
  und endet mit Exit 0 erst, wenn keiner der gefundenen Prozesse mehr lebt —
  erst dann ist die Sperre frei. Exit 1 heißt: Die Sperre bleibt, bis der Rest
  beendet ist. Was es nicht finden kann, steht unter GRENZEN im Kopf des
  Werkzeugs — darunter ein Container (`docker run`), ein Nachkomme, der sich
  vom Baum löst, bevor sein Elternprozess angehalten ist, und unter Git Bash
  ein Hintergrundkind vor einem `exec` in ein natives Programm oder ein Enkel,
  den ein Programm über einen kurzlebigen Zwischenprozess startet. Nach Exit 0
  zeigt `docker ps` die Container und unter Git Bash `ps -W` (auch native
  Prozesse), sonst `ps -eo pid,ppid,lstart,args`, welche Programme noch
  laufen; ob eines zum Lauf gehört, sagen Name und Startzeit, nicht die
  Elternnummer. Erst danach ist die Sperre frei. Wer stattdessen nur die Shell stoppt, findet den Rest mit dem
  Werkzeug nicht mehr (ohne lebende Wurzel endet es mit Exit 2), beendet ihn
  über die Nummern aus `ps` und gibt die Sperre nur frei, wenn
  `cat "$HOME/.sperre-schwerer-lauf/wer"` seine eigene Zeile zeigt (Block 1 gibt
  sie beim Nehmen aus).
  Eine fremde Sperre wird nie gebrochen: Hängt sie länger als 60 Minuten,
  meldet das der Bericht. `mkdir` ist atomar und überall da, `flock` fehlt unter
  Git Bash.
- Wenn parallel ein anderer Slice läuft: **welche Dateien tabu sind** — und
  **welche knappe Größe** er belegt. Zwei Pakete können streiten, ohne eine
  gemeinsame Zeile anzufassen: beide wollen dieselben CI-Minuten, dasselbe
  Guthaben, dieselben Ports, dieselbe Owner-Zeit, denselben Speicher. Gemessen
  in einem fremden Projekt (zwei Pakete, jedes für sich maßvoll, zusammen über der Grenze) und
  bei uns (drei Slices parallel am selben Prüf-Kontingent, keiner landete).
  Zwei Pakete an derselben knappen Größe laufen nicht parallel.
- **Der Einrichtungsblock ist in einer leeren Umgebung ausprobiert**, nicht
  aus dem Gedächtnis geschrieben — und endet mit einer Probe, WAS entstanden
  ist (`ls -laL` auf die angelegten Pfade; `-L`, sonst sieht ein toter Link wie
  ein guter aus). Gemessen: Ein Bau-Container ohne Migrationsschritt und ohne
  zwei Pflicht-Umgebungswerte lieferte 239 rote Tests, die niemand verursacht
  hatte. Eine Einrichtungsanweisung, die nie jemand leer ausgeführt hat, ist
  eine Vermutung.
- **Kann der Bauer die Tests nicht selbst ausführen, steigt die
  Defektdichte** — gemessen lagen 6 von 7 Blockern eines Laufs in Tests, die
  nie gelaufen waren. Die Umgebung des Bauers wird deshalb vor dem Start
  geprüft (Abbild vorhanden, Dienste erreichbar), nicht erst nach verbrauchten
  Tokens.
- Sprache/Zeichensatz-Regeln des Projekts.

---

## Typische Fallen (in den Brief kopieren, wenn einschlägig)

*Diese Texte werden wörtlich in Briefe kopiert. Deshalb gilt für sie dasselbe
wie für die Pflicht-Randbedingungen: kein Suchwort eines anderen Themas des
Prüfskripts — sonst erfüllt eine einzige kopierte Falle jenes Thema, auch wenn
dessen Block fehlt. Gemessen bis v1.15.2: drei Fallen trugen je ein Suchwort
der Themen Sichtbares, Nachweis und Fixtures und hielten sie ohne den
jeweiligen Block grün (Exit 0); die drei Formulierungen sind seitdem
geändert (CHANGELOG v1.15.2). Wer hier ändert, lässt die Selbstprobe laufen;
sie liest diesen Abschnitt.*

**Plattform.** Ein Test, der eine Ausnahme aus Betriebssystem oder C-Bibliothek
erwartet, läuft vor der Landung einmal auf der Zielplattform — bei einer
Container-Anwendung im Wegwerf-Container mit dem App-Abbild. Geht das vor der
Landung nicht, bleiben plattformabhängige Eingaben aus dem Test: jede, deren
erwartete Ausnahme aus Betriebssystem oder C-Bibliothek kommt, auch wenn sie
vermutlich überall gleich wirft. Eingaben, die nur auf einer Plattform werfen,
gehören nie in den Beweis, dass der Test rot werden kann (`lehren.md` §5).

**Datenmigration.** Treffermenge kumulativ eng fassen. Downgrade muss den
*Rollback-Pfad* heil lassen, nicht nur das Schema. Prüfen, ob Altbestand nach
der Änderung den alten *und* den neuen Wert gleichzeitig zeigt.

**Aggregat statt Einzelabfragen.** Index-Deckung der korrelierten Spalten prüfen.
Konzentrierte *und* gestreute Datenverteilung messen. Pfade prüfen, die das neue
Feld gar nicht lesen — sie zahlen trotzdem.

**Maskierte Daten / Mandantentrennung.** Nicht nur der Wert, auch **Reihenfolge,
Trefferzahl und Kappungsposition** dürfen nicht vom Geheimnis abhängen. Ein
Freitext-Label wird von feldbasierten Filtern nicht gefangen.

**Listen und Auswahlfelder.** Kappt die Tür? Sagt sie es? Wird aus der Liste
etwas *abgeleitet*, das still ausfällt, statt erkennbar zu degradieren?

**Wächter/Prüftests.** Enthalten die erfundenen Eingaben den Fall überhaupt, um
den es geht? Fallen zwei Ordnungen zufällig zusammen? Kennt ein AST-Wächter das
*hausübliche* Änderungsmuster oder nur die naive Form?

**Fremdcode (R3-Auslöser).** Der Auslöser sagt, wie geprüft wird — nicht, ob
fremde Inhalte angefasst werden dürfen. Trennlinie, gemessen an einem Beitrag in
einer Sprache, die niemand im Team sprach: **Korrigiert wird nur, wo der
Widerspruch im Artefakt selbst belegbar ist** (ein Label identisch mit der
Überschrift darüber, ein Navigationseintrag, der die Seite anders nennt als ihr
Titel, eine englische Pluralregel im fremdsprachigen Text). Alles, was
Sprachurteil verlangt, geht als Liste an den Autor zurück. Und was geändert
wird, legt man ihm offen — *war → ist → warum*, mit dem Satz „wenn eine davon
falsch ist, sag es". Der Gegenprüfer ist bei Fremdcode die richtige
Besetzung: drei belegbare Fehler im Fremdanteil, die zwei andere Stimmen nicht
hatten, bei einem Diff aus 95 % Zeichenketten.

**Generator, der in eine Datei mit handgeschriebenem Anteil schreibt.** Er
liest den Bestand, bevor er schreibt, und hat einen Erhaltungs-Rundlauf als
Test: handgeschriebenen Inhalt setzen, Generator ausführen, Hash vorher =
nachher. Gemessen in einem Benchmark: Drei von fünf unabhängigen Umsetzungen
desselben Slices vernichteten die handgeschriebene Übersetzung bei jedem Lauf
— eine davon mit Exit 0 und Erfolgsmeldung, auf dem Rechner des Owners, im
Container dagegen nicht. Keine von 15 Bewertungen fand es.

**Datenmigration: die leere Datenbank beweist nur die Syntax.** Vor dem
Release eine Generalprobe im Schemastand der Produktion mit **erfundenem**
Bestand, dazu VOR dem Lauf eine Vorhersage-Abfrage („danach stehen 5/2/3
Zeilen in …") und die Prüfung, dass die alten Migrationsdateien unverändert
sind. Gemessen: Vorhersage und Ergebnis stimmten — und die Probe fand
nebenbei einen Fehler, den die leere Datenbank nie gezeigt hätte.

**Ausnahme, die Sicherheit behauptet („ist unkritisch, weil …").** Sie
braucht einen Test, der genau diese Behauptung misst — sonst ist die Ausnahme
der Ort, an dem der Wächter still aufhört.

**Heuristik durch Kennung ablösen.** Wird ein Näherungsweg durch eine genaue
Kennung ersetzt, gilt die Umschaltung **pro Vorgang, nicht pro Element**: Sobald
mindestens eine echte Kennung ankommt, ist die Heuristik aus — auch für die
Elemente ohne Kennung. Gemessen: Ein Bau schaltete je Zeile um; für Zeilen ohne
Kennung blieb die Index-Heuristik aktiv, obwohl ihre Voraussetzung („die Menge
hat sich nicht geändert") durch die anderen Zeilen längst nicht mehr galt. Vor
dem Fix eine Zeile falsch markiert, danach zwei — der Fix erzeugte die Klasse,
die er beseitigen sollte (fünfter Fall dieser Art in neun Slices).

---

## Nacharbeit nach dem Panel

Wer die Nacharbeit baut, entscheidet die ART der Auflage — siehe unten.
Im Nachtrag:

- **Was bestätigt wurde**, nicht nur was zu tun ist. Sonst sucht der Bauer nach
  Problemen, die geprüft und in Ordnung sind.
- **Widerlegte Befunde ausdrücklich abräumen.** Prüfer irren; ein unkommentierter
  Fehlbefund kostet eine Runde.
- Je Punkt: Schwere, Fundstelle, **Nachweis**. „Wirkt unsauber" ist kein Auftrag.
- **Der Rot-Beweis mutiert die NEU GESCHRIEBENEN Zeilen der Reparatur**, nicht
  nur den gemeldeten Fall. Die Reparatur ist der am wenigsten geprüfte Code im
  Slice: Nach einem Fund entsteht der Rot-Beweis GEGEN den Fund, und die Zeilen,
  die beim Reparieren neu geschrieben wurden, bekommen keinen. Gemessen über
  drei Slices: Die schwersten Funde der ZWEITEN Panel-Runde waren jedes Mal die
  Reparaturen aus der ersten — eine zusammengezogene Bedingung machte eine
  Nutzerwahl still unwirksam, zwei Sicherungsarten in derselben Datei ließen
  jede weitere ausfallen, ein Schloss schob die Ablehnung wieder hinter den
  Schreibvorgang. (Die Regel darunter deckt die andere Richtung ab: nicht über
  den gemessenen Umfang hinaus beheben.)
- **Umfang der Behebung = gemessener Umfang.** Die Auflage nennt die Tür, den
  Pfad, die Eingabe, die der Prüfer gezeigt hat; dort wird behoben. Eine
  Ausdehnung auf weitere Türen, Aufrufer oder Bestandsdaten wird im Brief
  benannt und begründet — mit Prüffrage 3 (Geschwister-Routinen) und Prüffrage
  10 (Ausgangszustände) für die Erweiterung —, sonst ist sie ein eigener Slice
  (`lehren.md` §23: die mitgelöste Nachbartür sperrte Bestandsbelege).
- **Keine neuen Tests in der letzten Nacharbeitsrunde.** Ein Test, der zum
  ersten Mal läuft, ist erfahrungsgemäß zur Hälfte rot (Locator trifft ein
  Nachbarelement, Init-Script überschreibt den Zustand, Pfad im Abbild fehlt).
  Wird er in der Schlussrunde angefordert, landet ein nie grün gesehener Test —
  gemessen in einem Benchmark-Lauf: der einzige offene Blocker am Ende war der
  in Runde zwei neu bestellte Test. Neue Tests nur, wenn danach noch eine Runde
  folgt; sonst die fehlende Abdeckung als **offen** protokollieren.
- **Der Bericht des Bauers ist seine Abschlussantwort, keine Datei im Repo.**
  Zwei von drei Bauläufen legten ihn in den Arbeitsbaum, einer committete ihn —
  die Stimmen hätten ihn gelesen und wären nicht mehr blind gewesen. Steht im
  Brief als Pflichtzeile.
- **Den Herkunftsstempel setzt der Orchestrator, nie der Bauer.** Vier von vier
  Erstbauten trugen einen erfundenen `Built-With` (falsches Modell, falsches
  Datum) — auch nach ausdrücklicher Auflage „erfinde keine Herkunft". Der Bauer
  KENNT seine Modellkennung nicht zuverlässig; Selbst-Attestierung ist
  strukturell unmöglich. Im Brief steht der Platzhalter
  `Built-With: bau=<vom Orchestrator gesetzt>`, den der Orchestrator beim Landen
  ersetzt.

---

## Fixtures werden erfunden, nie aus dem Kontext übernommen

**Pflichtzeile in jeden Bau-Brief.** Ohne ausdrückliche Regel nimmt der Bauer die
Beispiele, die im Gespräch herumliegen — und das sind die echten.

Realer Verlauf, zweistufig, und die zweite Stufe ist der eigentliche Befund:
Ein Bau-Subagent brauchte einen Namen für ein Testszenario, erfand keinen,
sondern nahm den echten Namen einer realen Person aus dem Gesprächskontext und
schrieb ihn in einen committeten Seed. Beim Verifizieren gefunden und vor dem
Push ersetzt. **Danach** wurde daraus eine Regel formuliert — und in die Regel
selbst schrieb der Hauptagent denselben echten Namen als Beleg.

Die Klasse trifft also nicht nur den Bauer: Wer den Vorfall dokumentiert,
wiederholt ihn. Fälle anonymisieren, bis nur die Klasse übrig bleibt — im Code,
im Issue und in der Lehre.

## Rot-Beweis gilt auch für ganze Suiten

Der Rot-Beweis für einzelne Tests reicht nicht, wenn eine ganze Suite als
Sicherheitsnetz gemeldet wird (Rauchtests, Vor-Release-Sets). Vor der Meldung
**zwei bekannte Fehler absichtlich wieder einbauen** und beobachten.

Der Fall, der **nicht** rot wird, ist der lehrreichere: In einem realen Versuch
fing die Suite die eine Regression und die andere nicht — weil der Zugangsschutz
an zwei unabhängigen Strängen hing und der Test nur einen berührte. Was die
Suite **nicht** behauptet, gehört in den Test geschrieben, nicht in die
Erinnerung.

## Der Rot-Beweis ist eine Schrittfolge, keine Warnung

Ein misslungener Rot-Beweis meldet keinen Fehler — **er meldet grün**, und grün
ist die Farbe, die man sehen will. Dreimal in einem Slice hat ein Rot-Beweis
eine falsche Antwort geliefert, jedes Mal anders, jedes Mal wie eine gültige
Messung aussehend: die Sabotage war keine (zwei Werte per Regex „gleichgesetzt",
nachgemessen 1678 gegen 1671 Zeichen); die Sabotage kam im Test-Abbild nicht
an (nur das Anwendungs-Abbild wurde neu gebaut); der Bau scheiterte still, weil
seine Ausgabe nach `/dev/null` ging. Und ein Rückbau per `git checkout -- <datei>`
löschte die uncommittete Nacharbeit gleich mit — der zweite Rot-Beweis lief
gegen den unsabotierten Stand. Die Lehre stand als Warnung im Repo und trug
nicht; als Schrittfolge trägt sie:

1. **Committen** (`wip`, später amenden) — vor der ersten Mutation, immer.
   `git checkout --` löscht, was nicht committet ist, egal wer es aufruft.
2. **Sabotage setzen und belegen, dass sie steht** — zweiteilig:
   **2a** im Quelltext, gemessen (sind die beiden Werte jetzt wirklich gleich?),
   **2b** im laufenden Artefakt, wenn zwischen Quelle und Lauf ein Bau liegt:
   neu bauen **mit sichtbarer Ausgabe** und den Marker im Artefakt nachweisen.
   Liegen Tests und Anwendung in GETRENNTEN Abbildern, werden **beide** neu
   gebaut — gemessen lief sonst die alte Testfassung gegen die neue Sabotage.
   Der Marker steht in einem String, nicht in einem Kommentar — der
   Produktionsbau wirft Kommentare weg, und der Nachweis meldet dann
   falsch-negativ „0 Treffer", obwohl die Sabotage wirkt.
3. **Messen** — den Exit-Code ohne Pipe.
4. **Zurücknehmen und den Baum gegenprüfen** — `git status --short --ignored`
   ohne unerwartete Einträge.
5. **Gegenprobe: Der richtige Fall bleibt grün.** Ein Wächter, der den
   Fehlerfall fängt, muss den korrekten Fall nachweislich durchlassen — sonst ist
   eine Regel, die ALLES meldet, genauso „erfolgreich". Gemessen in einem
   fremden Projekt: Eine Prüfregel fing den gemeldeten Fehler und meldete die
   behobene Fassung derselben Aufgabe nicht — erst diese zweite Hälfte zeigte,
   dass sie unterscheidet; eine Regel, die alles meldet, hätte die erste Hälfte
   genauso bestanden. Bei
   einem Wächter heißt das dreigeteilt protokollieren, nicht vermischen:
   **(a) Hat er eine Selbstprobe? (b) Fängt er die Sollfälle? (c) Was lässt er
   durch?** Gemessen an fünf Wächtern: keiner hatte eine Selbstprobe, alle fünf
   fingen ihre Sollfälle, alle fünf ließen einen Nicht-Sollfall durch — drei
   verschiedene Aussagen, die als „ungetestet" zusammengefasst falsch gewesen
   wären.

Dazu vier Regeln, alle gemessen:

- **Die LISTE der Stellen kommt aus dem Diff, nicht aus dem Gedächtnis.** Die
  Regeln unten sagen, was eine Mutation tun muss; diese sagt, woher die Auswahl
  kommt. Gemessen: Die entscheidende Zuweisung stand an **vier** Aufrufstellen,
  die erinnerte Liste traf eine, und der Bericht sagte „30 Mutationen, alle
  gefangen" — zwei Panel-Stimmen fanden unabhängig elf bzw. drei überlebende.
  Also: jede geänderte Aufrufstelle einer geänderten Regel **aufzählen**
  (`grep -n` auf den Bezeichner über das ganze Repo), nicht erinnern. Nach
  einer Panel-Runde stammt die Liste **aus den Prüfberichten**, nicht aus der
  Auswahl des Bauers. Und **jede Zusage „X von X gefangen" nennt die Herkunft
  der Liste** — ohne sie ist die Zahl eine Aussage über die Vorstellungskraft
  des Bauers, nicht über den Code.
- **Die Mutation trifft die GESAMTE betroffene Menge.** Ein Arbiter leerte für
  den Beweis „leere Abschnitte werden rot" nur den ersten Abschnitt; der zweite
  hielt den Wächter grün, und der Beweis schien den Wächter zu widerlegen.
- **Ein Rot-Beweis mutiert eine Zeile, die im Diff steht.** Vier grüne
  Backend-Tests als Nachweis für einen Diff mit null Backend-Zeilen bestätigen
  die Ausgangslage, nicht den Slice — sie waren vorher schon grün.
- **Mutationen gehören in einen Wegwerf-Worktree** auf dem gemessenen Commit
  (`git worktree add --detach <pfad> <commit>`, mutieren, messen,
  `git worktree remove`). Keine Schutzprüfung springt an, weil der lebende Code
  unberührt bleibt; die Rücknahme entfällt; der Prüfgegenstand kann nicht
  beschädigt zurückbleiben. Real: Ein Klassifikator blockierte das Entfernen
  eines `try/catch` im Arbeitsbaum, der Bauer wich über die Shell aus — sauber
  im Ergebnis, falsch als Muster.

---

## Der Nacharbeits-Brief ist ein Bau-Brief

Panel-Auflagen sind **Anforderungen, keine Implementierungen** — die Freiheit,
die eine Auflage offenlässt, ist genau die Stelle, an der der nächste Defekt
entsteht (zweimal belegt, einmal *nachdem* der erste Fall dokumentiert war).

**Die Rundengrenze gilt** (Schwelle: `../../CLAUDE.md`, Risiko-Tabelle, Zeile
„Nacharbeit"; Verfahren: `panel.md`, Schritt 4). Die
letzte Runde bestellt keine neuen Tests (oben), und eine Nacharbeit fragt immer
auch: **Welche Texte behaupten noch
das alte Verhalten?** (Doku, Docstrings, Werkzeug-Beschreibungen, Hilfetexte —
gemessen lagen in einer Runde alle Funde dort und keiner im Code.)

Deshalb: Nacharbeit bekommt dasselbe Pflicht-Gerüst, plus zwei Blöcke:

```markdown
## 10 Bestätigt        ⟨arbitrierte Auflagen, nummeriert, je mit Nachweis⟩
## 11 Ausdrücklich abgeräumt — hier ist NICHTS zu tun
                       ⟨widerlegte Fehlbefunde, damit der Bauer nicht sucht⟩
```

*(Bis v1.13.1 trugen diese Blöcke die Nummern 9 und 10 — ein Nacharbeits-Brief
hatte damit zwei Blöcke „9". Gemeldet von einem Projekt; die Klasse „ein Schnitt
zieht Inhalt an eine neue Stelle und lässt die alte Nummer stehen" fängt die
**Zählprobe** für den Wortlaut (seltenstes Einzelwort zählen) nicht, weil beide Fundstellen
legitim aussehen. Seitdem gehört zur Schnitt-Praxis zusätzlich die
**Nummern-Probe**: nach dem Einfügen eines nummerierten Blocks die Nummern
zählen — `grep -o "^## [0-9][0-9]*" | sort | uniq -c`, jede genau einmal
(`[0-9][0-9]*` statt `[0-9]*`, sonst zählt jede unnummerierte Überschrift als
leere Nummer mit).)*

Block 11 wurde in einem Projekt erfunden, weil `panel.md` zwar „ausdrücklich
abgeräumt" verlangt, aber nicht sagt, wo das steht. Ohne ihn sucht der Bauer
nach Fehlern, die es nicht gibt.

**Wer die Nacharbeit baut — nach der Art der Auflage, nicht nach Vorliebe:**

- **Mechanische Auflage** (benannter Fix an benannter Stelle, kein Entwurf
  berührt) → **derselbe Bauer.** Sein Kontext spart die Einarbeitung, und es
  gibt nichts zu hinterfragen.
- **Auflage, die den ENTWURF berührt** (eine Vorgabe wird umgekehrt, eine
  Struktur kommt dazu) → **frischer Bauer.** Der bisherige verteidigt seine
  eigene Konstruktion; ein frischer widerspricht produktiv. Real belegt: Der
  frische Bauer widersprach der arbitrierten Auflage und fand dabei einen
  Folgefehler.

*Verworfen wurde die pauschale Regel „immer derselbe, er hat den Kontext" —
Kontext ist bei Entwurfs-Auflagen genau das Hindernis. Und die pauschale Regel
„immer frisch" kostet bei Ein-Zeilen-Fixes mehr, als sie bringt. Beide Varianten
standen kurzzeitig gleichzeitig in diesem Dokument; das war der Fehler. In einem Fall widersprach der frische Bauer der
arbitrierten Auflage produktiv und fand dabei einen Folgefehler.

## Was im Bericht des Bauers zu prüfen ist

Ein Bericht ist eine Absichtserklärung, kein Nachweis. Zwei Muster haben sich als
gefährlich erwiesen, beide **nicht böswillig** — Modelle vervollständigen
plausibel:

- **Erfundene Quellenangaben.** Ein Report meldete drei rote Läufe als
  „vorbestehende, ordnungsabhängige Flakes" — **mit Verweis auf einen Abschnitt
  der Lehren-Datei, der etwas völlig anderes behandelt.** Der Blindprüfer fuhr
  drei volle Läufe: alle grün, die Flakes reproduzierten nicht. Geliehene
  Autorität tarnt einen ungeprüften Befund, und die *erfundene* Quelle ist
  gefährlicher als gar keine — sie liest sich wie ein nachgeschlagener Fakt und
  wird leichter durchgewunken.
  → **Jedes Zitat im Bericht nachschlagen.** Steht dort nicht, was behauptet wird,
  ist der ganze Befund unbelegt.
- **Behauptete Flakes.** Wer einen roten Lauf als Flake abtut, muss ihn
  **reproduzieren** — mehrfach, mit und ohne Diff. Ein Flake, der sich nicht
  reproduzieren lässt, ist kein Flake, sondern ein Fund.

Verwandt: Ein als „verifiziert" gemeldeter Fix, bei dem nur der Nachbar-Zweig
geprüft wurde. Die Frage lautet nicht „hast du geprüft", sondern **„was genau hast
du ausgeführt, und was kam heraus"**.

## Das Hintergrund-Warte-Muster

Ein wiederkehrendes Bauer-Verhalten, **mindestens zehn dokumentierte Fälle
über zwei Projektgenerationen**: Der Bauer legt die Gates in den Hintergrund und endet mit
„warte auf das Ergebnis des Hintergrundlaufs" — obwohl die Randbedingung im
Brief das ausdrücklich untersagt. **Die Brief-Zeile allein verhindert es
nicht.** Zwei Mechanismen wirken:

**Inzwischen 10 von 10 ausgewerteten Fällen, und die Deutung hat sich geschärft: Die
Brief-Zeile kann nicht wirken, weil der Empfänger sie nicht befolgen KANN.** Das
Bau-Modell legt lange Läufe strukturell in den Hintergrund und wartet auf ein
Signal, das seine Ausführungsumgebung nie liefert. Auch doppelte, ausdrückliche
Formulierung im Brief ändert daran nichts (getestet).

**Deshalb gehört das nicht in den Bau-Brief, sondern eine Ebene höher:**

1. **In die Systeminstruktion des Bauers** (nicht in den Auftrag): Gates
   blockierend im Vordergrund, keine Hintergrundläufe. Das nimmt den Anlass an
   der Stelle, an der er entsteht.
2. **Als fester Ablaufschritt des Orchestrators**, nicht als Brief-Auflage: Der
   Nachstoß („Ergebnis selbst prüfen, Report abliefern") wird **eingeplant**,
   nicht als Reaktion auf ein Versäumnis improvisiert. Er wirkt zuverlässig
   (10/10), die Brief-Zeile nachweislich nicht.

Der Zustand „wartet auf Ergebnis" ist **kein Report** — er wird nie als
Abschluss akzeptiert.

*Die allgemeine Lehre dahinter: Eine Regel an einen Empfänger, der ihr
strukturell nicht folgen kann, ist keine Regel, sondern eine Beschwerde. Sie
gehört dorthin, wo das Verhalten entsteht.*

## Wenn ein Bauer mitten im Rot-Beweis stirbt

Der Rot-Beweis ist das einzige Ritual, das den Code **absichtlich kaputt macht**.
Bricht die Sitzung dabei ab, beschreibt der letzte Bericht den Zustand *davor*
(„alle Tests bestehen, jetzt der Rot-Beweis") — wer das liest und nicht
nachsieht, übernimmt Sabotage als fertige Arbeit.

**Wiederaufnahme-Protokoll, immer in dieser Reihenfolge:**

1. `git status` und `git diff` lesen, **bevor** irgendetwas gebaut wird.
2. `git log --oneline origin/main..HEAD` — was ist lokal, was gepusht?
3. Den letzten Bericht als **Absichtserklärung** lesen, nicht als Zustand.
4. Erst dann weiterbauen — und nichts doppelt.

**Stirbt ein Bauer außerhalb des Rot-Beweises** (Sitzungslimit, Neustart des
Rechners), gilt dieselbe Reihenfolge — und dazu: **Ein frischer Bauer
entscheidet je Stück, nicht pauschal**: übernehmen, fertigstellen oder
verwerfen, jeweils mit Beleg aus Schritt 1. Zweimal so wiederaufgenommen, je
rund zehn Minuten, beide Male ohne Verlust. Aufgeräumt wird nur per
**Positivliste bekannter Artefakte**; eine unbekannte Abweichung wird gemeldet,
nicht bereinigt — gemessen hat genau diese eine Zeile („unbekannte Abweichung,
nicht bereinigt") eine Runde gerettet.

---

## Die Wahrheit des Briefs: Behauptungen sind Bringschuld des Schreibers

Zweimal in einer Woche war die Fehlerquelle nicht der Bauer, sondern der
Brief. Drei Regeln daraus:

**„Dasselbe Muster wie Y" ist erst eine gültige Brief-Aussage, wenn Y wirklich
gelesen wurde und seine Schutzschichten AUFGEZÄHLT und in den Auftrag
übernommen sind.** Real: Der echte Zwilling trug drei Schutzschichten, die die
Kopie nicht bekam — der Blindprüfer fand es, weil er den Zwilling las. Ohne
die Aufzählung erbt die Kopie nur den Namen, nicht den Schutz.

**Eine Umfangsgrenze gilt für neue Features, nie für die Blast-Radius-Prüfung
einer Default-Änderung.** Wer einen globalen Default oder Wert ändert, prüft
ALLE Leser — auch die ausgeklammerten. Real: Der Bauer hielt sich regelkonform
an „nur Konsument X" und meldete statt zu fixen; ein ausgeklammerter Pfad las
den scharf geschalteten Default. Regelkonform und trotzdem falsch heißt: Die
Grenze war zu weit formuliert, nicht der Bauer zu wörtlich.

**Der Bauer korrigiert eine falsche Brief-Prämisse mit Beleg — das ist
erwünschtes Verhalten, kein Ungehorsam.** Zwei Belege: Ein Bauer suchte den im
Brief angenommenen Helfer, fand ihn nicht im Baum und korrigierte die Annahme
im Report; ein anderer korrigierte die R-Einstufung des Auftraggebers am
Tabellentext. Der Brief ist Anleitung, kein Dogma; verifizierte Gegenbelege
gehören in den Report.

**Die Klausel „prüfe meine Einschätzung, statt sie zu übernehmen" steht in
jedem Brief, der eine Empfehlung ausspricht — nicht nur bei heiklen.** Sie hat
in einer Serie zweimal einen Fehler des Orchestrators abgefangen und einmal
gefehlt; dort blieb der Fehler stehen, bis jemand zufällig darüber stolperte.
Den Orchestrator prüft sonst niemand: Das Panel liest den Diff des Bauers, die
Gates laufen gegen den Code — Briefe, Prüfaufträge, Issue-Texte gehen an beiden
vorbei. Vier Panels einer Woche: fünf Funde trafen Behauptungen des Briefs oder
des Prüfauftrags, keine Codezeile.

**Setzt der Brief eine Produktverhaltens-Entscheidung, ist sie ein Prüfpunkt,
kein Kontext.** Die Klausel trägt nur bei Empfehlungen; eine Vorgabe, die als
entschiedene Sache mit Begründung dasteht, wird von jeder Stimme übernommen,
die den Brief kennt — deshalb bekommt der Blindprüfer ihn nie. Gemessen: Der
schwerste Fund eines Slices war die Folge einer solchen Vorgabe; die Stimme,
die den Brief kannte,
hakte das Verhalten als „geprüft, ohne Befund" ab, die Stimme ohne Brief fand
es sofort. Deshalb steht jede Verhaltensvorgabe des Briefs im Auftrag
mindestens einer Stimme ausdrücklich als *„diese Vorgabe ist zu widerlegen"*
(`panel.md`, Prüfaufträge).

**Nennt das Ticket eine Fundstelle, ist sie ein Verdacht, kein Auftrag.**
Zwischen Ticket und Bau gehört eine Messung der Kette, Glied für Glied, in den
Befund. Gemessen: Das Ticket forderte die Änderung „im geteilten Mapper"; dort
war die Kette längst geschlossen, die Lücke saß im Frontend-Typ. Hätte der
Brief die Ticket-Aussage übernommen, wäre eine bewusste Entscheidung aus einem
früheren Slice lautlos rückabgewickelt worden — mit dem Ticket als
Rechtfertigung. Weicht die Messung ab, ist die Abweichung der wichtigste Inhalt
des Briefs.

**Ein Brief bestellt eine Tatsache an genau einer Stelle.** Ein Abgleich führte
drei Ein-Eigentümer-Verletzungen ein — vom selben Commit, der den Satz „diese
Regel steht hier und nur hier" enthielt. Ursache jedes Mal: Der Brief hatte
dieselbe Aussage an mehreren Stellen bestellt, weil sie an jeder sinnvoll
klang. Die Regel ist nicht schwer zu befolgen, sie ist schwer zu beauftragen —
ein Brief, der dieselbe Tatsache in zwei Blöcken verlangt, hat die Verletzung
schon geschrieben, bevor der Bauer sie baut.

## Ablage: der Brief gehört dorthin, wo der Fremdprüfer ihn findet

**Der Bau-Brief wird beim Start des Slices als Issue-Kommentar gepostet** —
nicht nur an den Bauer übergeben, und **nicht ins Repo committet**: Ein
committeter Brief liegt im Prüfgegenstand des Blindprüfers, und dessen
Blindheit wäre damit weg (bis v1.15.1 stand hier die Repo-Ablage als
gleichwertige Option). Der Blindprüfer erhält den Auftrag, keine Issues zu
lesen. Wo sein Werkzeug Tracker-Zugang hat (etwa `gh` über eine Shell), ist er
vom Brief nur **per Auftrag** getrennt, nicht technisch — deshalb prüft die
negative Probe in `panel.md` („Blindheit wird BELEGT, nicht behauptet") je
Lauf, dass er den Brief-Kommentar nicht erreicht oder nicht liest. **Der Prompt des Fremdprüfers
nennt dann die Fundstelle** („Brief:
Issue #N, Kommentar vom …") und trägt den Auftrag, den Commit gegen den Brief
zu messen — Tabelle *Behauptung → stimmt / stimmt nicht / überschärft → Beleg*.

*(Korrektur gegenüber v1.13.0: Dort stand an dieser Stelle „der Prompt der
blinden Stimme" — im Widerspruch zu `panel.md`, wo der Blindprüfer (damals „blinde Erststimme") den
Brief ausdrücklich NICHT bekommt. Drei Prüfer eines Projekts fanden den
Widerspruch unabhängig. Die Blindheit bleibt unangetastet; die Brief-Messung
ist Auftrag der Stimme, die den Brief kennen darf. Der Beleg, dass das
trägt: vier gefundene Falschzusagen in einem Lauf, drei davon vom Orchestrator.)*

**In einem öffentlichen Repo ist der Brief weltweit lesbar.** Das ist kein
Argument gegen die Ablage — aber der Brief enthält ohnehin keine Geheimnisse,
und **Zugangswege, echte Namen und Bestandsdaten gehören auch nicht hinein**
(die Regeln für öffentliche Kind-Repos stehen in `betrieb.md` der Vorlage,
bei uns in `CLAUDE.md`, Abschnitt „Sicherheit“).

Gemessen, in beide Richtungen: In einem Slice lag der Brief nur im Scratchpad
des Hauptagenten. Prüffrage 6 konnte deshalb nur gegen Code und CHANGELOG
laufen — und fand dort eine **erfundene Zahl** (vier Stellen behaupteten einen
Fehlercode, den das Produkt nie liefert). Am Brief gemessen wäre sie zwei
Runden früher aufgefallen. Im Folge-Slice lag der Brief als Issue-Kommentar
vor: Die Stimme lieferte eine Tabelle *Behauptung → stimmt/stimmt nicht →
Beleg*, zwei Behauptungen darin „überschärft".

Nebeneffekt, der allein den Aufwand trägt: **Der Owner sieht die Annahmen des
Briefs vor dem Bau**, nicht erst im Panel.

## Elf Prüffragen vor der Landung — mechanisch stellbar, alle aus Messungen

Gemessen über zwei Codebasen (sieben plus zwei Slices): **keine Frage ist reines
Ritual, aber zwei wirken woanders als gedacht** — die Rot-Zahl-Frage beim
Schreiben des Briefs, die Muss-wahr-Frage in der Testformulierung; beide fangen
nichts beim Beantworten und sehen deshalb wie Ritual aus. Die Frage nach dem
Pfad des Produkts und die nach der abgezählten Zusage tragen am häufigsten; die
Frage nach Auswahl-plus-Anlage hatte in neun Slices keinen Gegenstand und
kostet eine Zeile. **Sie bleibt** (Owner-Entscheid v1.15.0 — angekündigt war die
Streichung nach der dritten Null-Messung; die dritte Null kam, aber zwei
Projekte widersprachen mit Beleg): Null Funde in einer Codebasis beweisen nicht,
dass eine Frage nichts prüft. Die Antwort unterscheidet deshalb **drei
Ausgänge — kein Gegenstand / vorhanden und richtig gebaut / vorhanden und
falsch** — und nur der erste ist die Null, die zur Streichung zählt. Gemessen:
Ein Projekt fand einen Fall der zweiten Art, der ohne die Frage nie
angesehen worden wäre.

**Wer die Frage stellt, entscheidet, ob sie wirkt.** Die Frage nach den
belegten Behauptungen (6) und die nach dem, was wahr bleiben muss (2), wirken
erst, wenn ein anderer sie stellt — als Selbstprüfung antwortet der Schreiber
„ja" und die Stimme findet trotzdem drei unbelegte Behauptungen, und ein Test
„200 oder 307" misst nur die Absicht seines Autors. Beide stehen deshalb
zusätzlich im Prüfauftrag (`panel.md`, „Prüfaufträge, die sich bewährt haben").

**Die Fragen stehen WÖRTLICH im Brief — je Frage der fett gesetzte Fragesatz,
nicht der Erklärtext dahinter.** Gemessen trugen drei von vier Briefen
umformulierte Fragen — das Prüfskript prüft je Frage nur die ersten Wörter am
Zeilenanfang und sieht eine Umformulierung dahinter nicht, und eine
umformulierte Frage ist eine andere Frage. Jede Frage beginnt eine eigene Zeile. Projekteigene Fragen werden ab der nächsten freien
Nummer angehängt, nie zwischen die Vorlagen-Fragen geschoben
(`abgleich.md` der Vorlage, Schritt 2e).

1. **Schreibt dieser Fix an einer Stelle, die vorher nur las — und wer teilt
   sich die Zielzeilen?** (Ein Fix machte einen inerten Pfad aktiv und schuf
   damit den stillen Verlustweg, den er beheben sollte.)
2. **Prüft dieser Test, was wahr bleiben MUSS — oder nur, was sich nicht
   ändern DARF?** (Ein Test nagelte die Nebenbedingung fest und zementierte
   den Ausfall des Zwecks: eine 26 Monate zu großzügige Präklusionsfrist,
   grün abgesichert.)
3. **Welche Geschwister-Routinen haben denselben Aufbau, und warum bleiben
   sie so?** „Bewusst später" ist eine gültige Antwort — Fehlen keine.
   (Ein Pfad wurde transaktional, Anlegen und Löschen mit identischem Aufbau
   blieben zurück.)
4. **Wählt eine Routine eine Zeile aus UND legt bei Nichtpassung eine neue
   an?** (Antwort in drei Ausgängen, siehe oben.) Dann läuft die Auswahl über die Identität des Zwecks, nie über eine
   Reihenfolge — sonst wächst der Bestand mit jedem Aufruf. (Gemessen: vier
   offene Fristen nach drei Korrekturen, `.first()` fand immer die falsche.
   Bitter: Eine frühere, richtige deterministische Sortierung machte den
   Defekt reproduzierbar statt selten.)
5. **Gilt die Rot-Zahl auch mit Kontext?** „N Tests rot" zählt nur zusammen
   mit Lauf-Umfang (eine Datei / ganze Suite) und Zustand der Testdatenbank
   (frisch/befüllt). Gemessen: dieselbe Mutation ergab 1, 6 oder 26 rote
   Tests je nach Quelle — die nackte Zahl ist eine Erinnerung, keine Messung,
   und landet doch als harte Zusage im Code.
6. **Ist jede Behauptung im Brief belegt oder als Annahme markiert?**
   (Siehe „Die Wahrheit des Briefs" oben.)
7. **Welchen Pfad benutzt das PRODUKT wirklich?** Ein Test, der die Zusage auf
   einem Pfad beweist, den die Oberfläche nie aufruft, ist eine Beruhigung,
   keine Prüfung. Gemessen: Tests bewiesen einen Direkt-Aufruf, das Produkt
   nutzt einen anderen Weg — der Schutzzweig war unerreichbar, der Kanal tot,
   alles grün. Der Rot-Beweis stellt den ECHTEN Aufrufweg nach, mit dem
   Datenpaket der Oberfläche. (§10 in neuer Gestalt: Der Wächter lief, aber
   am falschen Objekt.)
8. **Zählt der Slice seine eigene Zusage ab?** Wer „kein X mehr über Y"
   verspricht, zählt die Y. Gemessen: Ein Slice versprach Dichtigkeit für
   einen Sprachassistenten mit acht Werkzeugen und schloss eines; der Brief
   listete unter „Konsumenten" genau dieses eine. Diese Frage ist als
   **Prüferfrage stärker denn als Bauerfrage** — ein Bauer, der seine Zusage
   nicht abzählt, beantwortet auch die Frage danach mit „ja"; im Prüfauftrag
   gestellt, erzeugte sie den schwersten Befund eines Panels (die Suite war
   vor und nach dem Fix identisch grün). Sie steht deshalb auch in `panel.md`.
9. **Welche Eigenschaft hat die Antwort, die es NUR gibt, wenn die Funktion
   wirklich läuft?** Ein Test auf „Antwort ist nicht kaputt" besteht im
   geheilten und im kranken Zustand — deshalb war eine Suite vor und nach dem
   Fix grün, während die Funktion wochenlang Log-Zeilen schrieb und nichts tat
   (die Bibliothek fing intern und lieferte unverändert weiter). Getragen hat
   ein Test auf zwei Antwort-Kopfzeilen, die es ohne die Funktion nicht gibt:
   zwei Zeilen, keine Abhängigkeit. Für still ausfallende Funktionen ist das
   die konkrete Form der zweiten Frage.
10. **Welche real verschiedenen Ausgangszustände stecken hinter demselben
    technischen Zustand — und ist jeder davon am laufenden Stand gemessen?**
    Die Frage hängt an der FORM, nicht am Speicher-Schlüssel (bis v1.14:
    „Wer hat den Schlüssel heute NICHT?"). Bei allem, was ausgerollt wird, sind
    es mindestens vier Zustände: **frische Installation, Bestand vor dem Update,
    Bestand nach dem Update ohne den neuen Zustand, bereits gesehen/erledigt**.
    Der Fall dahinter: Ein Slice führte einen Schlüssel ein, an dem er
    „gesehen" festmacht, und behandelte „Schlüssel fehlt" als Erstinstallation
    (still vermerken, nichts zeigen). Jeder Bestandsnutzer hatte den Schlüssel
    nicht — der Erst-Rollout zeigte also niemandem etwas, das Feature wirkte
    erst ab dem übernächsten Release. Der Owner-Entscheid „frische Installation
    zeigt nichts" war richtig und wurde trotzdem zum Fehler: **Ein
    Owner-Entscheid ist eine Anforderung, kein Abnahmekriterium** — die Abnahme
    denkt den Rollout auf den Bestand. In 27 Review-Läufen dreier
    Benchmark-Runs wurde der Fall einmal gefunden; in einem späteren Vergleich
    stand er in **vier von fünf** unabhängigen Endständen, gemessen als
    Zustandsmatrix am laufenden Stapel (Bestandsnutzer: 0 Dialoge,
    ununterscheidbar von der frischen Installation). Keine von 15 Bewertungen
    fand ihn — die Bewertungsrubrik trug selbst die Owner-Rahmung. Bei R3 ist
    die Matrix die risikospezifische Probe, nicht die Frage allein.
11. **Welche Projekt-Prämisse berührt der Slice — und welcher Wächter oder
    welche Prüffrage hält sie?** Eine Prämisse, die nur in `CLAUDE.md` steht
    („jede neue Funktion ist auch über die Schnittstelle erreichbar"), ist ein
    Satz. Gemessen: Vier Slices mit Bau-Brief lieferten eine von drei
    vorgesehenen Türen, elf Wochen lang, über vier Abgleiche — kein Brief
    fragte danach, kein Wächter zählte. Die Antwort nennt je Prämisse den Beleg
    (Wächter, Zähler, Test) oder schreibt „nicht gehalten" und macht daraus ein
    Issue.

---

## Projektspezifisch: Prüf-Kommandos und Hausbelege dieses Repos

Alles oberhalb dieser Linie ist die Vorlage (v1.18.13), mit zwei Ausnahmen:
Ihre fünf Lehren-Verweise stehen hier in UNSERER Zählung (`abgleich.md` der
Vorlage, 2d, einzeln nachgeschlagen: Vorlage-Lehre §21 zweimal als unsere §10,
Vorlage-Lehre §35 als §22, Vorlage-Lehre §36 als §23, Vorlage-Lehre §10 als
§5), und Verweise auf Dateien, die es nur in der Vorlage gibt
(`abgleich.md`, `betrieb.md`), tragen den Zusatz „der Vorlage“ — beim Absatz
zur Ablage im öffentlichen Repo dazu der Zeiger „bei uns in `CLAUDE.md`,
Abschnitt ‚Sicherheit‘“. Dieser
Abschnitt steht bewusst am Ende:
`scripts/bau-brief-pruefen-selbsttest.sh` liest die Prüffragen, die
Pflicht-Randbedingungen und die Typischen Fallen **der Vorlage** und baut
daraus seinen Muster-Brief — eine projekteigene Zeile dort landete in jedem
Muster-Brief und könnte ein fremdes Thema erfüllen.

### Prüf-Kommandos für Block 6

    sh scripts/gates.sh all      # Notiz-Parität, Backend-pytest gegen echtes Postgres,
                                 # Web tsc + next build + next lint, Notiz-Wächter,
                                 # Prüfskript- und Werkzeug-Selbstproben, Verweis-Wächter
    sh scripts/smoke.sh          # Playwright gegen einen Wegwerf-Stapel, wenn die Oberfläche berührt ist
    sh scripts/teststand.sh up   # Sichtprüfung am ECHTEN Bestand des Owners — nie reset, nie down -v

Die CI fährt `pytest` gegen echtes Postgres (SQLite ist ausgeschlossen),
`tsc --noEmit`, `next lint --max-warnings 0`, `next build` und
`npm run check:whatsnew`; `scripts/gates.sh all` deckt das ab und prüft
darüber hinaus (Was-ist-neu-Parität, Paritäts-Prüfung Gate ↔ CI,
Prozess-Werkzeuge — alle drei nur lokal).

Alle drei Kommandos oben sind **schwere Läufe** (sie starten Container) und
gehören zwischen die beiden Blöcke der Rechner-Sperre (Randbedingung
„Parallelität" oben). Die Zahlen für dieselbe Randbedingung stehen im
Schwellen-Inventar (`CLAUDE.md`, Zeile „Parallelität innerhalb eines
Laufs") — im Brief ausgeschrieben, nicht als Zeiger.

### Projekt-Auflagen für Block 7 (Fixtures) und Block 8 (Randbedingungen)

Ein Bauer liest nur den Brief, nicht `CLAUDE.md` — deshalb stehen diese
Regeln hier, damit sie in jeden Brief wandern:

- **Block 7: Testdaten und Fixtures erfunden**, nie aus dem echten Bestand:
  Das Repo ist öffentlich, ein echtes Fixture wäre eine Veröffentlichung
  (`CLAUDE.md`, „Sicherheit").
- **Block 8: Echte Umlaute** in allen deutschen Texten; interne ASCII-Werte
  nie roh ins UI (Label-Maps); **UI-Texte immer in DE und EN**
  (`web/src/lib/i18n.tsx`).
- **Block 8: Datenbank-Tests gegen echt migriertes Postgres** (`conftest.py`,
  SQLite ist ausgeschlossen). ORM-IDs **vor** dem `commit()` lesen
  (`flush()`), vor `_run_light_migrations()` ein `rollback()` — sonst hängt
  die Sitzung „idle in transaction" (`lehren.md` §2).

**Sperrdateien nur im Container.** Node und npm SIND lokal installiert, aber in
einer anderen Hauptversion als Container und CI (gemessen 28.09.2026:
`npm --version` lokal 11.16.0; im Abbild `node:22-alpine` seit #117 npm
10.9.9, gemessen 26.10.2026; die CI setzt `node-version: 22`). Ein lokal
erzeugter `package-lock.json` kann in der CI scheitern. Lock-Änderungen
deshalb nur so:

    MSYS_NO_PATHCONV=1 docker run --rm -v "<web>":/w -w //w node:22-alpine npm install --package-lock-only

### Hausbelege

Die Vorlage führt die Regeln verallgemeinert. Hier stehen die Fälle, an denen
sie bei uns entstanden oder bestätigt wurden:

- **Ohne Brief fehlt Block 5.** #52, #53, #55 und #67 entstanden ohne Brief;
  bei #52 fehlte genau der Rot-Beweis, den Block 5 verlangt hätte.
- **Block 3 ist der teuerste, wenn er fehlt.** Die Frage nach allen Aufrufern
  brachte im #55-Slice den schwersten Fund: dasselbe Schema wird serverseitig
  aus OCR-Text gebaut.
- **Eine Umfangsgrenze ist kein Bewegungsverbot.** Der Brief zu #66 verbot,
  `_apply_full` anzufassen — genau dort saß die Ein-Zeilen-Behebung eines
  Panel-Funds. Richtig ist der Befund mit Ziel: „`enrich_catalog` trägt
  dieselbe Klasse, wird aber in #75 eigens behandelt“.
- **Die Brief-Prämisse kann falsch sein.** Die arbitrierte #36-Auflage
  „Auswahl auf rohen Daten“ war zu grob und erzeugte eine Regression.
- **Frage 8 — die Zusage abzählen.** #82 versprach „ein Fehlschlag vernichtet
  kein vorhandenes Bild“; die Zusage galt für drei Aufrufstellen und zwei
  Türen. Erst das Abzählen machte daraus vier Tests statt zwei.
- **Frage 9 — eine Eigenschaft nur des geheilten Zustands.** #98: Rauchtest
  18/18 grün, während die Bild-Optimierung wochenlang nichts tat. Getragen
  haben `content-type: image/webp` und `x-nextjs-cache: HIT`.
- **Frage 10 — real verschiedene Ausgangszustände.** #99: „Frische
  Installation zeigt nichts“ ließ den Erst-Rollout stumm, weil jeder
  Bestandsnutzer den neu eingeführten Schlüssel nicht hatte (`lehren.md` §17).
  Dieselbe Frage fand in der Vorlage ihre allgemeine Form.
- **Eine Brief-Vorgabe ist Widerlegungs-Auftrag.** Ebenfalls #99: Die Stimme,
  die den Brief kannte, hakte das Verhalten ab; gefunden hat es die Stimme,
  die ihn nicht kannte.
- **Ein Entwurfs-Umbau in der Nacharbeit braucht einen frischen Bauer.** Die
  zweite #66-Runde baute aus einer langen Transaktion zwei kurze und die
  Fehlerbehandlung um — das hätte nach dem Kriterium einen frischen Bauer
  gebraucht. Es ging gut, war aber nicht abgesichert.
