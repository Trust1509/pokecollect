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

# Rechte für den App-Nutzer, OHNE die ZFS-Snapshot-Ordner (.zfs). Ist am
# Dataset snapdir=visible gesetzt, liegt dort ein schreibgeschützter Baum aller
# Snapshots; `chown -R` lief hinein, scheiterte („Read-only file system“) und
# brach den Deploy per set -e VOR dem Build ab.
# Ausgelassen wird JEDER Ordner namens .zfs, in jeder Tiefe (im Repo gibt es
# keinen); eine gewöhnliche Datei dieses Namens bekommt die Rechte weiter.
# -h ändert Symlinks selbst (.env), nicht ihr Ziel — wie vorher `chown -R`.
# Scheitert chown an einer anderen Datei, bricht der Deploy weiter ab.
find . -type d -name .zfs -prune -o -exec chown -h 3010:3010 {} +

# Backend und Frontend neu bauen (Code-Änderungen erfordern immer einen Rebuild).
# --pull (#117): ohne holt der Build die Basis-Images (python:3.12-slim,
# node:*-alpine) nie neu — Sicherheitskorrekturen im Basis-System kamen dann nie
# an. Ändert sich das Basis-Image, baut Docker auch die apt-/pip-Schichten neu.
# Folge: Ohne erreichbare Registry bricht der Deploy hier ab (set -e), der
# laufende Stand bleibt unverändert.
docker compose build --pull api web
docker compose up -d

echo "Deploy abgeschlossen."
