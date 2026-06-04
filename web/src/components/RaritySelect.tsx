"use client";
import { useEffect, useRef, useState } from "react";
import { RARITY_MAP } from "@/components/RarityBadge";

const EASTERN = new Set(["JP", "CN"]);

type Props = {
  value: string | null | undefined;
  onChange: (val: string | null) => void;
  options: string[];
  language?: string | null;
  label?: string;
};

export default function RaritySelect({ value, onChange, options, language, label }: Props) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const isEastern = language ? EASTERN.has(language) : false;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const getSymbol = (rarity: string) => {
    const def = RARITY_MAP[rarity];
    if (!def) return "";
    return (isEastern && def.jpCode) ? def.jpCode : def.symbol;
  };

  const getCls = (rarity: string) => RARITY_MAP[rarity]?.cls ?? "text-gray-400";

  const selected = value ?? "";

  return (
    <div ref={wrapRef} className="relative">
      {label && <label className="text-gray-400 text-xs block mb-1">{label}</label>}

      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-left text-sm flex items-center gap-2 hover:border-gray-500"
      >
        {selected ? (
          <>
            <span className={`text-base w-8 text-center leading-none ${getCls(selected)}`}>
              {getSymbol(selected)}
            </span>
            <span className="text-white">{selected}</span>
          </>
        ) : (
          <span className="text-gray-500">–</span>
        )}
        <span className="ml-auto text-gray-500 text-xs">{open ? "▲" : "▼"}</span>
      </button>

      {/* Dropdown */}
      {open && (
        <ul className="absolute z-50 w-full bg-gray-900 border border-gray-700 rounded mt-1 shadow-xl max-h-72 overflow-y-auto">
          {/* Leere Option */}
          <li
            onClick={() => { onChange(null); setOpen(false); }}
            className="px-3 py-2 text-gray-500 hover:bg-gray-800 cursor-pointer text-sm border-b border-gray-800"
          >
            –
          </li>
          {options.map((rarity) => {
            const sym = getSymbol(rarity);
            const cls = getCls(rarity);
            const isSelected = rarity === selected;
            return (
              <li
                key={rarity}
                onClick={() => { onChange(rarity); setOpen(false); }}
                className={`px-3 py-2 flex items-center gap-3 cursor-pointer hover:bg-gray-800 ${isSelected ? "bg-gray-800" : ""}`}
              >
                {/* Symbol — groß und prominent */}
                <span className={`text-lg w-10 text-center leading-none font-medium shrink-0 ${cls}`}>
                  {sym || <span className="text-gray-600 text-xs">—</span>}
                </span>
                <span className="text-white text-sm">{rarity}</span>
                {isSelected && <span className="ml-auto text-green-400 text-xs">✓</span>}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
