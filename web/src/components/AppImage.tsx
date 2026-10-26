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
 */
export function istEigenesFoto(src: ImageProps["src"]): boolean {
  return typeof src === "string" && src.startsWith(`${API_BASE}/images/`);
}

/** next/image mit der Ausnahme für eigene Fotos — überall statt next/image verwenden. */
export default function AppImage({ alt, unoptimized, ...rest }: ImageProps) {
  return <Image alt={alt} unoptimized={unoptimized || istEigenesFoto(rest.src)} {...rest} />;
}
