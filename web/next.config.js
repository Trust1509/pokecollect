/** @type {import('next').NextConfig} */

// #91 Panel-Härtung: API-Origin für next/image aus derselben Variable ableiten,
// die auch den Client baut (NEXT_PUBLIC_API_URL, web/Dockerfile ARG) — sonst
// driftet das Bild-Muster lautlos vom tatsächlichen Backend weg. Je Umgebung
// verschieden: Prod http://<server-ip>:3010 oder https://pokecollect.lan,
// Teststand http://localhost:3020, Rauchtest http://api:8000, Default (Code)
// http://localhost:3010 (web/src/lib/api.ts API_BASE, dieselbe Variable).
// Gemessen (#91-Nacharbeit): Der Standalone-Server liest diese Muster NICHT
// zur Laufzeit neu — `next build` backt sie in .next/required-server-files.json
// ein. Das ist unkritisch, weil NEXT_PUBLIC_API_URL auch die Client-Bundles
// zur Build-Zeit prägt: angeforderte URL und Muster hängen am SELBEN Wert und
// driften gemeinsam (alle <Image>-Stellen sind Client-Komponenten). Beleg:
// Build mit http://build-origin:1111, Laufzeit-Env http://runtime-origin:2222
// -> der Build-Origin wird durchgelassen (500 am Upstream), der Laufzeit-Wert
// mit 400 abgelehnt. ACHTUNG für später: Baut je eine SERVER-Komponente eine
// Bild-URL (dort gilt der Laufzeit-Wert), entsteht genau hier ein Bruch.
const apiOrigin = new URL(process.env.NEXT_PUBLIC_API_URL || "http://localhost:3010");

const nextConfig = {
  output: "standalone",
  // #72 Panel-Nacharbeit: Lint gehoert ins explizite Gate (scripts/gates.sh) und
  // den CI-Schritt "npm run lint --max-warnings 0" -- NICHT in `next build`.
  // Ohne diese Zeile lintet Next (14 wie 15) beim Build automatisch, sobald eslint +
  // Konfiguration vorhanden sind: Der Produktions-Image-Build (deploy.sh) koennte
  // an einem Lint-Error scheitern, und Gate/CI wuerden doppelt linten.
  eslint: { ignoreDuringBuilds: true },
  images: {
    // #117 Panel (Web-Slice): Querystring an LOKALEN Bildern und freie
    // Qualitätswerte erzeugten beliebig viele Cache-Einträge — `search: ""`
    // unten wirkt nur auf remotePatterns. Next 15 bietet dafür eigene Grenzen.
    // Die App setzt nirgends `quality`, also gilt nur der Standard 75.
    localPatterns: [{ pathname: "/**", search: "" }],
    qualities: [75],
    // #120: NUR NOCH DIE EIGENE API. Der Optimizer folgt Weiterleitungen und
    // prüft das Ziel danach NICHT mehr gegen diese Muster (gemessen im Panel
    // zu #117: image-optimizer.js fetch ohne redirect-Option; in 14.2.35
    // genauso). Mit fremden CDNs im Muster hätte eine offene Weiterleitung
    // bei einem von ihnen den Web-Server jedes Ziel abrufen lassen, auch
    // interne. Fremde Bilder holt seither das Backend (Bild-Spiegel,
    // backend/app/services/bild_spiegel.py: ohne Weiterleitungen, nur
    // signierte Quellen auf drei Hosts). Der Browser lädt /images/** und
    // /bild-spiegel/** direkt von der API, am Optimizer vorbei
    // (src/components/AppImage.tsx: der Web-Server erreicht die API unter
    // NEXT_PUBLIC_API_URL nicht in jeder Aufstellung). Die zwei Muster unten
    // bleiben als enge Allowlist stehen, falls doch ein API-Bild den
    // Optimizer erreicht; fremde Hosts lehnt er ab.
    // #91 Panel-Härtung: vorher https+http je "**" — die self-hosted Instanz war
    // damit ein offener Bild-Proxy (/_next/image?url=<beliebig> nahm JEDEN Host
    // an, s. GHSA-9g9p-9gw9-jx7f/-h64f-5h5j-jqjh/-3x4c-7xq6-9pq8).
    // #98 Panel-Nacharbeit: `search: ""` an JEDEM Muster. Ohne diese Zeile
    // vergleicht Next den Querystring gar nicht (match-remote-pattern.ts
    // prüft `search` nur, wenn es gesetzt ist) — dieselbe Bilddatei mit
    // ?n=1, ?n=2, … ergibt dann beliebig viele VERSCHIEDENE Cache-Schlüssel.
    // Rot-Beweis: Sperre entfernt → der Wächter in
    // e2e/tests/bildoptimizer.spec.ts fällt (404 statt 400). Kein Spiegel-
    // Pfad trägt einen Querystring (Signatur und Quelle stehen im Pfad).
    // Zweite, unabhängige Bremse: die Cache-Größe ist in allen drei
    // Compose-Dateien hart gedeckelt (tmpfs auf /app/.next/cache/images).
    // protocol kommt aus apiOrigin (oben) und ist damit http NUR für diesen
    // einen Origin, nie als eigenes Wildcard-Muster. Pfad-Präfix des Origins
    // mitnehmen (#91-Nacharbeit): bei NEXT_PUBLIC_API_URL="https://host/prefix"
    // baut imageUrl() "/prefix/images/…"; ein festes "/images/**" träfe das
    // nicht. Abschließender Schrägstrich ergibt hier "" (api.ts normalisiert
    // dieselbe Variable an der Wurzel) — beide Seiten bleiben gleich.
    remotePatterns: ["images", "bild-spiegel"].map((wurzel) => ({
      protocol: apiOrigin.protocol.replace(":", ""),
      hostname: apiOrigin.hostname,
      port: apiOrigin.port || "",
      pathname: `${apiOrigin.pathname.replace(/\/+$/, "")}/${wurzel}/**`,
      search: "",
    })),
  },
};

module.exports = nextConfig;
