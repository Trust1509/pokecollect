"use client";
import Image from "next/image";
import Link from "next/link";
import { Card } from "@/lib/api";
import { formatEur, pokemonPlaceholderUrl } from "@/lib/utils";
import RarityBadge from "@/components/RarityBadge";

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
  if (!cards.length) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Keine Karten gefunden
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
      {cards.map((card) => {
        const imgSrc =
          card.bild_thumbnail_pfad
            ? `${apiBase}/images/${card.bild_thumbnail_pfad.replace(/^.*\/images\//, "")}`
            : card.bild_pokedex_url
            ?? card.bild_karte_url
            ?? (placeholderEnabled ? pokemonPlaceholderUrl(card.pokedex_nr) : null);
        const isPlaceholder = !card.bild_thumbnail_pfad && !card.bild_pokedex_url && !card.bild_karte_url && !!imgSrc;
        const borderColor = card.seltenheit ? (RARITY_BORDER[card.seltenheit] ?? "border-gray-600") : "border-gray-600";

        return (
          <Link key={card.id} href={`/cards/${card.id}`}>
            <div
              className={`
                relative rounded-lg border-2 overflow-hidden cursor-pointer
                transition-transform hover:scale-105 hover:shadow-lg
                bg-pokemon-card
                ${card.besessen ? borderColor : "border-gray-700 opacity-50"}
              `}
            >
              <div className="aspect-[63/88] relative bg-gray-800">
                {imgSrc ? (
                  <>
                    <Image
                      src={imgSrc}
                      alt={card.kartenname}
                      fill
                      className={`object-contain${isPlaceholder ? " p-2 opacity-70" : " object-cover"}`}
                      sizes="(max-width: 640px) 45vw, (max-width: 1024px) 20vw, 15vw"
                    />
                    {isPlaceholder && (
                      <div className="absolute bottom-0 inset-x-0 bg-black/50 text-center text-gray-400 text-[10px] py-0.5">
                        Platzhalter
                      </div>
                    )}
                  </>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-600 text-xs text-center p-2">
                    {card.pokedex_nr ? `#${String(card.pokedex_nr).padStart(4, "0")}` : "?"}
                  </div>
                )}
                {card.besessen && (
                  <div className="absolute top-1 right-1 w-3 h-3 rounded-full bg-green-400" />
                )}
              </div>
              <div className="p-1.5">
                <p className="text-xs text-white font-medium truncate">{card.kartenname}</p>
                <div className="flex items-center justify-between gap-1 mt-0.5">
                  <p className="text-xs text-gray-400 truncate flex-1">
                    {card.set_edition ?? "–"}{card.karten_nr ? ` · ${card.karten_nr}` : ""}
                  </p>
                  <RarityBadge rarity={card.seltenheit} language={card.sprache} size="xs" />
                </div>
                {card.wert_eur && (
                  <p className="text-xs text-yellow-400 mt-0.5">{formatEur(card.wert_eur)}</p>
                )}
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
