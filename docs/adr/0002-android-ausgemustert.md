# ADR-0002: Android-App ausgemustert — Web-App ist die einzige Client-Plattform

Datum: 2026-07-14 · Status: angenommen (Owner-Entscheid 2026-07-14)

## Kontext

Es existierte eine Kotlin/Compose-Android-App (`android/`), die dieselbe
API nutzt. Die Toter-Code-Analyse zeigte: der `main`-Stand von `android/`
war nicht baubar (Gradle-Wrapper und Settings-Screen lagen nur auf dem
Branch `android-dev`), die App war DE-only und hinkte dem API-Schema
hinterher. Gleichzeitig ist die Web-App mobile-first gebaut (PWA,
Bottom-Nav, Kamera-Zugriff für den Scan).

## Entscheidung

Der Owner hat entschieden: **Die Android-App wird nicht weiterentwickelt
und aus dem Repo entfernt.** Die Web-App ist die einzige Client-Plattform
und muss im Handy-Browser vollständig funktionieren und skalieren
(Kredo 2, „Mobile-First-Web").

## Konsequenzen

- `android/` ist von `main` entfernt (Historie bleibt; der Branch
  `android-dev` bleibt vorerst als Archiv stehen und kann vom Owner
  gelöscht werden).
- Das P0-Auth-Paket (Issue #1) verliert seinen Android-Scope (kein
  Android-Login-Screen nötig).
- ROADMAP-Punkt 🅺 „Android-App verschlanken" entfällt.
- Kamera-Features müssen im mobilen Browser funktionieren → HTTPS
  (ROADMAP 🅸) gewinnt an Priorität, da Kamera + PWA-Install ohne
  HTTPS nur eingeschränkt gehen.
