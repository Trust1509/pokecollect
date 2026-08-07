"use client";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Card, Enums, PokemonSet, cardApi } from "@/lib/api";
import RarityBadge from "@/components/RarityBadge";
import FirstEditionBadge from "@/components/FirstEditionBadge";
import SetPicker from "@/components/SetPicker";
import { CardNrField, CurrencyField, DateField, PokedexNrField, SelectField, TextareaField, TextField } from "@/components/CardFormFields";
import { useCardForm } from "@/lib/useCardForm";
import { formatEur } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { fetchPokemonNames, PokemonNames } from "@/lib/pokedex";

// Detail-/Edit-Spalte der Kartendetailseite (Issue #14): Anzeige aller Felder,
// Edit-Modus über die gemeinsame Formular-Logik (CardFormFields/useCardForm,
// Issue #5). Herausgeschnitten aus cards/[id]/page.tsx — Verhalten 1:1.
// Das Formular (form/setForm) bleibt in der Seite, weil Quick-Aktionen
// (Pokédex-Flag, Wunschliste, Bild-URL) es ebenfalls synchronisieren.

type Props = {
  card: Card;
  form: Partial<Card>;
  setForm: Dispatch<SetStateAction<Partial<Card>>>;
  enums: Enums | null;
  sets: PokemonSet[];
  /** Nach Set-Neuanlage im SetPicker den geteilten Set-Cache neu laden. */
  onSetsRefresh: () => void;
  onCardUpdated: (card: Card) => void;
  onDelete: () => void;
};

export default function EditForm({
  card, form, setForm, enums, sets, onSetsRefresh, onCardUpdated, onDelete,
}: Props) {
  const { t } = useI18n();
  const [editing, setEditing] = useState(false);
  // Pokémon-Artname (DE/EN) aus der Pokédex-Nr. (PokéAPI, gecacht) — gibt auch
  // JP-Karten ohne DE/EN-Kartennamen einen Identifikator, konsistent zum Katalog.
  const [species, setSpecies] = useState<PokemonNames | null>(null);
  useEffect(() => {
    let alive = true;
    setSpecies(null);
    if (card.pokedex_nr) fetchPokemonNames(card.pokedex_nr).then((n) => { if (alive) setSpecies(n); });
    return () => { alive = false; };
  }, [card.pokedex_nr]);
  // Gemeinsame Formular-Logik (Lookup, Validierung, Set-Auswahl) — Issue #5
  const {
    selectedSet, cardNrError, setCardNrError, nameLoading,
    noteManualEdit, handlePokedexNr, validateCardNr, handleSetChange,
  } = useCardForm(setForm);

  const handleSave = async () => {
    const nr = (form as Record<string, unknown>).karten_nr as string | undefined;
    if (nr && !validateCardNr(nr)) return;
    try {
      const r = await cardApi.update(card.id, form);
      onCardUpdated(r.data);
      setEditing(false);
      toast.success(t.detail_saved);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  const field = (key: keyof Card, label: string, type: "text" | "number" | "select" | "boolean" | "textarea" = "text", options?: string[]) => {
    const value = (form as Record<string, unknown>)[key];
    if (!editing) {
      return (
        <div key={key}>
          <dt className="text-gray-500 text-xs">{label}</dt>
          <dd className="text-white">
            {type === "boolean" ? (value ? t.field_yes : t.field_no) : (String(value ?? "–"))}
          </dd>
        </div>
      );
    }
    if (type === "select" && options) {
      return (
        <SelectField
          key={key}
          fieldKey={key}
          label={label}
          value={value}
          onChange={(v) => setForm((f) => ({ ...f, [key]: v }))}
          options={options}
          language={(form as Record<string, unknown>).sprache as string | null}
          dense
        />
      );
    }
    if (type === "boolean") {
      return (
        <div key={key}>
          <label htmlFor={`field_${key}`} className="text-gray-500 text-xs block">{label}</label>
          <input
            id={`field_${key}`}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))}
            className="mt-1"
          />
        </div>
      );
    }
    if (type === "textarea") {
      return (
        <TextareaField
          key={key}
          label={label}
          value={value}
          onChange={(v) => setForm((f) => ({ ...f, [key]: v }))}
          dense
        />
      );
    }
    return (
      <TextField
        key={key}
        label={label}
        value={value}
        type={type as "text" | "number"}
        onChange={(v) => { noteManualEdit(key); setForm((f) => ({ ...f, [key]: v })); }}
        dense
      />
    );
  };

  // Unrealisierter G/V = aktueller Wert − Kaufpreis (nur wenn beide gesetzt), #26
  const kp = card.kaufpreis_eur != null ? parseFloat(card.kaufpreis_eur) : null;
  const wv = card.wert_eur != null ? parseFloat(card.wert_eur) : null;
  const gv = kp != null && wv != null ? wv - kp : null;
  const gvPct = gv != null && kp && kp !== 0 ? (gv / kp) * 100 : null;

  return (
    <div className="flex-1">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2 flex-wrap">
            {card.kartenname}
            {card.erste_edition && <FirstEditionBadge className="align-middle" />}
          </h1>
          {card.pokedex_nr && (
            <p className="text-gray-400">#{String(card.pokedex_nr).padStart(4, "0")} · {card.englischer_name || species?.en || ""}</p>
          )}
        </div>
        <div className="flex gap-2">
          {editing ? (
            <>
              <button type="button" onClick={handleSave} className="bg-green-600 text-white text-sm px-3 py-1.5 rounded hover:bg-green-700">{t.form_save}</button>
              <button type="button" onClick={() => { setEditing(false); setForm(card); setCardNrError(null); }} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded">{t.form_cancel}</button>
            </>
          ) : (
            <button type="button" onClick={() => setEditing(true)} className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700">{t.detail_edit}</button>
          )}
          {card.besessen && (
            <button type="button" onClick={onDelete} className="bg-red-900 text-red-300 text-sm px-3 py-1.5 rounded hover:bg-red-800">{t.detail_delete}</button>
          )}
        </div>
      </div>

      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        {field("kartenname", t.field_card_name)}
        {/* Pokédex-Nr. mit Auto-Namens-Lookup */}
        {editing ? (
          <PokedexNrField
            key="pokedex_nr"
            value={(form as Record<string, unknown>).pokedex_nr}
            onChange={handlePokedexNr}
            nameLoading={nameLoading}
            dense
          />
        ) : (
          <div key="pokedex_nr">
            <dt className="text-gray-500 text-xs">{t.field_pokedex_nr}</dt>
            <dd className="text-white">{String(card.pokedex_nr ?? "–")}</dd>
          </div>
        )}
        {field("englischer_name", t.field_english_name)}
        {species && (
          <div key="species">
            <dt className="text-gray-500 text-xs">{t.catalog_species}</dt>
            <dd className="text-white">{species.de} / {species.en}</dd>
          </div>
        )}

        {/* Set/Edition: im Edit-Modus SetPicker, sonst normales Feld */}
        {editing ? (
          <div className="col-span-2">
            <SetPicker
              value={String((form as Record<string, unknown>).set_edition ?? "")}
              onChange={handleSetChange}
              sets={sets}
              onSetAdded={() => onSetsRefresh()}
            />
          </div>
        ) : (
          <div>
            <dt className="text-gray-500 text-xs">{t.field_set}</dt>
            <dd className="text-white">{String(card.set_edition ?? "–")}</dd>
          </div>
        )}

        {/* Karten-Nr. mit Hinweis im Edit-Modus */}
        {editing ? (
          <CardNrField
            value={(form as Record<string, unknown>).karten_nr}
            onChange={(v) => { setForm((f) => ({ ...f, karten_nr: v })); setCardNrError(null); }}
            validate={validateCardNr}
            selectedSet={selectedSet}
            error={cardNrError}
            dense
          />
        ) : (
          <div>
            <dt className="text-gray-500 text-xs">{t.field_card_nr}</dt>
            <dd className="text-white">{String(card.karten_nr ?? "–")}</dd>
          </div>
        )}

        {editing ? (
          field("seltenheit", t.field_rarity, "select", enums?.seltenheit)
        ) : (
          <div key="seltenheit">
            <dt className="text-gray-500 text-xs">{t.field_rarity}</dt>
            <dd className="text-white flex items-center gap-2">
              {card.seltenheit ?? "–"}
              {card.seltenheit && (
                <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
              )}
            </dd>
          </div>
        )}
        {field("kartenversion", t.field_card_version, "select", enums?.kartenversion)}
        {field("folierung", t.field_foiling, "select", enums?.folierung)}
        {field("sprache", t.field_language, "select", enums?.sprache)}
        {field("zustand", t.field_condition, "select", enums?.zustand)}
        {field("besessen", t.field_owned, "boolean")}
        {field("erste_edition", t.first_edition_label, "boolean")}
        {/* Kaufpreis + Kaufdatum nur im Edit-Modus; die Anzeige läuft über den
            G/V-Kasten unten (Kaufpreis / aktueller Wert / G/V), Issue #26 */}
        {editing && (
          <CurrencyField
            key="kaufpreis_eur"
            label={t.form_purchase_price}
            value={(form as Record<string, unknown>).kaufpreis_eur}
            onChange={(v) => setForm((f) => ({ ...f, kaufpreis_eur: v }))}
            dense
          />
        )}
        {editing && (
          <DateField
            key="kaufdatum"
            label={t.form_purchase_date}
            value={(form as Record<string, unknown>).kaufdatum}
            onChange={(v) => setForm((f) => ({ ...f, kaufdatum: v }))}
            dense
          />
        )}
        {card.illustrator && (
          <div key="illustrator">
            <dt className="text-gray-500 text-xs">{t.field_illustrator}</dt>
            <dd className="text-white">{card.illustrator}</dd>
          </div>
        )}
        {field("notizen", t.field_notes, "textarea")}
      </dl>

      {(card.wert_eur != null || card.kaufpreis_eur != null) && (
        <div className="mt-4 p-3 bg-pokemon-card rounded-lg space-y-1.5">
          {card.kaufpreis_eur != null && (
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-gray-400">{t.detail_purchase_price}</span>
              <span className="text-white">
                {formatEur(card.kaufpreis_eur)}
                {card.kaufdatum && (
                  <span className="text-gray-500 text-xs ml-1">
                    · {new Date(card.kaufdatum).toLocaleDateString(t.date_locale)}
                  </span>
                )}
              </span>
            </div>
          )}
          {card.wert_eur != null && (
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-gray-400">{t.detail_current_value}</span>
              <span className="text-yellow-400 font-bold">{formatEur(card.wert_eur)}</span>
            </div>
          )}
          {gv != null && (
            <div className="flex items-baseline justify-between text-sm border-t border-gray-700 pt-1.5">
              <span className="text-gray-400">{t.detail_gain_loss}</span>
              <span className={`font-bold ${gv >= 0 ? "text-green-400" : "text-red-400"}`}>
                {gv > 0 ? "+" : ""}{formatEur(gv.toFixed(2))}
                {gvPct != null && (
                  <span className="text-xs font-normal ml-1">
                    ({gvPct > 0 ? "+" : ""}{gvPct.toFixed(0)}%)
                  </span>
                )}
              </span>
            </div>
          )}
          {card.wert_eur != null && (
            <div className="text-gray-500 text-xs pt-0.5">
              {t.detail_value_label}
              {card.wert_aktualisiert && (
                <> · {t.detail_value_updated}: {new Date(card.wert_aktualisiert).toLocaleDateString(t.date_locale)}</>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
