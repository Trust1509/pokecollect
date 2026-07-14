// Serie-ID → Anzeigename (für geclusterte Set-Dropdowns)
export const SERIES_LABEL: Record<string, string> = {
  sv: "Karmesin & Purpur", me: "Mega-Entwicklung", swsh: "Schwert & Schild",
  sm: "Sonne & Mond", xy: "XY", bw: "Schwarz & Weiß", hgss: "HeartGold & SoulSilver",
  dp: "Diamant & Perl", pl: "Platin", ex: "EX", base: "Base", neo: "Neo",
  gym: "Gym", ecard: "e-Card", col: "Call of Legends", pop: "POP", tk: "Trainer Kits",
};

export function seriesLabel(id?: string | null): string {
  return id ? (SERIES_LABEL[id] ?? id.toUpperCase()) : "—";
}

export type FilterCriteria = {
  besessen?: boolean;
  generation?: number;
  set?: string;
  seltenheit?: string;
  sprache?: string;
  illustrator?: string;
  search?: string;
  bild_status?: string;
};

export function hasActiveFilters(f: FilterCriteria): boolean {
  return Boolean(
    f.besessen !== undefined || f.generation || f.set || f.seltenheit ||
    f.sprache || f.illustrator || f.search || f.bild_status
  );
}

type MatchCard = {
  kartenname?: string | null; englischer_name?: string | null;
  pokedex_nr?: number | null; set_edition?: string | null;
  seltenheit?: string | null; sprache?: string | null; illustrator?: string | null;
  besessen?: boolean; bild_karte_pfad?: string | null; bild_pokedex_url?: string | null;
};

/** Client-seitiger Filter-Abgleich (für Dimmen im Binder, gleiche Logik wie Backend). */
export function cardMatchesFilters(card: MatchCard, f: FilterCriteria): boolean {
  if (f.besessen !== undefined && Boolean(card.besessen) !== f.besessen) return false;
  if (f.generation && generation(card.pokedex_nr ?? null) !== f.generation) return false;
  if (f.set && !(card.set_edition ?? "").toLowerCase().includes(f.set.toLowerCase())) return false;
  if (f.seltenheit && card.seltenheit !== f.seltenheit) return false;
  if (f.sprache && card.sprache !== f.sprache) return false;
  if (f.illustrator && !(card.illustrator ?? "").toLowerCase().includes(f.illustrator.toLowerCase())) return false;
  if (f.search) {
    const term = f.search.toLowerCase();
    const hit =
      (card.kartenname ?? "").toLowerCase().includes(term) ||
      (card.englischer_name ?? "").toLowerCase().includes(term) ||
      String(card.pokedex_nr ?? "").includes(term);
    if (!hit) return false;
  }
  if (f.bild_status) {
    const own = !!card.bild_karte_pfad;
    const url = !!card.bild_pokedex_url;
    if (f.bild_status === "eigenes_foto" && !own) return false;
    if (f.bild_status === "externe_url" && !(!own && url)) return false;
    if (f.bild_status === "platzhalter" && !(!own && !url)) return false;
  }
  return true;
}

// Bewusste Web-Kopie der Generationsgrenzen (clientseitiges Dimmen) —
// Quelle der Wahrheit: backend/app/domain/pokedex.py::GEN_RANGES.
// Bei Gen-10-Erweiterung BEIDE Stellen anpassen.
export function generation(pokedexNr: number | null): number | null {
  if (!pokedexNr) return null;
  const ranges: [number, number][] = [
    [1, 151], [152, 251], [252, 386], [387, 493],
    [494, 649], [650, 721], [722, 809], [810, 905], [906, 1025],
  ];
  for (let i = 0; i < ranges.length; i++) {
    const [lo, hi] = ranges[i];
    if (pokedexNr >= lo && pokedexNr <= hi) return i + 1;
  }
  return null;
}

export function formatEur(value: string | null | undefined): string {
  if (!value) return "–";
  return new Intl.NumberFormat("de-AT", { style: "currency", currency: "EUR" }).format(
    parseFloat(value)
  );
}

export function imageUrl(
  path: string | null | undefined,
  apiBase: string,
  version?: string | number | null,
): string | null {
  if (!path) return null;
  const base = `${apiBase}/images/${path.replace(/^(?:.*\/)?images\//, "")}`;
  // Cache-Busting: nach Re-Upload (gleicher Dateiname) lädt der Browser sonst
  // das alte Bild aus dem Cache.
  return version ? `${base}?v=${encodeURIComponent(String(version))}` : base;
}

export function pokemonPlaceholderUrl(pokedexNr: number | null | undefined): string | null {
  if (!pokedexNr || pokedexNr < 1 || pokedexNr > 1025) return null;
  const nr = String(pokedexNr).padStart(3, "0");
  return `https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/${nr}.png`;
}

/**
 * "Paldeas Schicksale (PAF)" → "PAF"; null wenn kein Klammer-Kürzel.
 * Regex-Vertrag mit backend/app/services/card_image_service.py::extract_set_code —
 * bei Änderungen beide Stellen anpassen (Punkt + bis 8 Zeichen, z. B. "SV03.5").
 */
export function setCodeFromEdition(setEdition: string | null | undefined): string | null {
  if (!setEdition) return null;
  const m = setEdition.match(/\(([A-Z0-9.]{1,8})\)\s*$/);
  return m ? m[1] : null;
}

/** Anzeige-Variante: fällt statt null auf die ersten Zeichen zurück. */
export function extractSetCode(setEdition: string | null | undefined): string {
  return setCodeFromEdition(setEdition) ?? (setEdition ? setEdition.slice(0, 4) : "");
}

type CardImageFields = {
  bild_karte_pfad?: string | null;      // eigenes Foto in voller Auflösung
  bild_thumbnail_pfad?: string | null;  // eigenes Foto als Thumbnail
  bild_pokedex_url?: string | null;
  bild_karte_url?: string | null;
  pokedex_nr?: number | null;
  aktualisiert_am?: string | null;   // für Cache-Busting eigener Fotos
};

/**
 * Liefert Bildquelle + ob es nur ein Pokédex-Platzhalter ist.
 *
 * Prioritätskette — Vertrag mit dem Backend, muss mit
 * backend/app/services/card_image_service.py:14-18 übereinstimmen:
 *   1. Eigenes Foto (Upload) — je nach Variante Thumbnail oder Vollbild
 *   2. bild_pokedex_url — manuell gesetzte URL
 *   3. bild_karte_url — auto von TCGdex
 *   4. Pokédex-Artwork — Platzhalter als letzter Fallback
 *
 * variant "thumb" (Raster/Binder) nutzt bild_thumbnail_pfad,
 * variant "full" (Detailseite) nutzt bild_karte_pfad.
 */
export function cardImageSrc(
  card: CardImageFields,
  apiBase: string,
  placeholderEnabled = true,
  variant: "thumb" | "full" = "thumb",
): { src: string | null; isPlaceholder: boolean } {
  const ownPath = variant === "full" ? card.bild_karte_pfad : card.bild_thumbnail_pfad;
  const own = imageUrl(ownPath, apiBase, card.aktualisiert_am);
  const src = own
    ?? card.bild_pokedex_url
    ?? card.bild_karte_url
    ?? (placeholderEnabled ? pokemonPlaceholderUrl(card.pokedex_nr) : null);
  const isPlaceholder = !own && !card.bild_pokedex_url && !card.bild_karte_url && !!src;
  return { src, isPlaceholder };
}
