"use client";
import { DragEvent as ReactDragEvent, TouchEvent as ReactTouchEvent, useEffect, useMemo, useRef, useState } from "react";
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
  onAddAtSlot?: (cardId: number, slot: number) => void;
  binderSlots?: number | null;
  onAddPage?: (newSlots: number) => void;
  onDeleteLastPage?: (cardIdsOnLastPage: number[], newSlots: number) => void;
  /** sessionStorage-Key, um die aktuelle Binder-Seite über Navigation hinweg zu merken */
  storageKey?: string;
};

export const ASSIGN_DRAG_TYPE = "application/x-pokecollect-add";

function parseLayout(layout: string): { cols: number; rows: number } {
  const m = layout.match(/^(\d+)x(\d+)$/);
  if (!m) return { cols: 3, rows: 3 };
  return { cols: Number(m[1]), rows: Number(m[2]) };
}

function extractSetCode(setEdition: string | null): string {
  if (!setEdition) return "";
  const m = setEdition.match(/\(([A-Z0-9]{1,6})\)\s*$/);
  return m ? m[1] : "";
}

const GAP = 8;        // gap zwischen Pockets
const PAGE_PAD = 24;  // p-3 links+rechts
const SPREAD_GAP = 16;
const SIZE_KEY = "binder_card_size";

export default function BinderView({
  items, apiBase, placeholderEnabled = true, layout,
  onLayoutChange, editable = false, onMoveToSlot, onAddAtSlot,
  binderSlots, onAddPage, onDeleteLastPage, storageKey,
}: Props) {
  const { t, lang } = useI18n();
  const { cols, rows } = parseLayout(layout);
  const perPage = cols * rows;

  const [showOpts, setShowOpts] = useState(false);
  const [page, setPage] = useState<number>(() => {
    if (storageKey && typeof window !== "undefined") {
      const v = Number(sessionStorage.getItem(storageKey));
      if (Number.isFinite(v) && v >= 0) return v;
    }
    return 0;
  });

  // Aktuelle Seite merken (z.B. um nach Öffnen einer Detailansicht zurückzukehren)
  useEffect(() => {
    if (storageKey && typeof window !== "undefined") {
      try { sessionStorage.setItem(storageKey, String(page)); } catch {}
    }
  }, [page, storageKey]);
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
  const slotPages = binderSlots != null ? Math.ceil(binderSlots / perPage) : 0;
  const totalPages = Math.max(contentPages, slotPages, 1);

  const pageWidth = cols * cardSize + (cols - 1) * GAP + PAGE_PAD;
  const twoPage = containerWidth >= 2 * pageWidth + SPREAD_GAP;

  const safePage = Math.min(Math.max(0, page), totalPages - 1);

  // Sichtbare Seiten: Einzelseite, oder Buch-Doppelseite (Seite 0 allein, dann Paare 1|2, 3|4 …)
  const visiblePages: number[] = !twoPage
    ? [safePage]
    : safePage === 0
    ? [0]
    : (() => {
        const left = safePage % 2 === 1 ? safePage : safePage - 1;
        return left + 1 < totalPages ? [left, left + 1] : [left];
      })();

  const leftVisible = visiblePages[0];
  const rightVisible = visiblePages[visiblePages.length - 1];

  const goPrev = () => {
    if (!twoPage) setPage(safePage - 1);
    else setPage(leftVisible <= 1 ? 0 : leftVisible - 2);
  };
  const goNext = () => {
    if (!twoPage) setPage(safePage + 1);
    else setPage(leftVisible === 0 ? 1 : leftVisible + 2);
  };

  // Wischen links/rechts zum Blättern (Mobile)
  const touchX = useRef<number | null>(null);
  const touchY = useRef<number | null>(null);
  const onTouchStart = (e: ReactTouchEvent) => {
    touchX.current = e.touches[0].clientX;
    touchY.current = e.touches[0].clientY;
  };
  const onTouchEnd = (e: ReactTouchEvent) => {
    if (touchX.current == null || touchY.current == null) return;
    const dx = e.changedTouches[0].clientX - touchX.current;
    const dy = e.changedTouches[0].clientY - touchY.current;
    touchX.current = null; touchY.current = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      if (dx < 0) { if (rightVisible < totalPages - 1) goNext(); }
      else { if (leftVisible > 0) goPrev(); }
    }
  };

  const flipThrottle = useRef(0);
  const handleEdgeOver = (dir: "prev" | "next") => (e: ReactDragEvent) => {
    e.preventDefault();
    const now = Date.now();
    if (now - flipThrottle.current < 700) return;
    flipThrottle.current = now;
    if (dir === "prev") goPrev();
    else goNext();
  };

  const handleDrop = (slot: number, e: ReactDragEvent) => {
    const addId = e.dataTransfer.getData(ASSIGN_DRAG_TYPE);
    if (addId && onAddAtSlot) {
      onAddAtSlot(Number(addId), slot);
      setDragId(null);
      return;
    }
    if (dragId != null && onMoveToSlot) onMoveToSlot(dragId, slot);
    setDragId(null);
  };

  const handleAddPage = () => {
    if (onAddPage) onAddPage((totalPages + 1) * perPage);
  };

  const handleDeleteLastPage = () => {
    if (!onDeleteLastPage) return;
    const last = totalPages - 1;
    const ids = items
      .filter((it) => Math.floor(it.position / perPage) === last)
      .map((it) => it.card.id);
    onDeleteLastPage(ids, last * perPage);
  };

  const renderPage = (pageNum: number) => {
    const startSlot = pageNum * perPage;
    return (
      <div
        key={pageNum}
        className="bg-gradient-to-br from-gray-900 to-gray-950 border border-gray-700 rounded-xl p-3 shadow-xl shrink-0"
      >
        <div className="grid" style={{ gridTemplateColumns: `repeat(${cols}, ${cardSize}px)`, gap: `${GAP}px` }}>
          {Array.from({ length: perPage }).map((_, i) => {
            const slot = startSlot + i;
            const card = slotMap.get(slot) ?? null;
            const dropProps = editable
              ? { onDragOver: (e: ReactDragEvent) => e.preventDefault(), onDrop: (e: ReactDragEvent) => handleDrop(slot, e) }
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
            const code = extractSetCode(card.set_edition);
            return (
              <div
                key={slot}
                {...dropProps}
                draggable={editable}
                onDragStart={editable ? (e) => { e.dataTransfer.setData("text/plain", String(card.id)); setDragId(card.id); } : undefined}
                onDragEnd={editable ? () => setDragId(null) : undefined}
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
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 px-1 py-0.5 grid grid-cols-3 items-center gap-1">
                    <span className="text-[10px] text-white truncate">{name}</span>
                    <span className="text-[10px] text-gray-400 font-mono text-center truncate">{code}</span>
                    <span className="flex justify-end"><RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" /></span>
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
    ? t.binder_pages(leftVisible + 1, rightVisible + 1, totalPages)
    : t.binder_page((leftVisible ?? 0) + 1, totalPages);

  return (
    <div className="flex flex-col items-center w-full" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
      {editable && <p className="text-gray-500 text-xs mb-2 text-center">{t.binder_dnd_hint}</p>}

      {/* Seiten */}
      <div ref={containerRef} className="w-full overflow-x-auto relative">
        <div className="flex gap-4 justify-center items-start min-w-min mx-auto">
          {visiblePages.map((p) => renderPage(p))}
        </div>
        {editable && dragId != null && leftVisible > 0 && (
          <div
            onDragOver={handleEdgeOver("prev")}
            onDrop={(e) => { e.preventDefault(); setDragId(null); }}
            className="absolute left-0 top-0 bottom-0 w-12 bg-gradient-to-r from-pokemon-yellow/40 to-transparent flex items-center pl-1 text-pokemon-yellow text-3xl"
          >
            ‹
          </div>
        )}
        {editable && dragId != null && rightVisible < totalPages - 1 && (
          <div
            onDragOver={handleEdgeOver("next")}
            onDrop={(e) => { e.preventDefault(); setDragId(null); }}
            className="absolute right-0 top-0 bottom-0 w-12 bg-gradient-to-l from-pokemon-yellow/40 to-transparent flex items-center justify-end pr-1 text-pokemon-yellow text-3xl"
          >
            ›
          </div>
        )}
      </div>

      {/* Darstellungsoptionen (über ⚙ in der Navigationszeile, keine extra Zeile) */}
      {showOpts && (
        <div className="flex items-center gap-3 mt-4 flex-wrap justify-center bg-pokemon-card/60 rounded px-3 py-2">
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
              type="range" min={70} max={260} step={10}
              value={cardSize}
              onChange={(e) => setSize(Number(e.target.value))}
              className="accent-pokemon-yellow"
            />
          </label>
          {editable && onAddPage && (
            <button onClick={handleAddPage} className="text-xs bg-pokemon-card text-gray-300 hover:text-white rounded px-2 py-1">
              {t.binder_add_page}
            </button>
          )}
          {editable && onDeleteLastPage && totalPages > 1 && (
            <button onClick={handleDeleteLastPage} className="text-xs bg-red-950/60 text-red-300 hover:text-red-100 rounded px-2 py-1">
              {t.binder_delete_last_page}
            </button>
          )}
        </div>
      )}

      {/* Navigation (mit ⚙ direkt daneben) */}
      <div className="flex items-center gap-3 mt-4 text-sm">
        <button
          disabled={leftVisible <= 0}
          onClick={goPrev}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ‹
        </button>
        <span className="text-gray-400">{pageLabel}</span>
        <button
          disabled={rightVisible >= totalPages - 1}
          onClick={goNext}
          className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40 hover:bg-gray-700"
        >
          ›
        </button>
        <button
          onClick={() => setShowOpts((o) => !o)}
          title={t.binder_display_options}
          className={`px-3 py-1.5 rounded ${showOpts ? "bg-pokemon-accent text-white" : "bg-pokemon-card text-gray-300 hover:text-white"}`}
        >
          ⚙
        </button>
      </div>
    </div>
  );
}
