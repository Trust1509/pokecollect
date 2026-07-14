# ADR-0003: Auth-Zwang mit JWT im localStorage

Datum: 2026-07-14 · Status: angenommen (Lock-Spec Issue #1, Grilling mit Owner)

## Kontext

Bis v0.9.15 erzwang die API keine Auth: `require_auth` war unverdrahtet,
`GET /settings` lieferte API-Keys im Klartext ins LAN, und es gab einen
eingebauten Default-Passwort-Hash („secret"). Extern schützte nur
Authelia + Caddy. Issue #1 (P0) schließt das.

## Entscheidung

1. **Auth-Zwang:** Alle Fach-Router verlangen ein gültiges JWT
   (`dependencies=[Depends(require_auth)]` beim `include_router`).
   Auth-frei bleiben nur `/auth/login`, `/health` und der
   `/images`-StaticFiles-Mount (`<img>`-Tags können keine
   Authorization-Header senden).
2. **Token-Ablage: localStorage** (Key `token`). Bewusste Entscheidung
   trotz XSS-Theorie-Risiko: Single-User-LAN-App hinter Authelia, kein
   Fremd-Content, kein Cookie-/CSRF-Apparat nötig; das Plumbing
   (Request-Interceptor in `web/src/lib/api.ts`) existierte bereits.
3. **JWT-Laufzeit 30 Tage, keine Revocation.** Abmelden = Token im
   Client löschen; bei 401 löscht der Response-Interceptor das Token und
   leitet auf `/login`.
4. **Kein Default-Passwort:** Ohne `APP_PASSWORD_HASH` (Env) bzw.
   DB-Hash verweigert die App den Start
   (`main.py::_ensure_password_configured`).
5. **Secrets nie im Klartext an Clients:** `GET /settings` liefert je
   Secret nur `*_set` + `*_masked` („•••• " + letzte 4 Zeichen).

## Konsequenzen

- Deploy braucht zwingend `APP_PASSWORD_HASH` in der `.env`
  (Erzeugung: siehe `.env.example` / `deploy/README.md`).
- CORS ist auf konkrete Origins eingeschränkt (`CORS_ORIGINS`, Default
  localhost:3011+3021) — Wildcard `*` wäre mit erzwungener Auth ein
  unnötiges Risiko.
- Tests laufen eingeloggt (conftest setzt den Hash und holt ein Token);
  für 401-Fälle gibt es ein `anon_client`-Fixture.
- Kredo-Grundsatz 4 („Secrets nie im Klartext an Clients") ist damit
  erfüllt, der Zielzustand-Vermerk in CONTEXT.md ist aufgehoben.
