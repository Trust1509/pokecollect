# Review-Panel: drei Stimmen über denselben Diff

Verbindlich ab **Risikoklasse R2** (Tabelle in `CLAUDE.md`), vor dem Landen. Zweck ist
**Diversität im Urteil**, nicht Token-Ersparnis.

> Die **Werkzeuge** (Skripte, Docker-Image, OpenRouter-Zugang) liegen bewusst
> **außerhalb dieses Repos** unter `model-panel/` neben dem Projektordner —
> dort liegen Zugangsdaten, und die haben in einem Repo nichts verloren. Diese
> Datei ist die **Anleitung**: Sie muss auch dann gelten, wenn die Werkzeuge
> einmal anders heißen.

## Modell und Stand gehören ins Ergebnis

Je Stimme in der Überschrift des Panel-Kommentars
(`### Stimme 2 — GPT über Codex (gpt-5.x, 2026-08-20)`). Das Gegenstück am
Commit (`Built-With:`) steht als Commit-Regel in `CLAUDE.md`. Zwei Gründe: Die Herkunfts-Regel
ist sonst nach vier Wochen nicht mehr durchsetzbar — „wer hat das gebaut" steht
nirgends. Und jede Aussage über Modellverhalten bleibt Anekdote, solange das
Ergebnis den Modellstand nicht trägt. Anbieter ziehen still nach, deshalb das
Datum.

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

**Stimme 3 — klassenabhängig besetzt (v1.12.0):** Bei **R3** eine **zweite
blinde Claude-Repo-Stimme, adversarial gerahmt** — vier R3-Runden Messbasis,
in jeder exklusive Funde der Blocker-Klasse. Bei R2 entfällt Stimme 3
(Mindestprüfung: Erst- + Zweitstimme). **DeepSeek ist keine Panel-Stimme
mehr** — diff-only konvergierte nur und lieferte hier eine falsche Entwarnung
am Blocker (#66); das Werkzeug bleibt als Ad-hoc-Zweitmeinung (Budget bis
2 $/Monat, Owner 15.08.2026; bei `402` Owner informieren).

**Besetzung folgt dem Diff-Typ, der Umfang der Klasse** (v1.12.0, sieben
Slices Messbasis): backend-Diffs → Zweit-/Drittstimme tragen; reine
frontend-/Text-Diffs → die blinde Erststimme allein ist tragend und
ausreichend. Jede Stimme zählt mit ihren Funden, nie mit ihrer Freigabe.

## Ablauf

0. **Ausführbarkeit prüfen, nicht Erreichbarkeit** (v1.13.0), bevor der Slice
   fertig gemeldet wird. Die übliche Vorabprüfung („sag OK") testet den
   Modell-Aufruf, nicht die Werkzeuge dahinter: Eine Stimme, die nichts
   ausführen kann, aber weiter antwortet, liefert ein Ergebnis, das äußerlich
   wie ein geprüftes aussieht — gleiche Form, gleiche Schwere-Angaben, ohne
   einen ausgeführten Befehl darunter. **Die Vorabprüfung setzt einen BEFEHL
   ab, dessen Ausgabe zurückkommen muss** — `git rev-parse HEAD` gegen den
   erwarteten Stand genügt; für Stimme 2 zusätzlich der gepushte Zweig.
   Kommt die Ausgabe nicht, ist die Stimme ausgefallen und der Ausfall-Vermerk
   gilt. **Konnte eine Stimme ihre Werkzeuge nicht nutzen, steht das unter
   IHRER Überschrift im Panel-Kommentar** — eine Freigabe aus reiner Lektüre
   ist etwas anderes als eine aus Reproduktion.
1. Prüf-Zweig pushen (Stimme 2 braucht ihn). **Stimmen mit Repo-Zugriff
   arbeiten in einem eigenen `git worktree` auf dem gemessenen Commit**
   (v1.13.0); Mutationen, Container und Images tragen ein stimmen-eigenes
   Präfix, das Aufräumen wird nachgewiesen. Der Hauptagent darf den Hauptbaum
   währenddessen weiterbewegen — der eigentliche Gewinn: **Die Nacharbeit
   kann beginnen, bevor die letzte Stimme fertig ist.** Bei uns real
   getroffen: Eine Erststimme prüfte `cfe0b25`, während im Hauptbaum bereits
   der nächste Slice entstand; sie musste zwei Stände auseinanderhalten und
   hat den fremden Commit ausdrücklich benannt. Das ist die Quellen-Regel
   (`git show <commit>:`) zu Ende gedacht.
2. **Alle drei parallel starten**, nicht nacheinander — zusammen 20–40 Minuten,
   sequenziell ein Vielfaches.
3. **Arbitrieren.** Jeden Blocker **am Code oder an der laufenden App
   reproduzieren**. Prüfer-Konvergenz ersetzt keine Reproduktion; Mehrheit
   entscheidet nie allein. **Widersprechen sich Stimmen, entscheidet die
   Reproduktion** — nicht die Mehrheit, nicht die Plausibilität der Begründung.
4. **Nacharbeit** — wer sie baut, entscheidet das Kriterium in `bau-brief.md`
   (mechanische Auflage → derselbe Bauer; Auflage, die den Entwurf berührt →
   frischer Bauer). Hier stand bis zum v1.8.2-Abgleich pauschal „derselbe
   Subagent" — das widersprach der Nachbardatei, und zwar so, dass es kein
   Leser beisammen sah. Im Auftrag stehen das **Bestätigte** und die
   ausdrücklich **abgeräumten** Fehlbefunde. Der Nacharbeits-Brief trägt **dasselbe Pflicht-Gerüst** wie ein
   Erstbau (`bau-brief.md`) plus den Block „Ausdrücklich abgeräumt — hier ist
   nichts zu tun".

   **Die Prüfpflicht hängt am GELANDETEN ZUSTAND, nicht am Slice** (v1.8.0): Was
   am Ende auf `main` liegt, ist geprüft — egal in wie vielen Anläufen es dorthin
   kam. Nacharbeit ist damit automatisch erfasst. Eine verkürzte zweite Runde
   (nur die blinde Stimme, zugeschnittener Auftrag) reicht; hier fand genau die
   sechs weitere Punkte, alle exklusiv.
5. **Panel-Kommentar** am Issue, Form nach `panel-kommentar.md`.

### Die Sonde, die verwirft, braucht den stärkeren Nachweis

Ein bestätigter Fund wird gefixt und nachgeprüft — ein **verworfener verschwindet
für immer**. Die Ad-hoc-Sonde des Arbiters ist damit die gefährlichste Prüfung im
Verfahren und hatte bisher kein Gegenstück zum Rot-Beweis.

- **Gegenfrage vor jedem Verwerfen: „Welche Eingabe würde der Stimme recht
  geben?"** Wer sie nicht beantworten kann, hat nicht widerlegt, sondern nicht
  reproduziert.
- **Wer einen STRUKTURELLEN Befund mit „aktuell nicht erreichbar" abstuft,
  begründet das** (v1.13.0): Wer garantiert, dass es so bleibt? Das ist die
  Umkehrung der üblichen Richtung — sonst gewinnt die Messung immer, und
  genau die Messung, die eine Repo-Stimme stark macht, macht sie hier milder.
  Hausbeleg (#91-Vorgeschichte): Die Wildcard in `remotePatterns` war
  strukturell falsch, obwohl „heute niemand im LAN" gemessen stimmte; die
  Eingrenzung kostete eine Konfigurationszeile.
- **Auch eine Text-Suche mit null Treffern ist eine verwerfende Sonde (v1.12.3).**
  grep arbeitet zeilenweise — eine Wortgruppe über einem Prosa-Umbruch liefert
  null Treffer, obwohl sie dasteht, und ohne `-i` verfehlt „Synthese" das
  „SYNTHESE". Vor dem Verwerfen: `grep -rni` mit dem **seltensten Einzelwort**
  (ein Einzelwort kann nicht umbrochen werden); mehrwortig nur umbruchtolerant
  (`grep -Pzo` mit `\s+`). Gilt auch für die Zählprobe beim Verschieben
  (v1.12.2: den neuen Wortlaut zählen, die Zahl muss eins bleiben).
- **Drittes Urteil neben bestätigt/verworfen: „richtiger Instinkt, falsche
  Begründung."** Der Fund bleibt, die Begründung wird ersetzt. Ohne diese
  Kategorie werden echte Befunde als Fehlbefunde abgeräumt.
- **Schwere-Umstufung durch den Arbiter ist erlaubt und wird gekennzeichnet**
  (`KLEIN → WICHTIG (arb.)`), sonst ist sie stille Meinung.

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

## Verhältnismäßigkeit — die Risikoklassen-Tabelle entscheidet

**Die verbindliche Tabelle (R0/R2/R3/R4) steht in `CLAUDE.md`** — dort wird
entschieden; sie hat die frühere Trivial-Liste und die Pflichtfälle ERSETZT
(v1.11.0). Hier steht das Verfahren je Klasse und, warum die Auslöser so
aussehen, damit sie beim nächsten Abgleich nicht aufgeweicht werden.

**Verfahren je Klasse:** R0 → lokale Gates. R2 → blinde Erststimme +
unabhängige Zweitstimme. R1 → Auslöser und Mindestprüfung stehen NUR in der Tabelle
(`../../CLAUDE.md`, Zeile *R1*; v1.12.2: ein Eigentümer, keine Prosa-Kopie) —
hier nur das Verfahrens-Detail: Die Begründung der Verkürzung steht unter der
Überschrift der ausgelassenen Stimme, nicht als Fließtext. R3 →
volles Panel, Drittstimme als **zweite blinde Claude-Repo-Stimme, adversarial
gerahmt** (nicht diff-only — die schweren R3-Funde liegen in der Beziehung
zwischen Diff und Umgebung), plus **risikospezifische Probe durch die echte
Tür**. R4 → wie R3, zusätzlich Owner-Freigabe vor Release.

**Ein neuer Test ist KEINE reine Testinfrastruktur** (v1.8.0). Er behauptet
etwas über das Verhalten — und kann falsch behaupten. Für dieses Repo heißt das
rückwirkend: Die Scheiben #52 (Rauchtest) und #70 (mobil) sind unter der alten,
weicheren Lesart ohne Panel gelandet. Beide trugen tatsächlich falsche
Behauptungen — der Querscroll-Wächter war vakant, und eine Farb-Mutation blieb
grün, weil sie an der unwirksamen Stelle saß. Aufgefallen ist beides nur durch
den Rot-Beweis, nicht durch ein Panel, das es nicht gab.

Warum sie abschließend ist, nicht beispielhaft: „Ist das trivial?" ist genau die
Frage, bei der man sich unter Zeitdruck selbst überzeugt.

Warum **Fremdcode** ein eigener R3-Auslöser ist (v1.11.1 — der Auslöser hieß
früher „Herkunft" und war zu weit gefasst: „Code, den niemand aus dem Team
gebaut hat" wäre bei durchgängiger Subagenten-Arbeit IMMER erfüllt, R2 wäre
leer; gemeint ist Produktionscode eines FREMDEN Systems, nicht der eigene
Bau-Subagent): Ein zugelieferter Zweig war fachlich unauffällig und tauschte
einen dokumentierten Endpunkt gegen einen ausdrücklich undokumentierten; alle
mitgelieferten Tests waren grün — sie stammten vom selben Autor und prüften
dessen Annahme. Das Risiko hängt am fremden Ursprung, nicht am Thema.

> **Nachtrag 20.08.2026:** Hier stand bis eben die zweite Hälfte der Pflichtliste
> („Immer volles Panel bei …") — ich hatte beim Verschieben nach `CLAUDE.md` nur
> die erste Hälfte mitgenommen. Damit stand die Schwelle zwei Stunden lang in
> zwei Dateien (v1.9.0 §17 / „eine Schwelle hat genau einen Eigentümer").
> Gefunden durch die Suche, zu der das Rückmeldungs-Issue aufgefordert hat.

**Sonderfall:** Eine Testinfrastruktur-Scheibe, die als **Sicherheitsnetz**
gemeldet wird, ist nicht trivial — sie braucht mindestens den Rot-Beweis über
die ganze Suite (`bau-brief.md`).

## Quellen-Regel: keine Stimme sieht den Arbeitsbaum

Der Kontext jeder Stimme kommt aus `git show HEAD:<pfad>` oder dem
Commit-Diff — **nie aus dem Arbeitsbaum** (v1.12.0). Sobald irgendein Prüflauf
mutieren darf (Rot-Beweise!), ist der Arbeitsbaum kein definierter Zustand
mehr; anderswo war der schwerste „Befund" einer Stimme ein Mutations-Marker.
Unsere Reviewer sabotieren bereits in gemounteten Kopien — die LESE-Quelle
muss trotzdem HEAD sein, nicht der Baum.

## Fremdstimmen: Suchverbot, und Ausfall heißt Ausfall

Jeder Auftrag an eine Fremdmodell-Stimme enthält ein ausdrückliches
**Suchverbot** (kein Web-Zugriff, keine Recherche nach Repo, Commit oder
Namen) — anderswo suchte eine Stimme bei Sandbox-Ausfall selbstständig im
Netz nach Repo und Commit. Ein Werkzeug-/Sandbox-Ausfall wird als **AUSFALL**
gemeldet, nie als Stimme mit dünnem Ergebnis. **Erfolgskriterium eines
Fremdstimmen-Aufrufs ist die SYNTHESE, nie der Exit-Code** (v1.12.1): Ein
Wrapper kann mit Exit 0 enden, ohne dass je ein Urteil entstand — dieselbe
Familie wie unsere Exit-hinter-der-Pipe-Fälle (lehren.md Klasse 8), nur an
der Werkzeuggrenze.

## Wenn eine Stimme ausfällt

Werkzeug nicht verfügbar, kein Guthaben, Dienst down: **mit zweien weitermachen,
im Kommentar vermerken und es dem Owner sagen.** Nicht stillschweigend
reduzieren, und die fehlende Stimme nachholen, solange der Slice nicht
ausgeliefert ist.

Ein Slice ohne vollständiges oder ausdrücklich vermerkt-verkürztes Panel gilt
als **nicht geprüft** und wird nicht ausgeliefert.

**Ausfall ist stimmen-neutral** (v1.12.0): Auch die eigene (Claude-)Stimme
fällt aus — ein Session-Limit mitten im Lauf ist ein AUSFALL unter ihrer
Überschrift, nie ein dünnes Ergebnis; hier zweimal real passiert. Ein
abgebrochener Prüflauf wird wie ein abgebrochener Bau behandelt: erst den
Baum prüfen, dann weiterreden. **Klumpenrisiko bei R3** (zwei von drei
Stimmen am selben Kontingent): bei knappem Kontingent laufen die beiden
Claude-Stimmen ZUERST. **Ersatzregel für die Zweitblinde (v1.12.1,
ergebnis- statt transportbezogen):** GPT übernimmt die adversariale Rahmung
mit **vollem Quelltext auf `git show HEAD:`-Stand** — Review-Zweig,
Commit-Snapshot oder Quelltext inline sind gleichwertig, solange die Quelle
stimmt (anderswo trug die Inline-Variante den einzigen echten Treffer der
Runde). **Die Ersatzregel ist eine Aussage über den Transport, keine Ausnahme
von der Datengrenze (v1.12.2):** Was einer Fremdstimme nicht gegeben werden
darf — Owner-Bestand, Schlüssel, Teststand-Daten (definiert in `../../CLAUDE.md`,
Secrets/Teststand) — darf ihr auch inline nicht gegeben werden.
