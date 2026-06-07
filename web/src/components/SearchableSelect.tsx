"use client";
import { useEffect, useMemo, useRef, useState } from "react";

export type SelectOption = {
  value: string;
  label: string;
  group?: string | null;
  image?: string | null;
};

type Props = {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  allLabel?: string;       // Eintrag für „alle/keine Auswahl" (value "")
  className?: string;
};

/** Durchsuchbares Dropdown mit optionaler Gruppierung + kleinem Logo je Option. */
export default function SearchableSelect({ value, onChange, options, placeholder, allLabel, className }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const selected = options.find((o) => o.value === value) || null;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options;
    return options.filter((o) =>
      o.label.toLowerCase().includes(q) ||
      o.value.toLowerCase().includes(q) ||
      (o.group ?? "").toLowerCase().includes(q)
    );
  }, [options, query]);

  // nach Gruppe ordnen (Gruppen in Reihenfolge des ersten Auftretens)
  const groups = useMemo(() => {
    const map = new Map<string, SelectOption[]>();
    for (const o of filtered) {
      const g = o.group ?? "";
      if (!map.has(g)) map.set(g, []);
      map.get(g)!.push(o);
    }
    return Array.from(map.entries());
  }, [filtered]);

  const pick = (v: string) => { onChange(v); setOpen(false); setQuery(""); };

  return (
    <div ref={wrapRef} className={`relative ${className ?? ""}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm text-left"
      >
        {selected?.image && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={selected.image} alt="" className="h-4 w-auto max-w-[48px] object-contain shrink-0" />
        )}
        <span className="truncate flex-1">{selected ? selected.label : (allLabel ?? placeholder ?? "–")}</span>
        <span className="text-gray-500 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full bg-gray-900 border border-gray-700 rounded shadow-xl max-h-80 overflow-hidden flex flex-col">
          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder ?? "Suchen …"}
            className="m-2 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
          />
          <ul className="overflow-y-auto">
            {allLabel !== undefined && (
              <li
                onClick={() => pick("")}
                className="px-3 py-2 text-sm text-gray-400 hover:bg-gray-800 cursor-pointer border-b border-gray-800"
              >
                {allLabel}
              </li>
            )}
            {groups.map(([g, opts]) => (
              <li key={g || "_"}>
                {g && <div className="px-3 pt-2 pb-1 text-[11px] uppercase tracking-wide text-gray-500">{g}</div>}
                <ul>
                  {opts.map((o) => (
                    <li
                      key={o.value}
                      onClick={() => pick(o.value)}
                      className={`px-3 py-2 flex items-center gap-2 cursor-pointer hover:bg-gray-800 ${o.value === value ? "bg-gray-800" : ""}`}
                    >
                      {o.image ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={o.image} alt="" className="h-5 w-auto max-w-[56px] object-contain shrink-0" />
                      ) : null}
                      <span className="text-white text-sm truncate">{o.label}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
            {!filtered.length && <li className="px-3 py-3 text-gray-500 text-sm">—</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
