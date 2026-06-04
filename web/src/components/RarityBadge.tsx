"use client";
import type { CSSProperties } from "react";

// Sprachen die JP/CN-Codes statt grafische Symbole verwenden
const EASTERN = new Set(["JP", "CN"]);

// Weißer Rand via 4-seitigen text-shadow (kompatibel mit allen Browsern)
const WHITE_OUTLINE: CSSProperties = {
  textShadow: "-1px -1px 0 white, 1px -1px 0 white, -1px 1px 0 white, 1px 1px 0 white",
};

function PromoSymbol({ size = 16 }: { size?: number }) {
  const star = "M50,5 L61.8,33.8 L92.8,36.1 L69,56.2 L76.4,86.4 L50,70 L23.6,86.4 L31,56.2 L7.2,36.1 L38.2,33.8 Z";
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" className="inline-block">
      {/* weißer Rand: Stern etwas größer in weiß dahinter */}
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

type RarityDef = {
  symbol: string;              // DE/EN grafisches Symbol (Unicode)
  cls: string;                 // Tailwind-Klassen
  jpCode: string;              // JP/CN Text-Code
  style?: CSSProperties;       // optionale Inline-Styles (z.B. text-shadow)
};

export const RARITY_MAP: Record<string, RarityDef> = {
  "Common":                    { symbol: "●",    cls: "text-gray-400",                                                                       jpCode: "C"     },
  "Uncommon":                  { symbol: "◆",    cls: "text-gray-300",                                                                       jpCode: "U"     },
  "Rare":                      { symbol: "★",    cls: "text-black",     style: WHITE_OUTLINE,                                                jpCode: "R"     },
  "Double Rare":               { symbol: "★★",   cls: "text-black",     style: WHITE_OUTLINE,                                                jpCode: "RR"    },
  "Ultra Rare":                { symbol: "★★",   cls: "text-white bg-gray-900 rounded px-0.5 leading-none",                                  jpCode: "SR"    },
  "Illustration Rare":         { symbol: "★",    cls: "text-yellow-400",                                                                     jpCode: "AR"    },
  "Special Illustration Rare": { symbol: "★★",   cls: "text-yellow-400",                                                                     jpCode: "SAR"   },
  "Hyper Rare":                { symbol: "★★★",  cls: "text-yellow-400",                                                                     jpCode: "UR"    },
  "Mega Hyper Rare":           { symbol: "✦",    cls: "text-yellow-400",                                                                     jpCode: "MUR"   },
  "ACE SPEC Rare":             { symbol: "★",    cls: "text-pink-400",                                                                       jpCode: "ACE"   },
  "Shiny Rare":                { symbol: "☆",    cls: "text-yellow-400",                                                                     jpCode: "S"     },
  "Shiny Ultra Rare":          { symbol: "☆☆",   cls: "text-yellow-400",                                                                     jpCode: "SSR"   },
  "Rainbow Rare":              { symbol: "★",    cls: "bg-gradient-to-r from-red-400 via-yellow-300 to-blue-400 bg-clip-text text-transparent", jpCode: ""  },
  "Secret Rare":               { symbol: "",     cls: "",                                                                                    jpCode: ""      },
  "Promo":                     { symbol: "PROMO", cls: "",                                                                                   jpCode: "PROMO" },
  // Legacy-Werte (noch in der DB, nicht mehr im Dropdown)
  "Holo Rare":                 { symbol: "★",    cls: "text-black",     style: WHITE_OUTLINE,                                                jpCode: "R"     },
  "Full Art":                  { symbol: "★★",   cls: "text-white bg-gray-900 rounded px-0.5 leading-none",                                  jpCode: "SR"    },
};

type Props = {
  rarity: string | null | undefined;
  language?: string | null;
  size?: "xs" | "sm";
  showLabel?: boolean;
};

export default function RarityBadge({ rarity, language, size = "xs", showLabel = false }: Props) {
  if (!rarity) return null;
  const def = RARITY_MAP[rarity];
  if (!def) return <span className="text-gray-500 text-xs">{rarity}</span>;

  const isEastern = language ? EASTERN.has(language) : false;
  const isPromo = !isEastern && rarity === "Promo";
  const display = isEastern && def.jpCode ? def.jpCode : def.symbol;

  if (isPromo) {
    return (
      <span className="inline-flex items-center gap-1" title={rarity}>
        <PromoSymbol size={size === "xs" ? 14 : 18} />
        {showLabel && <span className="text-gray-400 text-xs font-normal">Promo</span>}
      </span>
    );
  }

  if (!display) return null;
  const textSize = size === "xs" ? "text-xs" : "text-sm";

  return (
    <span
      className={`inline-block leading-none font-medium ${textSize} ${def.cls}`}
      style={def.style}
      title={rarity}
    >
      {display}
      {showLabel && (
        <span className="ml-1 text-gray-400 font-normal">{rarity}</span>
      )}
    </span>
  );
}

/** Für <select><option>-Elemente: gibt Symbol + Name als reinen Text zurück */
export function rarityOptionLabel(rarity: string, language?: string | null): string {
  const def = RARITY_MAP[rarity];
  if (!def) return rarity;
  const isEastern = language ? EASTERN.has(language) : false;
  const sym = isEastern && def.jpCode ? def.jpCode : def.symbol;
  return sym ? `${sym} ${rarity}` : rarity;
}
