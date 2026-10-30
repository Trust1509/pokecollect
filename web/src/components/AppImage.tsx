"use client";

import Image, { type ImageProps } from "next/image";

import { API_BASE } from "@/lib/api";

/**
 * Eigene Fotos (Karten, Sealed) kommen vom /images-Mount der API und tragen
 * `?v=<Zeitstempel>` als Cache-Busting nach einem Neu-Upload (lib/utils.ts
 * imageUrl). Der Bild-Optimizer lehnt jeden Querystring am API-Muster ab
 * (`search: ""` in next.config.js, #98 — Schutz gegen Cache-Vervielfältigung).
 * Ergebnis bis #117: Jedes eigene Foto lieferte 400 und blieb leer, sobald der
 * Optimizer an war (gemessen im Panel zu #117 am gebauten Image).
 *
 * Deshalb laufen eigene Fotos am Optimizer vorbei, direkt von der API. Sie sind
 * schon passend klein (die API legt ein Vorschaubild an), und der Querystring-
 * Schutz bleibt für alle fremden Quellen bestehen.
 *
 * #120: ebenso der Bild-Spiegel der API (fremde Bilder, die das Backend holt).
 * Über den Optimizer müsste der Web-SERVER die API erreichen — unter
 * NEXT_PUBLIC_API_URL, die für den BROWSER gilt: "http://localhost:3010"
 * zeigt im Web-Container auf ihn selbst, und hinter Caddy mit Authelia hat
 * der Server keine Sitzung (Blindprüfer #120). Der Browser lädt beides so
 * wie eigene Fotos, und der Optimizer ruft gar nichts mehr von außen ab.
 * Preis: Spiegel-Bilder kommen in Originalgröße (TCGdex high.webp, TCGplayer
 * 1000×1000), nicht verkleinert — anders als eigene Fotos ohne Vorschaubild.
 */
export function istApiBild(src: ImageProps["src"]): boolean {
  return (
    typeof src === "string" &&
    (src.startsWith(`${API_BASE}/images/`) || src.startsWith(`${API_BASE}/bild-spiegel/`))
  );
}

/** next/image mit der Ausnahme für API-Bilder — überall statt next/image verwenden. */
export default function AppImage({ alt, unoptimized, ...rest }: ImageProps) {
  return <Image alt={alt} unoptimized={unoptimized || istApiBild(rest.src)} {...rest} />;
}
