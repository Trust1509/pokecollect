# PokéCollect – Deploy-Anleitung

> **Aktueller Stand:** Lokaler Build (Images noch nicht auf GitHub veröffentlicht).
> Sobald v1.0.0 fertig ist, werden die Images auf ghcr.io gepusht.

---

## Voraussetzungen

- TrueNAS Scale (oder beliebiger Linux-Server mit Docker + ZFS)
- Portainer (Stack-Deployment)
- Caddy als Reverse Proxy (bereits vorhanden)
- SSH-Zugang zum Server
- Git auf dem Server

---

## 1. ZFS-Datasets anlegen (einmalig)

```bash
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/db
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/images
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/config

chown -R 3010:3010 /mnt/HDDs/Applications/pokecollect/
```

> Das frühere `cache`-Dataset (Redis) wird seit v0.9.11 nicht mehr benötigt –
> Redis war ungenutzt und wurde aus dem Stack entfernt. Ein vorhandenes Dataset
> kann bleiben oder gelöscht werden.

---

## 2. User anlegen (einmalig)

```bash
groupadd -g 3010 pokecollect
useradd -u 3010 -g 3010 -M -s /sbin/nologin pokecollect
```

---

## 3. Repo klonen (einmalig)

```bash
cd /mnt/HDDs/Applications/pokecollect
git config --global --add safe.directory /mnt/HDDs/Applications/pokecollect/app
git clone https://github.com/Trust1509/pokecollect.git app
```

---

## 4. .env-Datei anlegen (einmalig)

```bash
cat > /mnt/HDDs/Applications/pokecollect/config/.env << 'EOF'
POSTGRES_USER=pokecollect
POSTGRES_PASSWORD=<sicheres_passwort>
POSTGRES_DB=pokecollect
DATABASE_URL=postgresql://pokecollect:<passwort>@db:5432/pokecollect
JWT_SECRET=<langer_zufälliger_string>
APP_USERNAME=admin
APP_PASSWORD_HASH=<bcrypt_hash>
NEXT_PUBLIC_API_URL=http://<server-ip>:3010
CORS_ORIGINS=http://<server-ip>:3011
GEMINI_API_KEY=
CARDMARKET_APP_TOKEN=
CARDMARKET_APP_SECRET=
CARDMARKET_ACCESS_TOKEN=
CARDMARKET_ACCESS_SECRET=
EOF

# Symlink damit docker compose die .env findet:
ln -s /mnt/HDDs/Applications/pokecollect/config/.env \
      /mnt/HDDs/Applications/pokecollect/app/.env
```

> **Wichtig `NEXT_PUBLIC_API_URL`:** Next.js brennt diese URL zur **Build-Zeit** in den JavaScript-Bundle ein.
> Sie muss die extern erreichbare IP/Domain des Servers enthalten, nicht `localhost`.
> Nach jeder Änderung dieser Variable muss das Web-Image neu gebaut werden.

> **`CORS_ORIGINS`:** Die API erlaubt nur noch die hier gelisteten Browser-Origins
> (kommagetrennt, kein `*` mehr). Auf dem Server also die Web-URL eintragen:
> `CORS_ORIGINS=http://<server-ip>:3011`. Leer/ungesetzt gilt der Entwicklungs-Default
> `http://localhost:3011,http://localhost:3021`.

> **`APP_PASSWORD_HASH` ist Pflicht:** Seit Issue #1 gibt es kein eingebautes
> Default-Passwort mehr — ohne gesetzten Hash verweigert die API den Start
> (Fehlermeldung im Container-Log nennt die Abhilfe).

Bcrypt-Hash generieren (mit lokalem Python):
```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'DEIN_PASSWORT', bcrypt.gensalt()).decode())"
```

Oder ohne lokales Python via Docker:
```bash
docker run --rm python:3.12-slim sh -c \
  "pip -q install bcrypt==4.0.1 && python -c \"import bcrypt; print(bcrypt.hashpw(b'DEIN_PASSWORT', bcrypt.gensalt()).decode())\""
```

---

## 5. Erstmalig deployen

```bash
cd /mnt/HDDs/Applications/pokecollect/app
chmod +x deploy.sh
bash deploy.sh
```

> Die Datenbank initialisiert sich beim ersten API-Start selbst:
> `Base.metadata.create_all()` + Light-Migrations legen alle Tabellen und
> Spalten an — ein manueller SQL-Import ist nicht nötig.

---

## 6. Caddy-Config aktualisieren (einmalig)

```bash
cat /mnt/HDDs/Applications/pokecollect/app/deploy/Caddyfile.snippet \
  >> /mnt/HDDs/Applications/caddy/Caddyfile
caddy reload --config /mnt/HDDs/Applications/caddy/Caddyfile
```

---

## Updates einspielen

```bash
bash /mnt/HDDs/Applications/pokecollect/app/deploy.sh
```

Das Script macht automatisch: `git pull` → `chown` → API rebuild → Web rebuild → neu starten.

---

## Was muss wann neu gebaut werden?

| Änderung                        | Befehl                                          |
|---------------------------------|-------------------------------------------------|
| Backend Python-Code             | `docker compose build api && docker compose up -d api` |
| Frontend TypeScript/TSX/CSS     | `docker compose build web && docker compose up -d web` |
| `NEXT_PUBLIC_API_URL` geändert  | `docker compose build web && docker compose up -d web` |
| `docker-compose.yml` geändert   | `docker compose up -d`                          |
| Alles (nach `git pull`)         | `bash deploy.sh`                                |

> **Häufiger Fehler:** `docker compose restart api` baut das Image **nicht** neu —
> es startet nur den bestehenden Container neu. Für Code-Änderungen immer `build` verwenden.

> **Häufiger Fehler:** `NEXT_PUBLIC_API_URL` als Runtime-Env setzen reicht nicht —
> Next.js benötigt den Wert zur Build-Zeit. Nur `docker compose build web` liest die `.env` aus.

---

## Ports

| Dienst       | Host-Port |
|--------------|-----------|
| API          | 3010      |
| Web-Frontend | 3011      |
| Authelia     | 9091      |

---

## Externen Zugriff mit Authelia einrichten

> **Architektur:** Intern (192.168.2.x) ist alles offen. Extern (über Caddy + Authelia) wird ein Login erzwungen, bevor die App erreichbar ist.

### Schritt 1 – Authelia-Datasets anlegen (einmalig)

```bash
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/authelia/config
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/authelia/data
chown -R 1000:1000 /mnt/HDDs/Applications/authelia/
```

### Schritt 2 – Konfigurationsdateien hochladen

```bash
# Auf dem Entwicklungsrechner:
scp deploy/authelia/configuration.yml your_admin@192.168.x.x:/mnt/HDDs/Applications/authelia/config/
scp deploy/authelia/users_database.yml your_admin@192.168.x.x:/mnt/HDDs/Applications/authelia/config/
```

### Schritt 3 – Passwort-Hash für Authelia generieren

```bash
docker run --rm authelia/authelia:latest \
  authelia crypto hash generate bcrypt --password 'DEIN_PASSWORT'
```

Den ausgegebenen Hash in `/mnt/HDDs/Applications/authelia/config/users_database.yml` eintragen:

```yaml
users:
  your_username:
    displayname: "Your Name"
    password: "$2b$12$xxxx..."   # Hash hier eintragen
    email: your@email.com
    groups:
      - admins
```

### Schritt 4 – Geheimnisse in configuration.yml eintragen

```bash
# Zwei zufällige Strings generieren (je mind. 64 Zeichen):
openssl rand -hex 48   # → für jwt_secret
openssl rand -hex 48   # → für session.secret
```

In `/mnt/HDDs/Applications/authelia/config/configuration.yml` eintragen.

### Schritt 5 – Authelia als Portainer-Stack deployen

Neuen Stack in Portainer anlegen mit folgendem Inhalt:

```yaml
services:
  authelia:
    image: authelia/authelia:4.38
    container_name: authelia
    user: "1000:1000"
    volumes:
      - /mnt/HDDs/Applications/authelia/config:/config
    ports:
      - "9091:9091"
    restart: unless-stopped
```

### Schritt 6 – Caddy-Config aktualisieren

Inhalt von `deploy/Caddyfile.snippet` ans bestehende Caddyfile anhängen:

```bash
cat /mnt/HDDs/Applications/pokecollect/app/deploy/Caddyfile.snippet \
  >> /mnt/HDDs/Applications/caddy/Caddyfile

# DNS-Eintrag für auth.yourdomain.com auf your.external.ip setzen, dann:
caddy reload --config /mnt/HDDs/Applications/caddy/Caddyfile
```

### Schritt 7 – Testen

1. `https://auth.yourdomain.com` aufrufen → Authelia Login-Seite erscheint
2. `https://pokecollect.yourdomain.com` aufrufen → Weiterleitung zu Authelia
3. Mit den Zugangsdaten aus `users_database.yml` einloggen
4. App öffnet sich nach erfolgreichem Login

### Troubleshooting Authelia

```bash
# Logs prüfen:
docker logs authelia --tail 30

# Konfiguration validieren:
docker exec authelia authelia validate-config --config /config/configuration.yml
```
