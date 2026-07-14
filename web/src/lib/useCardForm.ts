"use client";
import { Dispatch, SetStateAction, useRef, useState } from "react";
import { Card, PokemonSet } from "@/lib/api";
import { fetchPokemonNames } from "@/lib/pokedex";
import { useI18n } from "@/lib/i18n";

// Gemeinsame Formular-Logik für Karten-Neuanlage (cards/new) und Detail-Edit
// (cards/[id]) — ein Codepfad je Sache (Kredo, Issue #5):
//   - Pokédex-Nr. → debounced Namens-Lookup inkl. Auto-Fill-Tracking
//   - Karten-Nr.-Validierung gegen das gewählte Set
//   - Set-Auswahl (SetPicker-Anbindung)

/** Mindest-Form-Felder, die der Hook liest/schreibt. */
type CardFormShape = {
  pokedex_nr?: number | null;
  kartenname?: string | null;
  englischer_name?: string | null;
  set_edition?: string | null;
};

/** Form-Typ der Neuanlage: Karten-Felder + freie Zusatzfelder. */
export type CardFormValues = Partial<Card> & Record<string, unknown>;

export function useCardForm<T extends CardFormShape>(
  setForm: Dispatch<SetStateAction<T>>,
) {
  const { t } = useI18n();
  const [selectedSet, setSelectedSet] = useState<PokemonSet | null>(null);
  const [cardNrError, setCardNrError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);
  // Tracking ob Name auto-befüllt wurde — dann darf er bei Nr.-Änderung überschrieben werden
  const autoFilled = useRef({ kartenname: false, englischer_name: false });
  const lookupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

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
          setForm((f) => ({
            ...f,
            kartenname: (!f.kartenname || autoFilled.current.kartenname) ? names.de : f.kartenname,
            englischer_name: (!f.englischer_name || autoFilled.current.englischer_name) ? names.en : f.englischer_name,
          } as T));
          autoFilled.current = { kartenname: true, englischer_name: true };
        }
      } finally {
        setNameLoading(false);
      }
    }, 500);
  };

  const validateCardNr = (nr: string): boolean => {
    if (!nr || !selectedSet?.max_card_nr) return true;
    if (!nr.match(/^(\d{1,4})\/(\d{1,4})$/)) {
      setCardNrError(t.form_card_nr_invalid(selectedSet.max_card_nr));
      return false;
    }
    setCardNrError(null);
    return true;
  };

  const handleSetChange = (setEdition: string, s: PokemonSet | null) => {
    setForm((f) => ({ ...f, set_edition: setEdition || null } as T));
    setSelectedSet(s);
    setCardNrError(null);
  };

  return {
    selectedSet,
    cardNrError,
    setCardNrError,
    nameLoading,
    noteManualEdit,
    handlePokedexNr,
    validateCardNr,
    handleSetChange,
  };
}
