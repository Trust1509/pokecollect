"use client";
import { DragEvent as ReactDragEvent, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Card, BINDER_LAYOUTS } from "@/lib/api";
import { cardImageSrc } from "@/lib/utils";
import RarityBadge from "@/components/RarityBadge";
import { useI18n } from "@/lib/i18n";

export type BinderItem = { card: Card; position: number };

type Props = {
  items: BinderItem[];
  apiBase: string;
  placeholderEnabled?: boolean;
  layout: string;
  onLayoutChange?: (l: string) => void;
  editable?: boolean;
  onMoveToSlot?: (cardId: number, slot: number) => void;
};

function parseLayout(layout: string): { cols: number; rows: number } {
  const m = layout.match(/^(\d+)x(\d+)$/);
  if (!m) return { cols: 3, rows: 3 };
  return { cols: Number(m[1]), rows: Number(m[2]) };
}

const GAP = 8;        // gap-2 zwischen Pockets
const PAGE_PAD = 24;  // p-3 links+rechts
const SPREAD_GAP = 16;
const SIZE_KEY = "binder_card_size";

export default function BinderView({
  items, apiBase, placeholderEnabled = true, layout,
  onLayoutChange, editable = false, onMoveToSlot,
}: Props) {
  const { t, lang } = useI18n();
  const { cols, rows } = parseLayout(layout);
  const perPage = cols * rows;

  const [spread, setSpread] = useState(0);
  const [extraPages, setExtraPages] = useState(0);
  const [dragId, setDragId] = useState<number | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [cardSize, setCardSize] = useState<number>(() => {
    if (typeof window !== "undefined") {
      const s = Number(localStorage.getItem(SIZE_KEY));
      if (s >= 70 && s <= 260) return s;
    }
    return 140;
  });
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) setContainerWidth(e.contentRect.width);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const setSize = (v: number) => {
    setCardSize(v);
    if (typeof window !== "undefined") localStorage.setItem(SIZE_KEY, String(v));
  };

  const slotMap = useMemo(() => {
    const m = new Map<number, Card>();
    for (const it of items) m.set(it.position, it.card);
    return m;
  }, [items]);

  const maxSlot = items.length ? Math.max(...items.map((i) => i.position)) : -1;
  const contentPages = maxSlot >= 0 ? Math.floor(maxSlot / perPage) + 1 : 1;
  const totalPages = contentPages + (editable ? 1 + extraPages : 0);

  const pageWidth = cols * cardSize + (cols - 1) * GAP + PAGE_PAD;
  const twoPage = containerWidth >= 2 * pageWidth + SPREAD_GAP;

  // Spreads: 0 = nur Seite 0; ab 1 = Seiten (2s-1, 2s)
  const maxSpread = twoPage ? Math.ceil(Math.max(0, totalPages - 1) / 2) : Math.max(0, totalPages - 1);
  const safeSpread = Math.min(spread, maxSpread);

  useEffect(() => { setSpread(0); }, [layout, twoPage]);

  const visiblePages: number[] = twoPage
    ? (safeSpread === 0 ? [0] : [2 * safeSpread - 1, 2 * safeSpread].filter((p) => p < totalPages))
    : [safeSpread];

  const handleDrop = (slot: number) => {
    if (dragId != null && onMoveToSlot) onMoveToSlot(dragId, slot);
    setDragId(null);
  };

  const renderPage = (pageNum: number) => {
    const startSlot = pageNum * perPage;
    return (
      <div
        key={pageNum}
        className="bg-gradient-to-br from-gray-900 to-gray-950 border border-gray-700 rounded-xl p-3 shadow-xl shrink-0"
      >
        <div
          className="grid"
          style={{ gridTemplateColumns: `repeat(${cols}, ${cardSize}px)`, gap: `${GAP}px` }}
        >
          {Array.from({ length: perPage }).map((_, i) => {
            const slot = startSlot + i;
            const card = slotMap.get(slot) ?? null;
            const dropProps = editable
              ? {
                  onDragOver: (e: ReactDragEvent) => e.preventDefault(),
                  onDrop: () => handleDrop(slot),
                }
              : {};

            if (!card) {
              return (
                <div
                  key={slot}
                  {...dropProps}
                  className="aspect-[63/88] rounded-lg border-2 border-dashed border-gray-700/60 bg-gray-800/30 flex items-center justify-center text-gray-700 text-[10px]"
                >
                  {t.binder_empty_pocket}
                </div>
              );
            }

            const { src, isPlaceholder } = cardImageSrc(card, apiBase, placeholderEnabled);
            const name = lang === "EN" && card.englischer_name ? card.englischer_name : card.kartenname;
            return (
              <div
                key={slot}
                {...dropProps}
                draggable={editable}
                onDragStart={editable ? () => setDragId(card.id) : undefined}
                className={`aspect-[63/88] rounded-lg overflow-hidden relative bg-gray-800 ring-1 ring-black/40 transition-transform hover:scale-[1.03] hover:ring-pokemon-yellow ${
                  editable ? "cursor-move" : ""
                } ${card.besessen ? "" : "opacity-50"}`}
              >
                <Link href={`/cards/${card.id}`} draggable={false} className="block w-full h-full">
                  {src ? (
                    <Image
                      src={src}
                      alt={name}
                      fill
                      draggable={false}
                      className={isPlaceholder ? "object-contain p-2 opacity-70" : "object-cover"}
                      sizes={`${cardSize}px`}
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-600 text-xs">
                      {card.pokedex_nr ? `#${String(card.pokedex_nr).padStart(4, "0")}` : "?"}
                    </div>
                  )}
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5 flex items-center justify-between gap-1">
                    <span className="text-[10px] text-white truncate">{name}</span>
                    <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
        <div className="text-center text-gray-600 text-[10px] mt-1">{pageNum + 1}</div>
      </div>
    );
  };

  const pageLabel = twoPage && visiblePages.length === 2
    ? t.binder_pages(visiblePages[0] + 1, visiblePages[1] + 1, totalPages)
    : t.binder_page((visiblePages[0] ?? 0) + 1, totalPages);

  return (
    <div className="flex flex-col items-center w-full">
      {/* Steuerleiste */}
      <div className="flex items-center gap-4 mb-3 flex-wrap justify-center">
        {onLayoutChange && (
          <label className="flex items-center gap-2 text-sm text-gray-400">
            {t.binder_layout_label}
            <select
              value={layout}
              onChange={(e) => onLayoutChange(e.target.value)}
              className="bg-pokemon-card border border-gray-700 rounded px-2 py-1 text-white text-sm"
            >
              {BINDER_LAYOUTS.map((l) => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </label>
        )}
        <label className="flex items-center gap-2 text-sm text-gray-400">
          {t.binder_card_size}
          <input
            type="range"
            min={70}
            max={260}
            step={10}
            value={cardSize}
            onChange={(e) => setSize(Number(e.target.value))}
            className="accent-pokemon-yellow"
          />
        </label>
        {editable && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setExtraPages((p) => p + 1)}
              className="text-xs bg-pokemon-card text-gray-300 hover:text-white rounded px-2 py-1"
            >
              {t.binder_add_page}
            </button>
            {extraPages > 0 && (
              <button
                onClick={() => setExtraPages((p) => Math.max(0, p - 1))}
                className="text-xs bg-pokemon-card text-gray-300 hover:text-white rounded px-2 py-1"
              >
                {t.binder_remove_page}
              </button>
            )}
          </div>
        )}
      </div>

      {editable && <p className="text-gray-500 text-xs mb-2 text-center">{t.binder_dnd_hint}</p>}

      {/* Seiten */}
      <div ref={containerRef} className="w-full overflow-x-auto">
        <div className="flex gap-4 justify-center items-start min-w-min mx-auto">
          {visiblePages.map((p) => renderPage(p))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center gap-4 mt-4 text-sm">
        <button
          disabled={safeSpread <= 0}
          onClick={() => setSpread(safeSpread - 1)}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ‹
        </button>
        <span className="text-gray-400">{pageLabel}</span>
        <button
          disabled={safeSpread >= maxSpread}
          onClick={() => setSpread(safeSpread + 1)}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ›
        </button>
      </div>
    </div>
  );
}
