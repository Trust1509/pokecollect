"use client";
import Image from "next/image";
import Link from "next/link";
import { Card } from "@/lib/api";
import { cardImageSrc, extractSetCode, formatEur } from "@/lib/utils";
import { rememberCardOrder } from "@/lib/cardNav";
import RarityBadge from "@/components/RarityBadge";
import { useI18n } from "@/lib/i18n";

type Props = {
  cards: Card[];
  apiBase: string;
  placeholderEnabled?: boolean;
};

const RARITY_BORDER: Record<string, string> = {
  "Common":                    "border-gray-500",
  "Uncommon":                  "border-green-500",
  "Rare":                      "border-blue-400",
  "Holo Rare":                 "border-blue-400",
  "Double Rare":               "border-indigo-400",
  "Ultra Rare":                "border-purple-500",
  "Full Art":                  "border-purple-400",
  "Secret Rare":               "border-yellow-400",
  "Illustration Rare":         "border-rose-400",
  "Special Illustration Rare": "border-orange-400",
  "Hyper Rare":                "border-amber-300",
  "Mega Hyper Rare":           "border-yellow-300",
  "ACE SPEC Rare":             "border-pink-400",
  "Shiny Rare":                "border-yellow-300",
  "Shiny Ultra Rare":          "border-yellow-300",
  "Rainbow Rare":              "border-pink-300",
  "Promo":                     "border-teal-400",
};

export default function CardGrid({ cards, apiBase, placeholderEnabled = true }: Props) {
  const { t, lang } = useI18n();

  if (!cards.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        {t.collection_no_results}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      {cards.map((card) => {
        const { src: imgSrc, isPlaceholder } = cardImageSrc(card, apiBase, placeholderEnabled);
        const borderColor = card.seltenheit ? (RARITY_BORDER[card.seltenheit] ?? "border-gray-600") : "border-gray-600";

        // Sprachabhängiger Name
        const displayName = lang === "EN" && card.englischer_name
          ? card.englischer_name
          : card.kartenname;

        const setCode = extractSetCode(card.set_edition) || "–";

        return (
          <Link
            key={card.id}
            href={`/cards/${card.id}`}
            onClick={() => rememberCardOrder(cards.map((c) => c.id))}
          >
            <div
              className={`
                relative rounded-lg border-2 overflow-hidden cursor-pointer
                transition-transform hover:scale-105 hover:shadow-lg
                bg-pokemon-card
                ${card.besessen ? borderColor : "border-gray-700 opacity-50"}
              `}
            >
              {/* Bild */}
              <div className="aspect-[63/88] relative bg-gray-800">
                {imgSrc ? (
                  <>
                    <Image
                      src={imgSrc}
                      alt={card.kartenname}
                      fill
                      className={isPlaceholder ? "object-contain p-2 opacity-70" : "object-cover"}
                      sizes="(max-width: 640px) 45vw, (max-width: 1024px) 20vw, 15vw"
                    />
                    {isPlaceholder && (
                      <div className="absolute bottom-0 inset-x-0 bg-black/50 text-center text-gray-400 text-[10px] py-0.5">
                        {t.detail_placeholder}
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-600 text-xs text-center p-2">
                    {card.pokedex_nr ? `#${String(card.pokedex_nr).padStart(4, "0")}` : "?"}
                  </div>
                )}
              </div>

              {/* Info-Bereich */}
              <div className="px-1.5 pt-1 pb-1.5 space-y-0.5">

                {/* Zeile 1: Pokédex-Nr. (links) | Name (rechts) */}
                <div className="flex items-baseline gap-1">
                  {card.pokedex_nr ? (
                    <span className="text-xs text-gray-500 shrink-0">
                      #{String(card.pokedex_nr).padStart(4, "0")}
                    </span>
                  ) : (
                    <span className="text-xs text-gray-700 shrink-0">–</span>
                  )}
                  <span className="text-xs text-white font-medium truncate text-right flex-1">
                    {displayName}
                  </span>
                </div>

                {/* Zeile 2: Set-Kürzel (links) | Karten-Nr. (mitte) | Seltenheit-Symbol (rechts) */}
                <div className="flex items-center gap-1">
                  <span className="text-xs text-gray-400 font-mono shrink-0">{setCode}</span>
                  <span className="text-xs text-gray-500 flex-1 text-center truncate">
                    {card.karten_nr ?? ""}
                  </span>
                  <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
                </div>

                {/* Zeile 3: Preis (links) | Sprache (mitte) | Status-Punkte (rechts) */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-yellow-400">
                    {card.wert_eur ? formatEur(card.wert_eur) : ""}
                  </span>
                  <span className="text-xs text-gray-500 font-mono">
                    {card.sprache ?? ""}
                  </span>
                  <div className="flex items-center gap-0.5">
                    {card.im_pokedex && (
                      <span
                        className="w-2.5 h-2.5 rounded-full bg-pokemon-pokedex shrink-0"
                        title={t.detail_pokedex_flag}
                      />
                    )}
                    {card.besessen && (
                      <span className="w-2.5 h-2.5 rounded-full bg-green-400 shrink-0" />
                    )}
                  </div>
                </div>

              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
