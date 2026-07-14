"use client";
import { useId } from "react";
import { PokemonSet } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import RaritySelect from "@/components/RaritySelect";

// Gemeinsame Feld-Bausteine für die Karten-Formulare (Neuanlage + Detail-Edit,
// Issue #5). `dense` ist die kompaktere Variante der Detailseite (py-1,
// Label ohne Abstand) — die Neuanlage nutzt die Standard-Variante.

const labelCls = (dense?: boolean) =>
  dense ? "text-gray-500 text-xs block" : "text-gray-400 text-xs block mb-1";

const inputCls = (dense?: boolean, error?: boolean) =>
  `w-full bg-gray-800 border rounded px-2 ${dense ? "py-1" : "py-1.5"} text-white text-sm ${
    error ? "border-red-500" : "border-gray-700"
  }`;

export function TextField({ label, value, onChange, type = "text", dense }: {
  label: string;
  value: unknown;
  onChange: (v: string | number | null) => void;
  type?: "text" | "number";
  dense?: boolean;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className={labelCls(dense)}>{label}</label>
      <input
        id={id}
        type={type}
        value={String(value ?? "")}
        onChange={(e) => onChange(type === "number" ? Number(e.target.value) || null : e.target.value)}
        className={inputCls(dense)}
      />
    </div>
  );
}

export function SelectField({ fieldKey, label, value, onChange, options, language, dense }: {
  fieldKey: string;
  label: string;
  value: unknown;
  onChange: (v: string | null) => void;
  options: string[];
  language?: string | null;
  dense?: boolean;
}) {
  const id = useId();
  // Seltenheit bekommt den Symbol-Picker statt eines nackten Selects
  if (fieldKey === "seltenheit") {
    return (
      <RaritySelect
        label={label}
        value={String(value ?? "")}
        onChange={onChange}
        options={options}
        language={language ?? null}
      />
    );
  }
  return (
    <div>
      <label htmlFor={id} className={labelCls(dense)}>{label}</label>
      <select
        id={id}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value || null)}
        className={inputCls(dense)}
      >
        <option value="">–</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

export function TextareaField({ label, value, onChange, dense }: {
  label: string;
  value: unknown;
  onChange: (v: string) => void;
  dense?: boolean;
}) {
  const id = useId();
  return (
    <div className="col-span-2">
      <label htmlFor={id} className={labelCls(dense)}>{label}</label>
      <textarea
        id={id}
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        className={inputCls(dense)}
      />
    </div>
  );
}

/** Pokédex-Nr. mit Lade-Indikator für den Namens-Lookup. */
export function PokedexNrField({ value, onChange, nameLoading, dense }: {
  value: unknown;
  onChange: (nr: number | null) => void;
  nameLoading: boolean;
  dense?: boolean;
}) {
  const { t } = useI18n();
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className={labelCls(dense)}>
        {t.form_pokedex_nr}
        {nameLoading && <span className="ml-2 text-gray-500 animate-pulse">…</span>}
      </label>
      <input
        id={id}
        type="number"
        value={String(value ?? "")}
        onChange={(e) => onChange(Number(e.target.value) || null)}
        className={inputCls(dense)}
      />
    </div>
  );
}

/** Karten-Nr. mit Format-Hinweis + Validierungsfehler aus useCardForm. */
export function CardNrField({ value, onChange, validate, selectedSet, error, dense }: {
  value: unknown;
  onChange: (v: string) => void;
  validate: (v: string) => boolean;
  selectedSet: PokemonSet | null;
  error: string | null;
  dense?: boolean;
}) {
  const { t } = useI18n();
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className={labelCls(dense)}>{t.form_card_nr}</label>
      <input
        id={id}
        type="text"
        value={String(value ?? "")}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => validate(e.target.value)}
        placeholder={selectedSet?.max_card_nr ? `001/${String(selectedSet.max_card_nr).padStart(3, "0")}` : t.form_card_nr_placeholder}
        className={inputCls(dense, !!error)}
      />
      {selectedSet?.max_card_nr && !error && (
        <p className={`text-gray-500 text-xs ${dense ? "mt-0.5" : "mt-1"}`}>
          {t.form_card_nr_hint(selectedSet.max_card_nr)}
        </p>
      )}
      {error && <p className={`text-red-400 text-xs ${dense ? "mt-0.5" : "mt-1"}`}>{error}</p>}
    </div>
  );
}
