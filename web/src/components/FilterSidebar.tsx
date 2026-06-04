"use client";
import { Enums } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export type Filters = {
  besessen?: boolean;
  generation?: number;
  set?: string;
  seltenheit?: string;
  sprache?: string;
  search?: string;
  sort?: string;
  bild_status?: string;
};

type Props = {
  filters: Filters;
  onChange: (f: Filters) => void;
  enums: Enums | null;
  sets: string[];
};

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export default function FilterSidebar({ filters, onChange, enums, sets }: Props) {
  const { t } = useI18n();
  const update = (key: keyof Filters, value: unknown) =>
    onChange({ ...filters, [key]: value === "" ? undefined : value });

  return (
    <aside className="w-56 shrink-0 space-y-5 text-sm">
      <div>
        <label className="block text-gray-400 mb-1">{t.filter_search}</label>
        <input
          type="text"
          value={filters.search ?? ""}
          onChange={(e) => update("search", e.target.value)}
          placeholder={t.filter_search_placeholder}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_status}</label>
        <select
          value={filters.besessen === undefined ? "" : String(filters.besessen)}
          onChange={(e) => update("besessen", e.target.value === "" ? undefined : e.target.value === "true")}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all_cards}</option>
          <option value="true">{t.filter_owned}</option>
          <option value="false">{t.filter_not_owned}</option>
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_generation}</label>
        <select
          value={filters.generation ?? ""}
          onChange={(e) => update("generation", e.target.value ? Number(e.target.value) : "")}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all}</option>
          {GENERATIONS.map((g) => (
            <option key={g} value={g}>Gen {g}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_set}</label>
        <select
          value={filters.set ?? ""}
          onChange={(e) => update("set", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all_sets}</option>
          {sets.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_rarity}</label>
        <select
          value={filters.seltenheit ?? ""}
          onChange={(e) => update("seltenheit", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all}</option>
          {(enums?.seltenheit ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_language}</label>
        <select
          value={filters.sprache ?? ""}
          onChange={(e) => update("sprache", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all}</option>
          {(enums?.sprache ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_image}</label>
        <select
          value={filters.bild_status ?? ""}
          onChange={(e) => update("bild_status", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">{t.filter_all}</option>
          <option value="eigenes_foto">{t.filter_own_photo}</option>
          <option value="externe_url">{t.filter_external_url}</option>
          <option value="platzhalter">{t.filter_placeholder_only}</option>
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">{t.filter_sort}</label>
        <select
          value={filters.sort ?? "pokedex_nr"}
          onChange={(e) => update("sort", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="pokedex_nr">{t.filter_sort_pokedex}</option>
          <option value="wert">{t.filter_sort_value}</option>
          <option value="hinzugefuegt_am">{t.filter_sort_added}</option>
        </select>
      </div>

      <button
        onClick={() => onChange({})}
        className="w-full text-gray-400 hover:text-white text-xs underline"
      >
        {t.filter_reset}
      </button>
    </aside>
  );
}
