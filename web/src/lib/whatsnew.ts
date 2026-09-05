import { WHATS_NEW, WhatsNewRisk } from "./whatsnew.generated";

export { WHATS_NEW };
export type { WhatsNewRisk };

const SEEN_KEY = "whatsnew_seen_version";

/**
 * Zuletzt vom Nutzer gesehene Version, oder null bei frischer Installation
 * (Schlüssel existiert noch gar nicht). try/catch: privater Modus o. Ä. kann
 * den Storage-Zugriff verweigern — dann eben bei jedem Laden erneut fragen,
 * statt die App abstürzen zu lassen.
 */
export function getSeenVersion(): string | null {
  try {
    return localStorage.getItem(SEEN_KEY);
  } catch {
    return null;
  }
}

/** Version als gesehen vermerken (Default: die aktuelle). */
export function markSeen(version: string = WHATS_NEW.version) {
  try {
    localStorage.setItem(SEEN_KEY, version);
  } catch {
    // kein Storage verfügbar — dann eben beim nächsten Laden erneut fragen
  }
}

// Schlankes Pub-Sub für den Wiederöffnen-Weg (Einstellungen → Modal, Issue
// #99 Auftrag): Das Modal hängt EINMAL global im Layout, die
// Einstellungsseite ist ein Geschwister im Client-Baum. Keine sechste
// Context-Konstruktion nur für dieses eine Signal — dafür reicht eine
// Listener-Liste. Die fünf bestehenden Modals brauchen das nicht: sie werden
// alle über lokalen State IHRER Elternseite geöffnet/geschlossen, nicht
// global über Seitenwechsel hinweg.
type Listener = () => void;
const listeners = new Set<Listener>();

export function openWhatsNew() {
  listeners.forEach((l) => l());
}

/** Für WhatsNewModal: abonnieren, Rückgabewert wieder aufrufen zum Abmelden. */
export function onOpenWhatsNew(cb: Listener): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}
