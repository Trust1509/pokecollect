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
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/cache
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/config

chown -R 3010:3010 /mnt/HDDs/Applications/pokecollect/
```

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
REDIS_URL=redis://redis:6379
JWT_SECRET=<langer_zufälliger_string>
APP_USERNAME=admin
APP_PASSWORD_HASH=<bcrypt_hash>
NEXT_PUBLIC_API_URL=http://<server-ip>:3010
CARDMARKET_APP_TOKEN=
CARDMARKET_APP_SECRET=
CARDMARKET_ACCESS_TOKEN=
CARDMARKET_ACCESS_SECRET=
POKEMONTCG_API_KEY=
EOF

# Symlink damit docker compose die .env findet:
ln -s /mnt/HDDs/Applications/pokecollect/config/.env \
      /mnt/HDDs/Applications/pokecollect/app/.env
```

> **Wichtig `NEXT_PUBLIC_API_URL`:** Next.js brennt diese URL zur **Build-Zeit** in den JavaScript-Bundle ein.
> Sie muss die extern erreichbare IP/Domain des Servers enthalten, nicht `localhost`.
> Nach jeder Änderung dieser Variable muss das Web-Image neu gebaut werden.

Bcrypt-Hash generieren:
```bash
docker run --rm python:3.12-slim sh -c \
  "pip install passlib[bcrypt] -q && python3 -c \"from passlib.hash import bcrypt; print(bcrypt.hash('mein_passwort'))\""
```

---

## 5. Erstmalig deployen

```bash
cd /mnt/HDDs/Applications/pokecollect/app
chmod +x deploy.sh
bash deploy.sh
```

---

## 6. Datenbank initialisieren (einmalig, nach erstem Start)

```bash
docker exec -i $(docker ps -qf name=pokecollect-db) \
  psql -U pokecollect -d pokecollect \
  < /mnt/HDDs/Applications/pokecollect/app/migrations/001_initial.sql
```

FastAPI legt Tabellen auch automatisch an beim ersten Start via `Base.metadata.create_all()`.

---

## 7. Caddy-Config aktualisieren (einmalig)

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
