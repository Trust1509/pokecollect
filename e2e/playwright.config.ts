import { defineConfig, devices } from "@playwright/test";

// Adressen kommen von außen (docker-compose.smoke.yml). Die Vorgaben zeigen auf
// den Teststand — falls jemand die Tests von Hand gegen einen laufenden Stand
// fahren will. Der reguläre Weg ist `sh scripts/smoke.sh`.
const BASE_URL = process.env.BASE_URL ?? "http://localhost:3021";

export default defineConfig({
  testDir: "./tests",

  // EIN Worker, keine Parallelität: PokéCollect ist eine Single-User-App mit
  // einer gemeinsamen Kartenliste — parallele Tests zögen sich gegenseitig die
  // Daten unter den Füßen weg und erzeugten Scheinfehler.
  workers: 1,
  fullyParallel: false,

  forbidOnly: !!process.env.CI,
  // Ein Wiederholungsversuch: ein Rauchtest, der wegen einer Zehntelsekunde rot
  // wird, wird ignoriert statt gelesen. Echte Fehler überleben den zweiten Lauf.
  retries: 1,
  timeout: 45_000,
  expect: { timeout: 10_000 },

  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  outputDir: "test-results",

  use: {
    baseURL: BASE_URL,
    locale: "de-DE",
    // Die UI startet ohne gespeicherte Sprache auf Deutsch (lib/i18n.tsx) —
    // die Texte unten in tests/ sind entsprechend deutsch.
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 15_000,
  },

  projects: [
    // Meldet sich einmal an und legt den Token-Stand ab; die Rauchtests erben ihn.
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    {
      name: "smoke",
      dependencies: ["setup"],
      testMatch: /smoke\.spec\.ts/,
      use: { ...devices["Desktop Chrome"], storageState: ".auth/state.json" },
    },
    // Mobil ist bei dieser PWA die EIGENTLICHE Plattform (ADR-0002) — der
    // Desktop-Lauf prüft die selten benutzte Hälfte. Bewusst nur die drei
    // kritischsten Flüsse, nicht alle zwölf doppelt: Laufzeit und Wartung
    // verdoppeln sich sonst für wenig Zusatzaussage.
    {
      name: "smoke-mobil",
      dependencies: ["setup"],
      testMatch: /mobil\.spec\.ts/,
      use: {
        ...devices["Pixel 7"],
        storageState: ".auth/state.json",
        // colorScheme bewusst "light": Die App hat KEIN Hell-Schema — der
        // Hintergrund steht fest in globals.css. Würde sie je der
        // System-Vorgabe folgen, fiele genau das hier auf.
        colorScheme: "light",
      },
    },
    // #91 Panel-Härtung: /_next/image ist eine Next.js-interne Route, kein
    // durch das Backend-JWT geschütztes Fach-Endpoint — deshalb KEINE
    // Abhängigkeit von "setup"/keine storageState nötig. Eigenes Projekt statt
    // Aufnahme in "smoke": läuft so auch dann, wenn die Anmeldung selbst
    // scheitert (eigene Aussage, kein Rot-Beweis versteckt hinter dem Login).
    {
      name: "bild-optimizer",
      testMatch: /bildoptimizer\.spec\.ts/,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
