# PokéCollect

A self-hosted Pokémon TCG collection app — track your cards, scan new ones with your Android phone, and monitor Cardmarket prices automatically.

> **Status: Pre-Release v0.1.0** — Core features working, some areas still being tested.

## Features

- **Web interface** — Pokédex-style grid, filters by generation/set/rarity/language, detail view with price charts
- **Android app** — camera scan with on-device OCR (ML Kit), offline Room cache, sync on connect
- **Single FastAPI backend** — one PostgreSQL database shared by all clients
- **Cardmarket price integration** — OAuth 1.0a, daily auto-update for owned cards
- **Notion CSV import** — migrate existing collections from Notion export
- **Dark theme** — responsive desktop + tablet

## Quick start (local)

```bash
cp .env.example .env
# Edit .env — set POSTGRES_PASSWORD, JWT_SECRET, APP_PASSWORD_HASH, NEXT_PUBLIC_API_URL
docker compose up --build
```

- API + Swagger UI: `http://localhost:3010/docs`
- Web frontend: `http://localhost:3011`

Generate a bcrypt password hash:
```bash
docker run --rm python:3.12-slim bash -c \
  "pip install bcrypt -q && python3 -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
```

## Server deployment (TrueNAS Scale / Portainer)

See [deploy/README.md](deploy/README.md) for full step-by-step instructions including:
- ZFS POSIX-ACL dataset setup
- Docker image build
- Portainer stack deployment
- Caddy reverse proxy config

## Configuration

Copy `.env.example` to `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | ✅ | Database password |
| `JWT_SECRET` | ✅ | Random string for JWT signing (min. 32 chars) |
| `APP_PASSWORD_HASH` | ✅ | bcrypt hash of your admin password |
| `NEXT_PUBLIC_API_URL` | ✅ | URL the browser uses to reach the API (e.g. `http://192.168.x.x:3010`) |
| `CARDMARKET_APP_TOKEN` | ➖ | Cardmarket OAuth 1.0a — register at api.cardmarket.com |
| `CARDMARKET_APP_SECRET` | ➖ | Cardmarket OAuth 1.0a |
| `CARDMARKET_ACCESS_TOKEN` | ➖ | Cardmarket OAuth 1.0a |
| `CARDMARKET_ACCESS_SECRET` | ➖ | Cardmarket OAuth 1.0a |
| `POKEMONTCG_API_KEY` | ➖ | Free key from pokemontcg.io |
| `COMPOSE_PROJECT_NAME` | ➖ | Docker project name (default: `pokecollect`) |

## Notion migration

Export your Notion database as CSV, then:

```bash
# Dry run first
docker exec pokecollect-api-1 \
  python /app/csv_import.py /app/cards.csv --dry-run

# Import
docker exec -e DRY_RUN=false pokecollect-api-1 \
  python /app/csv_import.py /app/cards.csv
```

## Android app

Configure the API base URL in the app settings (default: `http://192.168.x.x:3010/api/v1`).

Build with Android Studio. Requires minSdk 26 (Android 8.0+).

## Tech stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, PostgreSQL 16, Redis 7 |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS, Recharts |
| Android | Kotlin, Jetpack Compose, ML Kit OCR, CameraX, Room, Retrofit, Hilt |
| Deployment | Docker Compose, Portainer, Caddy |

## Ports

| Service | Host port |
|---------|-----------|
| API | 3010 |
| Web frontend | 3011 |

## Roadmap

- [ ] Web settings page for API keys (Cardmarket, PokémonTCG)
- [ ] Placeholder images for all cards (toggleable)
- [ ] Android scan feature — full end-to-end test
- [ ] Caddy external access config
- [ ] GitHub Actions CI/CD → ghcr.io image publish

## License

MIT
