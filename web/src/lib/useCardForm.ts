"use client";
import { Dispatch, SetStateAction, useRef, useState } from "react";
import { Card, PokemonSet, scanApi } from "@/lib/api";
import { fetchPokemonNames } from "@/lib/pokedex";
import { setCodeFromEdition } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

// Gemeinsame Formular-Logik für Karten-Neuanlage (cards/new) und Detail-Edit
// (cards/[id]) — ein Codepfad je Sache (Kredo, Issue #5):
//   - Pokédex-Nr. → debounced Namens-Lookup inkl. Auto-Fill-Tracking
//   - Karten-Nr.-Validierung gegen das gewählte Set
//   - Set-Auswahl (SetPicker-Anbindung)
//   - optional (Issue #31): Set-Kürzel + Kartennummer → derselbe TCGdex-Resolver
//     wie der Scan (POST /scan/resolve) füllt Name/Pokédex/Seltenheit/… vor

/** Mindest-Form-Felder, die der Hook liest/schreibt. */
type CardFormShape = {
  pokedex_nr?: number | null;
  kartenname?: string | null;
  englischer_name?: string | null;
  set_edition?: string | null;
  karten_nr?: string | null;
  seltenheit?: string | null;
  folierung?: string | null;
};

/** Form-Typ der Neuanlage: Karten-Felder + freie Zusatzfelder. */
export type CardFormValues = Partial<Card> & Record<string, unknown>;

type Options = {
  /** Set-Kürzel + Kartennummer automatisch über TCGdex auflösen (nur Neuanlage). */
  resolve?: boolean;
};

export function useCardForm<T extends CardFormShape>(
  setForm: Dispatch<SetStateAction<T>>,
  opts: Options = {},
) {
  const { t } = useI18n();
  const [selectedSet, setSelectedSet] = useState<PokemonSet | null>(null);
  const [cardNrError, setCardNrError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);
  const [resolving, setResolving] = useState(false);
  // Tracking ob Name auto-befüllt wurde — dann darf er bei Nr.-Änderung überschrieben werden
  const autoFilled = useRef({ kartenname: false, englischer_name: false });
  const lookupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Kontext für den Set+Nummer-Resolver (Issue #31)
  const resolveTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ctx = useRef<{ setCode: string | null; number: string | null; language: string }>({
    setCode: null, number: null, language: "DE",
  });

  /** Manuelle Eingabe in ein Namensfeld → Auto-Fill-Flag zurücksetzen. */
  const noteManualEdit = (key: string) => {
    if (key === "kartenname") autoFilled.current.kartenname = false;
    if (key === "englischer_name") autoFilled.current.englischer_name = false;
  };

  const handlePokedexNr = (nr: number | null) => {
    setForm((f) => ({ ...f, pokedex_nr: nr } as T));
    if (lookupTimeout.current) clearTimeout(lookupTimeout.current);

    if (!nr || nr < 1 || nr > 1025) {
      // Wert sichern BEVOR der Ref zurückgesetzt wird, sonst liest setForm schon false
      const af = { ...autoFilled.current };
      autoFilled.current = { kartenname: false, englischer_name: false };
      setForm((f) => ({
        ...f,
        kartenname: af.kartenname ? "" : f.kartenname,
        englischer_name: af.englischer_name ? "" : f.englischer_name,
      } as T));
      return;
    }

    // Debounce: erst nach 500ms Tippen-Pause den Lookup starten
    lookupTimeout.current = setTimeout(async () => {
      setNameLoading(true);
      try {
        const names = await fetchPokemonNames(nr);
        if (names) {
          setForm((f) => {
            // Flag nur für Felder setzen, die WIRKLICH auto-befüllt wurden —
            // sonst markiert ein Zwischen-Lookup (langsames Tippen: "2" → "25")
            // den manuell eingegebenen Namen als "auto" und der nächste
            // Lookup überschreibt ihn.
            const fillName = !f.kartenname || autoFilled.current.kartenname;
            const fillEn = !f.englischer_name || autoFilled.current.englischer_name;
            autoFilled.current = { kartenname: fillName, englischer_name: fillEn };
            return {
              ...f,
              kartenname: fillName ? names.de : f.kartenname,
              englischer_name: fillEn ? names.en : f.englischer_name,
            } as T;
          });
        }
      } finally {
        setNameLoading(false);
      }
    }, 500);
  };

  // ── Set + Nummer → TCGdex-Resolver (Issue #31) ─────────────────────────────
  const scheduleResolve = () => {
    if (!opts.resolve) return;
    if (resolveTimeout.current) clearTimeout(resolveTimeout.current);
    const { setCode, number, language } = ctx.current;
    if (!setCode || !number) return;
    resolveTimeout.current = setTimeout(async () => {
      setResolving(true);
      try {
        const { data } = await scanApi.resolve({ set_code: setCode, number, language });
        const s = (data.suggested ?? {}) as Record<string, unknown>;
        if (!data.match) return; // kein Treffer → nichts überschreiben
        setForm((f) => {
          const g = { ...f } as T & Record<string, unknown>;
          const str = (v: unknown) => (typeof v === "string" ? v : "");
          const empty = (v: unknown) => v == null || v === "";
          // Namen: leer ODER zuvor auto-befüllt → mit dem echten Kartennamen
          // („Glurak-ex") überschreiben; danach als auto markieren.
          if (str(s.kartenname) && (empty(g.kartenname) || autoFilled.current.kartenname)) {
            g.kartenname = s.kartenname as string;
            autoFilled.current.kartenname = true;
          }
          if (str(s.englischer_name) && (empty(g.englischer_name) || autoFilled.current.englischer_name)) {
            g.englischer_name = s.englischer_name as string;
            autoFilled.current.englischer_name = true;
          }
          // Nur leere Felder befüllen — Nutzer-Eingaben bleiben stehen.
          if (s.pokedex_nr != null && empty(g.pokedex_nr)) g.pokedex_nr = s.pokedex_nr as number;
          if (str(s.seltenheit) && empty(g.seltenheit)) g.seltenheit = s.seltenheit as string;
          if (str(s.folierung) && empty(g.folierung)) g.folierung = s.folierung as string;
          // Kartennummer + Set-Bezeichnung auf die aufgelöste Vollform anheben
          // („041" → „041/109", „OBF" → „Obsidianflammen (OBF)").
          if (str(s.karten_nr)) { g.karten_nr = s.karten_nr as string; ctx.current.number = s.karten_nr as string; }
          if (str(s.set_edition)) g.set_edition = s.set_edition as string;
          return g;
        });
        setCardNrError(null);
      } catch {
        /* offline / kein Treffer → still, Nutzer füllt manuell */
      } finally {
        setResolving(false);
      }
    }, 500);
  };

  const validateCardNr = (nr: string): boolean => {
    if (!nr) return true;
    // Akzeptiert nackte Nummer („041"), optional mit Buchstabe/Präfix und
    // optionaler Gesamtzahl („041/109", „TG01/TG30"). Der Resolver ergänzt die
    // Gesamtzahl — die volle NNN/MAX-Form wird NICHT mehr erzwungen (Issue #31).
    if (!nr.match(/^[A-Za-z]{0,3}\d{1,4}[a-z]?(\/[A-Za-z]{0,3}\d{1,4})?$/)) {
      setCardNrError(t.form_card_nr_bad);
      return false;
    }
    setCardNrError(null);
    return true;
  };

  /** Kartennummer setzen + (optional) Resolver anstoßen. */
  const handleCardNr = (nr: string, language?: string) => {
    setForm((f) => ({ ...f, karten_nr: nr } as T));
    setCardNrError(null);
    ctx.current.number = nr.trim() || null;
    if (language) ctx.current.language = language;
    scheduleResolve();
  };

  const handleSetChange = (setEdition: string, s: PokemonSet | null, language?: string) => {
    setForm((f) => ({ ...f, set_edition: setEdition || null } as T));
    setSelectedSet(s);
    setCardNrError(null);
    ctx.current.setCode = s?.code ?? setCodeFromEdition(setEdition);
    if (language) ctx.current.language = language;
    scheduleResolve();
  };

  return {
    selectedSet,
    cardNrError,
    setCardNrError,
    nameLoading,
    resolving,
    noteManualEdit,
    handlePokedexNr,
    handleCardNr,
    validateCardNr,
    handleSetChange,
  };
}
