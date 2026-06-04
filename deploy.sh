#!/bin/bash
set -e

APP_DIR="/mnt/HDDs/Applications/pokecollect/app"
cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true
git pull origin main

chown -R 3010:3010 .

docker compose restart api
docker compose build web
docker compose up -d web

echo "Deploy abgeschlossen."
