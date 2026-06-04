"use client";

// Sprachen die JP/CN-Codes statt grafische Symbole verwenden
const EASTERN = new Set(["JP", "CN"]);

type RarityDef = {
  symbol: string;   // DE/EN grafisches Symbol (Unicode)
  cls: string;      // Tailwind-Klassen
  jpCode: string;   // JP/CN Text-Code
};

export const RARITY_MAP: Record<string, RarityDef> = {
  "Common":                    { symbol: "●",     cls: "text-gray-400",                                                                      jpCode: "C"     },
  "Uncommon":                  { symbol: "◆",     cls: "text-gray-300",                                                                      jpCode: "U"     },
  "Rare":                      { symbol: "★",     cls: "text-gray-100",                                                                      jpCode: "R"     },
  "Double Rare":               { symbol: "★★",    cls: "text-gray-100",                                                                      jpCode: "RR"    },
  "Ultra Rare":                { symbol: "★★",    cls: "text-white bg-gray-900 rounded px-0.5 leading-none",                                 jpCode: "SR"    },
  "Illustration Rare":         { symbol: "★",     cls: "text-yellow-400",                                                                    jpCode: "AR"    },
  "Special Illustration Rare": { symbol: "★★",    cls: "text-yellow-400",                                                                    jpCode: "SAR"   },
  "Hyper Rare":                { symbol: "★★★",   cls: "text-yellow-400",                                                                    jpCode: "UR"    },
  "Mega Hyper Rare":           { symbol: "✦",     cls: "text-yellow-400",                                                                    jpCode: "MUR"   },
  "ACE SPEC Rare":             { symbol: "★",     cls: "text-pink-400",                                                                      jpCode: "ACE"   },
  "Shiny Rare":                { symbol: "☆",     cls: "text-yellow-400",                                                                    jpCode: "S"     },
  "Shiny Ultra Rare":          { symbol: "☆☆",    cls: "text-yellow-400",                                                                    jpCode: "SSR"   },
  "Rainbow Rare":              { symbol: "★",     cls: "bg-gradient-to-r from-red-400 via-yellow-300 to-blue-400 bg-clip-text text-transparent", jpCode: ""  },
  "Secret Rare":               { symbol: "",      cls: "",                                                                                   jpCode: ""      },
  "Promo":                     { symbol: "PROMO", cls: "text-purple-400 font-bold tracking-tight",                                           jpCode: "PROMO" },
  // Legacy-Werte (noch in der DB, nicht mehr im Dropdown)
  "Holo Rare":                 { symbol: "★",     cls: "text-gray-100",                                                                      jpCode: "R"     },
  "Full Art":                  { symbol: "★★",    cls: "text-white bg-gray-900 rounded px-0.5 leading-none",                                 jpCode: "SR"    },
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
  const display = isEastern && def.jpCode ? def.jpCode : def.symbol;
  if (!display) return null;

  const textSize = size === "xs" ? "text-xs" : "text-sm";

  return (
    <span
      className={`inline-block leading-none font-medium ${textSize} ${def.cls}`}
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
