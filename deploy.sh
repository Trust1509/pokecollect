#!/bin/bash
set -e

APP_DIR="/mnt/HDDs/Applications/pokecollect/app"
ENV_FILE="/mnt/HDDs/Applications/pokecollect/config/.env"

cd "$APP_DIR"

git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

# .env-Symlink sicherstellen
if [ ! -f "$APP_DIR/.env" ] && [ ! -L "$APP_DIR/.env" ]; then
  ln -s "$ENV_FILE" "$APP_DIR/.env"
fi

git pull origin main

chown -R 3010:3010 .

# Backend und Frontend neu bauen (Code-Änderungen erfordern immer einen Rebuild).
# --pull (#117): ohne holt der Build die Basis-Images (python:3.12-slim,
# node:*-alpine) nie neu — Sicherheitskorrekturen im Basis-System kamen dann nie
# an. Ändert sich das Basis-Image, baut Docker auch die apt-/pip-Schichten neu.
# Folge: Ohne erreichbare Registry bricht der Deploy hier ab (set -e), der
# laufende Stand bleibt unverändert.
docker compose build --pull api web
docker compose up -d

echo "Deploy abgeschlossen."
