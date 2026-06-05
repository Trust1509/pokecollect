"use client";
import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { CollectionCard } from "@/lib/api";
import { cardImageSrc } from "@/lib/utils";
import RarityBadge from "@/components/RarityBadge";
import { useI18n } from "@/lib/i18n";

type Props = {
  cards: CollectionCard[];
  apiBase: string;
  onReorder: (orderedIds: number[]) => void;
  onRemove: (cardId: number) => void;
};

export default function SortableCardGrid({ cards, apiBase, onReorder, onRemove }: Props) {
  const { t, lang } = useI18n();
  const [order, setOrder] = useState<CollectionCard[]>(cards);
  const [dragId, setDragId] = useState<number | null>(null);

  useEffect(() => { setOrder(cards); }, [cards]);

  const handleDropOn = (targetId: number) => {
    if (dragId == null || dragId === targetId) { setDragId(null); return; }
    const next = [...order];
    const from = next.findIndex((c) => c.id === dragId);
    const to = next.findIndex((c) => c.id === targetId);
    if (from < 0 || to < 0) { setDragId(null); return; }
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    setOrder(next);
    setDragId(null);
    onReorder(next.map((c) => c.id));
  };

  return (
    <div>
      <p className="text-gray-500 text-xs mb-2">{t.collection_reorder_hint}</p>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
        {order.map((card) => {
          const { src, isPlaceholder } = cardImageSrc(card, apiBase);
          const name = lang === "EN" && card.englischer_name ? card.englischer_name : card.kartenname;
          return (
            <div
              key={card.id}
              draggable
              onDragStart={() => setDragId(card.id)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDropOn(card.id)}
              className={`relative rounded-lg border-2 overflow-hidden cursor-move bg-pokemon-card ${
                card.besessen ? "border-gray-600" : "border-gray-700 opacity-60"
              } ${dragId === card.id ? "ring-2 ring-pokemon-yellow" : ""}`}
            >
              <Link href={`/cards/${card.id}`} draggable={false}>
                <div className="aspect-[63/88] relative bg-gray-800">
                  {src ? (
                    <Image
                      src={src}
                      alt={name}
                      fill
                      draggable={false}
                      className={isPlaceholder ? "object-contain p-2 opacity-70" : "object-cover"}
                      sizes="(max-width: 640px) 45vw, 15vw"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-600 text-xs">
                      {card.pokedex_nr ? `#${String(card.pokedex_nr).padStart(4, "0")}` : "?"}
                    </div>
                  )}
                </div>
              </Link>
              <div className="px-1.5 py-1 flex items-center justify-between gap-1">
                <span className="text-xs text-white truncate">{name}</span>
                <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
              </div>
              <button
                onClick={() => onRemove(card.id)}
                title={t.collection_remove}
                className="absolute top-1 right-1 bg-black/60 text-red-300 hover:text-red-100 rounded-full w-5 h-5 flex items-center justify-center text-xs"
              >
                ✕
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
