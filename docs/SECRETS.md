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

Gewollt ist: **lesend über HTTP** (`curl <server-ip>:3010/health`). Deployen
macht der Owner, und für dieses Projekt gibt es keinen MCP-Server (gemessen
19.10.2026: keiner in der Client-Konfiguration).

**SSH, gemessen am 19.10.2026 ohne Verbindung** (Kommandos in `CLAUDE.md`,
„Deploy“): In den Agenten-Einstellungen steht keine SSH-Regel. Auf diesem
Rechner liegt aber seit dem 18.10.2026 ein SSH-Schlüssel für Agenten
(`~/.ssh`, Kommentar `claude-homelab`), den der Owner für andere Geräte im
Heimnetz angelegt hat. **Ob er auf dem Server gilt, ist nicht gemessen** — das
zeigte nur ein Verbindungsversuch, und der gehört nicht zu den Aufgaben eines
Agenten. Die Frage steht beim Owner (Issue „Abgleich v1.18.13“).

Ob ein technischer Wächter (PreToolUse-Hook mit fail-closed-Allowlist) nötig
ist, hängt an einer einzigen Bedingung:

> **Sobald ein Produktiv-Token, das Prod-Passwort oder ein SSH-Weg zum Server
> für einen Agenten erreichbar ist, wird der Wächter sofort nötig.** Ein
> Schlüssel auf der Platte gehört dazu: Er muss nicht gekannt werden, ein
> Aufruf mit `-i` genügt. Bis der Owner die Frage oben beantwortet hat,
> benutzt kein Agent diesen Schlüssel gegen den Server — das ist Disziplin,
> keine Sperre.

**Welcher Wächter, hängt am Weg.** Der Wächter unten (Vorlage
`prod-readonly-hook.py`) entscheidet nur über MCP-Werkzeuge mit einem festen
Präfix; alles andere lässt er als „anderer Namensraum" durch. Einen
`ssh -i …` über Bash oder PowerShell trifft er deshalb nicht. Für den SSH-Weg
trägt strukturell nur eines: **Der Schlüssel gilt auf dem Server nicht.** Eine
Deny-Regel nach Kommandonamen (`ssh`, `scp`, `plink`) in den
Agenten-Einstellungen wäre nur eine Teil-Sperre: eine Denylist, die `sftp`,
`rsync -e ssh`, einen absoluten Pfad zum Programm oder eine SSH-Bibliothek
durchlässt — das Gegenteil der fail-closed-Allowlist oben, und eine Probe
„ein gesperrter Aufruf scheitert" belegt nur den einen Namen. Die Vorlage hat
für diesen Weg kein Werkzeug (an sie gemeldet).

Wenn es soweit ist: Die **Quelle** des Wächters gehört ins Repo (versioniert,
testbar), **ausgeführt** wird eine Kopie **außerhalb** — ein Schutz, den der
geschützte Agent per Repo-Änderung entschärfen kann, ist keiner. Vorlage und
Testfälle stehen in `Trust1509/agent-projekt-template`
(`docs/vorlagen/prod-readonly-hook.py`), inklusive der Echtprobe: erst wenn ein
**echter** Aufruf nachweislich am Wächter vorbeikommt oder blockiert wird, ist
er bewiesen.
