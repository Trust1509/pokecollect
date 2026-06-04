# PokéCollect – Roadmap

## ✅ v0.1.0-pre — Grundfunktionen
- 1025 Karten aus Notion importiert
- Pokédex-Raster mit Filtern (Status, Generation, Set, Seltenheit, Sprache)
- Suche nach Name oder Pokédex-Nr.
- Statistiken-Dashboard
- Karten-Detailansicht mit Bearbeitung

## ✅ v0.1.1 — Bilder & Filter
- Pokédex-Platzhalterbilder (pokemon.com) für alle 1025 Karten
- Bild-URL manuell hinterlegen (z.B. Cardmarket-Scan)
- Foto hochladen und löschen
- Bild-Filter: Eigenes Foto / Externe URL / Nur Platzhalter
- Typo-Fix: "Besossen" → "Besessen"

## ✅ v0.1.2 — Git-Deploy
- Git-basiertes Deployment via `deploy.sh`
- Deploy-Dokumentation mit Rebuild-Regeln
- NEXT_PUBLIC_API_URL korrekt als Docker Build-Arg

## ✅ v0.2.0 — Settings-Seite
- `/settings`-Seite mit 5 Sektionen:
  - 🖼️ Anzeige (Platzhalter-Toggle, Karten/Seite, Sortierung)
  - 💰 Preise (Auto-Update, Uhrzeit, Quelle)
  - 📦 Sammlung (Standard-Sprache & -Zustand)
  - 🔑 API-Keys (Cardmarket OAuth, PokémonTCG.io)
  - 👤 Konto (Passwort ändern)
- Versionsanzeige in der Navbar (v0.x.x)
- Settings in PostgreSQL gespeichert (key/value)

## ✅ v0.2.1 — Auth (zurückgenommen)
- Login-Seite, Middleware, Backend-Absicherung gebaut
- Entschieden: Auth wird von Authelia übernommen, nicht in-app

## ✅ v0.2.2 — Auth-Architektur: Authelia
- In-App-Auth vollständig entfernt (kein Login, kein Middleware)
- Authelia-Konfiguration vorbereitet (`deploy/authelia/`)
- Caddy-Snippet mit `forward_auth` für externen Zugriff
- Intern (192.168.2.x): offen
- Extern (yourdomain.com): Authelia-Login erzwungen

---

## 🔲 v0.3.0 — Authelia + Externer Zugriff
- [ ] Authelia als Portainer-Stack deployen
- [ ] DNS-Eintrag `auth.yourdomain.com` setzen
- [ ] DNS-Eintrag `pokecollect.yourdomain.com` setzen
- [ ] Caddy-Config mit Authelia `forward_auth` aktivieren
- [ ] Authelia-User anlegen, Hash generieren
- [ ] Externen Zugriff testen (Web + Android)

## 🔲 v0.4.0 — Android App
- [ ] Android-App auf Gerät testen
- [ ] Typo "Besossen" in Android-Code fixen (CardDetailScreen.kt Zeile 64, ScanScreen.kt)
- [ ] API-URL in App konfigurierbar machen (intern vs. extern)
- [ ] Basis-Funktionen testen: Karten scannen, Status setzen, Detailansicht

## 🔲 v0.5.0 — Cardmarket-Integration
- [ ] Cardmarket OAuth 1.0a testen (Keys via Settings-Seite eintragen)
- [ ] Preisabruf für einzelne Karte manuell triggern
- [ ] Preishistorie-Anzeige verbessern
- [ ] Preis-Quelle (30-Tage-Ø vs. Tagespreis) aktivieren

## 🔲 v0.6.0 — Bilder & Qualität
- [ ] PokémonTCG.io Integration: Karten-Bilder automatisch laden (exaktes Kartenset-Bild)
- [ ] Massenhafte Bild-URL-Zuweisung (alle Karten eines Sets auf einmal)
- [ ] CSV-Export (Backup)
- [ ] CSV-Import mit Duplikat-Erkennung

## 🔲 v1.0.0 — Production Release
- [ ] Docker Images auf ghcr.io pushen
- [ ] `docker-compose.yml`: `image:` statt `build:` verwenden
- [ ] Vollständige Test-Abdeckung kritischer Endpunkte
- [ ] Öffentliche Dokumentation
