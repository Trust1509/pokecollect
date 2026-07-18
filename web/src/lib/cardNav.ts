// Merkt sich die Reihenfolge der zuletzt gesehenen Karten-Liste (Pokédex, Owned,
// Wunschliste, Binder) in sessionStorage, damit die Detailseite Vor-/Zurück-
// Nachbarn der aktuellen Karte bestimmen kann (Issue #24) — analog dazu, wie der
// Binder seine aktuelle Seite über die Navigation hinweg merkt.
const KEY = "card_nav_order";

/** Reihenfolge der aktuell sichtbaren Liste merken (beim Öffnen einer Karte). */
export function rememberCardOrder(ids: number[]): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(KEY, JSON.stringify(ids));
  } catch {
    /* sessionStorage nicht verfügbar → Navigation fällt still auf „kein Nachbar" zurück */
  }
}

/** Zuletzt gemerkte Reihenfolge lesen (leeres Array, wenn keine vorhanden). */
export function readCardOrder(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = sessionStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((x): x is number => typeof x === "number")
      : [];
  } catch {
    return [];
  }
}

/**
 * Nachbar-IDs (Vorgänger/Nachfolger) der aktuellen Karte in der gemerkten Liste.
 * Ist die Karte nicht in der Liste (oder gibt es keine Liste), sind beide null →
 * die Blätter-Buttons werden deaktiviert.
 */
export function cardNeighbors(currentId: number): { prev: number | null; next: number | null } {
  const order = readCardOrder();
  const idx = order.indexOf(currentId);
  if (idx === -1) return { prev: null, next: null };
  return {
    prev: idx > 0 ? order[idx - 1] : null,
    next: idx < order.length - 1 ? order[idx + 1] : null,
  };
}
