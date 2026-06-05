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

export function imageUrl(path: string | null | undefined, apiBase: string): string | null {
  if (!path) return null;
  return `${apiBase}/images/${path.replace(/^.*\/images\//, "")}`;
}

export function pokemonPlaceholderUrl(pokedexNr: number | null | undefined): string | null {
  if (!pokedexNr || pokedexNr < 1 || pokedexNr > 1025) return null;
  const nr = String(pokedexNr).padStart(3, "0");
  return `https://www.pokemon.com/static-assets/content-assets/cms2/img/pokedex/full/${nr}.png`;
}

type CardImageFields = {
  bild_thumbnail_pfad?: string | null;
  bild_pokedex_url?: string | null;
  bild_karte_url?: string | null;
  pokedex_nr?: number | null;
};

/** Liefert Bildquelle + ob es nur ein Pokédex-Platzhalter ist. */
export function cardImageSrc(
  card: CardImageFields,
  apiBase: string,
  placeholderEnabled = true
): { src: string | null; isPlaceholder: boolean } {
  const src = card.bild_thumbnail_pfad
    ? `${apiBase}/images/${card.bild_thumbnail_pfad.replace(/^.*\/images\//, "")}`
    : card.bild_pokedex_url
    ?? card.bild_karte_url
    ?? (placeholderEnabled ? pokemonPlaceholderUrl(card.pokedex_nr) : null);
  const isPlaceholder =
    !card.bild_thumbnail_pfad && !card.bild_pokedex_url && !card.bild_karte_url && !!src;
  return { src, isPlaceholder };
}
