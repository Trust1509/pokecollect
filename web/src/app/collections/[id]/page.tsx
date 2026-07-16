"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import Image from "next/image";
import toast from "react-hot-toast";
import { API_BASE, Card, CollectionCard, Collection, cardApi, collectionApi } from "@/lib/api";
import SortableCardGrid from "@/components/SortableCardGrid";
import BinderView, { BinderItem, ASSIGN_DRAG_TYPE } from "@/components/BinderView";
import BinderEditor from "@/components/BinderEditor";
import GoalProgress from "@/components/GoalProgress";
import SollView from "@/components/SollView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { cardImageSrc, extractSetCode } from "@/lib/utils";
import RarityBadge from "@/components/RarityBadge";
import { useI18n } from "@/lib/i18n";
import { useSets } from "@/lib/useSets";

export default function CollectionDetailPage() {
  const params = useParams();
  const id = Number(params?.id);
  const { t, lang } = useI18n();
  const { sets } = useSets();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [cards, setCards] = useState<CollectionCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [editingPages, setEditingPages] = useState(false);

  // View aus sessionStorage lesen (nach Hydration — kein SSR-Mismatch)
  useEffect(() => {
    if (!Number.isNaN(id)) {
      try {
        const s = sessionStorage.getItem(`collection_view_${id}`);
        if (s === "binder" || s === "grid") setView(s);
      } catch {}
    }
  }, [id]);

  useEffect(() => {
    if (!Number.isNaN(id)) {
      try { sessionStorage.setItem(`collection_view_${id}`, view); } catch {}
    }
  }, [view, id]);

  // Karten-Zuweisung (Suche)
  const [showAssign, setShowAssign] = useState(false);
  const [query, setQuery] = useState("");
  // allSearchResults: aus API (nur bei Query-Änderung aktualisiert, kein Flicker bei cards-Änderung)
  const [allSearchResults, setAllSearchResults] = useState<Card[]>([]);
  const [searching, setSearching] = useState(false);
  // results: lokal gefiltert (Karten die schon in der Sammlung sind, werden ausgeblendet)
  const results = allSearchResults.filter((c) => !cards.some((cc) => cc.id === c.id));

  const loadCards = useCallback((silent = false) => {
    if (!silent) setLoading(true);
    collectionApi.cards(id).then((r) => {
      const data = r.data;
      // Alt-Daten ohne Position einmalig normalisieren
      if (data.length && data.some((c) => c.position == null)) {
        collectionApi
          .reorder(id, data.map((c) => c.id))
          .then(() => collectionApi.cards(id).then((r2) => setCards(r2.data)))
          .catch(() => setCards(data))
          .finally(() => { if (!silent) setLoading(false); });
      } else {
        setCards(data);
        if (!silent) setLoading(false);
      }
    }).catch(() => { if (!silent) setLoading(false); });
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
  // Kein 'cards' in deps → kein Flicker wenn Karte hinzugefügt wird (lokales Filter reicht)
  useEffect(() => {
    if (!showAssign) { setAllSearchResults([]); return; }
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        const p: Record<string, unknown> = { limit: 80, besessen: true };
        const q = query.trim();
        if (q) p.search = q; // immer Text-Suche, keine exakte pokedex_nr-Suche
        const r = await cardApi.list(p);
        setAllSearchResults(r.data.items);
      } finally {
        setSearching(false);
      }
    }, 350);
    return () => clearTimeout(handle);
  }, [query, showAssign]);

  const handleAdd = async (cardId: number) => {
    try {
      await collectionApi.addCard(id, cardId);
      toast.success(t.collection_added);
      loadCards(true);
      loadMeta();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemove = async (cardId: number) => {
    try {
      await collectionApi.removeCard(id, cardId);
      loadCards(true);
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
      loadCards(true);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleMoveToSlot = async (cardId: number, slot: number) => {
    try {
      await collectionApi.moveToSlot(id, cardId, slot);
      loadCards(true);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleAddAtSlot = async (cardId: number, slot: number) => {
    try {
      await collectionApi.addCard(id, cardId);
      await collectionApi.moveToSlot(id, cardId, slot);
      toast.success(t.collection_added);
      loadCards(true);
      loadMeta();
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

  const handleAddPage = async (newSlots: number) => {
    try {
      await collectionApi.update(id, { binder_slots: newSlots });
      setCollection((c) => (c ? { ...c, binder_slots: newSlots } : c));
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handlePagesChange = async (payload: {
    removeCardIds?: number[];
    positions?: { card_id: number; position: number }[];
    binderSlots?: number;
  }) => {
    try {
      if (payload.removeCardIds?.length) {
        for (const cid of payload.removeCardIds) await collectionApi.removeCard(id, cid);
      }
      if (payload.positions?.length) {
        await collectionApi.setPositions(id, payload.positions);
      }
      if (payload.binderSlots != null) {
        await collectionApi.update(id, { binder_slots: payload.binderSlots });
        setCollection((c) => (c ? { ...c, binder_slots: payload.binderSlots ?? null } : c));
      }
      loadCards(true);
      loadMeta();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const binderItems: BinderItem[] = cards.map((c, idx) => ({
    card: c,
    position: c.position ?? idx,
  }));

  // Set-Sammlung (Issue #16): Soll-Ansicht statt freier Karten-Zuweisung
  const isGoal = collection?.typ === "set_ziel";
  const zielSet = isGoal
    ? sets.find((s) => s.set_id === collection?.ziel_set_id) ?? null
    : null;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-4">
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">{t.collection_back}</Link>
      </div>

      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div className="min-w-0">
          <h1 className="text-2xl font-bold text-white">{collection?.name ?? "…"}</h1>
          {collection?.beschreibung && <p className="text-gray-400 text-sm">{collection.beschreibung}</p>}
          {isGoal && collection ? (
            <>
              <p className="text-gray-500 text-xs mt-1">
                {zielSet ? `${zielSet.name} (${zielSet.code})` : collection.ziel_set_id}
                {collection.ziel_folierung ? ` · ${collection.ziel_folierung}` : ""}
                {collection.ziel_sprache ? ` · ${collection.ziel_sprache}` : ""}
                {` · ${collection.ziel_master_set ? t.soll_master_badge : t.soll_official_badge}`}
              </p>
              {collection.fortschritt && (
                <GoalProgress progress={collection.fortschritt} className="mt-2 max-w-xs" />
              )}
            </>
          ) : (
            <p className="text-gray-500 text-xs mt-1">{t.collections_card_count(collection?.karten_anzahl ?? cards.length)}</p>
          )}
        </div>
        {!isGoal && (
          <div className="flex items-center gap-2 flex-wrap">
            <ViewToggle value={view} onChange={setView} />
            <button type="button"
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
        )}
      </div>

      {/* Zuweisungs-Panel */}
      {!isGoal && showAssign && (
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
                  <button type="button"
                    key={c.id}
                    onClick={() => handleAdd(c.id)}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData(ASSIGN_DRAG_TYPE, String(c.id))}
                    title={t.collection_add}
                    className="group text-left bg-gray-800/40 rounded-lg overflow-hidden border border-transparent hover:border-green-500 cursor-grab"
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
                      <div className="flex items-center gap-1 text-gray-500 text-[10px]">
                        <span className="truncate">{extractSetCode(c.set_edition)} {c.karten_nr ?? ""}</span>
                        {c.seltenheit && <RarityBadge rarity={c.seltenheit} language={c.sprache} size="sm" />}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {isGoal && collection ? (
        <SollView collection={collection} onMetaChange={loadMeta} />
      ) : loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : view === "binder" ? (
        <div>
          <div className="flex justify-end mb-2">
            <button type="button"
              onClick={() => setEditingPages((v) => !v)}
              className={`text-sm rounded px-3 py-1.5 ${
                editingPages ? "bg-green-600 text-white hover:bg-green-700" : "bg-pokemon-card text-gray-300 hover:text-white"
              }`}
            >
              {editingPages ? t.binder_done : t.binder_manage_pages}
            </button>
          </div>
          {editingPages ? (
            <BinderEditor
              items={binderItems}
              apiBase={API_BASE}
              layout={layout}
              binderSlots={collection?.binder_slots ?? null}
              onPagesChange={handlePagesChange}
            />
          ) : (
            <BinderView
              items={binderItems}
              apiBase={API_BASE}
              layout={layout}
              onLayoutChange={handleLayoutChange}
              editable
              onMoveToSlot={handleMoveToSlot}
              onAddAtSlot={handleAddAtSlot}
              binderSlots={collection?.binder_slots ?? null}
              onAddPage={handleAddPage}
              storageKey={`binder_page_coll_${id}`}
            />
          )}
        </div>
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
