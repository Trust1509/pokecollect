"use client";
import { useState } from "react";
import { useI18n } from "@/lib/i18n";
import { cardImageSrc } from "@/lib/utils";
import type { BinderItem } from "@/components/BinderView";

type PagesChange = {
  removeCardIds?: number[];
  positions?: { card_id: number; position: number }[];
  binderSlots?: number;
};

type Props = {
  items: BinderItem[];
  apiBase: string;
  layout: string;
  binderSlots?: number | null;
  placeholderEnabled?: boolean;
  onPagesChange: (payload: PagesChange) => void;
};

function parseLayout(layout: string): { cols: number; rows: number } {
  const m = layout.match(/^(\d+)x(\d+)$/);
  if (!m) return { cols: 3, rows: 3 };
  return { cols: Number(m[1]), rows: Number(m[2]) };
}

export default function BinderEditor({
  items, apiBase, layout, binderSlots, placeholderEnabled = true, onPagesChange,
}: Props) {
  const { t } = useI18n();
  const { cols, rows } = parseLayout(layout);
  const perPage = cols * rows;
  const [dragPage, setDragPage] = useState<number | null>(null);

  const slotMap = new Map<number, BinderItem["card"]>();
  for (const it of items) slotMap.set(it.position, it.card);

  const maxSlot = items.length ? Math.max(...items.map((i) => i.position)) : -1;
  const contentPages = maxSlot >= 0 ? Math.floor(maxSlot / perPage) + 1 : 1;
  const slotPages = binderSlots != null ? Math.ceil(binderSlots / perPage) : 0;
  const totalPages = Math.max(contentPages, slotPages, 1);

  const cardsOnPage = (p: number) =>
    items.filter((it) => Math.floor(it.position / perPage) === p);

  const handleAddPage = () => {
    onPagesChange({ binderSlots: (totalPages + 1) * perPage });
  };

  const handleDeletePage = (p: number) => {
    const onPage = cardsOnPage(p);
    if (onPage.length && !confirm(t.binder_delete_page_warn(onPage.length))) return;
    const removeCardIds = onPage.map((it) => it.card.id);
    // Nachfolgende Seiten rücken eine Seite nach vorne
    const positions: { card_id: number; position: number }[] = [];
    for (const it of items) {
      const op = Math.floor(it.position / perPage);
      if (op <= p) continue;
      const slotInPage = it.position % perPage;
      positions.push({ card_id: it.card.id, position: (op - 1) * perPage + slotInPage });
    }
    onPagesChange({
      removeCardIds,
      positions,
      binderSlots: Math.max(0, (totalPages - 1) * perPage),
    });
  };

  const handleDropPage = (target: number) => {
    if (dragPage == null || dragPage === target) { setDragPage(null); return; }
    const order = Array.from({ length: totalPages }, (_, i) => i);
    const [moved] = order.splice(dragPage, 1);
    order.splice(target, 0, moved);
    // order[k] = alte Seitennummer, die jetzt an Stelle k steht
    const positions: { card_id: number; position: number }[] = [];
    for (const it of items) {
      const op = Math.floor(it.position / perPage);
      const slotInPage = it.position % perPage;
      const newPage = order.indexOf(op);
      positions.push({ card_id: it.card.id, position: newPage * perPage + slotInPage });
    }
    setDragPage(null);
    onPagesChange({ positions });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <p className="text-gray-400 text-sm">{t.binder_editor_hint}</p>
        <button
          onClick={handleAddPage}
          className="text-sm bg-pokemon-accent text-white rounded px-3 py-1.5 hover:bg-blue-700"
        >
          {t.binder_add_page}
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {Array.from({ length: totalPages }).map((_, p) => {
          const count = cardsOnPage(p).length;
          return (
            <div
              key={p}
              draggable
              onDragStart={() => setDragPage(p)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => handleDropPage(p)}
              className={`group relative bg-pokemon-card rounded-lg p-2 border cursor-move ${
                dragPage === p ? "border-pokemon-yellow" : "border-gray-700"
              }`}
            >
              <button
                onClick={() => handleDeletePage(p)}
                title={t.collection_remove}
                className="absolute -top-2 -right-2 z-10 bg-red-700 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm opacity-0 group-hover:opacity-100 transition hover:bg-red-600"
              >
                ✕
              </button>
              <div
                className="grid gap-0.5 mb-1"
                style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
              >
                {Array.from({ length: perPage }).map((_, i) => {
                  const slot = p * perPage + i;
                  const card = slotMap.get(slot) ?? null;
                  if (!card) {
                    return <div key={slot} className="aspect-[63/88] rounded-sm border border-dashed border-gray-700/50 bg-gray-800/30" />;
                  }
                  const { src } = cardImageSrc(card, apiBase, placeholderEnabled);
                  return (
                    <div
                      key={slot}
                      className="aspect-[63/88] rounded-sm bg-gray-800 bg-center bg-cover"
                      style={src ? { backgroundImage: `url("${src}")` } : undefined}
                    />
                  );
                })}
              </div>
              <div className="flex items-center justify-between text-[11px] text-gray-400">
                <span>{t.binder_page_n(p + 1)}</span>
                <span>{count > 0 ? t.collections_card_count(count) : ""}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
