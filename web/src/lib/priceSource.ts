// Herkunft eines Preises deuten (v1.8.2) — geteilt von Preisverlauf-Chart und
// Detailansicht, damit beide dieselbe Wahrheit beschriften.
//
// `quelle` steht so im Preisverlauf (preis_historie.quelle):
//   "tcgdex-cardmarket" · "cardmarket-oauth" · "tcgplayer-usd@0.8666"

export type PriceSourceKey = "cardmarket" | "oauth" | "tcgplayer" | "unbekannt";

export const PRICE_SOURCE_COLOR: Record<PriceSourceKey, string> = {
  cardmarket: "#FFCA28",   // Haus-Gelb (bisherige Linienfarbe)
  oauth: "#FFA000",
  tcgplayer: "#42A5F5",    // Blau = $-Basis
  unbekannt: "#9ca3af",
};

export function priceSourceKey(quelle?: string | null): PriceSourceKey {
  if (!quelle) return "unbekannt";
  if (quelle.startsWith("tcgplayer-usd")) return "tcgplayer";
  if (quelle.startsWith("cardmarket-oauth")) return "oauth";
  if (quelle.startsWith("tcgdex-cardmarket")) return "cardmarket";
  // Alles andere ist NICHT automatisch Cardmarket (Panel-Fund): eine unbekannte
  // oder künftige Quelle wird neutral gezeigt statt falsch etikettiert.
  return "unbekannt";
}

/** Umrechnungskurs aus "tcgplayer-usd@0.8666" → "0.8666"; sonst null. */
export function priceSourceRate(quelle?: string | null): string | null {
  const at = quelle?.indexOf("@") ?? -1;
  return at >= 0 ? quelle!.slice(at + 1) : null;
}
