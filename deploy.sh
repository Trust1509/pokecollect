#!/bin/bash
set -e

APP_DIR="/mnt/HDDs/Applications/pokecollect/app"
ENV_FILE="/mnt/HDDs/Applications/pokecollect/config/.env"

cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

# .env-Symlink sicherstellen
if [ ! -f "$APP_DIR/.env" ]; then
  ln -s "$ENV_FILE" "$APP_DIR/.env"
fi

git pull origin main

chown -R 3010:3010 .

docker compose restart api
docker compose build web
docker compose up -d web

echo "Deploy abgeschlossen."
