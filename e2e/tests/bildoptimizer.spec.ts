import { expect, test } from "@playwright/test";

/**
 * HOTFIX (Oktober 2026): Der Bild-Optimizer von Next.js ist abgeschaltet
 * (web/next.config.js, images.unoptimized). Zwei kritische Lücken darin
 * (GHSA-2xp9-vwfh-vxw4, GHSA-2464-fhr4-w9xw) sind erst in Next 15.5.28
 * behoben. Dieser Wächter prüft an der echten Tür, dass der Endpunkt
 * /_next/image wirklich NICHT mehr antwortet — nicht nur, dass die Option in
 * der Datei steht.
 *
 * Gemessen am gebauten Web-Image (vorher/nachher, gleicher Stand sonst):
 * vorher erlaubter Host 200 mit Bilddaten, fremder Host 400; nachher 404 für
 * alle drei Arten von Ziel. Rot-Beweis: ohne die Option antwortet der
 * Endpunkt wieder (200/400/500), keiner der Fälle unten ist dann 404.
 *
 * ZURÜCKNEHMEN mit dem Umstieg auf Next 15: Dann kommen die Wächter für
 * Host-Allowlist, sharp und Cache (#91, #98) aus der Git-Historie dieser
 * Datei zurück.
 *
 * KEINE Anmeldung nötig: /_next/image ist eine Next.js-interne Route des
 * Web-Containers, kein Fach-Router des Backends.
 */
test.describe("Bild-Optimizer ist abgeschaltet (Hotfix bis Next 15)", () => {
  const apiUrl = process.env.API_URL ?? "http://api:8000";
  // Fixtures erfunden: evil.invalid ist laut RFC 2606 reserviert; die Datei
  // am eigenen API-Origin existiert absichtlich nicht; /icon-512.png liegt im
  // Repo und damit in jedem Stapel.
  const ziele = [
    { name: "lokale Datei", url: "/icon-512.png" },
    { name: "erlaubter Host (eigene API)", url: `${apiUrl}/images/hotfix-gibt-es-nicht.webp` },
    { name: "fremder Host", url: "https://evil.invalid/x.svg" },
  ];
  for (const ziel of ziele) {
    test(`/_next/image antwortet nicht mehr: ${ziel.name}`, async ({ request, baseURL }) => {
      const antwort = await request.get(
        `${baseURL}/_next/image?url=${encodeURIComponent(ziel.url)}&w=64&q=75`,
        { headers: { Accept: "image/webp,image/avif,*/*" } },
      );
      expect(antwort.status()).toBe(404);
      expect(antwort.headers()["content-type"] ?? "").not.toMatch(/^image\//);
    });
  }
});
