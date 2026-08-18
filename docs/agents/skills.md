# Skills: fertige Methoden, die dieser Prozess voraussetzt

Herkunft: `mattpocock/skills`, installiert **global** unter `~/.claude/skills/`.

**Skills liegen pro Rechner, nicht im Repo.** Ein frischer Klon bringt sie nicht
mit; auf einem neuen Rechner zuerst `/setup-matt-pocock-skills` ausführen. Nur
Skills nennen, die dort **wirklich existieren** — ein erfundener Name ist eine
teure Art, Zeit zu verlieren.

## Abgrenzung: Skill ≠ Prozess

Ein Skill ist eine **Methode**, der Prozess ist die **Verbindlichkeit**. `tdd`
sagt, *wie* man test-first arbeitet; dass jeder neue Test einen Rot-Beweis
braucht, sagt `bau-brief.md`. **Wo beide etwas zum selben Thema sagen, gilt der
Prozess.**

## Abgrenzung: `review`-Skill ≠ Panel

Der `review`-Skill fährt mehrere Subagenten **desselben Anbieters**. Das ist
wertvoll als Vorstufe, aber **nicht unabhängig** im Sinne des Panels: Das lebt
von anderen Anbietern (Stimme 2 und 3) und von der blinden Erststimme.
`review` ersetzt das Panel nicht — siehe `panel.md`.

## Nach Prozess-Phase

| Phase | Skill | Wozu hier |
|---|---|---|
| Vor dem Bauen | `grilling`, `/grill-with-docs` | Große oder riskante Designs durchleuchten, bevor eine Zeile entsteht (CLAUDE.md Regel 6). Lock-Spec als Issue-Kommentar. |
| Vor dem Bauen | `domain-modeling`, `ubiquitous-language` | Begriffe scharf halten — hier besonders wichtig, weil Fremdquellen dieselben Wörter anders benutzen (Folierung, Muster, Variante). Ergebnis nach `CONTEXT.md`. |
| Zerlegen | `/to-prd`, `/to-issues` | Aus einer Diskussion eine Spec, aus der Spec vertikale Slices. Passt zu „ein Issue, ein Commit". |
| Fundament | `codebase-design`, `design-an-interface` | Modul-/Schnittstellenschnitt bei größeren Umbauten. |
| Bauen | `tdd` | Test-first. Der **Rot-Beweis** kommt aus `bau-brief.md` und geht vor. |
| Prüfen | `diagnosing-bugs` | Strukturierte Schleife statt Rateversuchen — besonders bei Fehlern, die nur in Produktion auftreten. |
| Prüfen | `review` | Vorstufe zum Panel, kein Ersatz (siehe oben). |
| Aufräumen | `/improve-codebase-architecture` | Architektur-Schwachstellen scannen, wenn eine Welle abgeschlossen ist. |
| Triage | `/triage`, `qa` | Issue-Status pflegen; QA-Sitzungen mit dem Owner in Issues überführen. |
| Unklar | `/ask-matt` | Router, wenn nicht klar ist, welcher Skill passt. |

## Was hier NICHT über Skills läuft

- **Das Panel** — eigenes Verfahren, `panel.md`.
- **Das Release** — eigenes Ritual, `release-ritual.md`.
- **Die Gates** — `scripts/gates.sh` und `scripts/smoke.sh`, nicht wegdelegierbar.
