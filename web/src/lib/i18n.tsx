"use client";
import { createContext, useContext, useState, ReactNode } from "react";

export type Lang = "DE" | "EN";

const DE = {
  // Navbar
  nav_collection: "Sammlung",
  nav_statistics: "Statistiken",
  nav_settings: "Einstellungen",
  nav_add_card: "+ Karte",

  // HomePage
  home_collected: "Gesammelt",
  home_total_value: "Gesamtwert",
  home_cards_count: (n: number) => `${n} Karten`,

  // FilterSidebar
  filter_search: "Suche",
  filter_search_placeholder: "Name oder Pokédex-Nr. …",
  filter_status: "Status",
  filter_all_cards: "Alle Karten",
  filter_owned: "Besessen ✓",
  filter_not_owned: "Nicht besessen",
  filter_generation: "Generation",
  filter_all: "Alle",
  filter_set: "Set",
  filter_all_sets: "Alle Sets",
  filter_rarity: "Seltenheit",
  filter_language: "Sprache",
  filter_image: "Bild",
  filter_own_photo: "📷 Eigenes Foto",
  filter_external_url: "🔗 Externe URL",
  filter_placeholder_only: "🔲 Nur Platzhalter",
  filter_sort: "Sortierung",
  filter_sort_pokedex: "Pokédex-Nr.",
  filter_sort_value: "Wert",
  filter_sort_added: "Hinzugefügt",
  filter_reset: "Filter zurücksetzen",

  // CardForm (new + edit)
  form_new_card: "Neue Karte",
  form_card_name: "Kartenname",
  form_card_name_required: "Kartenname ist Pflichtfeld",
  form_pokedex_nr: "Pokédex-Nr.",
  form_english_name: "Englischer Name",
  form_set: "Set / Edition",
  form_set_code: "Set-Kürzel",
  form_set_name: "Set-Name",
  form_set_search_placeholder: "Kürzel oder Name …",
  form_set_new: "Neues Set anlegen",
  form_set_add: "Set anlegen",
  form_card_nr: "Karten-Nr.",
  form_card_nr_hint: (max: number) => `Format: NNN/${String(max).padStart(3, "0")} — höhere Nummern (Secret Rare etc.) sind erlaubt`,
  form_card_nr_invalid: (_max: number) => `Ungültiges Format. Erwartet: NNN/MAX (z.B. 001/091 oder 092/091 für Secret Rare)`,
  form_rarity: "Seltenheit",
  form_card_version: "Kartenversion",
  form_foiling: "Folierung",
  form_language: "Sprache",
  form_condition: "Zustand",
  form_owned: "Besessen (physisch vorhanden)",
  form_notes: "Notizen",
  form_save: "Speichern",
  form_cancel: "Abbrechen",
  form_saved: "Karte gespeichert",
  form_save_error: "Fehler beim Speichern",
  form_back: "← Sammlung",

  // CardDetailPage
  detail_loading: "Lädt …",
  detail_edit: "Bearbeiten",
  detail_delete: "Löschen",
  detail_delete_confirm: (name: string) => `"${name}" wirklich löschen?`,
  detail_upload_photo: "📷 Foto hochladen",
  detail_replace_photo: "📷 Foto austauschen",
  detail_set_url: "🔗 Bild-URL hinterlegen",
  detail_change_url: "🔗 Bild-URL ändern",
  detail_delete_photo: "Foto löschen",
  detail_delete_url: "Bild-URL löschen",
  detail_delete_photo_confirm: "Foto wirklich löschen? Der Pokédex-Platzhalter wird dann angezeigt.",
  detail_delete_url_confirm: "Bild-URL löschen? Der Pokédex-Platzhalter wird dann angezeigt.",
  detail_photo_saved: "Foto gespeichert",
  detail_upload_error: "Upload fehlgeschlagen",
  detail_url_saved: "Bild-URL gespeichert",
  detail_url_save_error: "Speichern fehlgeschlagen",
  detail_url_deleted: "Bild-URL gelöscht",
  detail_delete_error: "Löschen fehlgeschlagen",
  detail_price_history: "Preisverlauf",
  detail_value_label: "Wert (Cardmarket 30-Tage-Ø)",
  detail_value_updated: "Aktualisiert",
  detail_placeholder: "Pokédex-Platzhalter",
  detail_no_image: "Kein Bild",
  detail_saved: "Gespeichert",

  // Field labels
  field_card_name: "Kartenname",
  field_pokedex_nr: "Pokédex-Nr.",
  field_english_name: "Englischer Name",
  field_set: "Set/Edition",
  field_card_nr: "Karten-Nr.",
  field_rarity: "Seltenheit",
  field_card_version: "Kartenversion",
  field_foiling: "Folierung",
  field_language: "Sprache",
  field_condition: "Zustand",
  field_owned: "Besessen",
  field_notes: "Notizen",
  field_yes: "✓ Ja",
  field_no: "✗ Nein",
};

const EN: typeof DE = {
  nav_collection: "Collection",
  nav_statistics: "Statistics",
  nav_settings: "Settings",
  nav_add_card: "+ Card",

  home_collected: "Collected",
  home_total_value: "Total Value",
  home_cards_count: (n: number) => `${n} cards`,

  filter_search: "Search",
  filter_search_placeholder: "Name or Pokédex no. …",
  filter_status: "Status",
  filter_all_cards: "All cards",
  filter_owned: "Owned ✓",
  filter_not_owned: "Not owned",
  filter_generation: "Generation",
  filter_all: "All",
  filter_set: "Set",
  filter_all_sets: "All sets",
  filter_rarity: "Rarity",
  filter_language: "Language",
  filter_image: "Image",
  filter_own_photo: "📷 Own photo",
  filter_external_url: "🔗 External URL",
  filter_placeholder_only: "🔲 Placeholder only",
  filter_sort: "Sort",
  filter_sort_pokedex: "Pokédex no.",
  filter_sort_value: "Value",
  filter_sort_added: "Date added",
  filter_reset: "Reset filters",

  form_new_card: "New Card",
  form_card_name: "Card name",
  form_card_name_required: "Card name is required",
  form_pokedex_nr: "Pokédex no.",
  form_english_name: "English name",
  form_set: "Set / Edition",
  form_set_code: "Set code",
  form_set_name: "Set name",
  form_set_search_placeholder: "Code or name …",
  form_set_new: "Add new set",
  form_set_add: "Add set",
  form_card_nr: "Card no.",
  form_card_nr_hint: (max: number) => `Format: NNN/${String(max).padStart(3, "0")} — higher numbers (Secret Rare etc.) are allowed`,
  form_card_nr_invalid: (_max: number) => `Invalid format. Expected: NNN/MAX (e.g. 001/091 or 092/091 for Secret Rare)`,
  form_rarity: "Rarity",
  form_card_version: "Card version",
  form_foiling: "Foiling",
  form_language: "Language",
  form_condition: "Condition",
  form_owned: "Owned (physically present)",
  form_notes: "Notes",
  form_save: "Save",
  form_cancel: "Cancel",
  form_saved: "Card saved",
  form_save_error: "Error saving",
  form_back: "← Collection",

  detail_loading: "Loading …",
  detail_edit: "Edit",
  detail_delete: "Delete",
  detail_delete_confirm: (name: string) => `Really delete "${name}"?`,
  detail_upload_photo: "📷 Upload photo",
  detail_replace_photo: "📷 Replace photo",
  detail_set_url: "🔗 Set image URL",
  detail_change_url: "🔗 Change image URL",
  detail_delete_photo: "Delete photo",
  detail_delete_url: "Delete image URL",
  detail_delete_photo_confirm: "Really delete photo? The Pokédex placeholder will be shown.",
  detail_delete_url_confirm: "Delete image URL? The Pokédex placeholder will be shown.",
  detail_photo_saved: "Photo saved",
  detail_upload_error: "Upload failed",
  detail_url_saved: "Image URL saved",
  detail_url_save_error: "Save failed",
  detail_url_deleted: "Image URL deleted",
  detail_delete_error: "Delete failed",
  detail_price_history: "Price history",
  detail_value_label: "Value (Cardmarket 30-day avg)",
  detail_value_updated: "Updated",
  detail_placeholder: "Pokédex placeholder",
  detail_no_image: "No image",
  detail_saved: "Saved",

  field_card_name: "Card name",
  field_pokedex_nr: "Pokédex no.",
  field_english_name: "English name",
  field_set: "Set/Edition",
  field_card_nr: "Card no.",
  field_rarity: "Rarity",
  field_card_version: "Card version",
  field_foiling: "Foiling",
  field_language: "Language",
  field_condition: "Condition",
  field_owned: "Owned",
  field_notes: "Notes",
  field_yes: "✓ Yes",
  field_no: "✗ No",
};

const translations: Record<Lang, typeof DE> = { DE, EN };

type I18nCtx = { lang: Lang; t: typeof DE; setLang: (l: Lang) => void };

const I18nContext = createContext<I18nCtx>({
  lang: "DE",
  t: DE,
  setLang: () => {},
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const stored = typeof window !== "undefined" ? (localStorage.getItem("lang") as Lang | null) : null;
  const [lang, setLangState] = useState<Lang>(stored ?? "DE");

  const setLang = (l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem("lang", l);
  };

  return (
    <I18nContext.Provider value={{ lang, t: translations[lang], setLang }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  return useContext(I18nContext);
}
