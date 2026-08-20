# Bau-Brief: Vorlage für Aufträge an Bau-Subagenten

> **Der Bau-Brief ist die einzige Leitplanke, die den Bauer erreicht.** Regeln im
> Repo erreichen ihn nicht: Ein Bau-Subagent arbeitet den Brief ab, nicht
> `docs/agents/`. In fünf Projekten gemeldet; zweimal ist genau daran eine
> Pflichtregel gescheitert — sie stand im Repo und fehlte im Brief.

Ein Bau-Brief ist der Unterschied zwischen einem Slice, der beim ersten Panel
durchgeht, und einem, der drei Runden braucht. Die Punkte unten stehen alle,
weil ihr Fehlen einmal etwas gekostet hat — die Belege in `lehren.md`.

## Pflicht-Gerüst (alle acht Blöcke, keiner leer)

Vor dem Absenden prüfen: `sh scripts/bau-brief-pruefen.sh <brief.md>`.

**Baut der Hauptagent selbst, entfällt der Empfänger — nicht das Gerüst**
(v1.9.0). Die acht Themen werden dann vor dem ersten Commit durchgegangen. Für
dieses Repo ist das der Regelfall bei kleinen Scheiben; #52, #53, #55 und #67
sind ohne jeden Brief entstanden, und bei #52 hat genau das gefehlt, was Block 5
verlangt hätte.

**Die acht Themen sind die Pflicht, die Gliederung ist ein Vorschlag** (v1.8.1).
Das Skript sucht die Themen im ganzen Dokument und meldet ein Fehlen als *Fund,
kein Urteil* — ob ein Thema hier gegenstandslos ist, entscheidet weiterhin der
Kopf.

```markdown
## 1 Auftrag            was gebaut wird, in zwei Sätzen
## 2 Befund             bereits verifiziert — NICHT neu recherchieren
## 3 Konsumenten        WER RUFT DEN GEÄNDERTEN CODE AUF? Jeden nennen.
## 4 Sichtbares         ändert der Slice sichtbares Verhalten? CHANGELOG-Folge?
## 5 Nachweis           Rot-Beweis je neuem Test, inkl. Verdrahtung;
                        bei ganzen Suiten zwei Mutationen
## 6 Prüf-Kommandos     ALLE, die die CI fährt — nicht nur die naheliegenden
## 7 Fixtures           erfunden, nie aus dem Kontext übernommen
## 8 Randbedingungen    Vordergrund, lokal committen, nicht pushen,
                        Umfang nicht erweitern
```

**Block 3 ist der teuerste, wenn er fehlt** — in vier von fünf Projekten kam
darüber ein Fund, den sonst niemand hatte. Hier ebenfalls: Die Frage nach den
Aufrufern hat im #55-Slice den schwersten Fund gebracht (dasselbe Schema wird
serverseitig aus OCR-Text gebaut).

**Block 5 hat immer einen Gegenstand** — dieses Projekt führt eine Testsuite
(`backend/tests/`, 437 Tests) und einen Rauchtest. Ein Brief, der ihn leer lässt,
ist unfertig, nicht „nicht zutreffend".

**Was NICHT in den Brief gehört: Bewegungsverbote.** Ein Brief liefert Befunde,
keine gesperrten Zonen. Real hier passiert: Mein Brief zu #66 verbot, `_apply_full`
anzufassen — genau dort saß die Ein-Zeilen-Behebung eines Panel-Funds, und die
Nacharbeit musste das Verbot ausdrücklich aufheben.

Ist eine Abgrenzung nötig, gehört sie als **Befund mit Ziel** in den Brief, nicht
als Verbot: „`enrich_catalog` trägt dieselbe Klasse, wird aber in #75 eigens
behandelt" sagt dem Bauer, warum er es stehen lässt — und wo die Arbeit hingeht.

---

## Gerüst

```
Repo: C:\Users\manue\.claude\Immich\pokecollect. Branch main, HEAD ⟨…⟩.
Baue Issue #⟨…⟩.

## Befund (bereits verifiziert, nicht neu recherchieren)
⟨Was schon gemessen/geprüft ist — mit Datei:Zeile.⟩

## Auftrag
⟨Was gebaut werden soll. Bei mehreren Teilen: Reihenfolge und warum.⟩

## Fallen, die ich kenne
⟨Einschlägiges aus docs/agents/lehren.md wörtlich hereinkopieren.⟩

## Pflichtfragen
- Wer ruft den geänderten Code auf? (auflisten, nicht behaupten)
- Wird derselbe Code auch SERVERSEITIG aufgerufen, nicht nur vom Client?
- Ändert der Slice sichtbares Verhalten? (dann Doku/CHANGELOG im selben Slice)
- Rot-Beweis je neuem Test — auch die Verdrahtung sabotieren.

## Abnahme
⟨Prüfbare Punkte, kein Fließtext. Je Punkt: womit belegt.⟩

## Randbedingungen
sh scripts/gates.sh all        # Backend-pytest gegen echtes Postgres + Web-Build
sh scripts/smoke.sh            # nur wenn die Oberfläche berührt ist (~3-5 min)
Läufe im Vordergrund, Zeitlimits explizit, keine Hintergrundprozesse.
Lokal committen, NICHT pushen. Landen entscheidet der Hauptagent nach dem Panel.
Echte Umlaute in allen deutschen Texten; UI-Texte in DE und EN pflegen.
```

---

## Die Pflichtfragen — warum sie drinstehen

**„Wer ruft den geänderten Code auf?"**
Der Bauer soll die Konsumenten **auflisten**, nicht behaupten, es gäbe keine.

**„Wird derselbe Code auch serverseitig aufgerufen?"**
Diese Frage hat den #55-MAJOR gefunden: Das gehärtete Schema wird nicht nur vom
Client geschickt, sondern auch aus OCR-/Modelltext **im Server** gebaut. Eine
Sperre, die für den Client richtig ist, wäre dort ein Absturz.

**„Ändert der Slice sichtbares Verhalten?"**
Wenn ja, gehören CHANGELOG-Eintrag und Doku in denselben Slice. Sonst driftet
die Doku, und der nächste Agent glaubt ihr.

**„Rot-Beweis für jeden neuen Test."**
Den Fix sabotieren und zeigen, dass der Test fällt. **Auch die Verdrahtung
sabotieren** — die Frage lautet: „Welche einzelne Zeile könnte ich löschen, ohne
dass etwas rot wird?"

**Wird eine ganze SUITE als Sicherheitsnetz gemeldet** (Rauchtest,
Property-Tests), gilt dasselbe eine Ebene höher: mindestens einen bekannten
Fehler zurückbauen und zeigen, dass die Suite rot wird. Bleibt eine Mutation
grün, ist das ein Fund — die Grenze der Aussage gehört als Kommentar in den Test.

---

## Fixtures werden erfunden, nie aus dem Kontext übernommen

**Pflichtzeile in jeden Bau-Brief.** Ohne ausdrückliche Regel nimmt der Bauer
die Beispiele, die im Gespräch herumliegen — und das sind die echten.

Der Fall aus der Vorlage ist zweistufig, und die zweite Stufe ist der
eigentliche Befund: Ein Bau-Subagent brauchte einen Namen für ein Testszenario,
erfand keinen, sondern nahm den echten Namen einer realen Person aus dem
Gesprächskontext und schrieb ihn in einen committeten Seed. **Danach** wurde
daraus eine Regel formuliert — und in die Regel selbst schrieb der Hauptagent
denselben echten Namen als Beleg.

Die Klasse trifft also nicht nur den Bauer: **Wer den Vorfall dokumentiert,
wiederholt ihn.** Hier gilt sie auch für Karten- und Sammlungsnamen in Seeds und
Tests — erfundene Namen mit erkennbarem Testpräfix (`RT-…`, `H55-…`), nie
Beispiele aus dem Gespräch.

## Randbedingungen, die immer mitmüssen

- **Alle** Prüf-Kommandos nennen, die die CI fährt — nicht nur die
  naheliegenden. Die CI fährt `pytest` (gegen echtes Postgres), `tsc --noEmit`
  und `next build`; `scripts/gates.sh all` deckt genau das ab.
- Läufe im **Vordergrund**, Zeitlimits explizit. Keine Hintergrundprozesse,
  keine eigenen Subagenten.
- **Lokal committen, nicht pushen.**
- Bei Datenbank-Tests: gegen eine **echt migrierte** DB testen (`conftest.py`
  fährt Postgres, SQLite ist ausgeschlossen), IDs vor dem Commit lesen.
- Wenn parallel ein anderer Slice läuft: **welche Dateien tabu sind**.
- Sprache/Zeichensatz: echte Umlaute, interne ASCII-Werte nie roh ins UI.

---

## Typische Fallen (in den Brief kopieren, wenn einschlägig)

**Light-Migration.** Additiv und idempotent. Bekannte Altdaten schreiben,
Migration fahren, Erhalt auslesen, ein zweites Mal fahren, Gleichstand zeigen.
Expand–Contract: nie erweitern und verengen im selben Release.

**Preise/Werte.** Der angezeigte Wert muss aus den Quelldaten stammen, nie
gerechnet sein; die bepreiste **Variante** gehört ins Label; Umrechnungskurse
nur im Plausibilitätsfenster; bei Quellenausfall lieber kein Update als ein
stiller Wechsel der Bezugsgröße.

**Eingabe-Härtung.** Sperre auf den Schreib-Weg, nicht an die Basisklasse.
Serverseitig erzeugte Texte säubern statt ablehnen. Prüfen, was schon in der DB
liegt.

**Oberfläche.** Mobile-First: Was auf dem Desktop funktioniert, ist die selten
benutzte Hälfte. Neue Tabellen als responsive Karten, nicht als rohe Tabelle.

---

## Nacharbeit nach dem Panel

**Wer nacharbeitet, entscheidet ein Kriterium, keine Vorliebe** (v1.8.2):

- **Mechanische Auflage** — benannter Fix an benannter Stelle: **derselbe
  Bauer**. Sein Kontext spart die Einarbeitung.
- **Auflage, die den ENTWURF berührt** — Transaktionsgrenzen, Fehlerbehandlung,
  Datenfluss, Schnittstellenzuschnitt: **frischer Bauer**. Der bisherige
  verteidigt seine eigene Konstruktion, auch ohne es zu merken.

Selbstprüfung an unserem Fall: Die zweite #66-Runde hat aus einer langen
Transaktion zwei kurze gemacht und die Fehlerbehandlung umgebaut — das berührt
den Entwurf und hätte nach diesem Kriterium einen frischen Bauer gebraucht. Es
ging gut, war aber nicht abgesichert.

Im Nachtrag:

- **Was bestätigt wurde**, nicht nur was zu tun ist.
- **Widerlegte Befunde ausdrücklich abräumen.** Prüfer irren; ein
  unkommentierter Fehlbefund kostet eine Runde.
- Je Punkt: Schwere, Fundstelle, **Nachweis**. „Wirkt unsauber" ist kein Auftrag.
- Nacharbeits-Briefe tragen **dasselbe Pflicht-Gerüst** plus den Block
  „Ausdrücklich abgeräumt — hier ist nichts zu tun".

## Der Bericht des Bauers ist eine Absichtserklärung, kein Nachweis

Die Frage an einen Bericht lautet nicht „hast du geprüft", sondern **„was genau
hast du ausgeführt, und was kam heraus"** (v1.8.1). Zwei Muster, die anderswo
teuer waren:

- **Zitate nachschlagen.** Ein Bericht belegte drei rote Läufe als bekannte
  Flakes — mit Quellenangabe auf einen Abschnitt, der etwas völlig anderes
  behandelt. Geliehene Autorität tarnt einen ungeprüften Befund, und eine
  erfundene Quelle ist gefährlicher als gar keine: Sie liest sich wie ein
  nachgeschlagener Fakt.
- **Flakes reproduzieren.** „Vorbestehend, ordnungsabhängig" ist eine These, bis
  sie mit mehreren Läufen belegt ist.

Praktisch heißt das hier: Gate-Ergebnisse aus einem Bericht mindestens einmal
selbst nachfahren — sie sind billig zu wiederholen.
