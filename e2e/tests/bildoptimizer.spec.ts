import { expect, test } from "@playwright/test";

/**
 * #91 Panel-Härtung: web/next.config.js images.remotePatterns eng gefasst —
 * vorher https+http je "**" (offener Bild-Proxy: /_next/image?url=<beliebig>
 * nahm JEDEN Host an). Dieser Test prüft die Wirkung an der echten Tür (dem
 * Next.js-Optimizer-Endpunkt selbst), nicht nur die next.config.js-Datei.
 *
 * Rot-Beweis (lehren.md §1): remotePatterns sabotage-halber auf die alte
 * Wildcard-Fassung zurückgesetzt und den Rauchtest erneut gefahren → der
 * erste Test hier fiel (evil.invalid antwortete nicht mehr mit 400, siehe
 * Bau-Bericht #91 für die Zahlen).
 *
 * KEINE Anmeldung/storageState nötig: /_next/image ist eine Next.js-interne
 * Route des Web-Containers, kein Fach-Router des Backends — der JWT-Zwang aus
 * CLAUDE.md („Sicherheit", auth-frei nur /auth/login, /health, /images) gilt
 * für die FastAPI-Seite, nicht für diese Next.js-Route.
 */
test.describe("Bild-Optimizer nimmt nur die erlaubten Hosts an (#91)", () => {
  test("fremder Host wird abgelehnt (400)", async ({ request, baseURL }) => {
    // Fixture erfunden (e2e/tests/helfer.ts-Konvention: nichts aus der echten
    // Sammlung übernehmen) — evil.invalid ist laut RFC 2606 reserviert und
    // existiert nie wirklich.
    const fremd = "https://evil.invalid/x.png";
    const antwort = await request.get(
      `${baseURL}/_next/image?url=${encodeURIComponent(fremd)}&w=64&q=75`,
    );
    expect(antwort.status(), await antwort.text()).toBe(400);
  });

  test("erlaubter Host wird nicht als Fremd-Host abgelehnt", async ({ request, baseURL }) => {
    // #91-Nacharbeit (Panel): vorher fragte dieser Test ein echtes CDN an
    // (assets.tcgdex.net, gemessen 404 nach 678 ms echtem Netzverkehr). Der
    // Rauchtest-Stapel verzichtet sonst bewusst auf Fremdaufrufe
    // (docker-compose.smoke.yml) — die Zusicherung braucht das Netz auch
    // nicht. Jetzt in-stack: der eigene API-Origin steht im Muster
    // (pathname /images/**), die Datei existiert absichtlich nicht. Gemessen:
    // ein erlaubter Host mit fehlender Datei antwortet 404/500, ein NICHT
    // erlaubter 400 — die Unterscheidung trägt ohne Fremdnetz.
    // Aus der echten Allowlist gebildet (backend/app/services/tcgdex.py
    // ALLOWED_IMAGE_HOSTS / web/next.config.js remotePatterns) — realer Host,
    // Pfadform wie tcgdex.py::image_url() sie baut ("{base}/{quality}.{format}").
    // Ob genau DIESES Bild beim CDN existiert, ist nicht die Zusicherung: der
    // Wegwerf-Stapel (docker-compose.smoke.yml) hat keine garantierte Netzsperre
    // nach außen, aber auch keine garantierte Freigabe — ein Upstream-Fehler
    // (5xx bei Netzsperre oder 404 bei falschem Pfad) beweist trotzdem, dass
    // next/image den Host akzeptiert und die Anfrage tatsächlich hinausgeschickt
    // hat, statt sie schon an der eigenen Tür mit 400 abzuweisen. Mindest-
    // zusicherung laut Bau-Brief #91: „nicht 400".
    const apiUrl = process.env.API_URL ?? "http://api:8000";
    const erlaubt = `${apiUrl}/images/test91-gibt-es-nicht.webp`;
    const antwort = await request.get(
      `${baseURL}/_next/image?url=${encodeURIComponent(erlaubt)}&w=64&q=75`,
    );
    expect(antwort.status(), await antwort.text()).not.toBe(400);
  });
});
