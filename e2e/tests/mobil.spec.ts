import { expect, test } from "@playwright/test";

import { PASSWORT, T, einmalName, karteAnlegen, karteLoeschen, token } from "./helfer";

/**
 * Rauchtest am schmalen Schirm (#70). PokéCollect ist mobile-first (ADR-0002):
 * Der Handy-Browser ist die eigentliche Plattform, der Desktop-Lauf prüft die
 * selten benutzte Hälfte.
 *
 * Bewusst nur die drei kritischsten Flüsse — Anmeldung, Liste → Detail, Karte
 * anlegen. Dazu die Prüfungen, die es NUR hier gibt: die untere Navigationsleiste
 * (erscheint erst unter der md-Grenze), das Ausbleiben von seitlichem Scrollen,
 * und dass ein fixiertes Element den Speichern-Knopf nicht verdeckt.
 *
 * Zum Farbschema: Die App hat nur EINES (globals.css setzt den Hintergrund
 * fest). Der Lauf fährt deshalb mit `colorScheme: "light"` — folgte die App je
 * der System-Vorgabe, fiele es an der Hintergrund-Prüfung auf.
 */

const HINTERGRUND = "rgb(26, 26, 46)";   // #1a1a2e aus web/src/app/globals.css

/** Seitliches Scrollen ist am Handy immer ein Fehler, nie Absicht. */
async function keinQuerscrollen(page: import("@playwright/test").Page, wo: string) {
  // NICHT window.innerWidth als Bezug nehmen: In der Handy-Emulation ist das
  // die VISUELLE Ansichtsfläche — sie wächst mit dem Überlauf mit (gemessen:
  // 901 statt 412), womit der Vergleich immer wahr wäre. Der ehrliche Bezug ist
  // clientWidth des scrollenden Elements: die Breite, die wirklich da ist.
  const { inhalt, schirm } = await page.evaluate(() => {
    const el = document.scrollingElement ?? document.documentElement;
    return { inhalt: el.scrollWidth, schirm: el.clientWidth };
  });
  expect(inhalt, `${wo}: Inhalt ist ${inhalt}px breit bei ${schirm}px Schirm`)
    .toBeLessThanOrEqual(schirm + 1);   // 1px Toleranz für Rundung
}

// ── Ohne Anmeldung ──────────────────────────────────────────────────────────

test.describe("Mobil — Anmeldung", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("Anmeldung am Handy führt in die App", async ({ page }) => {
    await page.goto("/login");
    await keinQuerscrollen(page, "Anmeldeseite");

    await page.locator('input[type="password"]').fill(PASSWORT);
    await page.getByRole("button", { name: T.anmelden }).click();

    await expect(page).toHaveURL(/\/$/);
    // Die untere Leiste ist am Handy das Navigations-Chrome (BottomNav, #34) —
    // am Desktop existiert sie nicht. Ihr Fehlen macht die App am Handy
    // unbedienbar, ohne dass ein Desktop-Test etwas merkt.
    await expect(page.locator("nav.fixed")).toBeVisible();
  });
});

// ── Angemeldet ──────────────────────────────────────────────────────────────

test.describe("Mobil — Kernflüsse", () => {
  test("die Oberfläche schaltet wirklich auf die schmale Fassung", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("nav.fixed")).toBeVisible();
    // Gegenprobe: die Kopfzeilen-Links sind unter der md-Grenze ausgeblendet.
    // Ohne sie wäre „nav.fixed sichtbar" auch bei einem breiten Schirm wahr.
    await expect(page.locator('a[href="/stats"]')).toBeHidden();
    await keinQuerscrollen(page, "Kartenliste");

    // Das Farbschema der App bleibt, egal was das System vorgibt.
    const hintergrund = await page.evaluate(() =>
      getComputedStyle(document.body).backgroundColor);
    expect(hintergrund).toBe(HINTERGRUND);
  });

  test("Kartenliste und Detailansicht am schmalen Schirm", async ({ page, request }) => {
    const t = await token(request);
    const name = einmalName("RT-Mobil");
    const id = await karteAnlegen(request, t, {
      kartenname: name, pokedex_nr: 25, set_edition: "SVI", karten_nr: "063",
    });
    try {
      await page.goto("/");
      const kachel = page.locator(`a[href="/cards/${id}"]`);
      await expect(kachel).toBeVisible();

      await kachel.click();
      await expect(page).toHaveURL(new RegExp(`/cards/${id}$`));
      await expect(page.getByRole("heading", { name })).toBeVisible();
      await keinQuerscrollen(page, "Detailansicht");
    } finally {
      await karteLoeschen(request, t, id);
    }
  });

  test("Karte anlegen am schmalen Schirm", async ({ page, request }) => {
    const name = einmalName("RT-MobilNeu");
    const t = await token(request);
    let id: number | null = null;
    try {
      await page.goto("/cards/new");
      await keinQuerscrollen(page, "Formular");

      await page.locator("#kartenname").fill(name);
      await page.locator("#besessen").check();
      // Der Klick ist die eigentliche Prüfung: Playwright verlangt, dass der
      // Knopf sichtbar UND klickbar ist. Verdeckte die fixierte untere Leiste
      // ihn, schlüge genau das hier fehl — am Desktop gibt es sie nicht.
      await page.getByRole("button", { name: T.speichern, exact: true }).click();

      await expect(page).toHaveURL(/\/cards\/\d+$/);
      id = Number(page.url().split("/").pop());
      await expect(page.getByRole("heading", { name })).toBeVisible();
    } finally {
      if (id) await karteLoeschen(request, t, id);
    }
  });
});
