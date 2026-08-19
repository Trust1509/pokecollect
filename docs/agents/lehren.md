# Lehren aus gebauten Slices

Fehlerklassen, die uns **in diesem Projekt** real getroffen haben — mit dem
Nachweis, warum sie durchrutschten. **Nicht chronologisch, sondern nach
Klasse:** Die Frage beim Lesen ist nicht „was ist damals passiert", sondern
„welche dieser Fallen liegt in meinem Slice".

Die Einzelfälle stehen in den GitHub-Issues und im CHANGELOG; hier steht, was
übertragbar ist. Prozessregeln stehen in `CLAUDE.md`, das Panel in `panel.md`.

Der gemeinsame Prozess-Stand kommt aus `Trust1509/agent-projekt-template`.
Fällt hier eine Lehre an, die **nicht am eigenen Stack klebt**, gehört sie als
Issue dorthin (Label `prozess-lehre`) — nicht nur in diese Datei, sonst erfahren
die anderen Projekte nie davon.

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
- **package-locks nur im Node-Container erzeugen.** Der lokale npm-Wrapper
  schreibt Locks einer anderen Hauptversion — lokal und in der CI grün, im
  Abbild kaputt.
- **CI-Läufe run-id-gepinnt beobachten** (`gh run watch <id> --exit-status`),
  nie über eine Listenposition — sonst wartet man auf den falschen Lauf.
- **Gepinnte Actions altern still.** SHA-Pins sind sicher, aber unsere lagen im
  August 2026 drei Hauptversionen zurück (Node-20-Abkündigung in den
  Lauf-Annotationen). Beim Übernehmen prüfen, ob die Hauptversion noch aktuell
  ist: `gh api repos/<owner>/<action>/releases/latest`.
- **Ein Push kostet CI-Minuten.** Reine Doku- oder Konfigurations-Commits, die
  keine Prüfung beweisen können, mit `[skip ci]` pushen — und die Verifikation
  einmal per `workflow_dispatch` fahren statt durch wiederholtes Pushen.

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
