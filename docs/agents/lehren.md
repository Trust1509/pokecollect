# Lehren aus gebauten Slices

Fehlerklassen, die uns **in diesem Projekt** real getroffen haben — mit dem
Nachweis, warum sie durchrutschten. **Nicht chronologisch, sondern nach
Klasse:** Die Frage beim Lesen ist nicht „was ist damals passiert", sondern
„welche dieser Fallen liegt in meinem Slice".

Die Einzelfälle stehen in den GitHub-Issues und im CHANGELOG; hier steht, was
übertragbar ist. Prozessregeln stehen in `CLAUDE.md`, das Panel in `panel.md`.

Verweise auf eine Lehre schreiben wir `§N`. Nur diese Form prüft der
Verweis-Wächter (Gate P), und nur in `CLAUDE.md` und `docs/agents/*.md`.
Code-Kommentare und Skripte prüft niemand. Dort stehen zwei Formen:
`lehren.md §N` und die ältere „Klasse N" (gemessen 19.10.2026: 15 Zeilen in 10
Dateien, darunter `scripts/gates.sh` und `.githooks/commit-msg`). Beim
Umnummerieren beide mitsuchen:

    git grep -nE 'Klasse [0-9]|lehren\.md`? ?§ ?[0-9]' -- ':!CLAUDE.md' ':!docs/'

Der gemeinsame Prozess-Stand kommt aus `Trust1509/agent-projekt-template`.
Fällt hier eine Lehre an, die **nicht am eigenen Stack klebt**, gehört sie als
Issue dorthin (Label `prozess-lehre`) — nicht nur in diese Datei, sonst erfahren
die anderen Projekte nie davon.

## Vor jedem Slice: fünf Fragen

Die Abschnitte unten liest man einmal. Die Kurzfassung, die tatsächlich vor den
Slice gehört — wer sie beantwortet, hat die teuersten Klassen unten abgedeckt:

1. **Womit beweist dieser Slice, dass er wirkt** — und war dieser Beweis je rot?
2. **Wer ruft den geänderten Code auf?** Jeden Aufrufer, auch den serverseitigen.
3. **Welche Aussage im Repo wird durch diesen Diff falsch?** (Doku, Kommentare,
   Docstrings, Anweisungen für später.)
4. **Beruht ein Schutz hier auf einer Angabe, die das Geprüfte über sich selbst
   macht?** (Ein Datenstand, den der Schreiber selbst setzt, ist keine Prüfung.)
5. **Was kann ich nicht prüfen** — und wo steht das, damit es nicht still zur
   Schuldenliste wird?

**Und wenn etwas schiefging: Ein Eintrag hier endet mit einer Regel oder einem
Wächter, nie mit einem Vorsatz.** „Künftig sorgfältiger prüfen" ist keine
Gegenmaßnahme, sondern das Eingeständnis, keine gefunden zu haben. Beim
Aufschreiben die Ursachen einzeln prüfen, nicht nur die erste: **Quelle,
Werkzeug, Umgebung, Messung, Annahme, Prozess** — wer nur die erste nennt,
baut eine Gegenmaßnahme, die den zweiten Weg offen lässt (aus der Vorlage,
Abgleich v1.17.2).

---

## 1. Grün heißt nicht bewiesen

**Rot-Beweis für jeden neuen Test.** Den Fix sabotieren und zeigen, dass der
Test fällt. Ein Test ohne Rot-Beweis ist eine Behauptung.

**Das gilt auch für ganze Suiten.** Der Rauchtest (#52) wurde nicht als „12/12
grün" gemeldet, sondern erst nachdem zwei bekannte Fehler absichtlich wieder
eingebaut waren:

- Die Sealed-Liste lädt nach dem Speichern nicht nach (der Owner-Fund aus
  v1.8.1) → Suite wurde **rot**. Das Netz trägt.
- Der Auth-Guard leitet nicht mehr um → Suite blieb **grün**, und zwar zu
  Recht: Der Zugangsschutz hängt an **zwei** unabhängigen Mechanismen (Guard in
  der Oberfläche, 401-Interceptor in `api.ts`). Der Test behauptet „niemand
  kommt ohne Anmeldung hinein", nicht „der Guard funktioniert".

**Die Mutation, die NICHT rot wird, ist die lehrreichere** — sie zeigt die
Grenze der Aussage. Diese Grenze gehört als Kommentar **in den Test**, nicht in
den Bericht, wo sie niemand mehr liest.

**Testdaten müssen den Fall enthalten.** Der erste Rauchtest-Lauf war rot, weil
die angelegte Testkarte keine Pokédex-Nummer hatte — die Startseite fragt mit
`pokedex_view=true` und zeigt solche Karten nie. Kein Produktfehler, sondern
Testdaten, die den geprüften Fall gar nicht herstellen.

**Git wirkt auf den REPO-ZUSTAND, nicht auf die Absicht — auch beim Push.**
Bekannt aus `git add -A` und `git checkout --`; am 04.09.2026 in der teuersten
Variante wiederholt: Ein Push nach zwei Doku-Commits nahm **vier ungepanelte
Commits eines parallel arbeitenden Bau-Subagenten** mit auf `main` — beide
hatten auf denselben Branch im selben Baum committet. Der Code war grün, der
Prozess gebrochen: Die Prüfung fand danach statt, nicht davor. Zwei Regeln,
die zweite ist die tragende: **(a)** Vor jedem Push `git log --oneline
@{u}..HEAD` lesen — ein Push landet alles, nicht das Letzte. **(b)** Parallel
arbeitende Bau-Subagenten bekommen einen eigenen Worktree mit eigenem Branch;
dann ist das Mitnehmen strukturell unmöglich statt nur verboten. Eine Regel,
deren Einhaltung von Aufmerksamkeit abhängt, ist eine Notiz (§10).

**Und der Rot-Beweis ist genau so ein Fall — belegt am 05.09.2026.** Mein
Sabotage-Skript zu #98 nahm jede Mutation mit `git checkout -- <datei>`
zurück. Das ist richtig, solange die eigene Arbeit **committet** ist — sie war
es nicht. Der Rückbau setzte drei Dateien auf `HEAD` und löschte damit die
Nacharbeit, die er schützen sollte; der zweite von drei Rot-Beweisen lief
dadurch gegen den unsabotierten Stand und war wertlos, ohne dass etwas rot
wurde. Das Perfide: Ein verunglückter Rot-Beweis meldet sich nicht — er meldet
**grün**, und grün sieht aus wie Erfolg.

Die Lehre stand zu diesem Zeitpunkt bereits geschrieben (`git checkout --`
oben in genau diesem Absatz) und hat trotzdem nicht getragen, weil sie eine
**Warnung** war und kein **Schritt**. Daraus wurde eine Schrittfolge — und
die steht seit dem Abgleich v1.17.2 **nur noch in `bau-brief.md`, „Der
Rot-Beweis ist eine Schrittfolge"** (fünf Schritte: 2b weist die Sabotage
im Artefakt nach, 4 prüft den Baum mit `git status --short --ignored`, 5
ist die Gegenprobe). Hier stand bis dahin eine eigene Fassung mit vier
Schritten, die neben der längeren Vorlagen-Fassung still veraltet wäre. Die
Fälle, aus denen die Schritte stammen, sind unsere — dreimal in EINEM Slice
(05./06.09.2026):

- Eine Regex-Ersetzung setzte zwei Felder angeblich auf denselben Wert —
  nachgemessen 1678 gegen 1671 Zeichen, sie waren nie gleich.
- Die Tests lagen in einem ANDEREN Image als der Anwendungscode; nur eines
  war neu gebaut, gemessen wurde gegen die alten Tests.
- Ein Bau scheiterte still, weil seine Ausgabe nach `/dev/null` ging — der
  Container lief mit dem alten Image weiter.

Dazu am 06.09. ein vierter, beim Messen: Eine Hilfsfunktion schickte jeden
Lauf durch `| tail -1`; vier Wächter meldeten damit `exit=0`, obwohl sie
korrekt mit 1 abbrachen.

**Warum ein misslungener Rot-Beweis so teuer ist:** Er meldet keinen
Fehler — er meldet **grün**. Und grün ist die Farbe, die man sehen will;
deshalb prüft dort niemand nach. Die drei Fälle aus dem einen Slice sahen wie gültige
Messungen aus, und aus zweien habe ich einen falschen Befund abgeleitet,
bevor er aufflog.

Der erste Schritt (committen) kostet fünf Sekunden und macht die Rücknahme
gefahrlos. Ohne ihn ist `git checkout --` kein Rückbau, sondern ein
Datenverlust mit grüner Anzeige.

**Ein Widerspruch zwischen zwei Dateien ist unsichtbarer als einer in einer.**
Beim Übernehmen einer neuen Regel habe ich die eine Fundstelle geändert und die
andere stehen lassen: Der Bau-Brief trug das neue Kriterium für die
Nacharbeits-Besetzung, `panel.md` daneben weiter die alte Pauschalregel. In
einem Dokument fällt so etwas beim Lesen auf; über zwei Dateien verteilt sieht
sie kein Leser beisammen — jeder befolgt die, die er zuerst findet. **Nach jeder
übernommenen Regel prüfen, wo dasselbe Thema sonst noch steht** (`grep` über
`docs/`), nicht nur die Stelle ändern, die im Abgleich benannt war.

**Beim Beheben zählt die Sorte der Datei** (v1.9.1): Eine **anleitende** Datei
(Skript, Checkliste, Anweisung) wird umgeschrieben. Eine **dokumentierende**
Datei (ADR, Protokoll, Panel-Kommentar) bekommt einen **datierten Nachtrag** —
wer sie umschreibt, löscht die Historie und damit den Grund, aus dem die
Entscheidung damals richtig war.

**Eine Messung, die der Vorlage widerspricht, ist zuerst ein Befund über die
Vorlage** (v1.9.0 §18). Zwei Projekte machten dieselbe Messung; eines schloss
„das Werkzeug ist falsch", das andere „dann heißen meine Überschriften eben
falsch". Die Vorlage ist gemeinsamer Stand, nicht Wahrheit — sie irrt
regelmäßig, und genau dafür gibt es den Rückkanal.

**Geliehene Autorität tarnt einen ungeprüften Befund.** Ein Bericht, der eine
Abweichung mit einer Quellenangabe mildert („bekannter Flake, siehe §X"), ist
gefährlicher als einer ohne Quelle — er liest sich wie nachgeschlagen und wird
leichter durchgewunken. Auch die **mildere Erklärung** einer Abweichung braucht
einen Beleg, sonst verdeckt sie den Fehler. Zitate nachschlagen, Flakes
reproduzieren; die Frage lautet nicht „hast du geprüft", sondern „was genau hast
du ausgeführt, und was kam heraus".

**Eine Prüfung, die ausgibt statt abzubrechen, ist keine Prüfung.** Vor einem
Doku-Commit habe ich korrekt festgestellt, dass fremder Code im Arbeitsbaum
liegt — die Zeile gab es aus und lief weiter, weil sie mit `&&` an den Commit
gekettet war statt davor zu stehen. Ergebnis: unbewiesene Nacharbeit landete in
einem `[skip ci]`-Doku-Commit auf `main` und musste zurückgenommen werden.
Dieselbe Klasse wie ein grüner Wächter, nur eine Stufe früher: Der Befund war
richtig, die Konsequenz fehlte. **Wer prüft, muss auch abbrechen können** —
sonst ist die Prüfung Dekoration. Praktisch: vor jedem Commit `git status`
lesen und Pfade einzeln adden, statt `git add -A` mit einer Sichtprüfung davor.

**Ein Wächter muss seine eigene Reichweite belegen.** Vier Fragen, bevor ein
Test oder Gate als Schutz gilt (aus der Vorlage §8, hier auf Tests gemünzt —
einen Produktiv-Wächter haben wir nicht):

- **Prädikat:** Prüft er dieselbe Bedingung wie der Mechanismus, den er
  absichert — oder eine ähnliche? Eine geliehene Bedingung bricht, sobald sich
  die andere ändert.
- **Quelle:** Kennt seine Aufzählung wirklich alle Fälle? Registrierungen und
  Schreibweisen gibt es meist in mehr als einer Form.
- **Ausnahmen:** Zählt er eine Ausnahme-Mechanik versehentlich als Schutz?
- **Echtprobe:** Sieht er den Aufruf überhaupt, den das System wirklich erzeugt?
  Selbst gebaute Eingaben beweisen nur, dass er auf selbst gebaute Eingaben
  reagiert.

**Der Bezugswert einer Messung kann mit dem Fehler mitwachsen.** Der mobile
Rauchtest (#70) prüfte „kein seitliches Scrollen" als
`documentElement.scrollWidth <= window.innerWidth`. Grün — auch mit einer
absichtlich 900 px breiten Seite auf einem 412-px-Schirm. Grund: In der
Handy-Emulation ist `window.innerWidth` die **visuelle** Ansichtsfläche und
wächst mit dem Überlauf mit (gemessen: 901 statt 412). Der Vergleich war damit
immer wahr. Ehrlicher Bezug ist `clientWidth` des scrollenden Elements — die
Breite, die wirklich da ist. **Frage bei jeder Messung: Bewegt der Fehler, den
ich suche, auch meinen Maßstab?**

**Eine Mutation, die grün bleibt, muss erst die wirksame Stelle treffen.** Beim
Rot-Beweis derselben Scheibe wurde der Hintergrund in `globals.css` auf Weiß
gesetzt — nichts wurde rot. Nicht weil der Test schwach war, sondern weil die
Farbe aus einer Tailwind-Klasse in `layout.tsx` kommt und der Klassen-Selektor
den Element-Selektor schlägt. Erst die Mutation an der wirksamen Stelle machte
genau einen Test rot. **Bevor „bleibt grün" als Aussage über den Test gilt:
belegen, dass die Mutation überhaupt ankam.**

**Property-Tests dort, wo Geld gerechnet wird** (#53): Beispieltests prüfen die
Fälle, an die wir gedacht haben. Für die Rechenkerne gilt die Eigenschaft — ein
angezeigter Preis stammt **immer** aus den Quelldaten, nie aus einer Rechnung.

**Wer eine Zahl gegen die Wirklichkeit prüft, umhüllt die GRENZE, nicht die
Stelle, die er verdächtigt** (Vorlage §9, v1.17.0). Dort druckte eine Probe
eine Aufrufzahl, die zu hoch schien; ein Zähler in der verdächtigten Funktion
bestätigte den Verdacht — es gab aber eine zweite Stelle, die denselben
Befehl startet, und die ursprüngliche Zahl war richtig. Eine Messung, die nur
die vermutete Stelle instrumentiert, ist eine Bestätigungsmaschine. Die
Grenze ist der Systemaufruf, die HTTP-Anfrage, der Datenbank-Treffer.

**Auch die Gate-Kette ist eine Mutation** (Vorlage §1, v1.18.2). „Die neue
Prüfung aus der Gate-Datei streichen" gehört in jede Mutationsliste; in einem
anderen Projekt rutschte genau das durch, weil die Selbstprobe das Prüfskript
prüfte, nicht seinen Aufruf. Bei uns gilt das für jede Zeile von Gate P in
`scripts/gates.sh`: Fehlt eine, wird keine der Selbstproben rot (#106).

**Wer einen Mutanten für äquivalent erklärt, schuldet die Sonde, die ihm recht
gäbe** (Vorlage §1, v1.18.2). Überlebt eine Mutation alle Tests, ist entweder
der Code überflüssig, oder es fehlt ein Test — und unter Druck wird die bequeme
Erklärung gewählt. Dort entfernte ein Bauer einen „überflüssigen" Block vor dem
Commit; der Blindprüfer fand mit einer Sonde den Fall, in dem der Block
Verhalten trug, und die Commit-Nachricht beschrieb den Block weiter. **Ein
Commit-Text wird gegen den Diff gelesen, nicht gegen die Absicht.** Ohne Sonde
bleibt der Code stehen.

**Ein Eigenschafts-Wächter prüft die STÄRKE, nicht den Wahrheitswert**
(Vorlage §1, v1.18.2). Ein Sperr-Wächter, der „irgendeine Sperre" verlangte,
blieb dort grün, als eine schwächere Sperrform den Fehler auf PostgreSQL
zurückbrachte. Der Wächter liest den Rohwert und vergleicht ihn mit der
verlangten Stufe.

**Fixtures tragen feste Daten oder Daten relativ zum Test-„heute", nie das
echte Datum** (Vorlage §1, v1.18.2): Zwei Tests mit dem echten Datum kippten
dort am Quartalswechsel auf jedem Stand rot. Bei uns stand das echte Datum am
19.10.2026 in 15 Zeilen von 8 Testdateien (gesucht nach `date.today()`,
`datetime.now(`, `datetime.utcnow(` und `time.time()` unter `backend/tests/`,
nach `new Date()` und `Date.now()` unter `e2e/tests/`; ob ein Treffer ein
Ergebnis vom Datum abhängig macht, ist nicht je Treffer geprüft). Umgestellt
wird bei der nächsten Arbeit an der jeweiligen Suite.

**Eine Selbstprobe, deren Eingabe das Format eines fremden Werkzeugs nachbaut,
prüft die Annahme mit, statt sie zu prüfen** (Vorlage §1, v1.18.2). Dort
scheiterte ein Wächter für Commit-Nachrichten zweimal an nachgebauten
Eingaben: Ein Fall erwartete, dass git eine Kommentarzeile entfernt — bei
`git commit -F` tut es das nicht —, ein zweiter baute den `-v`-Anhang ohne die
zwei Zeilen, die git dort schreibt; der Wächter lehnte danach jeden echten
Commit mit `-v` ab, die Probe blieb grün. **Regel:** Mindestens ein Fall
bekommt seine Eingabe vom fremden Werkzeug selbst (echtes `git commit`). Bei
uns betrifft das `.githooks/commit-msg`; der Hook hat bisher gar keine
Selbstprobe (gemessen 19.10.2026). Entsteht eine, gilt diese Regel für sie.

---

## 2. Migrationen ohne Framework

Wir haben **kein Alembic**. `create_all` legt nur neue Tabellen an;
Spaltenänderungen sind idempotente Light-Migrations in
`backend/app/main.py::_run_light_migrations` (`ALTER TABLE … ADD COLUMN IF NOT
EXISTS`, additiv, nie destruktiv ohne Owner-OK).

Daraus folgt eine eigene Prüfpflicht — der Roundtrip anderer Projekte
(`downgrade -1`) ist hier gegenstandslos, **die Datenerhalt-Probe nicht**:

1. Bekannte Altdaten **in der alten Form** schreiben.
2. Migration fahren.
3. Erhalt **und** korrekte Umsetzung auslesen (nicht nur „Zeile ist noch da").
4. Migration ein **zweites Mal** fahren und Gleichstand zeigen.

Schritt 4 ist die Zusatzpflicht dieser Bauform: Was bei jedem Start läuft, läuft
auch über schon migrierte Daten. Muster: `backend/tests/test_63_muster.py`.
**Die Datenerhalt-Stichprobe deckt die ANGEFASSTEN Tabellen** (Vorlage,
v1.12.0): Eine Stichprobe in einer unbeteiligten Tabelle ist schlechter als
keine — anderswo loggte ein Roundtrip den eigenen Datenverlust und blieb grün.

**Expand–Contract ist Pflicht** bei Semantik-Änderungen: erst additiv erweitern
(beide Formen lesbar, Alt-Zeilen bekommen einen Default — vgl. `region` DEFAULT
`'west'`), dann die Konsumenten umstellen, **erst in einem späteren Release**
verengen. Nie beides im selben Release. Bei Semantik-/Typwechsel eines
bestehenden Feldes **alle** Konsumenten auf Alt-Werte absichern — im
Schwesterprojekt hat genau das in Produktion gekracht, beim ersten unpassenden
Bestandswert.

**Falle beim Testen der Migration:** ORM-IDs **vor** dem `commit()` lesen
(`flush()`), und vor `_run_light_migrations()` ein `rollback()`. Ein Lesezugriff
nach dem Commit öffnet still eine neue Transaktion — die Sitzung steht dann auf
„idle in transaction" und blockiert die `ALTER`-Anweisungen. Das Gate hing so
zehn Minuten, ohne Fehlermeldung.

---

## 3. Eingaben und stille Ausfälle

**Ungültige Eingabe muss 4xx werden, nicht 5xx** (#55). Steuerzeichen in Texten
und ein ausdrückliches `null` auf Pflichtfeldern endeten im Serverfehler — bei
einem Treffer auf den Einstellungen legte das **jede** Einstellungsseite lahm,
bei einem Treffer auf einer Karte **die ganze Kartenliste**.

Drei Regeln, alle aus Panel-Funden:

- **Die Sperre gehört auf den SCHREIB-Weg**, nicht an die gemeinsame
  Basisklasse. Hing sie dort, prüfte sie auch die **Antworten** — und
  Bestandsdaten mit Steuerzeichen (Alt-Backup, früherer 500er-Pfad) waren nicht
  mehr lesbar.
- **Serverseitig erzeugte Texte säubern statt ablehnen.** Dasselbe Schema wird
  aus OCR-/Modellantworten gebaut; Tesseract liefert Seitenvorschübe. Ablehnen
  hieße dort: Absturz statt Rückfall auf OCR.
- **Was schon in der Datenbank liegt, heilt keine Schreibsperre.** Ein „None" in
  einer Zahl-Einstellung und NULL-Flags mussten per Migration repariert **und**
  beim Lesen toleriert werden.

**Die eigene Sonde kann den Teststand vergiften.** Genau dieses „None" stammte
aus einer Probe-Anfrage von mir. Erwartungswerte vor der Sonde fixieren, und
nach Sonden aufräumen.

**Eine Liste, die kappt, muss es sagen.** Gilt hier besonders für Katalog- und
Auswahl-Türen: ein Sprachmodell kann „das sind alle" sonst nicht von „das ist
der Anfang" unterscheiden.

Zwei Regeln aus einem Prod-Fund der Vorlage (§5, v1.17.0: ein
Wartungsschritt konnte einen Container nicht starten, schrieb eine Warnung
ins Protokoll und lief weiter — der Container stand elf Tage in „Created"):

- **Jede Prod-Wirkung braucht einen Meldeweg in die Oberfläche — am
  sichersten einen Zustand, den die Oberfläche selbst MISST**, nicht eine
  Meldung, die jemand lesen muss. Ein Urteil über Zeitstempel unterscheidet
  nicht zwischen „läuft und tut nichts" und „läuft nicht". Bei uns
  betrifft das jeden Hintergrundjob, etwa die geplanten Preis-Aktualisierungen.
- **Die Tür-Probe misst die QUELLE, nicht die Anwesenheit.** „Der Container
  läuft" ist auch mit falscher Mount-Quelle wahr (Docker Desktop legt eine
  fehlende Quelle als Verzeichnis an). Geprüft wird, WAS eingehängt ist
  (`docker inspect … .Mounts`), nicht DASS etwas läuft.

---

## 4. Fremde Datenquellen

- **TCGdex kennt keine Sprachdimension bei Preisen.** `de`, `en` und `fr`
  liefern dasselbe Cardmarket-Produkt. Wer „deutscher Preis" anzeigen will,
  bekommt das aus dieser Quelle nicht — die Grenze gehört ins UI-Label, nicht in
  eine Annahme (offen als #68).
- **Die TCGplayer-`abbreviation` ist ein anderes Vokabular als die
  PTCGO-Codes.** `TR` ist dort Team Rocket 1999, nicht Team Rocket heute.
  Zuordnung nur über Vokabular-Familie **plus** Nenner-Verifikation.
- **Cardmarkets `-holo`-Felder bepreisen die Foil-Variante.** Für Karten ohne
  echte Holo-Variante ist genau das der Reverse-Preis.
- **Muster-Karten (Pokéball/Masterball) sind eigene Produkte** — bei TCGplayer
  und bei Cardmarket („Additionals"), und TCGdex kennt sie gar nicht. Ein Preis
  ohne Varianten-Angabe ist deshalb wertlos; die Anzeige nennt seit v1.8.2 die
  bepreiste Variante.
- **Umrechnung braucht ein Plausibilitätsfenster und einen letzten guten Wert.**
  Ein Kurs außerhalb 0,3–3 ist ein Datenfehler, kein Kurs. Und: bei Ausfall der
  Quelle lieber „kein Update" als ein stiller Wechsel der Bezugsgröße — der
  TCGdex-502 am Testtag hat gezeigt, dass der Riegel greift.

---

## 5. Werkzeuge und Umgebung

- **Lokales Gate und CI installieren Prüf-Abhängigkeiten aus derselben Datei.**
  `scripts/gates.sh` hatte pytest hartkodiert, die CI las
  `requirements-dev.txt` — ein neues Prüfwerkzeug wäre lokal nie gelaufen.
  Zwei Installationspfade driften still.
- **Git-Bash verstümmelt Umlaute** in `curl -d` und in manchen Heredocs. Texte
  mit Umlauten als **UTF-8-Datei** schreiben und per `--data-binary @datei` bzw.
  `--body-file` übergeben.
- **Next.js im Standalone-Modus bindet an `$HOSTNAME`**, nicht an `127.0.0.1`.
  Eine Gesundheitsprüfung gegen `localhost` schlägt im Container fehl, obwohl
  der Server läuft.
- **Wo eine Adresse zur Bauzeit eingebacken wird** (`NEXT_PUBLIC_API_URL`), muss
  der Testläufer ins selbe Netz wie die Anwendung — deshalb hat der Rauchtest
  einen **eigenen Stapel** und läuft nicht gegen den Teststand.
- **Prüfungen, die schreiben, gehören auf eine Wegwerf-Umgebung.** Der Teststand
  trägt den echten Bestand des Owners und dessen API-Schlüssel; `teststand.sh
  reset` löscht ihn samt Schlüssel.
- **package-locks nur im Node-Container erzeugen.** Der lokale npm schreibt
  Locks einer anderen Hauptversion (lokal npm 11; Abbild und CI npm 10.8.2,
  gemessen 28.09.2026) — lokal grün, im Abbild und in der CI rot. Allgemein (Vorlage §21, v1.15.0): **Das lokale Gate läuft
  im Werkzeug-Major der CI, und jeder übersprungene Schritt nennt sein
  lokales Äquivalent** — sonst ist „lokal grün" eine Aussage über ein
  anderes Werkzeug. Bei uns: npm 11 lokal, npm 10.8.2 in Container und CI
  (gemessen 28.09.2026), deshalb laufen `gates.sh` und die Sperrdateien im
  Container.
- **CI-Läufe run-id-gepinnt beobachten** (`gh run watch <id> --exit-status`),
  nie über eine Listenposition — sonst wartet man auf den falschen Lauf.
  Verschärfung (v1.9.1): `gh run list --limit 1` **unmittelbar nach dem Push**
  liefert den Lauf des VORGÄNGER-Commits, weil der eigene noch nicht angelegt
  ist. Über den eigenen `headSha` filtern. Anderswo wurde so ein Issue gegen
  fremdes Grün geschlossen. Vollständige Regel (v1.10.1, anderswo trotz
  headSha erneut passiert): **das `conclusion`-Feld lesen, nie den Exit-Code
  einer Pipe** (`… --exit-status | tail` liefert den Exit von `tail` — bei
  Grün unsichtbar, beim ersten Rot falsch; dieselbe Falle hat hier einen
  Rot-Beweis als „exit=0" gemeldet). Und: **„nicht gestartet" ist auch ein
  Fehlschlag** — ein roter Lauf mit null Schritten ist „Infrastruktur weg",
  nicht „Code kaputt"; die Reaktionen sind gegensätzlich.
  **Und ein ABGEBROCHENER Lauf ist für den Beobachter ein Erfolg**
  (Vorlage §6, v1.17.0): `gh run watch <id> --exit-status` endet mit **0**, wenn der
  Lauf abgebrochen wurde — auch ohne Pipe. Der Exit des Wartens beantwortet
  „habe ich zu Ende gewartet", nicht „ist es gut ausgegangen". Das Ergebnis
  deshalb nach dem Warten abfragen: `gh run view <id> --json
  status,conclusion` — und dieser Wert gehört in den Bericht, nicht das
  Wort „grün" (Verfahren: `release-ritual.md`, Schritt 9).
- **Gepinnte Actions altern still.** SHA-Pins sind sicher, aber unsere lagen im
  August 2026 drei Hauptversionen zurück (Node-20-Abkündigung in den
  Lauf-Annotationen). Beim Übernehmen prüfen, ob die Hauptversion noch aktuell
  ist: `gh api repos/<owner>/<action>/releases/latest`.
- **Ein Push kostet CI-Minuten.** Reine Doku- oder Konfigurations-Commits, die
  keine Prüfung beweisen können, mit `[skip ci]` pushen — und die Verifikation
  einmal per `workflow_dispatch` fahren statt durch wiederholtes Pushen.
- **Umgebungsaussagen in `CLAUDE.md` sind Behauptungen und werden gemessen**
  (Vorlage §28; `abgleich.md` der Vorlage, 2f) — beim Abgleich und vor jedem
  Ritual-Slice je Aussage ein Kommando mit Exit-Code. Hausbeleg (Abgleich
  v1.17.2): „Kein Node/npm lokal" stand bei uns seit dem 14.07.2026
  (`428fe52`) und war falsch
  (node v24.18.0, npm 11.16.0, beide Exit 0), und „SSH ist für Agenten
  geblockt" beschrieb eine Umstands-Sperre als eingerichtete — in den
  Agenten-Einstellungen steht keine SSH-Regel.
- **Wer sein eigenes Gate startet, wählt dessen Umgebung** (Vorlage §8,
  v1.16.0) — für JEDEN Eingang: Interpreter, Einstellungspfad, Programme aus
  `PATH`, `PYTHONPATH`, das Verzeichnis für Zwischenergebnisse, parallele
  Prozesse. Was trägt: Interpreter und Pfade **verdrahtet** statt gesucht,
  jedes Urteil in Python mit `-I`, Zwischenergebnisse an einem Ort, den nur
  der eigene Lauf kennt — und die verbliebene Grenze benannt statt verneint.
  Bei uns: Das Prozess-Gate läuft im Container mit `/usr/local/bin/python3.12`
  (über den Symlink `python3` war die Wächter-Selbstprobe rot, gemessen
  28.09.2026).
- **Werte holt man von dem Werkzeug, das die Datei ohnehin liest, nicht vom
  eigenen Parser** (Vorlage §6, v1.17.0) — für eine Umgebungsdatei die
  Konfigurations-Abfrage des Werkzeugs (`docker compose config`), der eigene
  Parser nur als Rückfall. Dort fanden vier Stimmen an einem selbst
  geschriebenen Dotenv-Parser je ANDERE Fälle.
- **Keine relativen Bind-Quellen, sobald Compose je aus einem CONTAINER
  heraus gefahren wird** (Vorlage §6, v1.17.0): `./datei` löst dann gegen das
  Dateisystem dieses Containers auf, nicht gegen den Host. Bei uns fährt
  `deploy.sh` auf dem Host — die Regel greift, sobald der Deploy über einen
  Verwaltungs-Container läuft.
- **Eine zweimal behobene Defektklasse gehört in einen Wächter, nicht in
  einen Kommentar** (Vorlage §8): Dieselbe Invariante wurde dort in einer
  Datei dreimal hintereinander verletzt, beim dritten Mal vier Zeilen unter
  dem Kommentar, der davor warnte. Und die Bauform folgt der Lage des
  Defekts: Ein Wächter, der von außen durch die Tür fährt, erreicht nur den
  FRÜHESTEN Ablehnungsweg — lebt der Defekt am spätesten, braucht es
  zusätzlich eine Prüfung, die alle Wege sieht.
- **Grün auf der Bau-Maschine ist kein Urteil über die Zielplattform**
  (Vorlage §10, v1.18.2). Ein Test, der ein Verhalten von Betriebssystem oder
  C-Bibliothek festhält (Zeitfunktionen vor 1970, Pfadlängen, Signale,
  Locale), hält die Plattform des Bauers fest; bei „wirft X" entscheidet die
  Plattform, OB geworfen wird. Dort warf ein Datum vor 1970 nur unter Windows,
  und erst ein Lauf im Wegwerf-Container mit dem App-Abbild zeigte es.
  **Regel:** Ein Test, der eine Ausnahme aus Betriebssystem oder C-Bibliothek
  erwartet, läuft vor der Landung einmal auf der Zielplattform. Ohne einen
  solchen Lauf bleiben solche Eingaben aus dem Test, und eine Eingabe, die nur
  auf einer Plattform wirft, gehört nie in den Rot-Beweis. Bei uns ist die
  Zielplattform Linux im Container: `scripts/gates.sh` fährt pytest im Abbild,
  ein Lauf auf dem Windows-Host allein belegt nichts (Typische Falle
  „Plattform" in `bau-brief.md`).
- **`.gitattributes` wirkt beim Schreiben, nicht rückwirkend** (Vorlage §10,
  v1.18.2). Eine Datei mit `eol=lf` kann nach einem abgebrochenen Umschreiben
  mit CRLF im Arbeitsbaum liegen, weil git Dateien mit unverändertem Blob
  nicht neu schreibt; ein Werkzeug, das den Arbeitsbaum liest, sieht dann
  andere Bytes als die CI. Was zu tun ist, zeigt `git ls-files --eol`: Bei
  `i/crlf` oder `i/mixed` liegen schon die Blobs falsch — dann bei sauberem
  Baum `git add --renormalize .`, ein eigener Commit, danach die Dateien neu
  schreiben lassen. Steht nur der Arbeitsbaum auf `w/crlf`, reicht das
  Neuschreiben (bei sauberem Baum `git rm --cached -r -q . && git reset
  --hard`). Hausbeleg: Bei uns gilt `* text=auto eol=lf`, und trotzdem
  standen am 19.10.2026 zehn unveränderte Dateien im Arbeitsbaum auf `w/crlf`
  (Index `i/lf`), darunter drei aus `docs/agents/`, die Gate P liest. Neu
  geschrieben aus dem Index (`git checkout -- <datei>` nach dem Löschen, je
  Datei, weil der Baum nicht sauber war); danach 0.
- **Ein byteweise arbeitendes Werkzeug sieht Mehrbyte-Zeichen als Bytes**
  (Vorlage §10, v1.18.2). Eine Zeichenklasse wie `[^"“]` in `sed` ohne
  UTF-8-Locale schließt die drei Bytes von `“` einzeln aus — und damit auch
  `…`, das zwei davon teilt. Dieselbe Klasse wie bei der Suche unter
  `LC_ALL=C` (`abgleich.md` der Vorlage, 2b), hier im Code.

---

## 6. Auslieferung

- **Die Version wird an ZWEI Stellen geführt** (`web/src/lib/version.ts`,
  `backend/app/config.py`). Der häufigste Deploy-Fehler ist, dass nur eines der
  beiden Images neu ist — der Rauchtest prüft den Gleichstand deshalb selbst.
- **Keine echten IPs committen.** Die LAN-Adresse wurde einmal per
  `filter-branch` aus der History entfernt; Platzhalter `<server-ip>` benutzen.
- **Das Vergleichs-Repo `Git-Romer/pokecollector` ist AGPL** — Ideen ja,
  Code-Übernahme nie (PokéCollect ist MIT).
- **Deutsche Typo-Quotes in JS-Strings** brechen den Build, wenn sie mit
  ASCII-`"` geschlossen werden. Innere Quotes weglassen oder Backtick-Template.
- **Next-Hooks sind nullable:** `useSearchParams()`/`useParams()` brauchen
  Optional-Chaining, `useSearchParams()` zusätzlich `<Suspense>`.
- **Eine Ausschlussliste lässt jedes neue Verzeichnis durch** (Vorlage §6,
  v1.18.2). Ein Deploy, der den Baum spiegelt und ausnimmt, was nicht live
  soll, liefert alles aus, woran beim Schreiben der Liste niemand dachte; dort
  wäre ein neues Hook-Verzeichnis drei Wochen lang öffentlich abrufbar
  gewesen, weil jede Prüfung die Liste las und keine die Menge. **Regel:** Wer
  per Ausschlussliste ausliefert oder prüft, rechnet die Menge nach —
  `git ls-files` minus die Ausnahmen gegen eine kurze Positivliste. Bei uns
  gemessen am 19.10.2026: Beide Abbilder entstehen aus Positivlisten
  (`backend/Dockerfile` kopiert `requirements.txt` und `app/`, die letzte
  Stufe von `web/Dockerfile` nur `public/`, `.next/standalone` und
  `.next/static`); eine Ausschlussliste gibt es nicht.

---

## 7. Notmaßnahmen ohne Rückdreh-Datum werden dauerhaft

Die Actions-Minuten-Notbremse vom 14.08.2026 hat drei Dinge stillgelegt:
Dependabot, den `pull_request`-Trigger und neun offene Bot-PRs. Jede einzelne
Maßnahme war richtig — und jede einzelne wäre still liegen geblieben, weil
niemand ein Ablaufdatum daran geschrieben hätte.

Deshalb gilt: **Eine Notmaßnahme bekommt beim Setzen ein Datum und einen
Rückweg**, beides an der Stelle, an der sie steht. Konkret hier:

- ein Rücksetz-Kasten in `.github/dependabot.yml` mit den alten Werten,
- ein Issue mit Datum (#71) statt einer Notiz im Chat,
- der Grund im Kommentar, damit der Rückbau nicht als Verschlechterung gelesen
  wird.

Der Befund ist erst aus der Portfolio-Sicht sichtbar geworden: vier Repos, vier
Notbremsen, kein Datum. Wer nur das eigene Repo ansieht, hält das für Ordnung.

**Dritte Rückbau-Frage** (Vorlage §11, v1.13.0): *Hat die Messung aus der
Notzeit die Ausgangsannahme widerlegt?* Wenn ja, wird die Notmaßnahme zur
Regel mit neuer Begründung und die Rückdreh-Anweisung **gelöscht** — nicht
pflichtschuldig ausgeführt. Hausbeleg: Unser Rücksetz-Kasten in
`.github/dependabot.yml` verlangte „am 01.09. zurück auf weekly/limit 5" —
genau eine der beiden Ursachen des Kontingent-Platzers. Eine sauber datierte,
sauber bedingte Notiz hätte den Fehler wiederhergestellt; die Messung hatte
die Annahme („weekly ist normal") längst widerlegt.

**Nachtrag 02.09.2026 — der Rückweg wurde begangen, und das Datum hat gewirkt:**
Am Stichtag entschied der Owner je Maßnahme *Rückdreh* oder *Dauerregel* — das
ist der Zweck des Datums, nicht ein automatischer Rückbau. Ergebnis:
`pull_request`-Trigger weg, Ein-Job-pytest, `concurrency` und `paths-ignore`
bleiben dauerhaft (kosten keine Qualität); Dependabot kommt nur halb zurück
(monthly, Limit 1 — der Rücksetz-Kasten mit „weekly/limit 5" war in die falsche
Richtung geschrieben); `[skip ci]` wird von der Notmaßnahme zum Standard mit
EINEM `workflow_dispatch` je Slice (CLAUDE.md, CI-Dauerregel). Die
Aussetzungs-Hinweise „bis 01.09." in §10 und §12 sind damit historisch.

---

## 8. Eine Prüfung rutscht zu dem, was leichter zu messen ist

Zwei eigene Fälle an einem Tag, beide gegen den Prüfenden selbst (Vorlage v1.10.0 §19):

- **Präsenz geprüft, Struktur nicht.** Nach dem Abbruch eines Bau-Subagenten
  mitten im Rot-Beweis suchte die Kontrolle per `grep`, ob der Schutz
  `if pr["eur"] is not None` existiert — er existierte. Dass die Sabotage die
  geschützte Zuweisung **aus ihm herausgeschoben** hatte, sah die Suche nicht.
  Die Entwarnung war falsch; der Baum stand zwei Tage in einem Zustand, in dem
  jede Karte ohne Cardmarket-Daten ihren Preis verloren hätte.
- **Aufruf geprüft, Wirkung nicht.** Ein Test blieb ohne den zugehörigen Fix
  grün, weil jede Hilfsfunktion ihren Namen **vor** der geprüften Anweisung
  protokollierte — die Liste sah vollständig aus, obwohl jeder Schritt
  scheiterte.

Dritter eigener Fall derselben Familie: **Eine Prüfung, deren Ergebnis eine
Entscheidung steuern soll, darf nie im selben verketteten Kommando laufen wie
die Entscheidung** — der Exit-Code hinter einer Pipe/`&&`-Kette gehörte schon
zweimal uns (Rot-Beweis als „exit=0" gemeldet; die Suche nach Vorlage §17 lief, aber der Commit
wartete nicht auf ihr Ergebnis). Seit v1.12.0 Vorlagen-Regel.

Diagnose beide Male: *Die Prüfung maß etwas, das leichter zu messen war als das
Gemeinte.* Keine Nachlässigkeit, sondern die Richtung, in die jede Prüfung von
selbst rutscht. Gegenfrage vor dem Vertrauen: **„Messe ich die Wirkung oder nur
ihr Anzeichen?"**

**Die dritte Rutschrichtung: vorhanden, aber falsch** (Vorlage §19,
v1.15.0). Ein Typ erzwang, dass für jede Sprache ein Eintrag existiert —
`tsc` Exit 0 —, und der Wert war Unsinn. „Vollständigkeit ist typerzwungen"
war belegt, aber nur für das Vorhandensein des Schlüssels, nicht für die
Richtigkeit des Werts. Eine Mutation, die den Wert kaputt macht und den
Schlüssel stehen lässt, gehört deshalb zu jedem Vollständigkeits-Wächter —
bei uns etwa zu jeder Prüfung auf „DE und EN nicht leer" (Issue #99).

**Ein Signal, das ein Zeitfenster ersetzt, macht das Urteil schneller und
schwächer zugleich** (Vorlage §14, v1.18.2). Ein Urteil „Container gesund" war
dort ein Schnappschuss nach drei Sekunden; ein Slice ersetzte ihn durch ein
Lebenszeichen des Prozesses, das Millisekunden nach dem Start kommt — ein
Prozess, der nach vier Sekunden stirbt, galt damit eher als gesund als vorher.
**Regel:** Wer ein Zeitfenster durch ein Signal ersetzt, stellt den Zeitpunkt
des Signals gegen das abgeschaffte Fenster, und die Tür-Probe enthält den Fall
**„Signal da, dann Ausfall"**, nicht nur „kein Signal".

**Eine Tür-Probe ist selbst ein Werkzeug ohne Selbstprobe** (Vorlage §14,
v1.18.2). Von sieben Läufen einer Signal-Probe am echten Container meldeten
dort drei rot oder nichts, ohne dass das Produkt beteiligt war: Docker wertete
`docker kill` als manuellen Stopp, die Prüfschleife fand ihre eigene Shell, und
das Signal traf die Erstfassung eines Skripts statt der per `exec`
gewechselten. **Regel:** Eine Tür-Probe gibt VOR dem Urteil ihre Beweismittel
aus — getroffener Prozess mit Nummer und Befehlszeile, Zustand des
Containers, die letzten Zeilen des Produkt-Logs —, und ihr erster Lauf gilt
als Probe der Probe: Zeigt ein Fall nicht das erwartete Bild, wird zuerst das
Skript geprüft, dann das Produkt.

---

## 9. Eine Fähigkeitsgrenze, die still verwirft, macht die Metadaten-Karte zur Lüge

Übernommen aus der Vorlage (v1.11.0 §20), mit eigenem Beleg: Beim E2E-Testen
schluckte `POST /api/v1/cards` die Felder `tcgdex_card_id`/`set_id` **still** —
`CardCreate` kennt sie nicht, Pydantic verwirft unbekannte Felder wortlos. Der
Aufruf gelang, die Karte war unverknüpft, und die Referenz musste von Hand in
der DB gesetzt werden. Bei menschlichen Aufrufern ärgerlich; für die geplante
LLM-Tür (#56) ein Datenintegritäts-Risiko — ein Modell behandelt die
API-Beschreibung als verlässliche Karte.

**Regeln:** Eine Fähigkeitsgrenze wird DEKLARIERT und ABGELEHNT, nie still
verworfen. Prüfsatz: **„Wenn ein Aufrufer dieses Feld ausdrücklich mitschickt —
erfährt er, was damit passiert ist, auch wenn der Wert dabei seine BEDEUTUNG
wechselt?"** Verwerfen ist nur die eine Hälfte, die andere ist **UMDEUTEN**
(`"nein"` per `bool()` zu `True` — nichts verworfen, Bedeutung verkehrt). Wer
eine Grenze begradigt, prüft beide Richtungen: kommt der Wert an — und kommt er
als DASSELBE an?

---

## 10. Ein Wächter, dessen Lauf niemand erzwingt, macht die Abdeckungszahl zur Beruhigung

Übernommen aus der Vorlage (v1.11.0 §21), mit ehrlicher eigener Inventur:
`scripts/bau-brief-pruefen.sh` erzwingt **niemand** — es läuft nur, wenn der
Hauptagent daran denkt. Nach der Hierarchie **Abdeckung < Zustand < AUSFÜHRUNG**
ist es damit eine Notiz, kein Wächter. Ebenso ehrlich: Während der
CI-Aussetzung (Quota, bis 01.09.) macht **keine** unserer Suiten automatisch
etwas rot — das ist die nach §7 zulässige, **terminierte** Ersetzung mit
Rückdreh-Bedingung, kein stiller Verzicht.

**Regeln** — darunter drei Wächterfragen (bis zum Abgleich v1.17.2
„Pflichtfragen", umbenannt wie in der Vorlage seit v1.15.2):
- **Erste Wächterfrage, beim Anlegen jeder Prüfung: „Was macht sie rot, ohne
  dass jemand daran denkt?"** Ohne Antwort ist sie eine Notiz, kein Wächter.
- **Zweite Wächterfrage (Vorlage §21, v1.13.0): „Wurde der Wächter einmal
  GENAU SO ausgeführt, wie der Job ihn ausführt?"** Ein Skript, das im Import
  grün ist, kann beim CI-Aufruf an `ModuleNotFoundError` scheitern. Hausbeleg
  mit ehrlicher Lücke: Unser Paritäts-Wächter (Gate ↔ CI, `scripts/gates.sh`)
  wird von der CI GAR NICHT ausgeführt — die CI ruft `gates.sh` nicht auf. Er
  ist damit ein rein lokaler Wächter; das ist bewusst (die CI spiegelt die
  Schritte selbst), aber es heißt: Fällt er, merkt es nur, wer lokal baut.
- **Dritte Wächterfrage (Vorlage §21, v1.14.0; hier übernommen im Abgleich
  v1.17.2): „Wer liest das Rot — und woran merkt er es?"** Ein Wächter ohne
  Leser ist nicht neutral: Er erzeugt den Eindruck von Abdeckung und
  verhindert die Frage, die sonst jemand gestellt hätte. **Hausbeleg, beim
  Übernehmen gemessen (28.09.2026):** Unser wöchentlicher Security-Scan war
  seit seiner Einrichtung am 06.08. in **9 von 9** Läufen rot, jedes Mal in
  allen drei Jobs (`npm audit` mit einer kritischen Lücke, `pip-audit` mit
  16, Schemathesis mit fünf 500ern) — und niemand hat einen Lauf gelesen,
  weil kein Schritt im Ablauf ihn liest (#105). „Bewusst kein Push-Gate" war
  richtig; es hätte einen Leser gebraucht. Der Leser steht seit dem Abgleich
  im Release-Ritual (letzten Lauf jedes Zeitplan-Workflows lesen).
- **Ein Zeitplan-Wächter ist zwischen Bau und erstem planmäßigem Lauf
  unbewiesen** (Vorlage §21, v1.14.0): Wer einen `schedule`-Job anlegt oder
  umbaut, löst ihn einmal von Hand aus. Die Antwort auf die zweite
  Wächterfrage ist der **Exit-Code ohne Pipe**; ein „lief durch" aus einer
  Pipeline beantwortet sie nicht.
- **Eine Regel braucht einen Erzwingungsweg, sonst ist sie eine Notiz** —
  auch eine Regel über Läufe: Unsere Dauerregel „ein CI-Lauf je Slice" gilt
  erst als eingehalten, wenn ein grüner Lauf zum gelandeten `headSha`
  nachgewiesen ist. Umgekehrt: Eine Styleguide-Regel, die nirgends geprüft
  wird, ist eine Absichtserklärung.
- **Anwesenheit, Richtigkeit, Parität und Abdeckung sind vier Prüfungen**
  (Vorlage §21). Ein Paritäts-Wächter prüft nur die Paare, die
  existieren; die fehlenden Gegenstücke sieht er nie. „Was fehlt" braucht
  einen Zähler über die Menge mit begründeter Ausnahmeliste.
- Geht der automatische Lauf (noch) nicht: ausdrücklich und **terminiert**
  ersetzen (Datum + Rückdreh-Bedingung) — kein stiller Verzicht.
- **Abdeckung hat zwei Achsen:** welche Objekte UND in welchen Zuständen.
  Persistierte Bedien-Zustände (localStorage-Filter, BottomNav-Konfiguration)
  sind eigene Fälle, keine Varianten.
- Ein **Sicherheitsnetz kann den Fehler unsichtbar machen** — wer eines
  einzieht, lässt den Wächter dahinter messen (unser Beleg: der 401-Interceptor
  fing die AuthGuard-Mutation ab, die Suite blieb zu Recht grün — die Grenze
  steht als Kommentar im Test).

---

## 11. Eine als Spezialfall formulierte Regel wird beim strukturgleichen Fall nicht wiedererkannt

Übernommen aus der Vorlage (dort §22, drei unabhängige Belege — einer vom
Autor der Regel selbst). Die Klasse: Eine Regel, die an ihrem Entstehungsfall
klebt („bei Preisen nie …"), wird nicht angewandt, wenn dieselbe Struktur mit
anderen Wörtern auftritt („bei Zuschnitt-Hinweisen …"). Eigener Beleg im Haus:
Die v1.8.2-Preis-Label-Lehre („das Label darf nichts behaupten, was die Quelle
nicht deckt") wurde beim #47-Bild-Label zunächst nicht wiedererkannt — beide
Stimmen fanden denselben Fehler als „neu". **Beim Formulieren einer Lehre die
Struktur benennen, nicht nur den Fall; beim Lesen fragen: Wo ist dieselbe
Struktur unter anderem Namen?**

---

## 12. Ein Hook deckt nur, was er nennt

Übernommen aus der Vorlage (dort §23): Eine Ausnahme-/Auslassungsliste in
einem Hook oder einer Notmaßnahme wird scharf, sobald der Normalpfad
pausiert. Unser aktueller Fall: Die CI-Pause (Quota) macht die
`[skip ci]`-Praxis zur einzigen Wahrheit — alles, was NUR die CI geprüft
hätte, prüft bis 01.09. niemand automatisch (ehrliche Inventur in §10).
**Beim Einrichten jeder Pause/Ausnahme: die Liste dessen, was dadurch
ungeprüft wird, ausschreiben — sie ist die eigentliche Änderung.**

---

## 13. Wächter-Code ist die defektdichteste Stelle eines Slices

Produkt-Code hat Nutzer, die ihn benutzen. **Wächter-Code hat als einzigen
Nutzer den Fehlerfall** — und der tritt beim Bauen nie ein. Die Vorlage (§24)
misst über fünf Panel-Runden: die meisten Funde lagen im Prüfcode, darunter
beide Blocker.

Hausbeleg, derselbe Slice zweimal: In #72 lagen **beide WICHTIG-Funde des
Panels im Wächter-Bereich** (der Produktions-Build lintete implizit mit; die
Parität Gate ↔ CI war unbewacht, obwohl der Brief sie zusicherte). Und der
Wächter, den wir daraufhin bauten, trug selbst einen Fehler: ein verlorener
Fortsetzungs-Backslash, `grep` bekam ein Extra-Argument (`439d9ab`). Beide
Beweise gingen trotzdem richtig aus — der Fehler wäre nie aufgefallen, wenn
nicht jemand die Zeile gelesen hätte.

Weitere Regeln der Vorlage (§24), jede dort gemessen:

- **Ausnahmelisten eines neuen Wächters sind Teil des Diffs** — je Ausnahme
  ein Grund und ein Issue, und „bewusst" widerlegbar formuliert.
- **Ein neuer Wächter mit null Funden am ersten Tag verdient Misstrauen.**
  Die Rot-Probe gegen einen absichtlich eingebauten Fall entscheidet, nicht
  die Null.
- **Eine hohe Fallzahl der Selbstprobe ist keine Breite** — sie zählt
  Umgebungen, nicht nur Fälle. Bei uns gemessen: Die Wächter-Selbstprobe
  zählt unter Python 3.14 518 Erwartungen, unter Python 3.12 521 — unter
  Linux wie unter Windows, die Zahl hängt an der Python-Version, nicht an
  der Plattform (Gegenprüfer, Abgleich v1.17.2; Linux mit 3.14 nachgemessen:
  518).
- **Eine Ersatzschreibweise im Muster muss die Byte-Zahl treffen** (ein
  Umlaut ist in UTF-8 zwei Bytes). Und: **Geschlossen heißt nicht
  umgesetzt.**
- **Wird ein Artefakt aus Quellen erzeugt, prüft ein Paritäts-Gate
  „Artefakt == Generator(Quellen)"** — es fängt, was Feldprüfungen
  durchlassen. Bei uns genau so gebaut: `whatsnew_paritaet_gate` in
  `scripts/gates.sh` erzeugt die Was-ist-neu-Notizen neu und vergleicht (#99).
- **Jede Schwelle sagt, was sie ist:** unter dem gemessenen Stand ein
  Regressionswächter, darüber eine Zusage mit Plan — beides mit dem Abstand
  zum gemessenen Stand genannt.
- **Eine neue Bedingung trägt ihre Trefferzahl** — wie oft feuert sie, an
  wie vielen Fällen? Dort sahen drei Mechanismen gebaut aus und feuerten nie.

Maßnahmen: **Der Wächter-Teil eines Slices wird wie Produktcode geprüft**
(eigener Rot-Beweis, nicht nur „läuft durch"); jeder CI-Job trägt
`timeout-minutes` (ohne Grenze läuft ein hängender Lauf 360 Minuten — mehr als
das ganze Tagesbudget, Schwellen-Inventar in `CLAUDE.md`); und ein Gate, das eine Datei
prüft, wird einmal MIT verletzter Bedingung ausgeführt, nicht nur ohne.

---

## 14. Freitext in einem `run:`-Block ist Code

Vorlage §25: Ein zitierter Auslieferungsbefehl in Backticks, übergeben in einem
doppelt gequoteten String, wäre bei jedem roten Monitoring-Lauf **ausgeführt**
worden — verhindert nur durch zwei Zufälle. Die dortige Leitplanken-Prüfung war
grün: Sie suchte die ARTEFAKTE des Deploy-Pfads, nicht den AUFRUF.

Regeln: Text, der in einen Befehl fließt, geht per **Heredoc + `--body-file`**,
nie in `--body "…"`. Und wer „kann nicht ausliefern" behauptet, prüft Rechte,
Secrets **und den Text aller `run:`-Blöcke**, Zitate eingeschlossen.

Bei uns geprüft (04.09.2026) und **ohne Befund**: kein einziger `gh`-Aufruf in
den Workflows, Backticks nur in YAML-Kommentaren, die zwei
Kommandosubstitutionen in `security-scan.yml` sind eigene `curl`/`seq`-Aufrufe.
Die Klasse bleibt hier stehen, weil sie beim nächsten Workflow mit
Issue-Kommentar sofort greift — und weil unsere eigene Praxis am Werkzeug
(`gh` immer mit `--body-file`) genau daraus stammt.

---

## 15. Was einmal richtig gemacht und nicht aufgeschrieben wurde, ist keine Regel

Vorlage §26. Eine einmal gelungene Handlung ist eine **Anekdote**; erst
aufgeschrieben wird sie zur Regel, die beim strukturgleichen Fall wieder
gefunden wird (das ist §11 von der anderen Seite).

Hausbeleg: Die **Äquivalenz-Probe ALT vs. NEU** (dieselbe Aufrufsequenz, beide
Versionen, byte- dann pixelweise vergleichen) entstand beim #82-Refactor als
Einfall einer Stimme. Nicht aufgeschrieben — beim Pillow-Sprung zwei Slices
später musste sie neu erfunden werden. Jetzt steht sie hier: **Für
Umbau-Slices und Bibliotheks-Sprünge, deren Zusage „Verhalten bleibt gleich"
lautet, ist die Äquivalenz-Probe der Nachweis** — kein Rot-Beweis kann sie
ersetzen, weil es keine neue Zusage gibt, die rot werden könnte. Sie fand im
Pillow-Slice über 307 Vergleichspfade die einzige echte Verhaltensänderung
(16-Bit-PNG-Thumbnails), die keine Suite gefunden hätte.

---

## 16. Ein hängender Hintergrund-Lauf ist ein aufgeschobenes Kommando

Übernommen aus der Vorlage (§27), weil wir Läufe routinemäßig in den
Hintergrund legen — in einer einzigen Sitzung mehrfach gleichzeitig.

Dort hingen fünf Hintergrund-Shells stundenlang an einem Kommando, das auf
eine Eingabe wartete. Sie sahen untätig aus. **Beim Beenden liefen sie nicht
ab, sondern weiter:** Alles, was in derselben Kommandozeile HINTER dem
hängenden Aufruf stand, wurde ausgeführt — gegen ein Repo, das viele Commits
weiter war. Eine dieser Shells committete, pushte den Hauptzweig und verschob
einen Release-Tag zwangsweise auf einen ungeprüften Stand.

**Regeln:** Vor dem Beenden lesen, was hinter dem hängenden Aufruf steht.
Danach den Zustand prüfen (`git log`, `git status`, Tags), nicht annehmen.
Ein Aufruf, der hängen kann, steht am ENDE seiner Zeile — nie mit einem
Commit oder Push dahinter.

**Für uns besonders:** Unsere Bau- und Prüfläufe enden regelmäßig mit
`down -v`, `git checkout --` oder einem Aufräum-Schritt in derselben Zeile.
Genau diese Ketten sind der Schaden, wenn der Anfang hängt.

**Das Stoppen eines Treibers stoppt seine Kinder nicht** (Vorlage §27,
v1.15.0): Ein gestoppter Hintergrund-Treiber ließ seine Shell weiterlaufen,
der Neustart unter demselben Namen kollidierte mit ihr (gleiche
Container-Namen, gleiche Ausgabedateien). Nach jedem Stopp die Prozessliste
prüfen; **jeder Neustart bekommt einen eigenen Namensraum** (Präfix,
Ausgabeordner). Bei uns heikel: `scripts/gates.sh` benutzt feste
Container-, Netz- und Image-Namen (`pokecollect-gate-db`, `pokecollect-gate`).

---

## 17. Ein Owner-Entscheid ist eine Anforderung, kein Abnahmekriterium

Unser eigener Fall (#99), in der Vorlage als §30 verallgemeinert.

Der Owner entschied für die „Was ist neu“-Box: **eine frische Installation
zeigt nichts.** Richtig entschieden. Der Slice führte den Schlüssel ein, an
dem „gesehen“ hängt, und behandelte „Schlüssel fehlt“ als frische
Installation. **Jeder Bestandsnutzer hatte den Schlüssel nicht** — der
Erst-Rollout hätte niemandem etwas gezeigt, die Funktion erst ab dem
übernächsten Release gewirkt. Ausgerechnet der Fall, der im Issue als Anlass
stand. Am laufenden Stapel reproduziert: 0 Dialoge.

Die blinde Stimme, die den Brief kannte, hakte das Verhalten als
„geprüft, ohne Befund“ ab — sie prüfte gegen den Entscheid. Gefunden hat es
die Stimme, die ihn nicht als gesetzt kannte.

**Die Klasse:** Ein Entscheid beschreibt den ZIELZUSTAND. Zwischen heute und
dem Zielzustand liegt der Rollout auf den Bestand, und der hat eine eigene
Semantik. Wer einen Schlüssel heute nicht hat, ist nicht dieselbe Person wie
„frisch“.

**Regel:** Die Abnahme denkt den Rollout auf Bestandsnutzer mit — als
Prüffrage 10 im Bau-Brief verankert, inzwischen an die Form gebunden
(„Welche real verschiedenen Ausgangszustände …") statt an den
Speicher-Schlüssel. In einem späteren Vergleich der Vorlage stand derselbe
Fehler in vier von fünf unabhängigen Umsetzungen, gemessen am laufenden
Stapel.

---

## 18. Was der Owner ausführt, wird auf seinem Rechner gemessen

Übernommen aus der Vorlage (§31). Dort war ein Ritual-Skript im Container
grün und auf dem Windows-Host rot — keine Panel-Stimme kann das sehen, weil
keine auf dem Host läuft.

**Bei uns einschlägig:** `deploy.sh` läuft auf dem Server des Owners, nicht
bei uns, und kein Agent fährt ihn (der Agenten-Schlüssel gilt nach
Auskunft des Owners nicht für den Server — `CLAUDE.md`, „Deploy").
Alles, was wir über den
Deploy behaupten, ist deshalb eine Nachstellung — und die gehört als solche
benannt.
Belegt am 06.09.: Ob der tmpfs-Deckel aus #98 beim Deploy überhaupt ankommt,
hatte vorher nichts geprüft. Nachgestellt an einem Wegwerf-Stapel (alter
Stand hoch, neue Compose-Datei, `up -d`) zeigte `/proc/mounts` danach
`tmpfs … size=262144k,mode=700,uid=3010,gid=3010` — vorher 0 Einträge.

**Der Exit-Code allein ist als Kriterium widerlegt** (Vorlage §31, Nachtrag
v1.15.0): Auf dem Rechner des Owners vernichtete eine Umsetzung desselben
Ritual-Skripts die Übersetzung mit Exit 0 und Erfolgsmeldung; zwei andere
schrieben korrekt und endeten mit Exit 1, weil die Konsole das Häkchen der
Erfolgsmeldung nicht darstellen konnte. Kriterium ist die Wirkung: **Hash der
Zieldatei vorher und nachher**, dazu der Exit-Code (Verfahren:
`release-ritual.md`). Die zweite ungeprüfte Umgebung ist der **Server**:
Kommandos, die der Owner dort tippt, werden in genau der Form geprobt, in
der er sie tippt; eine nicht geprobte Zeile steht als Einschränkung in der
Anweisung.

---

## 19. Ein Satz ÜBER den Überspring-Marker verschluckt den CI-Lauf

Schwesterfall zu §14 („Freitext in einem `run:`-Block ist Code“),
übernommen aus Vorlagen-v1.14.1 als eingetretener Vorfall eines anderen
Projekts.

Ein Commit landete auf dem Hauptzweig und löste **null** Läufe aus — keinen
roten, keinen abgebrochenen, gar keinen. Die Ursache stand in seiner eigenen
Nachricht: ein Satz, der erklärte, dass der VORIGE Commit den Marker bewusst
nicht trägt. **Die Plattform liest die ganze Commit-Nachricht, nicht nur die
Betreffzeile.** Die Nachricht tat genau das, wovon sie sich distanzierte.

**Warum das uns besonders trifft:** Unsere CI-Dauerregel führt dazu, dass wir
den Marker ständig erklären — in Abgleich-Commits, in Nacharbeits-Commits, in
jeder Begründung. Je disziplinierter die Regel dokumentiert wird, desto eher
stolpert man. Verschärfend: **Ein Lauf, den es nie gab, hinterlässt nichts.**
Wer danach in die Lauf-Liste sieht, findet den grünen Lauf des Vorgängers
ganz oben und liest ihn als seinen eigenen.

**Regel:** In einer Commit-Nachricht steht der Marker nur als Marker — nie
erklärt, zitiert oder verneint. Wer über ihn schreiben muss, umschreibt ihn.
In Dateien und Issue-Texten bleibt die wörtliche Nennung unbedenklich.
**Mechanisch erzwungen** durch `.githooks/commit-msg`.

**Dasselbe gilt für Schließ-Schlüsselwörter** (Vorlage §25):
`Fixes #N`, `Closes #N` und ihre Verwandten schließen Issues — auch in einem
Satz, der erklärt, warum ein Issue gerade NICHT geschlossen wird. Issue-Bezüge
in Commit-Texten deshalb ohne Verb davor („zu #N"). Das erzwingt kein Hook;
es ist Disziplin.

---

## 20. Zeit wird in drei Zuständen gezählt, nicht als eine Wandzeit

_Übernommen aus der Vorlage (§33), Abgleich v1.17.2._

Ein Vergleich meldete „9 h 34 gegen 1 h 46" — und war irreführend: Der längere
Lauf enthielt Stunden, in denen niemand arbeiten konnte, weil ein fremdes
Kontingent erschöpft war. Neu gerechnet lagen beide in derselben
Größenordnung. **Wartezeit auf fremde Kapazität ist keine Umsetzungszeit**, und
wer sie addiert, misst den Tarif, nicht den Prozess.

**Regel** (Owner-Entscheid, gilt für jede Bilanz):

| Zustand | Bedeutung | wird |
|---|---|---|
| **ACTIVE** | es wird gearbeitet — auch verworfene Arbeit | summiert |
| **PAUSED_EXTERNAL_CAPACITY** | Sitzungslimit, Guthaben, Kontingent eines Anbieters | **gezählt** (Anzahl, Dauer), nicht summiert |
| **MIXED** | Block, der sich nachträglich nicht trennen lässt | ausgewiesen, **nie geschätzt** |

Jede Bilanz nennt drei Zahlen: brutto, aktiv, Ausfälle. Eine Untergrenze („≥ 1 h
40") wird als Untergrenze geschrieben, nie als Zahl. **Warten auf eine
Entscheidung des Owners** ist weder ACTIVE noch PAUSED und bleibt aus der
Vergleichsgröße heraus (gemessen: eine Lücke von 7 h 35 in einem Slice). Der
Orchestrator wird mitgezählt — seine Zeit ist Teil des gemessenen Systems
(Vorlage §28). **Reparaturen am Prüfstand werden getrennt bilanziert**
(Vorlage §28): Wer zwischen zwei Läufen seine Messumgebung repariert, meldet
den zweiten Lauf nicht als Verbesserung des Geprüften.

## 21. Ein Commit, der Dateien still verliert

_Übernommen aus der Vorlage (§34), Abgleich v1.17.2._

Zwei Release-Commits der Vorlage löschten zusammen **zwölf Dateien** — CI-,
Abhängigkeits- und Hook-Vorlagen, das Werkzeug der dritten Stimme, die
Beispiel-Umgebung, die Geheimnis-Übersicht, die englischen Fassungen samt
Prüfskript. Keine Commit-Nachricht und kein CHANGELOG-Eintrag erwähnte es. Die
Doku verwies **25 bzw. 13 Tage** lang weiter auf die fehlenden Dateien, durch
mehrere Panels und Abgleiche hindurch; gefunden hat es erst eine
Bestandsprüfung, und dort nur zwei von vier Prüfern.

**Wie es entsteht:** Ein Release-Commit wird aus einer Arbeitskopie gebaut,
die nicht alle Dateien enthält — ein Teilbestand wird bearbeitet und als
Ganzes übernommen. Das Muster beider Commits passt dazu: Geändert wurden nur
Dateien, die ohnehin in Arbeit waren; gelöscht wurden genau die, die niemand
anfasste. Kein Prüfschritt sah hin, weil jeder den **Inhalt** des Diffs las —
eine Löschung hat keinen Inhalt, den man lesen könnte, und fällt in einer
langen Diff-Statistik als eine Zeile unter vielen nicht auf.

**Warum es still bleibt:** Eine gelöschte Datei macht nichts rot. Die
Verweise auf sie stehen in Prosa, und Prosa wird nicht ausgeführt (Vorlage §17). Wer
eine Datei sucht, die fehlt, hält das für einen Fehler seines eigenen Klons.

**Regel (Ritualschritt, im Release-Skript ein Wächter):** Vor jedem Tag listet
`liste=$(git -c core.quotepath=off log -m --no-renames --diff-filter=D --name-only --format= <letzter-tag>..HEAD) || exit 1`, dann `printf '%s\n' "$liste" | sort -u` (die Zuweisung trägt den Exit — eine Pipe verschluckt ihn, ein falscher Tag sähe aus wie „nichts verloren"; Form und Begründung in `release-ritual.md`, Schritt 8)
jede gelöschte oder verschobene Datei — `log` statt `diff`, weil ein Diff
Anfang gegen Ende vergleicht und eine Datei übersieht, die nach dem Tag
angelegt, verlinkt und wieder gelöscht wurde; ohne `--no-renames` fällt eine
verschobene Datei als Umbenennung durch, ohne `core.quotepath=off` ein Name
mit Umlaut als maskierter Pfad, den keine Suche findet —, jede steht mit Grund
im Notizen-Eintrag, und `git grep -n -i -F "<dateiname>"` (bei Umlaut oder
Leerzeichen auch in URL-kodierter Form, bei einem ganzen Verzeichnis der
Verzeichnisname **ohne** Schrägstrich) findet keinen Verweis mehr, der nicht
gewollt ist; sonst ROT
(`release-ritual.md`, Schritt 8). Der Schritt prüft nicht, ob
eine Löschung richtig ist, sondern dass sie **gesagt** wurde und nichts mehr
auf sie zeigt; das genügt, weil beide Fälle oben keine Absicht waren. Als
Schritt im Ritual ist er Disziplin — erst im Release-Skript macht sein
Auslassen etwas rot (§10).

## 22. Ein Zeitlimit beendet nichts

_Übernommen aus der Vorlage (§35), Abgleich v1.17.2._

Ein Messbefehl lief in sein Zeitlimit. Die Umgebung verschob ihn in den
Hintergrund und meldete das — eine Zeile, die aussah wie ein Abschluss. Der
Aufrufende wiederholte die Messung eine Minute später auf einem anderen Weg
und ließ den ersten Lauf liegen: **Er lief anderthalb Stunden weiter**, bis er
jemandem auffiel. Kein Schaden, weil er nur in ein Wegwerf-Verzeichnis
schrieb — das war Glück, keine Vorkehrung.

**Warum das strukturell ist:** Ein Zeitlimit ist eine Grenze für das *Warten*,
nicht für den *Prozess*. Die Meldung „in den Hintergrund verschoben" beendet
den Dialog und wird deshalb wie ein Ergebnis gelesen; danach ist der Lauf aus
der Aufmerksamkeit, aber nicht aus der Maschine. Dasselbe gilt für jeden
Abbruch: Ein Abbruch der ANZEIGE ist kein Abbruch der ARBEIT.

**Warum es gerade den Orchestrator trifft:** Die Regel „Läufe im Vordergrund,
Zeitlimits explizit, keine Hintergrundprozesse" steht im Pflicht-Gerüst des
Bau-Briefs — sie erreicht damit den Bauer und **nicht den, der sie verteilt**.
Genau der startet Stimmen, Bauer, Proben und Gates in **fremden Bäumen** (Vorlage §28:
den Orchestrator prüft niemand). Ein vergessener Lauf hält dort einen
Worktree, eine Sperre, ein Temp-Verzeichnis oder einen Port — und die nächste
Stimme misst einen Baum, der sich bewegt.

**Was macht die Regel rot?** Kein Wächter — deshalb trägt sie die Form:
**Jeder Bau- und Panel-Bericht endet mit der Zeile „Eigene Läufe am Ende: …"**
(`panel-kommentar.md`). Eine fehlende Zeile springt ins Auge, ein vergessener
Prozess nicht — dieselbe Mechanik wie die festen Überschriften im
Panel-Kommentar. Ein bewusst gestarteter Hintergrundlauf ist erlaubt (Stimmen
laufen parallel); er gehört in diese Zeile, nicht in die Stille.

**Regel (Wächterfrage; nach jedem Zeitlimit, jedem Abbruch und jedem „in den
Hintergrund verschoben"):** *Welcher Prozess läuft noch, was hält er (Worktree,
Sperre, Temp-Verzeichnis, Port), und ist er gestoppt?* Erst dann die nächste
Messung. Die Antwort gehört ins Ergebnis, auch wenn sie „keiner" lautet —
eine Zusage, die nie gesagt werden muss, wird nie geprüft (§10).

**Verwandt, gleiche Wurzel — ein Hintergrundlauf wird für inert gehalten:**
§16 (das Beenden führt aus, was hinter dem hängenden Kommando steht) und das
Hintergrund-Warte-Muster in `bau-brief.md` (der Bauer wartet auf seinen eigenen
Hintergrund-Gate und endet ohne Bericht). Die Folge fürs Panel steht in
`panel.md`, „Eine Stimme, ein Worktree": vor dem Start einer Stimme ist der
Baum leer **und kein eigener Lauf mehr offen, der in diesen Baum schreibt** —
andere Stimmen laufen bewusst parallel und zählen nicht; und **je Runde ein
neuer Worktree, nie umhängen** — eine Stimme, die mit offener Hintergrundarbeit
berichtet, gilt als laufend (v1.15.4).

## 23. Eine Nacharbeit behebt den Fund im gemessenen Umfang

_Übernommen aus der Vorlage (§36), Abgleich v1.17.2._

Ein Prüfer meldet einen Fund an EINER Stelle: der Tür, dem Pfad, der Eingabe,
die er gezeigt hat. Der Bauer der Nacharbeit „löst ihn mit" und zieht die
Prüfung in eine gemeinsame Routine, die jede Tür und jede Bestandszeile sieht —
und baut damit den nächsten Blocker: Ein gesperrter Beleg mit einer Alt-Zeile,
die die neue Regel nicht erfüllt, ist nicht mehr überführbar, weil gesperrt
nicht korrigierbar heißt (Rückmeldung P1, Slice mit drei Nacharbeitsrunden;
die Nachbarfunktion trug als Kommentar die ältere Auflage „Alt-Daten dürfen
unverbundene Änderungen nicht blockieren").

Die Klasse: **Ein Fund wird über seinen GEMESSENEN Umfang hinaus behoben.**
Nacharbeit ist Arbeit unter Zeitdruck mit der Versuchung, das Nachbarloch gleich
mitzustopfen — und genau dort fehlt der Blick auf Bestandsdaten, den ein
Bau-Brief für den Erst-Bau erzwingt (Block 2 Befund mit Konsumentenliste,
Prüffrage 10 „real verschiedene Ausgangszustände"). Die Auflage der Nacharbeit
kommt als Prüferzeile, nicht als Befund.

**Regel:** Eine Nacharbeit behebt den Fund im gemessenen Umfang. Wer den Fix auf
weitere Türen, Aufrufer oder Bestandsdaten ausdehnt, beantwortet VORHER
Prüffrage 3 (Geschwister-Routinen) und Prüffrage 10 (Ausgangszustände) für die
Erweiterung — sonst wird die Erweiterung ein eigener Slice. Im
Nacharbeits-Brief steht die Zeile „Umfang der Behebung = gemessener Umfang"
und je Erweiterung ihre Begründung (`bau-brief.md`, Nacharbeit).

---

## 24. Ein Skript, das sich selbst aktualisiert, läuft mit seinen alten Funktionen weiter

_Übernommen aus der Vorlage (§37), Abgleich v1.17.2._

Ein Ein-Klick-Update holt den neuen Stand und macht dann weiter — mit der
Fassung, die die Shell **vor** dem Auschecken gelesen hat. Die Datei auf der
Platte ist neu, der laufende Prozess ist alt. Jede Änderung, die Skript **und**
Konfiguration gemeinsam braucht, greift deshalb erst ab dem **übernächsten**
Update: Das Update AUF die Fix-Version trägt den Fehler noch einmal.

Gemessen in einem Kind-Repo: Der Fix am Update-Pfad war korrekt, und trotzdem
hätte der nächste Lauf ihn nicht benutzt — gefunden hat es die Panel-Runde, nicht
der Bau.

**Regel:** Wer ein sich selbst ersetzendes Skript ändert, entscheidet
ausdrücklich zwischen zwei Wegen und schreibt die Wahl in die Release-Notiz:
nach dem Auschecken per `exec` in die neue Fassung wechseln, oder den Übergang
dokumentieren („dieses eine Update von außen fahren"). Ein dritter Weg —
„fällt niemandem auf" — ist keiner.

Die Frage dazu steht in `panel.md` („Fragen, die überdurchschnittlich oft etwas
finden"): **Läuft der geänderte Code beim Übergang zwischen zwei Versionen
überhaupt schon, oder noch die alte Fassung mit der neuen Konfiguration?** Sie
gilt über Skripte hinaus — für Migrationen, Hooks, Gate-Zeilen und jede
Konfiguration, die von einem Programm gelesen wird, das sich mit ihr ändert.
