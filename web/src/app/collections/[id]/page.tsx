"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import toast from "react-hot-toast";
import { Card, Collection, cardApi, collectionApi } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { cardImageSrc } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function CollectionDetailPage() {
  const params = useParams();
  const id = Number(params?.id);
  const { t, lang } = useI18n();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("grid");

  // Karten-Zuweisung (Suche)
  const [showAssign, setShowAssign] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Card[]>([]);
  const [searching, setSearching] = useState(false);

  const loadCards = useCallback(() => {
    setLoading(true);
    collectionApi.cards(id).then((r) => setCards(r.data)).finally(() => setLoading(false));
  }, [id]);

  const loadMeta = useCallback(() => {
    collectionApi.get(id).then((r) => setCollection(r.data)).catch(() => setCollection(null));
  }, [id]);

  useEffect(() => {
    if (!Number.isNaN(id)) { loadMeta(); loadCards(); }
  }, [id, loadMeta, loadCards]);

  // Suche nach Karten zum Zuweisen (debounced)
  useEffect(() => {
    if (!showAssign) return;
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        const params: Record<string, unknown> = { limit: 30 };
        const q = query.trim();
        if (q) {
          if (/^\d+$/.test(q)) params.pokedex_nr = Number(q);
          else params.search = q;
        }
        const r = await cardApi.list(params);
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
    if (!confirm(t.collection_remove_confirm)) return;
    try {
      await collectionApi.removeCard(id, cardId);
      toast.success(t.collection_removed);
      loadCards();
      loadMeta();
    } catch {
      toast.error(t.collections_error);
    }
  };

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
        <div className="flex items-center gap-2">
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
            <ul className="max-h-80 overflow-y-auto divide-y divide-gray-800">
              {results.map((c) => {
                const { src, isPlaceholder } = cardImageSrc(c, API_BASE);
                const name = lang === "EN" && c.englischer_name ? c.englischer_name : c.kartenname;
                return (
                  <li key={c.id} className="flex items-center gap-3 py-2">
                    <div className="w-9 h-12 relative bg-gray-800 rounded overflow-hidden shrink-0">
                      {src && (
                        <Image src={src} alt={name} fill className={isPlaceholder ? "object-contain p-0.5 opacity-70" : "object-cover"} sizes="36px" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-white text-sm truncate">{name}</div>
                      <div className="text-gray-500 text-xs truncate">
                        {c.pokedex_nr ? `#${String(c.pokedex_nr).padStart(4, "0")} · ` : ""}
                        {c.set_edition ?? ""} {c.karten_nr ?? ""}
                      </div>
                    </div>
                    <button
                      onClick={() => handleAdd(c.id)}
                      className="bg-green-700 text-white text-xs px-3 py-1.5 rounded hover:bg-green-600 shrink-0"
                    >
                      {t.collection_add}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : cards.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.collection_empty}</div>
      ) : view === "binder" ? (
        <BinderView cards={cards} apiBase={API_BASE} />
      ) : (
        <div className="space-y-3">
          <CardGrid cards={cards} apiBase={API_BASE} />
          <div className="flex flex-wrap gap-2 pt-2 border-t border-gray-800">
            {cards.map((c) => (
              <button
                key={c.id}
                onClick={() => handleRemove(c.id)}
                className="text-red-400 hover:text-red-300 text-xs bg-red-950/40 rounded px-2 py-1"
                title={t.collection_remove}
              >
                ✕ {lang === "EN" && c.englischer_name ? c.englischer_name : c.kartenname}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
