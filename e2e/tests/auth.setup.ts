import { expect, test as setup } from "@playwright/test";

import { PASSWORT, STATE_PFAD, T } from "./helfer";


/**
 * Anmeldung als Voraussetzung aller Rauchtests — und zugleich der erste
 * kritische Flow: geht das Login nicht, ist die App als Ganzes unbenutzbar.
 *
 * Bewusst durch die OBERFLÄCHE, nicht per API-Token: nur so ist mitgeprüft,
 * dass das Formular den Token in localStorage schreibt (dort liest ihn der
 * Axios-Interceptor, ADR-0003) und die harte Navigation auf „/" ankommt.
 */
setup("anmelden", async ({ page }) => {
  await page.goto("/login");

  await page.locator('input[type="text"]').fill("admin");
  await page.locator('input[type="password"]').fill(PASSWORT);
  await page.getByRole("button", { name: T.anmelden }).click();

  // Nach erfolgreichem Login: harte Navigation auf die Startseite.
  await expect(page).toHaveURL(/\/$/);
  // Der AuthGuard rendert erst NACH bestandener Token-Prüfung Inhalt — sichtbare
  // Navigation heißt also: Token liegt, Guard ist zufrieden. Griff über href
  // statt Beschriftung: sprachunabhängig und unabhängig davon, welche Links
  // die Kopfzeile bei welcher Breite zeigt.
  await expect(page.locator('a[href="/collections"]').first()).toBeVisible();

  await page.context().storageState({ path: STATE_PFAD });
});
