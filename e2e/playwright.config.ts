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
  ],
});
