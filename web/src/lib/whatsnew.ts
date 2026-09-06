import { WHATS_NEW, WhatsNewRisk } from "./whatsnew.generated";

export { WHATS_NEW };
export type { WhatsNewRisk };

const SEEN_KEY = "whatsnew_seen_version";

/**
 * Zuletzt vom Nutzer gesehene Version, oder null, wenn der Schlüssel fehlt.
 *
 * ACHTUNG, null heißt NICHT "frische Installation" — siehe istFrischeInstallation():
 * Der Schlüssel wird mit Issue #99 EINGEFÜHRT, eine bestehende Installation
 * hat ihn nach dem Update also genauso wenig wie ein neuer Browser.
 *
 * try/catch: Ist der Storage gesperrt (privater Modus, Richtlinie), kommt hier
 * null zurück. Panel-Nacharbeit — der frühere Kommentar behauptete, dann werde
 * "bei jedem Laden erneut gefragt"; tatsächlich schlägt auch markSeen() fehl und
 * das Modal erscheint dort NIE. Das ist hinnehmbar (ohne Storage lässt sich
 * "schon gesehen" nicht merken, und ein Modal bei JEDEM Laden wäre schlimmer),
 * aber es gehört richtig beschrieben.
 */
export function getSeenVersion(): string | null {
  try {
    return localStorage.getItem(SEEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Ist das hier wirklich eine frische Installation — oder eine BESTEHENDE, die
 * den Schlüssel nur noch nicht kennt?
 *
 * Panel-Nacharbeit (#99, BLOCKER der Zweitstimme, am laufenden Stapel
 * reproduziert): `whatsnew_seen_version` wird von diesem Slice erst eingeführt.
 * Wer die App heute benutzt, hat ihn nach dem Update nicht — mit der alten
 * Logik galt er als "frisch", die Box blieb aus und die Version wurde still
 * vermerkt. Ergebnis: Ausgerechnet beim ERSTEN Deploy dieser Funktion hätte
 * niemand etwas gesehen; gewirkt hätte sie erst beim übernächsten Release.
 * Gemessen vor dem Fix: Bestandsnutzer mit Token → 0 Dialoge.
 *
 * Unterscheidungsmerkmal ist deshalb, ob ÜBERHAUPT App-Zustand im Storage
 * liegt. `token` schreibt die Anmeldung (ADR-0003), `lang` der Sprachschalter
 * (i18n.tsx) — beides gibt es nur, wenn die App hier schon benutzt wurde.
 */
export function istFrischeInstallation(): boolean {
  try {
    return localStorage.getItem("token") === null && localStorage.getItem("lang") === null;
  } catch {
    // Kein Storage lesbar → wie frisch behandeln (es lässt sich ohnehin nichts merken).
    return true;
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
