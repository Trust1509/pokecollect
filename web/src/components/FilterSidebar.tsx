"use client";
import { Enums } from "@/lib/api";

export type Filters = {
  besessen?: boolean;
  generation?: number;
  set?: string;
  seltenheit?: string;
  sprache?: string;
  search?: string;
  sort?: string;
};

type Props = {
  filters: Filters;
  onChange: (f: Filters) => void;
  enums: Enums | null;
  sets: string[];
};

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export default function FilterSidebar({ filters, onChange, enums, sets }: Props) {
  const update = (key: keyof Filters, value: unknown) =>
    onChange({ ...filters, [key]: value === "" ? undefined : value });

  return (
    <aside className="w-56 shrink-0 space-y-5 text-sm">
      <div>
        <label className="block text-gray-400 mb-1">Suche</label>
        <input
          type="text"
          value={filters.search ?? ""}
          onChange={(e) => update("search", e.target.value)}
          placeholder="Name oder Pokédex-Nr. …"
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white placeholder-gray-500"
        />
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Status</label>
        <select
          value={filters.besessen === undefined ? "" : String(filters.besessen)}
          onChange={(e) => update("besessen", e.target.value === "" ? undefined : e.target.value === "true")}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">Alle Karten</option>
          <option value="true">Besessen ✓</option>
          <option value="false">Nicht besessen</option>
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Generation</label>
        <select
          value={filters.generation ?? ""}
          onChange={(e) => update("generation", e.target.value ? Number(e.target.value) : "")}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">Alle</option>
          {GENERATIONS.map((g) => (
            <option key={g} value={g}>Gen {g}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Set</label>
        <select
          value={filters.set ?? ""}
          onChange={(e) => update("set", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">Alle Sets</option>
          {sets.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Seltenheit</label>
        <select
          value={filters.seltenheit ?? ""}
          onChange={(e) => update("seltenheit", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">Alle</option>
          {(enums?.seltenheit ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Sprache</label>
        <select
          value={filters.sprache ?? ""}
          onChange={(e) => update("sprache", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="">Alle</option>
          {(enums?.sprache ?? []).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div>
        <label className="block text-gray-400 mb-1">Sortierung</label>
        <select
          value={filters.sort ?? "pokedex_nr"}
          onChange={(e) => update("sort", e.target.value)}
          className="w-full bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white"
        >
          <option value="pokedex_nr">Pokédex-Nr.</option>
          <option value="wert">Wert</option>
          <option value="hinzugefuegt_am">Hinzugefügt</option>
        </select>
      </div>

      <button
        onClick={() => onChange({})}
        className="w-full text-gray-400 hover:text-white text-xs underline"
      >
        Filter zurücksetzen
      </button>
    </aside>
  );
}
