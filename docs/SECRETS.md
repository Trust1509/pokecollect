# Geheimnisse: was gebraucht wird und wo es hingehört

## Grundregel

**Der Agent trägt keine Geheimnisse ein.** Auch nicht auf Zuruf, auch nicht in
eine private Datei, auch nicht „nur zum Testen". Er darf Platzhalter setzen, das
erwartete Format erklären und die Stelle vorbereiten — den Wert setzt der Mensch
ein.

Der Grund ist nicht Misstrauen: Ein Wert, der durch einen Chatverlauf, ein
Werkzeug-Protokoll oder einen Subagenten-Bericht läuft, liegt danach an Stellen,
die niemand mehr überblickt.

Praktisch heißt das hier: **Der Gemini-/OpenAI-/OpenRouter-Schlüssel wird vom
Owner selbst eingetragen** — auf der Einstellungs-Seite der laufenden App oder
als Umgebungsvariable vor `teststand.sh up`. Nie im Repo, nie im Chat.

## Wo Geheimnisse hingehören

| Zweck | Ort |
|---|---|
| Lokale Entwicklung / Teststand | `.env` (in `.gitignore`), Vorlage `.env.example` |
| Betrieb auf dem Server | `.env` auf dem TrueNAS, nicht im Repo |
| Lese-Modelle (Gemini/OpenAI/OpenRouter) | Einstellungs-Seite der App — landen verschlüsselt in der DB, `GET /settings` gibt sie nur maskiert zurück (`*_set` / `*_masked`) |
| CI (falls je nötig) | GitHub-Secrets des Repos |

Heute braucht die CI **kein** Secret — die Gates laufen gegen Wegwerf-Container
mit fest verdrahteten Test-Zugangsdaten. Das ist Absicht: Ein Workflow ohne
Geheimnis kann keines verlieren.

## Was im Repo stehen darf

- `.env.example` mit **Platzhaltern** und Erklärung des Formats.
- Test-Zugangsdaten für Wegwerf-Stapel (`docker-compose.test.yml`,
  `docker-compose.smoke.yml`): `admin` / `teststand`, ein bcrypt-Hash davon,
  `JWT_SECRET=teststand-secret`. Dort liegt nichts Echtes, und der Stapel ist
  von außen nicht erreichbar.
- **Keine echten IP-Adressen** — Platzhalter `<server-ip>` (die LAN-Adresse
  wurde einmal per `filter-branch` aus der History entfernt).

## Wenn doch etwas durchgerutscht ist

1. Wert **beim Aussteller widerrufen** — das ist der einzige Schritt, der zählt.
2. Neuen Wert erzeugen und an der richtigen Stelle hinterlegen.
3. Erst danach die Historie bereinigen. Einen Commit zu entfernen macht einen
   veröffentlichten Schlüssel nicht ungültig; Klone und Zwischenspeicher
   bleiben.

## Nicht in Agenten-Konfigurationen

Ein Zugangstoken in der Konfigurationsdatei des Agenten (als Umgebungsvariable
in den Werkzeug-Einstellungen) ist bequem und die schlechteste Ablage: sichtbar
für **jede** Sitzung, für jeden Subagenten, und es landet im Protokoll jeder
Sitzung, die es liest. Stattdessen das Anmeldewerkzeug der jeweiligen Plattform
benutzen, das den Zugang im Schlüsselspeicher des Betriebssystems ablegt.

## Zugriff des Agenten auf die Produktivinstanz

Heute: **lesend über HTTP** (`curl <server-ip>:3010/health`), sonst nichts. SSH
ist für Agenten geblockt, deployen macht der Owner, und es gibt keinen
MCP-Server mit schreibenden Werkzeugen.

Ein technischer Wächter (PreToolUse-Hook mit fail-closed-Allowlist) ist deshalb
**heute gegenstandslos** — aber die Entscheidung hängt an einer einzigen
Bedingung:

> **Sobald ein Produktiv-Token oder das Prod-Passwort in den Kontext eines
> Agenten gerät, wird der Wächter sofort nötig.** Dann ist die Sperre keine
> strukturelle mehr, sondern nur noch der Umstand, dass der Agent die
> Zugangsdaten nicht kennt.

Wenn es soweit ist: Die **Quelle** des Wächters gehört ins Repo (versioniert,
testbar), **ausgeführt** wird eine Kopie **außerhalb** — ein Schutz, den der
geschützte Agent per Repo-Änderung entschärfen kann, ist keiner. Vorlage und
Testfälle stehen in `Trust1509/agent-projekt-template`
(`docs/vorlagen/prod-readonly-hook.py`), inklusive der Echtprobe: erst wenn ein
**echter** Aufruf nachweislich am Wächter vorbeikommt oder blockiert wird, ist
er bewiesen.
