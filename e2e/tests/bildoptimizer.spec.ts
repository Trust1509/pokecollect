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

/**
 * #98 Panel-Nacharbeit: Wächter für die ZWEI Zusagen des Slices.
 *
 * Warum es die braucht (beide Panel-Stimmen, unabhängig): Der Rauchtest
 * meldete 18/18 grün, WÄHREND beide Fehler bestanden — er war für sie nie
 * ein Wächter. Grund im Next-Quelltext (v14.2.35 image-optimizer.ts):
 * Schlägt die Optimierung fehl, fängt ein catch den Fehler und liefert das
 * UNveränderte Original mit dessen ursprünglichem Content-Type aus
 * ("If we fail to optimize, fallback to the original image"). Die Seite
 * sieht deshalb heil aus, obwohl nichts optimiert wird — genau das
 * beobachtete Verhalten vor dem Fix (Antwort 94 380 B statt 25 694 B).
 *
 * Daraus die zwei Assertions, je eine pro Fehler:
 *  1. `content-type: image/webp`  → sharp hat WIRKLICH transformiert. Ohne
 *     sharp wirft Next im Standalone-Modus intern 500, der catch greift und
 *     der Content-Type bleibt der des Originals (image/png).
 *  2. `x-nextjs-cache: HIT` beim zweiten Abruf → der Cache wurde WIRKLICH
 *     geschrieben. Bei EACCES auf /app/.next/cache/images bleibt jeder Abruf
 *     MISS, ohne dass die Antwort selbst kaputtgeht.
 *
 * Fixture: `public/icon-512.png` — liegt im Repo und damit in JEDEM Stapel
 * (Prod, Teststand, Rauchtest); nichts aus der echten Sammlung, kein Fremdnetz.
 * Lokaler Pfad, deshalb greifen remotePatterns hier nicht — die Zusage ist
 * sharp + Cache, nicht die Host-Allowlist (die prüfen die Tests oben).
 */
test.describe("Bild-Optimizer optimiert und cacht wirklich (#98)", () => {
  test("sharp transformiert nach webp und der Cache greift beim zweiten Abruf", async ({
    request,
    baseURL,
  }) => {
    // Eigener q-Wert je Lauf wäre falsch: der Cache-Schlüssel soll zwischen
    // den beiden Abrufen GLEICH sein. Fester Wert, damit der zweite Abruf
    // denselben Eintrag trifft.
    const ziel = `${baseURL}/_next/image?url=${encodeURIComponent("/icon-512.png")}&w=64&q=75`;
    // Accept muss webp anbieten: Next wählt das Ausgabeformat daraus
    // (getSupportedMimeType). Ohne diesen Header bliebe der Content-Type auch
    // MIT sharp der des Originals — die Assertion würde falsch rot.
    const kopf = { Accept: "image/webp,image/avif,*/*" };

    const ersterAbruf = await request.get(ziel, { headers: kopf });
    expect(ersterAbruf.status(), await ersterAbruf.text()).toBe(200);
    // Zusage 1: sharp läuft. Vor dem Fix stand hier image/png.
    expect(ersterAbruf.headers()["content-type"]).toBe("image/webp");

    const zweiterAbruf = await request.get(ziel, { headers: kopf });
    expect(zweiterAbruf.status(), await zweiterAbruf.text()).toBe(200);
    expect(zweiterAbruf.headers()["content-type"]).toBe("image/webp");
    // Zusage 2: der Cache ist beschreibbar. Vor dem Fix stand hier MISS.
    expect(zweiterAbruf.headers()["x-nextjs-cache"]).toBe("HIT");
  });

  test("Querystring an einem erlaubten Host wird abgelehnt (Cache-Verstärkung)", async ({
    request,
    baseURL,
  }) => {
    // #98 Panel: Ohne `search: ""` in den remotePatterns vergleicht Next den
    // Querystring gar nicht — dieselbe Datei mit ?n=1, ?n=2, … erzeugt dann
    // beliebig viele verschiedene Cache-Einträge. Am laufenden Teststand
    // reproduziert: 5 Abrufe mit ?cachebust=1..5 → Cache-Einträge 1 → 6.
    // Derselbe Host und Pfad wie im Test darüber, NUR um einen Querystring
    // ergänzt: der Unterschied im Ergebnis kann damit nur vom Querystring
    // kommen.
    const apiUrl = process.env.API_URL ?? "http://api:8000";
    const mitQuery = `${apiUrl}/images/test98-gibt-es-nicht.webp?cachebust=1`;
    const antwort = await request.get(
      `${baseURL}/_next/image?url=${encodeURIComponent(mitQuery)}&w=64&q=75`,
    );
    expect(antwort.status(), await antwort.text()).toBe(400);
  });
});
