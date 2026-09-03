/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // #72 Panel-Nacharbeit: Lint gehoert ins explizite Gate (scripts/gates.sh) und
  // den CI-Schritt "npm run lint --max-warnings 0" -- NICHT in `next build`.
  // Ohne diese Zeile lintet Next 14 beim Build automatisch, sobald eslint +
  // Konfiguration vorhanden sind: Der Produktions-Image-Build (deploy.sh) koennte
  // an einem Lint-Error scheitern, und Gate/CI wuerden doppelt linten.
  eslint: { ignoreDuringBuilds: true },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "**" },
    ],
  },
};

module.exports = nextConfig;
