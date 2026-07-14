# ADR-0001: Kredo — sechs Grundsätze für PokéCollect

Datum: 2026-07-14 · Status: angenommen (Owner-Abstimmung 2026-07-14)

## Kontext

PokéCollect übernimmt die in der Wagner-Business-App etablierte
Entwicklungs-Pipeline (Issue-getriebene Wellen, Gates, Teststand). Dazu
gehört ein explizites Kredo, gegen das Architektur-Reviews prüfen können.
Die Architektur-Analyse vom 2026-07-14 hat den Entwurf gegen den realen
Code gehalten und drei Ehrlichkeits-Anpassungen empfohlen, die hier
eingearbeitet sind.

## Entscheidung

Die sechs Grundsätze in CONTEXT.md „Grundsätze" sind verbindlich:

1. DRY — eine Routine je Sache (Invarianten nie in Routern duplizieren)
2. Mobile-First-Web (die Web-App ist die Mobile-App, siehe ADR-0002)
3. Testbar by default (Session-Injection, Unit-Tests für pure Logik)
4. Secrets nie im Klartext an Clients — **als Ziel formuliert**, solange
   Issue #1 (P0 Auth) offen ist; Neubauten dürfen den Zustand nicht
   verschlechtern
5. Additive Light-Migrations — destruktive Statements nur mit Owner-OK,
   im Code markiert
6. i18n DE/EN konsequent (gilt für die Web-App; native Apps existieren
   nicht mehr, ADR-0002)

## Konsequenzen

- Architektur-Reviews und Issue-Triage prüfen gegen diese Liste.
- Kredo 3 ist heute nicht erfüllt (Services erzeugen Sessions selbst,
  Issue #9) — es ist die Messlatte, nicht der Ist-Zustand.
- Kredo 4 wird mit dem P0-Auth-Paket (Issue #1) zum Ist-Zustand.
