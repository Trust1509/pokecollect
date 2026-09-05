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
  // Ohne diese Zeile lintet Next 14 beim Build automatisch, sobald eslint +
  // Konfiguration vorhanden sind: Der Produktions-Image-Build (deploy.sh) koennte
  // an einem Lint-Error scheitern, und Gate/CI wuerden doppelt linten.
  eslint: { ignoreDuringBuilds: true },
  images: {
    // #91 Panel-Härtung: vorher https+http je "**" — die self-hosted Instanz war
    // damit ein offener Bild-Proxy (/_next/image?url=<beliebig> nahm JEDEN Host
    // an, s. GHSA-9g9p-9gw9-jx7f/-h64f-5h5j-jqjh/-3x4c-7xq6-9pq8). Jetzt NUR die
    // Hosts, die laut Host-Inventar (Bau-Bericht #91, alle acht next/image-
    // Stellen bis zur Quelle zurückverfolgt) tatsächlich in ein <Image src>
    // fließen. Bekannte Lücke, bewusst NICHT abgedeckt: `bild_pokedex_url`
    // (manuell vom Nutzer gesetzte Karten-URL, PhotoPanel.tsx) hat KEINE
    // Host-Prüfung im Backend (backend/app/services/provenance.py Zeile 52ff.,
    // Absicht) — eine bereits gesetzte URL zu einem fremden Host lädt ab jetzt
    // nicht mehr über den Optimizer. Siehe Bau-Bericht #91 für den Befund.
    remotePatterns: [
      // TCGdex-CDN: auto-gesetztes bild_karte_url, Backend erzwingt denselben
      // Host bereits selbst (services/tcgdex.py ALLOWED_IMAGE_HOSTS/image_url()).
      { protocol: "https", hostname: "assets.tcgdex.net" },
      // TCGplayer-CDN: JP-Bildfallback bei Karten (dieselbe ALLOWED_IMAGE_HOSTS)
      // UND Sealed-Produktbilder (services/tcgcsv.py hires_image_url() prüft
      // denselben Host EXAKT — kein Substring —, bevor er in
      // SealedCatalog.image_url landet).
      { protocol: "https", hostname: "tcgplayer-cdn.tcgplayer.com" },
      // Pokédex-Sprite-Platzhalter (web/src/lib/utils.ts pokemonPlaceholderUrl,
      // letztes Glied der cardImageSrc-Kette) — fließt mit Default
      // placeholderEnabled=true tatsächlich in sechs der acht next/image-Stellen
      // (u. a. die Start-Binderansicht), pathname eng auf den einen genutzten
      // Unterpfad.
      { protocol: "https", hostname: "www.pokemon.com", pathname: "/static-assets/**" },
      // API-Origin für eigene Fotos + Katalog-Bild-Cache (nur der eine Mount,
      // der Bilder ausliefert: backend/app/main.py app.mount("/images", …)).
      // pathname eng auf /images/** statt "**" — ein offener Proxy auf JEDEN
      // Pfad dieses Hosts wäre derselbe Fehler nur einen Host kleiner. protocol
      // kommt aus apiOrigin (oben) und ist damit http NUR für diesen einen
      // Origin, nie als eigenes Wildcard-Muster.
      {
        protocol: apiOrigin.protocol.replace(":", ""),
        hostname: apiOrigin.hostname,
        port: apiOrigin.port || "",
        // Pfad-Präfix des Origins mitnehmen (#91-Nacharbeit): bei
        // NEXT_PUBLIC_API_URL="https://host/prefix" baut imageUrl()
        // "/prefix/images/…"; ein festes "/images/**" träfe das nicht.
        // Abschließender Schrägstrich ergibt hier "" (api.ts normalisiert
        // dieselbe Variable an der Wurzel) — beide Seiten bleiben gleich.
        pathname: `${apiOrigin.pathname.replace(/\/+$/, "")}/images/**`,
      },
    ],
  },
};

module.exports = nextConfig;
