"use client";
import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card } from "@/lib/api";
import { cardImageSrc } from "@/lib/utils";
import RarityBadge from "@/components/RarityBadge";
import { useI18n } from "@/lib/i18n";

type Props = {
  cards: Card[];
  apiBase: string;
  placeholderEnabled?: boolean;
};

const PER_PAGE = 9; // klassische 9-Pocket-Binderseite (3×3)

export default function BinderView({ cards, apiBase, placeholderEnabled = true }: Props) {
  const { t, lang } = useI18n();
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(cards.length / PER_PAGE));
  const safePage = Math.min(page, totalPages - 1);
  const start = safePage * PER_PAGE;
  const pageCards = cards.slice(start, start + PER_PAGE);

  // Auf 9 Slots auffüllen, damit das Raster immer vollständig wirkt
  const slots: (Card | null)[] = [...pageCards];
  while (slots.length < PER_PAGE) slots.push(null);

  return (
    <div className="flex flex-col items-center">
      <div className="bg-gradient-to-br from-gray-900 to-gray-950 border border-gray-700 rounded-xl p-4 shadow-xl w-full max-w-2xl">
        <div className="grid grid-cols-3 gap-3">
          {slots.map((card, i) => {
            if (!card) {
              return (
                <div
                  key={`empty-${i}`}
                  className="aspect-[63/88] rounded-lg border-2 border-dashed border-gray-700/60 bg-gray-800/30 flex items-center justify-center text-gray-700 text-xs"
                >
                  {t.binder_empty_pocket}
                </div>
              );
            }
            const { src, isPlaceholder } = cardImageSrc(card, apiBase, placeholderEnabled);
            const displayName =
              lang === "EN" && card.englischer_name ? card.englischer_name : card.kartenname;
            return (
              <Link key={card.id} href={`/cards/${card.id}`}>
                <div
                  className={`aspect-[63/88] rounded-lg overflow-hidden relative bg-gray-800 ring-1 ring-black/40 transition-transform hover:scale-[1.03] hover:ring-pokemon-yellow ${
                    card.besessen ? "" : "opacity-50"
                  }`}
                >
                  {src ? (
                    <Image
                      src={src}
                      alt={displayName}
                      fill
                      className={isPlaceholder ? "object-contain p-2 opacity-70" : "object-cover"}
                      sizes="(max-width: 768px) 30vw, 220px"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-600 text-xs">
                      {card.pokedex_nr ? `#${String(card.pokedex_nr).padStart(4, "0")}` : "?"}
                    </div>
                  )}
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5 flex items-center justify-between gap-1">
                    <span className="text-[10px] text-white truncate">{displayName}</span>
                    <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="flex items-center gap-4 mt-4 text-sm">
        <button
          disabled={safePage <= 0}
          onClick={() => setPage(safePage - 1)}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ‹
        </button>
        <span className="text-gray-400">{t.binder_page(safePage + 1, totalPages)}</span>
        <button
          disabled={safePage >= totalPages - 1}
          onClick={() => setPage(safePage + 1)}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ›
        </button>
      </div>
    </div>
  );
}
