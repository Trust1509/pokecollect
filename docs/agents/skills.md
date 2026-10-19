# Skills: fertige Methoden, die dieser Prozess voraussetzt

Herkunft: `mattpocock/skills`, installiert **global** unter `~/.claude/skills/`.
Herkunft, Installationswege und Mindestsatz führt `skills.md` der Vorlage; hier
steht, was davon bei uns gilt.

**Skills liegen pro Rechner, nicht im Repo — und nicht in einer
Cloud-Sitzung.** Ein frischer Klon bringt sie nicht mit; auf einem neuen
Rechner zuerst `/setup-matt-pocock-skills` ausführen. Eine Cloud-Sitzung
startet in einem frischen Container ohne `~/.claude` des Owners: Dort fehlen
still die Skills, die globale `CLAUDE.md` und die Panel-Werkzeuge außerhalb des
Repos (Vorlage v1.18.1). Nur Skills nennen, die dort **wirklich existieren** —
ein erfundener oder veralteter Name ist eine teure Art, Zeit zu verlieren.

## Namen: Quell-Repo und dieser Rechner laufen auseinander

**Geprüft am 19.10.2026** gegen `.claude-plugin/plugin.json` des Quell-Repos
(Plugin `mattpocock-skills` 1.3.1, 27 Skills) und gegen `ls ~/.claude/skills/`
auf diesem Rechner:

```bash
gh api repos/mattpocock/skills/contents/.claude-plugin/plugin.json --jq .content | base64 -d
```

Im Quell-Repo sind vier Namen umbenannt (am Inhalt geprüft, Vorlage v1.18.1):
`to-prd` → `to-spec`, `to-issues` → `to-tickets`, `review` → `code-review`;
`ubiquitous-language` ist in `domain-modeling` aufgegangen. Entfallen sind
`design-an-interface`, `qa`, `request-refactor-plan`,
`resolving-merge-conflicts` und `decision-mapping`. **Auf diesem Rechner liegen
noch die alten Kopien:** `to-prd`, `to-issues`, `review` und
`ubiquitous-language` gibt es hier, `to-spec` und `to-tickets` nicht. Ein
frischer Rechner und jede Cloud-Sitzung haben es umgekehrt. Die Tabelle unten
nennt deshalb beide.

**Achtung bei `code-review`:** Auf diesem Rechner ist `code-review` der
eingebaute Skill von Claude Code (Korrektheits-Review mit Effort-Stufen),
nicht der umbenannte `review` aus dem Quell-Repo (Standards und Spezifikation
in parallelen Subagenten). Wer hier den Standards-und-Spezifikations-Review
will, ruft `review`.

## Abgrenzung: Skill ≠ Prozess

Ein Skill ist eine **Methode**, der Prozess ist die **Verbindlichkeit**. `tdd`
sagt, *wie* man test-first arbeitet; dass jeder neue Test einen Rot-Beweis
braucht, sagt `bau-brief.md`. **Wo beide etwas zum selben Thema sagen, gilt der
Prozess.**

## Abgrenzung: Review-Skill ≠ Panel

Der Review-Skill (`review` hier, `code-review` im Quell-Repo) fährt mehrere
Subagenten **desselben Anbieters**. Das ist wertvoll als Vorstufe, aber
**nicht unabhängig** im Sinne des Panels: Das lebt davon, dass der Fremdprüfer
von einem anderen Anbieter kommt und Blind- wie Gegenprüfer den Bau-Kontext
nicht kennen (Namen seit Vorlage v1.15.0). Der Review-Skill ersetzt das Panel
nicht — siehe `panel.md`.

## Nach Prozess-Phase

| Phase | Skill (Quell-Repo; auf diesem Rechner, wenn anders) | Wozu hier |
|---|---|---|
| Vor dem Bauen | `grilling`, `grill-me`, `/grill-with-docs` | Große oder riskante Designs durchleuchten, bevor eine Zeile entsteht (CLAUDE.md, Arbeitsregel 7). Lock-Spec als Issue-Kommentar. |
| Vor dem Bauen | `domain-modeling` (hier zusätzlich die alte Kopie `ubiquitous-language`) | Begriffe scharf halten — hier besonders wichtig, weil Fremdquellen dieselben Wörter anders benutzen (Folierung, Muster, Variante). Ergebnis nach `CONTEXT.md`. |
| Zerlegen | `/to-spec`, `/to-tickets` (hier: `/to-prd`, `/to-issues`) | Aus einer Diskussion eine Spezifikation, daraus vertikale Slices. Passt zu „ein Issue, ein Commit". |
| Fundament | `codebase-design` | Modul-/Schnittstellenschnitt bei größeren Umbauten. (`design-an-interface` ist im Quell-Repo entfallen, hier noch vorhanden.) |
| Bauen | `tdd` | Test-first. Der **Rot-Beweis** kommt aus `bau-brief.md` und geht vor. |
| Prüfen | `diagnosing-bugs` | Strukturierte Schleife statt Rateversuchen — besonders bei Fehlern, die nur in Produktion auftreten. |
| Prüfen | `code-review` (hier: `review`, siehe „Achtung" oben) | Vorstufe zum Panel, kein Ersatz (siehe oben). |
| Aufräumen | `/improve-codebase-architecture` | Architektur-Schwachstellen scannen, wenn eine Welle abgeschlossen ist. |
| Triage | `/triage` | Issue-Status pflegen. (`qa` ist im Quell-Repo entfallen, hier noch vorhanden.) |
| Sitzungswechsel | `handoff` | Übergabe an die nächste Sitzung, wenn der Kontext knapp wird. |
| Unklar | `/ask-matt` | Router, wenn nicht klar ist, welcher Skill passt. |

Nur im Quell-Repo, auf diesem Rechner (noch) nicht vorhanden: `research`,
`wayfinder`, `implement-spec`, `pr`, `retro` — Beschreibung in `skills.md` der
Vorlage.

## Was hier NICHT über Skills läuft

- **Das Panel** — eigenes Verfahren, `panel.md`.
- **Das Release** — eigenes Ritual, `release-ritual.md`.
- **Die Gates** — `scripts/gates.sh` und `scripts/smoke.sh`, nicht wegdelegierbar.
