import { expect, test, type Page } from "@playwright/test";

import { PASSWORT, T } from "./helfer";

// Nur für diese Datei gebraucht (Modal-Text, DE-Standardsprache) — bewusst
// NICHT in helfer.ts::T ergänzt: Block 8 des Bau-Briefs #99 zählt die
// anzufassenden Dateien abschließend auf, helfer.ts steht nicht darin.
const SCHLIESSEN = "Schließen";

/**
 * "Was ist neu"-Box nach Updates (Issue #99) — Wächter 2 (erscheint nach
 * einem Update, verschwindet dauerhaft nach dem Wegklicken, erscheint nicht
 * bei bereits gesehener aktueller Version) und Wächter 3 (beide Sprachen
 * kommen wirklich an).
 *
 * EIGENER Kontext OHNE "setup"-Abhängigkeit/storageState (wie
 * bildoptimizer.spec.ts: eigenes Projekt ohne "dependencies", siehe
 * playwright.config.ts) — bewusst NICHT das gemeinsame ".auth/state.json"
 * geerbt: Jeder Test steuert localStorage ("whatsnew_seen_version") von
 * Grund auf selbst. Würde dieses Projekt den gemeinsamen Anmelde-Stand
 * erben, wäre "aktuelle Version bereits gesehen" darin schon gesetzt (siehe
 * WhatsNewModal.tsx — genau DESHALB bleiben die 20 bestehenden Tests von
 * diesem Slice unberührt) und keine der drei Zusagen ließe sich hier mehr
 * unabhängig herstellen.
 *
 * Fixture: "0.0.1" als erfundene Altversion (Bau-Brief #99, Block 7) — nie
 * eine echte aus dem CHANGELOG, sonst wird der Test beim übernächsten
 * Release stillschweigend sinnlos.
 *
 * Rot-Beweis-Rezept (Bau-Brief #99, Block 5, Nr. 2 + 3 — Schrittfolge aus
 * lehren.md Klasse 1: committen → Sabotage → messen → zurücknehmen):
 *  - Vergleichslogik in WhatsNewModal.tsx auf "immer zeigen" (z. B.
 *    `setShow(true)` bedingungslos im Mount-Effekt) → "bleibt weg nach
 *    reload" UND "aktuelle Version gesehen → nichts" fallen rot.
 *  - Auf "nie zeigen" (die `if`-Bedingung nie erfüllen) → "ältere Version
 *    → erscheint" fällt rot.
 *  - `whatsnew.generated.ts`-Feld "en" auf denselben Text wie "de" setzen →
 *    der Sprachwechsel-Test fällt rot (Inhalt identisch statt verschieden).
 */

async function login(page: Page) {
  await page.locator('input[type="text"]').fill("admin");
  await page.locator('input[type="password"]').fill(PASSWORT);
  await page.getByRole("button", { name: T.anmelden }).click();
  await expect(page).toHaveURL(/\/$/);
}

/** Version von der (öffentlichen) Anmeldeseite lesen — ohne sie hart im Test
 * zu verdrahten: login/page.tsx zeigt "v{APP_VERSION}" schon vor der
 * Anmeldung. Vermeidet eine Zahl, die beim nächsten Release veraltet, ohne
 * dass ein Test das bemerkt (dieselbe Klasse wie ein Test auf Wortlaut). */
async function currentVersion(page: Page): Promise<string> {
  const text = await page.locator("text=/^v\\d+\\.\\d+\\.\\d+/").first().textContent();
  const m = text?.match(/^v([\d.]+(?:-\S+)?)/);
  if (!m) throw new Error(`Version nicht auf /login gefunden (Text: "${text}")`);
  return m[1];
}

const seedSeenVersion = (page: Page, version: string) =>
  page.evaluate((v) => localStorage.setItem("whatsnew_seen_version", v), version);

test.describe("Erscheint nach einem Update, sonst nicht (Wächter 2)", () => {
  test("frische Installation zeigt kein Modal, merkt sich die aktuelle Version aber still (Auftrag Block 4)", async ({
    page,
  }) => {
    await page.goto("/login");
    const version = await currentVersion(page);
    // Bewusst KEIN localStorage vorbelegt — echte frische Installation.
    await login(page);

    await expect(page.getByRole("dialog")).toHaveCount(0);
    const stored = await page.evaluate(() => localStorage.getItem("whatsnew_seen_version"));
    expect(stored).toBe(version);
  });

  test("mit einer älteren gesehenen Version erscheint das Modal", async ({ page }) => {
    await page.goto("/login");
    await seedSeenVersion(page, "0.0.1");
    await login(page);

    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("mit der aktuellen Version als gesehen erscheint das Modal gar nicht", async ({ page }) => {
    await page.goto("/login");
    const version = await currentVersion(page);
    await seedSeenVersion(page, version);
    await login(page);

    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("nach dem Wegklicken ist es weg und bleibt nach reload() weg", async ({ page }) => {
    await page.goto("/login");
    await seedSeenVersion(page, "0.0.1");
    await login(page);

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    // Zwei Schließen-Knöpfe tragen denselben Namen (X-Button per aria-label,
    // Fuß-Button per Text) — .first() greift deterministisch den X-Button.
    await dialog.getByRole("button", { name: SCHLIESSEN }).first().click();
    await expect(dialog).toHaveCount(0);

    await page.reload();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
});

test.describe("Beide Sprachen kommen an (Wächter 3)", () => {
  test("Sprachwechsel ändert den Inhalt des Modals", async ({ page }) => {
    await page.goto("/login");
    await login(page);
    await page.goto("/settings");

    // Stabiler Griff unabhängig von Sprache/Version: der sichtbare TEXT
    // "PokéCollect v…" wird NICHT übersetzt (nur das aria-label ist es —
    // und ein aria-label ERSETZT den Text als Accessible Name vollständig,
    // getByRole("button", { name: … }) griffe hier also ins Leere;
    // getByText() sieht den gerenderten Text unabhängig davon).
    const reopenBtn = page.getByText(/PokéCollect v/);
    const dialog = page.getByRole("dialog");
    // NUR den generierten Notiz-Text greifen, nicht den ganzen Dialog: Titel,
    // Schließen-Knopf und Risiko-Label kommen aus t.whatsnew_* (i18n.tsx) und
    // unterscheiden sich IMMER zwischen den Sprachen — ein Vergleich auf
    // dialog.innerText() bliebe deshalb auch dann "verschieden", wenn
    // ausgerechnet whatsnew.generated.ts::de/en sabotiert und identisch
    // wären. Am eigenen Rot-Beweis gefunden: siehe WhatsNewModal.tsx,
    // data-testid="whatsnew-body".
    const body = dialog.getByTestId("whatsnew-body");

    await reopenBtn.click();
    await expect(dialog).toBeVisible();
    const deText = (await body.innerText()).trim();
    await dialog.getByRole("button", { name: SCHLIESSEN }).first().click();
    await expect(dialog).toHaveCount(0);

    // Navbar-Sprachschalter zeigt "EN" an, solange DE aktiv ist (Navbar.tsx).
    await page.getByRole("button", { name: "EN", exact: true }).click();

    await reopenBtn.click();
    await expect(dialog).toBeVisible();
    const enText = (await body.innerText()).trim();

    // NICHT gegen einen fest verdrahteten Satz prüfen (Bau-Brief #99, Block
    // 5 Nr. 3 + Prüffrage F2) — nur gegen die Tatsache, dass beide Texte
    // existieren und sich unterscheiden. Sonst bricht der Test bei jedem
    // Release, in dem sich der Notiz-Text ändert, ohne je einen echten
    // Fehler zu fangen.
    expect(deText.length).toBeGreaterThan(0);
    expect(enText.length).toBeGreaterThan(0);
    expect(enText).not.toBe(deText);
  });
});
