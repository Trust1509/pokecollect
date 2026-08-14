import { expect, test } from "@playwright/test";

import {
  API, T, einmalName, karteAnlegen, karteLoeschen, sammlungIdFinden,
  sammlungLoeschen, sealedIdFinden, sealedLoeschen, token,
} from "./helfer";

/**
 * Rauchtest (#52): die Flüsse, deren Ausfall die App unbenutzbar macht.
 *
 * Absicht ist BREITE, nicht Tiefe — die Fachlogik prüfen die pytest-Tests. Hier
 * geht es um das, was kein Unit-Test sieht: dass Next-Build, API, Auth-Guard,
 * CORS und Datenbank im Verbund tatsächlich zusammenspielen.
 *
 * Testdaten tragen ein „RT-"-Präfix und einen Zeitstempel und werden am Ende
 * wieder entfernt — der Rauchtest darf keinen Bestand hinterlassen (er läuft
 * zwar gegen einen Wegwerf-Stapel, aber jemand könnte ihn auf einen echten
 * Stand richten).
 */

// ── Ohne Anmeldung ──────────────────────────────────────────────────────────

test.describe("Anmeldung", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  // Geprüft wird die Wirkung, nicht der Weg: der Schutz hängt an ZWEI Stricken
  // (AuthGuard in der Oberfläche, 401-Interceptor in api.ts). Reißt nur einer,
  // bleibt dieser Test grün — er sagt „niemand kommt ohne Anmeldung hinein",
  // nicht „der AuthGuard funktioniert". (Am mutierten Bau nachgemessen.)
  test("ohne Token führt jeder Aufruf auf die Anmeldeseite", async ({ page }) => {
    for (const pfad of ["/", "/catalog", "/settings", "/sealed"]) {
      await page.goto(pfad);
      await expect(page, `${pfad} war ohne Anmeldung erreichbar`).toHaveURL(/\/login/);
    }
  });

  test("falsches Passwort kommt nicht hinein", async ({ page }) => {
    await page.goto("/login");
    await page.locator('input[type="password"]').fill("garantiert-falsch");
    await page.getByRole("button", { name: T.anmelden }).click();

    await expect(page.getByText(T.anmeldung_fehlgeschlagen)).toBeVisible();
    await expect(page).toHaveURL(/\/login/);
  });
});

// ── Angemeldet (Token aus auth.setup.ts) ────────────────────────────────────

test.describe("Kernflüsse", () => {
  test("Kartenliste zeigt den Bestand und führt in die Detailansicht", async ({ page, request }) => {
    const t = await token(request);
    const name = einmalName("RT-Liste");
    // pokedex_nr ist Pflicht für diese Ansicht: die Startseite ist der Pokédex
    // und fragt mit pokedex_view=true — Karten ohne Nummer stehen dort nie.
    const id = await karteAnlegen(request, t, {
      kartenname: name, pokedex_nr: 25, set_edition: "SVI", karten_nr: "063", sprache: "DE",
    });
    try {
      await page.goto("/");
      const kachel = page.locator(`a[href="/cards/${id}"]`);
      await expect(kachel).toBeVisible();
      await expect(page.getByText(name).first()).toBeVisible();

      await kachel.click();
      await expect(page).toHaveURL(new RegExp(`/cards/${id}$`));
      await expect(page.getByRole("heading", { name })).toBeVisible();
    } finally {
      await karteLoeschen(request, t, id);
    }
  });

  test("Karte anlegen, bearbeiten und löschen", async ({ page, request }) => {
    const t = await token(request);
    const name = einmalName("RT-Neu");
    const notiz = "Rauchtest-Notiz";

    await page.goto("/cards/new");
    await expect(page.getByRole("heading", { name: T.neue_karte })).toBeVisible();
    await page.locator("#kartenname").fill(name);
    await page.locator("#besessen").check();
    await page.getByRole("button", { name: T.speichern, exact: true }).click();

    // Speichern führt in die Detailansicht der neuen Karte.
    await expect(page).toHaveURL(/\/cards\/\d+$/);
    const id = Number(page.url().split("/").pop());
    expect(Number.isInteger(id)).toBeTruthy();

    try {
      // Bearbeiten: Notiz setzen und das Neuladen überleben.
      await page.getByRole("button", { name: T.bearbeiten }).click();
      await page.getByRole("textbox", { name: T.notizen }).fill(notiz);
      await page.getByRole("button", { name: T.speichern, exact: true }).click();
      await expect(page.getByText(T.karte_gespeichert)).toBeVisible();

      await page.reload();
      await expect(page.getByText(notiz)).toBeVisible();

      // Löschen: der Bestätigungsdialog gehört zum Fluss.
      page.once("dialog", (dialog) => dialog.accept());
      await page.getByRole("button", { name: T.loeschen, exact: true }).click();

      // Nachweis am Bestand, nicht an der Liste: die neue Karte hat keine
      // Pokédex-Nr. und stünde ohnehin nicht im Pokédex-Raster — ein „nicht
      // sichtbar" wäre also auch ohne Löschung wahr.
      await expect
        .poll(async () => (await request.get(`${API}/api/v1/cards/${id}`,
          { headers: { Authorization: `Bearer ${t}` } })).status())
        .toBe(404);
    } finally {
      // Falls das Löschen scheiterte: nicht liegen lassen.
      await karteLoeschen(request, t, id);
    }
  });

  test("Katalogseite beantwortet eine Suche", async ({ page }) => {
    await page.goto("/catalog");
    await expect(page.getByRole("heading", { name: T.katalog_titel })).toBeVisible();

    // Suchbegriff geht als ?q= an die API — Antwort muss 200 sein, egal ob der
    // Katalog (wie im Wegwerf-Stapel) noch leer ist.
    const antwort = page.waitForResponse(
      (r) => r.url().includes("/api/v1/catalog") && r.url().includes("q=Pikachu"),
    );
    await page.getByPlaceholder(T.katalog_suche).fill("Pikachu");
    expect((await antwort).status()).toBe(200);
  });

  test("Sealed-Produkt erscheint ohne Neuladen in der Liste", async ({ page, request }) => {
    // Owner-Fund v1.8.1: das gespeicherte Produkt tauchte erst nach „Aktualisieren"
    // auf. Genau deshalb steht hier bewusst KEIN page.reload().
    const name = einmalName("RT-Display");
    const t = await token(request);
    try {
      await page.goto("/sealed");
      await page.getByRole("button", { name: T.sealed_neu }).click();
      await page.locator("#sealed-name").fill(name);
      await page.getByRole("button", { name: T.speichern, exact: true }).click();

      await expect(page.getByText(T.produkt_gespeichert)).toBeVisible();
      await expect(page.getByText(name)).toBeVisible();
    } finally {
      const id = await sealedIdFinden(request, t, name);
      if (id) await sealedLoeschen(request, t, id);
    }
  });

  test("Sammlung anlegen", async ({ page, request }) => {
    const name = einmalName("RT-Sammlung");
    const t = await token(request);
    try {
      await page.goto("/collections");
      await page.getByRole("button", { name: T.sammlung_neu }).click();
      await page.getByPlaceholder(T.sammlung_name).fill(name);
      await page.getByRole("button", { name: T.anlegen, exact: true }).click();

      await expect(page.getByText(name)).toBeVisible();
    } finally {
      const id = await sammlungIdFinden(request, t, name);
      if (id) await sammlungLoeschen(request, t, id);
    }
  });

  test("Einstellung überlebt das Neuladen", async ({ page }) => {
    await page.goto("/settings");
    const auswahl = page.getByLabel(T.karten_pro_seite);
    await expect(auswahl).toBeVisible();

    const vorher = await auswahl.inputValue();
    const werte = await auswahl.locator("option").evaluateAll(
      (o) => o.map((el) => (el as HTMLOptionElement).value));
    const neu = werte.find((v) => v !== vorher);
    expect(neu, "Auswahlfeld hat nur einen Wert").toBeTruthy();

    // Nächster Speichern-Knopf oberhalb des Feldes = der dieser Sektion.
    const sektion = auswahl.locator("xpath=ancestor::div[.//button][1]");
    const speichern = sektion.getByRole("button", { name: T.speichern, exact: true });

    await auswahl.selectOption(neu!);
    await speichern.click();
    // exact: „Gespeichert" steckt sonst auch in Hinweistexten („Gespeicherte
    // Keys werden maskiert …") — gemeint ist die Bestätigungsmeldung.
    await expect(page.getByText(T.gespeichert, { exact: true })).toBeVisible();

    await page.reload();
    await expect(page.getByLabel(T.karten_pro_seite)).toHaveValue(neu!);

    // Ausgangszustand wiederherstellen.
    await page.getByLabel(T.karten_pro_seite).selectOption(vorher);
    await page.getByLabel(T.karten_pro_seite)
      .locator("xpath=ancestor::div[.//button][1]")
      .getByRole("button", { name: T.speichern, exact: true }).click();
    await expect(page.getByLabel(T.karten_pro_seite)).toHaveValue(vorher);
  });

  test("Scan-Seite kommt mit einer aktiven Engine hoch", async ({ page }) => {
    await page.goto("/scan");
    await expect(page.getByRole("heading", { name: T.scan_titel })).toBeVisible();
    // „Engine: …" heißt aktiv; ohne Engine stünde dort die rote Warnung.
    await expect(page.getByText(/^Engine:/)).toBeVisible();
  });

  test("Statistikseite zeigt den Bestand", async ({ page, request }) => {
    const t = await token(request);
    const name = einmalName("RT-Stat");
    const id = await karteAnlegen(request, t, { kartenname: name, wert_eur: "42.42" });
    try {
      await page.goto("/stats");
      await expect(page.getByRole("heading", { name: T.statistik_titel })).toBeVisible();
      // Die Karte muss in „zuletzt hinzugefügt"/„teuerste" auftauchen — damit ist
      // die Kette Datenbank → Aggregat-Endpunkt → Anzeige belegt.
      await expect(page.getByRole("link", { name }).first()).toBeVisible();
    } finally {
      await karteLoeschen(request, t, id);
    }
  });

  test("API und Oberfläche melden dieselbe Version", async ({ page, request }) => {
    // Ein häufiger Deploy-Fehler: nur eines der beiden Images ist neu.
    const gesundheit = await request.get(`${API}/health`);
    expect(gesundheit.ok()).toBeTruthy();
    const version = (await gesundheit.json()).version;
    expect(version, "/health liefert keine Version").toBeTruthy();

    await page.goto("/login");
    await expect(page.getByText(`v${version}`)).toBeVisible();
  });
});
