# Vorlage: Panel-Kommentar

Kopiervorlage für das Panel-Ergebnis am Issue. **Die Form ist der Mechanismus** —
eine leere Überschrift springt ins Auge, ein fehlender Absatz nicht. Deshalb
bleiben alle drei Stimmen stehen, auch wenn eine nichts gefunden hat oder
ausgefallen ist.

Nicht kürzen, nicht zu Fließtext zusammenfassen, keine Stimme weglassen.

**Modell und Stand gehören in jede Überschrift** (v1.8.0). Ohne sie ist die
Herkunfts-Regel nach vier Wochen nicht durchsetzbar, und jede Aussage über
Modellverhalten bleibt Anekdote — Anbieter ziehen still nach.

**Panel-Bilanzen (Meldung an die Vorlage) tragen ab v1.11.3 Risikoklasse UND
Diff-Typ** — ohne beides sind Zahlen über Projekte hinweg nicht vergleichbar
(der Fragetyp bestimmt, was ein Panel wert ist).

**Eine Stimme zählt mit ihren Funden, nie mit ihrer Freigabe.** Ein „keine
Funde" beschreibt die Reichweite dieser Stimme, es ist kein Argument fürs
Landen. In der Arbitrierung wird begründet, was geprüft und widerlegt wurde —
nie „zwei von drei Stimmen sahen nichts".

> Warum das hier steht: In diesem Repo lief das Panel bereits **zweistimmig**,
> ohne dass es jemandem auffiel — der Kommentar war Fließtext plus Fund-Tabelle
> und las sich vollständig (siehe #38). Eine Regel ohne Form hält nicht; diese
> Datei **ist** die Form.

---

```markdown
## Panel ⟨Slice / Issue⟩

Basis: `⟨commit-a⟩..⟨commit-b⟩` · Risiko: R⟨n⟩ — Auslöser: ⟨…⟩ ·
Diff-Typ: ⟨backend/frontend/config/gemischt⟩ · Umfang: ⟨was geprüft wurde⟩

### Stimme 1 — Claude, blinde Erststimme (⟨modell⟩, ⟨datum⟩)
⟨Nur Diff + Repo, kein Bau-Brief, kein Bericht des Bauers. Je Fund: Schwere,
Datei:Zeile, Nachweis. „Keine Funde" ist ein gültiges Ergebnis und wird
hingeschrieben.⟩

### Stimme 2 — GPT über Codex (⟨modell⟩, ⟨datum⟩)
⟨Über denselben Diff, Zweig `review/⟨issue⟩-⟨kurzname⟩`.⟩

### Stimme 3 — ⟨R3: zweite blinde Claude-Repo-Stimme, adversarial (⟨modell⟩, ⟨datum⟩) · R2: entfällt (Klasse)⟩
⟨Bei R3: eigener Prüf-Fokus, adversarial gerahmt. Bei R2 bleibt die
Überschrift stehen mit „entfällt — R2-Mindestprüfung".⟩

### Arbitrierung
⟨Je Fund eines von DREI Urteilen: reproduziert · verworfen · richtiger Instinkt,
falsche Begründung. Dazu WIE reproduziert (Kommando, Test, Messung) und die
Attribution: welche Stimme hatte ihn, welche nicht. Vor jedem Verwerfen die
Gegenfrage beantworten: „Welche Eingabe würde der Stimme recht geben?"
Schwere-Umstufungen kennzeichnen (`KLEIN → WICHTIG (arb.)`).
Prüfer-Konvergenz ersetzt keine Reproduktion.⟩

**Urteil:** ⟨landen / nacharbeiten⟩
```

---

## Wenn eine Stimme fehlt

Überschrift **stehen lassen**, Grund darunter:

```markdown
### Stimme 3 — zweite blinde Claude-Repo-Stimme (adversarial)
Ausgefallen: Session-Limit mitten im Lauf (stimmen-neutral — auch die eigene
Stimme fällt aus). Ersatz nach Klumpenregel: GPT adversarial über den
Review-Zweig, gestartet am ⟨Datum⟩.
```

Ein Slice ohne vollständiges oder so vermerkt-verkürztes Panel gilt als **nicht
geprüft** und wird nicht ausgeliefert.
