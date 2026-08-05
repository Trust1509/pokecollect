"use client";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { API_BASE, Card, Collection, cardApi, collectionApi } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { useEnums } from "@/lib/useEnums";
import { useI18n } from "@/lib/i18n";

const LAYOUT_KEY = "wishlist_binder_layout";

// Wunschlisten-Karte planend einer freien Sammlung zuordnen (Issue #29):
// kleines „+"-Overlay mit Auswahl der freien Sammlungen. Die Karte bleibt auf
// der Wunschliste und erscheint in der Sammlung als geplanter Geister-Slot.
function AddToCollectionOverlay({
  card, collections, t,
}: {
  card: Card;
  collections: Collection[];
  t: ReturnType<typeof useI18n>["t"];
}) {
  const [open, setOpen] = useState(false);
  if (!collections.length) return null;
  const add = async (collectionId: number) => {
    setOpen(false);
    try {
      await collectionApi.addCard(collectionId, card.id);
      toast.success(t.collection_added);
    } catch {
      toast.error(t.collections_error);
    }
  };
  return (
    <div className="relative">
      <button
        type="button"
        title={t.catalog_add_collection}
        onClick={() => setOpen((o) => !o)}
        className="rounded-full w-7 h-7 flex items-center justify-center bg-black/70 text-white hover:bg-pokemon-accent text-base leading-none shadow"
      >
        +
      </button>
      {open && (
        <div className="absolute right-0 mt-1 w-40 max-h-48 overflow-y-auto bg-pokemon-card border border-gray-700 rounded shadow-lg z-20">
          {collections.map((c) => (
            <button
              type="button"
              key={c.id}
              onClick={() => add(c.id)}
              className="block w-full text-left px-2 py-1.5 text-xs text-gray-200 hover:bg-pokemon-accent hover:text-white truncate"
            >
              {c.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WishlistPage() {
  const { t } = useI18n();
  const [cards, setCards] = useState<Card[]>([]);
  const { enums } = useEnums();
  const [priority, setPriority] = useState<string>("");
  const [sprache, setSprache] = useState<string>("");
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [loading, setLoading] = useState(true);
  // Freie Sammlungen für „zu Sammlung hinzufügen" (Set-Sammlungen bleiben außen
  // vor — die verwalten ihre Karten über die Soll-Liste; Issue #29).
  const [freeCollections, setFreeCollections] = useState<Collection[]>([]);

  useEffect(() => {
    collectionApi.list()
      .then((r) => setFreeCollections(r.data.filter((c) => c.typ !== "set_ziel")))
      .catch(() => setFreeCollections([]));
  }, []);

  useEffect(() => {
    const s = sessionStorage.getItem("wishlist_view");
    if (s === "binder" || s === "grid") setView(s);
  }, []);

  useEffect(() => {
    const s = localStorage.getItem(LAYOUT_KEY);
    if (s) setLayout(s);
  }, []);

  useEffect(() => { try { sessionStorage.setItem("wishlist_view", view); } catch {} }, [view]);

  const handleLayoutChange = (l: string) => {
    setLayout(l);
    if (typeof window !== "undefined") localStorage.setItem(LAYOUT_KEY, l);
  };

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, unknown> = { wunschliste: true, limit: 200 };
    if (priority) params.prioritaet = priority;
    if (sprache) params.sprache = sprache;
    cardApi.list(params).then((r) => setCards(r.data.items)).finally(() => setLoading(false));
  }, [priority, sprache]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">⭐ {t.wishlist_title}</h1>
          <p className="text-gray-400 text-sm">{t.wishlist_subtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          >
            <option value="">{t.wishlist_all_priorities}</option>
            {(enums?.prioritaet ?? []).map((p) => (
              <option key={p} value={p}>{p === "Chase" ? `🔥 ${p}` : p}</option>
            ))}
          </select>
          <select
            value={sprache}
            onChange={(e) => setSprache(e.target.value)}
            className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          >
            <option value="">{t.filter_language}: {t.filter_all}</option>
            {(enums?.sprache ?? []).map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <ViewToggle value={view} onChange={setView} />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : cards.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.wishlist_empty}</div>
      ) : view === "binder" ? (
        <BinderView
          items={cards.map((c, idx) => ({ card: c, position: idx }))}
          apiBase={API_BASE}
          layout={layout}
          onLayoutChange={handleLayoutChange}
        />
      ) : (
        <CardGrid
          cards={cards}
          apiBase={API_BASE}
          renderOverlay={(card) => (
            <AddToCollectionOverlay card={card} collections={freeCollections} t={t} />
          )}
        />
      )}
    </div>
  );
}
