# Bau-Brief: Vorlage für Aufträge an Bau-Subagenten

Ein Bau-Brief ist der Unterschied zwischen einem Slice, der beim ersten Panel
durchgeht, und einem, der drei Runden braucht. Die Punkte unten stehen alle,
weil ihr Fehlen einmal etwas gekostet hat — die Belege in `lehren.md`.

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

Denselben Subagenten weiterbeauftragen, nicht einen neuen — er hat den Kontext.
Im Nachtrag:

- **Was bestätigt wurde**, nicht nur was zu tun ist.
- **Widerlegte Befunde ausdrücklich abräumen.** Prüfer irren; ein
  unkommentierter Fehlbefund kostet eine Runde.
- Je Punkt: Schwere, Fundstelle, **Nachweis**. „Wirkt unsauber" ist kein Auftrag.
