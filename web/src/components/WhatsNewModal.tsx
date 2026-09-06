"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/i18n";
import {
  WHATS_NEW,
  getSeenVersion,
  istFrischeInstallation,
  markSeen,
  onOpenWhatsNew,
} from "@/lib/whatsnew";

const RISK_LABEL_KEYS = {
  gefahrlos: "whatsnew_risk_gefahrlos",
  backup: "whatsnew_risk_backup",
  breaking: "whatsnew_risk_breaking",
} as const;

/**
 * "Was ist neu"-Box nach einem Update (Issue #99). Erscheint einmalig, wenn
 * die zuletzt gesehene Version (localStorage) von der aktuellen abweicht;
 * danach über die Versionsnummer in den Einstellungen jederzeit wieder
 * erreichbar (siehe lib/whatsnew.ts, Pub-Sub `openWhatsNew`).
 *
 * Frische Installation (kein gespeicherter Stand) zeigt NICHTS — die
 * aktuelle Version wird still als gesehen vermerkt. Für eine erste
 * Installation ist ohnehin alles neu, und das hält auch den
 * Rauchtest-Stapel frei vom Modal: auth.setup.ts meldet sich mit einem
 * frischen Browser an, bevor storageState abgelegt wird — dieser Effekt
 * läuft also VOR der Aufnahme, und alle 20 bestehenden Tests erben danach
 * "aktuelle Version bereits gesehen" (siehe Bau-Bericht #99, Block F6).
 *
 * Visuelles Muster lehnt sich an ImageLightbox.tsx an (fixed inset-0 + ESC +
 * Scroll-Sperre) — fünftes Modal-Muster im Projekt neben CatalogCardModal,
 * SealedFormModal, CornerEditor, BurgerMenu; keine sechste Eigenbauweise
 * (Kredo/DRY). NEU gegenüber allen fünf: dieses Modal hängt global im
 * Layout statt lokal auf einer Seite — deshalb der eigene Pfad-Check unten
 * (AuthGuard selbst schließt /login NICHT aus, siehe Navbar.tsx/
 * BottomNav.tsx: beide prüfen denselben Pfad separat) und das kleine
 * Pub-Sub für den seitenübergreifenden Wiederöffnen-Weg.
 */
export default function WhatsNewModal() {
  const { t, lang } = useI18n();
  const pathname = usePathname() ?? "/";
  const [show, setShow] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const close = useCallback(() => {
    markSeen();
    setShow(false);
  }, []);

  // Nur beim ersten Mount prüfen ("nach einem Update" — nicht bei jedem
  // Re-Render neu bewerten, sonst würde z. B. ein Sprachwechsel während der
  // Sitzung den Vergleich erneut anstoßen).
  useEffect(() => {
    const seen = getSeenVersion();
    if (seen === null) {
      // Kein Eintrag — zwei sehr verschiedene Lagen (Panel-Nacharbeit #99):
      if (istFrischeInstallation()) {
        // Wirklich frisch: alles ist neu, es gibt kein "seit zuletzt".
        // Nichts zeigen, aktuelle Version still vermerken (Auftrag Block 4).
        markSeen();
        return;
      }
      // BESTEHENDE Installation, die den Schlüssel noch nicht kennt — das ist
      // der Zustand direkt nach dem Deploy dieser Funktion. Genau hier soll die
      // Box erscheinen, sonst bliebe ausgerechnet ihr erster Einsatz stumm.
      setShow(true);
      return;
    }
    if (seen !== WHATS_NEW.version) setShow(true);
  }, []);

  useEffect(() => onOpenWhatsNew(() => setShow(true)), []);

  // Panel-Nacharbeit (#99, beide Stimmen): `aria-modal="true"` verspricht, dass
  // der Hintergrund für die Tastatur nicht existiert — gemessen lagen vorher
  // ALLE 8 Tab-Stopps AUSSERHALB des Dialogs, auf Bedienelementen unter der
  // Verdunklung. Fokusfang deshalb nach dem bereits vorhandenen, richtigen
  // Muster aus BurgerMenu.tsx:27-65 (Kredo/DRY, Prüffrage F3): Anfangsfokus ins
  // Panel, Tab-Zyklus, Fokus-Rückgabe beim Schließen. ImageLightbox.tsx (das
  // optische Vorbild) hat dieselbe Lücke — die übrigen Modals nachziehen ist ein
  // eigener Slice, siehe Panel-Kommentar.
  useEffect(() => {
    if (!show) return;
    const zuvorFokussiert = document.activeElement as HTMLElement | null;

    const fokussierbare = () =>
      Array.from(
        panelRef.current?.querySelectorAll<HTMLElement>("a[href], button:not([disabled])") ?? [],
      );

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        return;
      }
      if (e.key === "Tab") {
        const els = fokussierbare();
        if (els.length === 0) return;
        const erstes = els[0];
        const letztes = els[els.length - 1];
        if (e.shiftKey && document.activeElement === erstes) {
          e.preventDefault();
          letztes.focus();
        } else if (!e.shiftKey && document.activeElement === letztes) {
          e.preventDefault();
          erstes.focus();
        }
      }
    };

    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    fokussierbare()[0]?.focus();

    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      zuvorFokussiert?.focus();
    };
  }, [show, close]);

  // Vor der Anmeldeseite nichts (wie Navbar.tsx/BottomNav.tsx) — AuthGuard
  // setzt "ready" auf /login SOFORT (kein Token nötig), schließt die Route
  // also NICHT automatisch aus.
  if (pathname === "/login" || !show) return null;

  const body = lang === "EN" ? WHATS_NEW.en : WHATS_NEW.de;
  // Panel-Nacharbeit (#99, beide Stimmen fanden es unabhängig): Der Untertitel
  // stammt aus der DEUTSCHEN CHANGELOG-Überschrift und stand deshalb auch im
  // englischen Dialog auf Deutsch — Zusage "in beiden Sprachen" gebrochen.
  // titleEn kommt jetzt aus whatsnew.en.json; fällt auf den deutschen Titel
  // zurück, damit eine vergessene Übersetzung keine leere Zeile erzeugt (der
  // Wächter macht sie ohnehin rot, siehe check-whatsnew.mjs).
  const titel = (lang === "EN" ? WHATS_NEW.titleEn : WHATS_NEW.title) || WHATS_NEW.title;
  const risk = WHATS_NEW.risk;
  const riskKey = risk ? RISK_LABEL_KEYS[risk] : null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t.whatsnew_title(WHATS_NEW.version)}
      onClick={close}
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4"
    >
      <div
        ref={panelRef}
        onClick={(e) => e.stopPropagation()}
        className="bg-pokemon-card rounded-lg shadow-2xl max-w-md w-full max-h-[80vh] overflow-y-auto p-5 space-y-3"
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-white font-bold text-lg">{t.whatsnew_title(WHATS_NEW.version)}</h2>
            {titel && <p className="text-gray-400 text-sm">{titel}</p>}
          </div>
          <button
            type="button"
            onClick={close}
            aria-label={t.whatsnew_close}
            className="shrink-0 w-8 h-8 flex items-center justify-center rounded-full text-gray-400 hover:text-white hover:bg-black/30 text-2xl leading-none"
          >
            ×
          </button>
        </div>
        {riskKey && (
          <span className="inline-block text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-200">
            {t[riskKey]}
          </span>
        )}
        {/* data-testid bewusst (nicht Rolle/Text): der restliche Dialog trägt
            immer sprachabhängige Chrome-Texte (Titel, Schließen-Knopf,
            Risiko-Label aus t.whatsnew_*) — ein Test auf den GANZEN Dialog
            sähe fälschlich "unterschiedlich", selbst wenn ausgerechnet DIESER
            generierte Text (de/en aus whatsnew.generated.ts) sabotiert und
            identisch wäre. Siehe e2e/tests/whatsnew.spec.ts, Wächter 3. */}
        <p data-testid="whatsnew-body" className="text-gray-200 text-sm whitespace-pre-line">{body}</p>
        <div className="pt-1 text-right">
          <button
            type="button"
            onClick={close}
            className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600"
          >
            {t.whatsnew_close}
          </button>
        </div>
      </div>
    </div>
  );
}
