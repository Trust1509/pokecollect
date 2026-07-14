"use client";
import { useEffect, useId, useRef, useState } from "react";
import { RARITY_MAP } from "@/components/RarityBadge";

function PromoSymbol({ size = 28 }: { size?: number }) {
  const star = "M50,5 L61.8,33.8 L92.8,36.1 L69,56.2 L76.4,86.4 L50,70 L23.6,86.4 L31,56.2 L7.2,36.1 L38.2,33.8 Z";
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className="inline-block shrink-0">
      <path d={star} fill="white" transform="scale(1.08) translate(-4,-4)" />
      <path d={star} fill="black" />
      <text x="50" y="56" textAnchor="middle" dominantBaseline="middle"
        fill="white" fontSize="19" fontWeight="900"
        fontFamily="Arial Black, Arial, sans-serif" letterSpacing="0.5">
        PROMO
      </text>
    </svg>
  );
}

const EASTERN = new Set(["JP", "CN"]);

type Props = {
  value: string | null | undefined;
  onChange: (val: string | null) => void;
  options: string[];
  language?: string | null;
  label?: string;
};

export default function RaritySelect({ value, onChange, options, language, label }: Props) {
  const id = useId();
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

  const isPromo = (rarity: string) => !isEastern && rarity === "Promo";

  const getSymbol = (rarity: string) => {
    if (isPromo(rarity)) return null; // SVG rendert separat
    const def = RARITY_MAP[rarity];
    if (!def) return "";
    return (isEastern && def.jpCode) ? def.jpCode : def.symbol;
  };

  const getCls = (rarity: string) => RARITY_MAP[rarity]?.cls ?? "text-gray-400";

  const selected = value ?? "";

  return (
    <div ref={wrapRef} className="relative">
      {label && <label htmlFor={id} className="text-gray-400 text-xs block mb-1">{label}</label>}

      {/* Trigger */}
      <button
        id={id}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-left text-sm flex items-center gap-2 hover:border-gray-500"
      >
        {selected ? (
          <>
            <span className="w-8 flex items-center justify-center shrink-0">
              {isPromo(selected)
                ? <PromoSymbol size={22} />
                : <span className={`text-base leading-none ${getCls(selected)}`} style={RARITY_MAP[selected]?.style}>{getSymbol(selected)}</span>
              }
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
                <span className="w-10 flex items-center justify-center shrink-0">
                  {isPromo(rarity)
                    ? <PromoSymbol size={30} />
                    : sym
                      ? <span className={`text-lg leading-none font-medium ${cls}`} style={RARITY_MAP[rarity]?.style}>{sym}</span>
                      : <span className="text-gray-600 text-xs">—</span>
                  }
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
