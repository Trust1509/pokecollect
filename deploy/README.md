# PokéCollect – Deploy-Anleitung

> **Aktueller Stand:** Lokaler Build (Images noch nicht auf GitHub veröffentlicht).
> Sobald v1.0.0 fertig ist, werden die Images auf ghcr.io gepusht und
> die `build:`-Direktiven durch `image:`-Pulls ersetzt.

---

## Voraussetzungen

- TrueNAS Scale (oder ein beliebiger Linux-Server mit Docker + ZFS)
- Portainer (Stack-Deployment)
- Caddy als Reverse Proxy (bereits vorhanden)
- SSH-Zugang zum Server
- Git auf dem Server (zum Klonen des Repos)

---

## 1. ZFS-Datasets anlegen (einmalig)

```bash
# Auf dem Host via SSH ausführen:
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/db
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/images
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/cache
zfs create -o acltype=posixacl -o xattr=sa HDDs/Applications/pokecollect/config

chown -R 3010:3010 /mnt/HDDs/Applications/pokecollect/
```

> Passe `HDDs/Applications` an deinen tatsächlichen Pool-Pfad an.

---

## 2. User anlegen (einmalig)

```bash
groupadd -g 3010 pokecollect
useradd -u 3010 -g 3010 -M -s /sbin/nologin pokecollect
```

---

## 3. Repo auf den Server klonen

```bash
cd /mnt/HDDs/Applications/pokecollect
git clone https://github.com/OWNER/pokecollect.git app
# Oder: git clone git@github.com:OWNER/pokecollect.git app
# Bis v1.0.0: Repo-Ordner direkt per scp/rsync hochladen – siehe unten
```

### Alternative bis v1.0.0: Dateien per rsync hochladen

```bash
# Auf dem Entwicklungsrechner ausführen (Pfad anpassen):
rsync -av --exclude='.env' --exclude='node_modules' --exclude='__pycache__' \
  /pfad/zu/pokecollect/ \
  user@192.168.x.x:/mnt/HDDs/Applications/pokecollect/app/
```

---

## 4. .env-Datei anlegen

```bash
cat > /mnt/HDDs/Applications/pokecollect/config/.env << 'EOF'
POSTGRES_USER=pokecollect
POSTGRES_PASSWORD=<sicheres_passwort>
POSTGRES_DB=pokecollect
DATABASE_URL=postgresql://pokecollect:<passwort>@db:5432/pokecollect
REDIS_URL=redis://redis:6379
JWT_SECRET=<langer_zufälliger_string>
CARDMARKET_APP_TOKEN=
CARDMARKET_APP_SECRET=
CARDMARKET_ACCESS_TOKEN=
CARDMARKET_ACCESS_SECRET=
POKEMONTCG_API_KEY=
API_URL=http://api:8000
APP_USERNAME=admin
APP_PASSWORD_HASH=<bcrypt_hash>
EOF

# Symlink damit docker-compose die .env findet:
ln -s /mnt/HDDs/Applications/pokecollect/config/.env \
      /mnt/HDDs/Applications/pokecollect/app/.env
```

Bcrypt-Hash für das Admin-Passwort generieren:
```bash
python3 -c "from passlib.hash import bcrypt; print(bcrypt.hash('mein_passwort'))"
# oder: docker run --rm python:3.12-slim python3 -c \
#   "import subprocess; subprocess.run(['pip','install','passlib[bcrypt]','-q']); \
#    from passlib.hash import bcrypt; print(bcrypt.hash('mein_passwort'))"
```

---

## 5. Images lokal bauen

```bash
cd /mnt/HDDs/Applications/pokecollect/app

# Backend bauen
docker build -t pokecollect-api:local ./backend

# Frontend bauen
docker build -t pokecollect-web:local ./web
```

> Das dauert beim ersten Mal einige Minuten (npm install, pip install).
> Danach werden nur geänderte Layer neu gebaut.

---

## 6. Stack in Portainer anlegen

1. Portainer öffnen → **Stacks → Add Stack**
2. Name: `pokecollect`
3. `docker-compose.yml` einfügen (Inhalt aus dem Repo kopieren)
4. Env-Variablen eintragen **oder** `.env`-Pfad als Stack-Env-File angeben
5. **Deploy the stack**

> Portainer baut die Images automatisch wenn `build:` im Compose steht –
> alternativ vorher manuell bauen (Schritt 5) und `image: pokecollect-api:local` setzen.

---

## 7. Datenbank initialisieren (einmalig)

```bash
# Warten bis db-Container healthy ist, dann:
docker exec -i $(docker ps -qf name=pokecollect-db) \
  psql -U pokecollect -d pokecollect \
  < /mnt/HDDs/Applications/pokecollect/app/migrations/001_initial.sql
```

Oder direkt über FastAPI: Beim ersten Start legt `Base.metadata.create_all()` alle Tabellen automatisch an.

---

## 8. Caddy-Config aktualisieren

Inhalt von `deploy/Caddyfile.snippet` an das bestehende Caddyfile anhängen:

```bash
# IP und Domain anpassen, dann:
cat /mnt/HDDs/Applications/pokecollect/app/deploy/Caddyfile.snippet \
  >> /mnt/HDDs/Applications/caddy/Caddyfile

caddy reload --config /mnt/HDDs/Applications/caddy/Caddyfile
```

---

## 9. Notion-Import (optional, einmalig)

```bash
# Erst Probelauf ohne Schreibzugriff:
docker exec pokecollect-api \
  env NOTION_API_KEY=... NOTION_DATABASE_ID=... \
  python migrations/notion_import.py --dry-run

# Wenn alles passt, scharf schalten:
docker exec pokecollect-api \
  env NOTION_API_KEY=... NOTION_DATABASE_ID=... \
  python migrations/notion_import.py
```

---

## Update (lokal)

```bash
cd /mnt/HDDs/Applications/pokecollect/app

# Code aktualisieren (rsync oder git pull)
rsync -av ... oder git pull

# Images neu bauen
docker build -t pokecollect-api:local ./backend
docker build -t pokecollect-web:local ./web

# Stack in Portainer: "Update the stack" → redeploy
```

---

## Ports

| Dienst       | Host-Port |
|--------------|-----------|
| API          | 3010      |
| Web-Frontend | 3011      |

---

## Wenn v1.0.0 fertig ist → GitHub release

Dann werden:
- Images auf `ghcr.io/OWNER/pokecollect-api:1.0.0` und `…-web:1.0.0` gepusht
- `docker-compose.yml`: `build:`-Direktiven durch `image:`-Pulls ersetzt
- Deploy-Schritt 3 wird zu `docker pull …` statt lokalem Build
