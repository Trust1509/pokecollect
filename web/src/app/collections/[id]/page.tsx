"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import toast from "react-hot-toast";
import { Card, CollectionCard, Collection, cardApi, collectionApi } from "@/lib/api";
import SortableCardGrid from "@/components/SortableCardGrid";
import BinderView, { BinderItem } from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { cardImageSrc } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function CollectionDetailPage() {
  const params = useParams();
  const id = Number(params?.id);
  const { t, lang } = useI18n();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [cards, setCards] = useState<CollectionCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>(() => {
    if (typeof window !== "undefined") {
      const s = sessionStorage.getItem(`collection_view_${params?.id}`);
      if (s === "binder" || s === "grid") return s;
    }
    return "grid";
  });
  const [layout, setLayout] = useState("3x3");

  useEffect(() => {
    if (!Number.isNaN(id)) {
      try { sessionStorage.setItem(`collection_view_${id}`, view); } catch {}
    }
  }, [view, id]);

  // Karten-Zuweisung (Suche)
  const [showAssign, setShowAssign] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Card[]>([]);
  const [searching, setSearching] = useState(false);

  const loadCards = useCallback(() => {
    setLoading(true);
    collectionApi.cards(id).then((r) => {
      const data = r.data;
      // Alt-Daten ohne Position einmalig normalisieren
      if (data.length && data.some((c) => c.position == null)) {
        collectionApi
          .reorder(id, data.map((c) => c.id))
          .then(() => collectionApi.cards(id).then((r2) => setCards(r2.data)))
          .catch(() => setCards(data))
          .finally(() => setLoading(false));
      } else {
        setCards(data);
        setLoading(false);
      }
    }).catch(() => setLoading(false));
  }, [id]);

  const loadMeta = useCallback(() => {
    collectionApi.get(id).then((r) => {
      setCollection(r.data);
      setLayout(r.data.binder_layout || "3x3");
    }).catch(() => setCollection(null));
  }, [id]);

  useEffect(() => {
    if (!Number.isNaN(id)) { loadMeta(); loadCards(); }
  }, [id, loadMeta, loadCards]);

  // Suche: nur besessene Karten (keine Pokédex-Platzhalter)
  useEffect(() => {
    if (!showAssign) return;
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        const p: Record<string, unknown> = { limit: 60, besessen: true };
        const q = query.trim();
        if (q) {
          if (/^\d+$/.test(q)) p.pokedex_nr = Number(q);
          else p.search = q;
        }
        const r = await cardApi.list(p);
        const inCollection = new Set(cards.map((c) => c.id));
        setResults(r.data.items.filter((c) => !inCollection.has(c.id)));
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [query, showAssign, cards]);

  const handleAdd = async (cardId: number) => {
    try {
      await collectionApi.addCard(id, cardId);
      toast.success(t.collection_added);
      setResults((r) => r.filter((c) => c.id !== cardId));
      loadCards();
      loadMeta();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemove = async (cardId: number) => {
    try {
      await collectionApi.removeCard(id, cardId);
      loadCards();
      loadMeta();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemoveConfirm = (cardId: number) => {
    if (!confirm(t.collection_remove_confirm)) return;
    handleRemove(cardId);
  };

  const handleReorder = async (orderedIds: number[]) => {
    try {
      await collectionApi.reorder(id, orderedIds);
      loadCards();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleMoveToSlot = async (cardId: number, slot: number) => {
    try {
      await collectionApi.moveToSlot(id, cardId, slot);
      loadCards();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleLayoutChange = async (l: string) => {
    setLayout(l);
    try {
      await collectionApi.update(id, { binder_layout: l });
    } catch {/* nicht kritisch */}
  };

  const binderItems: BinderItem[] = cards.map((c, idx) => ({
    card: c,
    position: c.position ?? idx,
  }));

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">{t.collection_back}</Link>
      </div>

      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">{collection?.name ?? "…"}</h1>
          {collection?.beschreibung && <p className="text-gray-400 text-sm">{collection.beschreibung}</p>}
          <p className="text-gray-500 text-xs mt-1">{t.collections_card_count(collection?.karten_anzahl ?? cards.length)}</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <ViewToggle value={view} onChange={setView} />
          <button
            onClick={() => setShowAssign((v) => !v)}
            className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700"
          >
            {t.collection_add_existing}
          </button>
          <Link
            href={`/cards/new?collection=${id}`}
            className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600"
          >
            {t.collection_create_new}
          </Link>
        </div>
      </div>

      {/* Zuweisungs-Panel */}
      {showAssign && (
        <div className="bg-pokemon-card rounded-lg p-4 mb-6">
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.collection_search_placeholder}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm mb-3"
          />
          {searching ? (
            <div className="text-gray-500 text-sm py-4 text-center">{t.detail_loading}</div>
          ) : results.length === 0 ? (
            <div className="text-gray-500 text-sm py-4 text-center">{t.collection_no_results}</div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2 max-h-[28rem] overflow-y-auto pr-1">
              {results.map((c) => {
                const { src, isPlaceholder } = cardImageSrc(c, API_BASE);
                const name = lang === "EN" && c.englischer_name ? c.englischer_name : c.kartenname;
                return (
                  <button
                    key={c.id}
                    onClick={() => handleAdd(c.id)}
                    title={t.collection_add}
                    className="group text-left bg-gray-800/40 rounded-lg overflow-hidden border border-transparent hover:border-green-500"
                  >
                    <div className="aspect-[63/88] relative bg-gray-800">
                      {src && (
                        <Image src={src} alt={name} fill className={isPlaceholder ? "object-contain p-1 opacity-70" : "object-cover"} sizes="120px" />
                      )}
                      <div className="absolute inset-0 bg-green-600/0 group-hover:bg-green-600/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                        <span className="bg-green-700 text-white text-xs px-2 py-1 rounded">+ {t.collection_add}</span>
                      </div>
                    </div>
                    <div className="px-1 py-1">
                      <div className="text-white text-[11px] truncate">{name}</div>
                      <div className="text-gray-500 text-[10px] truncate">
                        {c.set_edition ?? ""} {c.karten_nr ?? ""}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : view === "binder" ? (
        <BinderView
          items={binderItems}
          apiBase={API_BASE}
          layout={layout}
          onLayoutChange={handleLayoutChange}
          editable
          onMoveToSlot={handleMoveToSlot}
        />
      ) : cards.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.collection_empty}</div>
      ) : (
        <SortableCardGrid
          cards={cards}
          apiBase={API_BASE}
          onReorder={handleReorder}
          onRemove={handleRemoveConfirm}
        />
      )}
    </div>
  );
}
