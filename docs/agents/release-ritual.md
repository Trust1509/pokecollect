# Release-Ritual

## Grundsätze

**Version und Notizen im selben Commit.** Ein Tag ohne gepflegten
CHANGELOG-Eintrag zeigt dem Nutzer die Angaben der Vorversion — inklusive
falscher Risiko-Kennzeichnung.

**Die Version steht an ZWEI Stellen** und wird gemeinsam gezogen:
`web/src/lib/version.ts` (`APP_VERSION`) und `backend/app/config.py`
(`app_version`). Der Rauchtest prüft den Gleichstand selbst („API und Oberfläche
melden dieselbe Version") — der häufigste Deploy-Fehler ist, dass nur eines der
beiden Images neu ist.

**Risiko ehrlich kennzeichnen** — als Zusatz in der CHANGELOG-Überschrift:

| Stufe | Bedeutung |
|---|---|
| `gefahrlos` | nur Code, keine Migration |
| `backup` | Light-Migration im Spiel — Backup vor dem Deploy empfohlen |
| `breaking` | Hinweise beachten, Backup zwingend |

**Im Zweifel die vorsichtigere Stufe.** Auch eine reine Index-Migration ändert
keine Daten und bekommt trotzdem `backup`, damit die Kennzeichnung verlässlich
bleibt. Ein Flag, das mal so und mal so gemeint ist, wird ignoriert.

> Diese Kennzeichnung war bis v1.4.0 gepflegt und ist danach eingeschlafen,
> obwohl seither fast jede Auslieferung eine Light-Migration mitbringt
> (Abgleich 15.08.2026). Sie ist wieder verbindlich.

**Autonomes Release ist freigegeben** für: gefahrlos **und** alle Gates grün
**und** real im Teststand verifiziert. Alles andere (Migration, Auth, Security,
möglicher Datenverlust) braucht **Owner-OK vor dem Tag** — siehe Riskant-Gate in
`CLAUDE.md`.

## Ablauf

1. **Alles gelandet**, CI grün — jeden Lauf **run-id-gepinnt** beobachten
   (`gh run watch <id> --exit-status`), nie über eine Listenposition.
2. **Version an beiden Stellen** ziehen.
3. **CHANGELOG-Eintrag** ganz oben: Titel, Risiko-Stufe, was der Nutzer merkt.
   In seiner Sprache, nicht in der des Codes: *was er merkt*, nicht welche
   Funktion umgebaut wurde.
4. **Gates**: `sh scripts/gates.sh all`.
5. **Rauchtest**: `sh scripts/smoke.sh` — frischer Stapel, damit nicht ein
   veralteter Stand geprüft wird.
6. **Teststand**: `sh scripts/teststand.sh up` und die geänderten Stellen im
   Browser ansehen. Bei UI-Änderungen **mobil** mitprüfen (Mobile-First-PWA).
7. Tag + `gh release create`, Notizen aus dem CHANGELOG-Abschnitt.
8. **Deploy-Anweisung an den Owner** — deployen macht immer er.

## Notizen schreiben

Was der Nutzer merkt, nicht was umgebaut wurde:

> ❌ „`variant_usd` liefert jetzt zusätzlich den Varianten-Schlüssel"
> ✅ „Der angezeigte TCGplayer-Preis war der Basispreis der Karte, nicht der der
> besessenen Variante — bei einer Pokéball-Karte stand $0.25 neben einem Wert,
> der aus $0.60 kam."

**Nach einem Folge-Slice gegenlesen.** Ein Eintrag kann durch den nächsten Slice
unwahr werden.

## Nach dem Ausliefern

**Prüfen, ob es wirklich läuft** — `curl <server-ip>:3010/health` sagt mehr als
eine Versionsanzeige: Es liefert die Backend-Version, die mit der Oberfläche
übereinstimmen muss.
