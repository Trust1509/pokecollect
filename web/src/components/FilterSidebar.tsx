"use client";
import { useEffect, useMemo, useState } from "react";
import { Enums, PokemonSet } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { rarityOptionLabel } from "@/components/RarityBadge";
import { seriesLabel, SERIES_LABEL } from "@/lib/utils";
import SearchableSelect, { SelectOption } from "@/components/SearchableSelect";

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
  sets: PokemonSet[];
};

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export default function FilterSidebar({ filters, onChange, enums, sets }: Props) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  // Auf Desktop standardmäßig geöffnet, auf Mobile eingeklappt (nach Mount,
  // damit kein SSR-Hydration-Mismatch entsteht).
  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth >= 768) setOpen(true);
  }, []);
  const update = (key: keyof Filters, value: unknown) =>
    onChange({ ...filters, [key]: value === "" ? undefined : value });

  const activeCount = (["besessen", "generation", "set", "seltenheit", "sprache", "search", "bild_status"] as const)
    .filter((k) => filters[k] !== undefined && filters[k] !== "").length;

  const setOptions: SelectOption[] = useMemo(() => {
    const order = Object.keys(SERIES_LABEL);
    const sorted = [...sets].sort((a, b) => {
      const ag = order.indexOf(a.series_id ?? ""); const bg = order.indexOf(b.series_id ?? "");
      const av = ag === -1 ? 999 : ag; const bv = bg === -1 ? 999 : bg;
      if (av !== bv) return av - bv;
      return (a.name ?? "").localeCompare(b.name ?? "");
    });
    return sorted.map((s) => ({
      value: s.code,
      label: `${s.name}${s.code ? ` (${s.code})` : ""}`,
      group: seriesLabel(s.series_id),
      image: s.logo_url ?? null,
    }));
  }, [sets]);

  return (
    <aside className="w-full text-sm">
      {/* Filter ein-/ausklappen (Mobile + Desktop) */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between bg-pokemon-card border border-gray-700 rounded px-3 py-2 text-gray-200"
      >
        <span>🔍 {t.filter_title}{activeCount > 0 ? ` (${activeCount})` : ""}</span>
        <span className="text-gray-500">{open ? "▲" : "▼"}</span>
      </button>

      <div className={`${open ? "grid" : "hidden"} grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mt-3 items-end`}>
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
        <SearchableSelect
          value={filters.set ?? ""}
          onChange={(v) => update("set", v)}
          options={setOptions}
          allLabel={t.filter_all_sets}
          placeholder={t.filter_set}
        />
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
            <option key={s} value={s}>{rarityOptionLabel(s)}</option>
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
      </div>
    </aside>
  );
}
