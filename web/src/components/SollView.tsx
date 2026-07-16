"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Star } from "lucide-react";
import {
  API_BASE, CatalogItem, Collection, SollSlot, catalogApi, collectionApi,
} from "@/lib/api";
import BinderView, { BinderGhost, BinderItem } from "@/components/BinderView";
import CatalogCardModal from "@/components/CatalogCardModal";
import RarityBadge from "@/components/RarityBadge";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { useEnums } from "@/lib/useEnums";
import { useI18n } from "@/lib/i18n";
import { cardImageSrc } from "@/lib/utils";

type Props = {
  collection: Collection;
  /** Nach Kuratier-Änderungen aufrufen (Fortschritt in der Kopfzeile neu laden). */
  onMetaChange?: () => void;
};

/** Katalog-Detailansicht (CatalogCardModal) aus einem Soll-Slot speisen. */
function slotToCatalogItem(s: SollSlot): CatalogItem {
  return {
    card_id: s.tcgdex_card_id,
    set_id: s.set_id,
    set_code: s.set_code,
    set_name: s.set_name,
    local_id: s.local_id,
    name: s.name,
    name_en: s.name_en,
    dex_id: s.dex_id,
    rarity: s.rarity,
    illustrator: null,
    category: null,
    image_url: s.image_url,
    variants_normal: null,
    variants_reverse: null,
    variants_holo: null,
    variants_firstedition: null,
    enriched: null,
    owned: s.erfuellt,
    in_pokedex: false,
  };
}

/**
 * Soll-Ansicht einer Set-Sammlung (Issue #16): erfüllte Slots = besessene
 * Karte, fehlende = gedimmter Katalog-Platzhalter mit Wunschlisten-Aktion.
 * Kuratier-Modus: Slots entfernen, Folierung je Slot ändern, Karten aus dem
 * Katalog hinzufügen (bestehende Katalog-Suche + CatalogCardModal).
 */
export default function SollView({ collection, onMetaChange }: Props) {
  const { t, lang } = useI18n();
  const { enums } = useEnums();
  const [slots, setSlots] = useState<SollSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState(collection.binder_layout || "3x3");
  const [curate, setCurate] = useState(false);
  const [selected, setSelected] = useState<CatalogItem | null>(null);

  // Kuratier-Modus: Katalog-Suche (bestehende Katalog-API, Standard = Ziel-Set)
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CatalogItem[]>([]);
  const [searching, setSearching] = useState(false);

  // View aus sessionStorage lesen (nach Hydration — kein SSR-Mismatch)
  useEffect(() => {
    try {
      const s = sessionStorage.getItem(`soll_view_${collection.id}`);
      if (s === "binder" || s === "grid") setView(s);
    } catch {}
  }, [collection.id]);
  useEffect(() => {
    try { sessionStorage.setItem(`soll_view_${collection.id}`, view); } catch {}
  }, [view, collection.id]);

  const loadSlots = useCallback((silent = false) => {
    if (!silent) setLoading(true);
    collectionApi
      .soll(collection.id)
      .then((r) => setSlots(r.data))
      .catch(() => toast.error(t.collections_error))
      .finally(() => { if (!silent) setLoading(false); });
    // t ist ein stabiles Objekt je Sprache — kein Re-Fetch bei Sprachwechsel nötig
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [collection.id]);

  useEffect(() => { loadSlots(); }, [loadSlots]);

  // Katalog-Suche im Kuratier-Modus (debounced, gefiltert aufs Ziel-Set)
  useEffect(() => {
    if (!curate) { setResults([]); return; }
    const handle = setTimeout(async () => {
      setSearching(true);
      try {
        const params: Record<string, unknown> = { limit: 60, sort: "set" };
        if (collection.ziel_set_id) params.set_id = collection.ziel_set_id;
        if (query.trim()) params.q = query.trim();
        const r = await catalogApi.list(params);
        setResults(r.data.items);
      } finally {
        setSearching(false);
      }
    }, 300);
    return () => clearTimeout(handle);
  }, [curate, query, collection.ziel_set_id]);

  const afterChange = () => {
    loadSlots(true);
    onMetaChange?.();
  };

  const handleWishlist = async (slot: SollSlot) => {
    try {
      await collectionApi.sollToWishlist(collection.id, slot.id);
      toast.success(t.catalog_added_wishlist);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemove = async (slot: SollSlot) => {
    if (!confirm(t.soll_remove_confirm)) return;
    try {
      await collectionApi.removeSoll(collection.id, slot.id);
      toast.success(t.soll_removed);
      afterChange();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleFoilChange = async (slot: SollSlot, value: string) => {
    try {
      await collectionApi.updateSoll(collection.id, slot.id, {
        soll_folierung: value || null,
      });
      toast.success(t.soll_updated);
      afterChange();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleAdd = async (item: CatalogItem) => {
    try {
      await collectionApi.addSoll(collection.id, item.card_id);
      toast.success(t.soll_added);
      afterChange();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const slotName = (s: SollSlot) =>
    lang === "EN" && s.name_en ? s.name_en : (s.name ?? s.name_en ?? s.tcgdex_card_id);

  // Binder-Ansicht: erfüllte Slots als echte Karten, fehlende als Geister-Slots
  const binderItems: BinderItem[] = [];
  const ghosts: BinderGhost[] = [];
  slots.forEach((s, idx) => {
    if (s.erfuellt && s.karte) {
      binderItems.push({ card: s.karte, position: idx });
    } else {
      ghosts.push({
        position: idx,
        imageUrl: s.image_url,
        label: slotName(s),
        sub: s.local_id,
        onWishlist: () => handleWishlist(s),
        wishlistTitle: t.catalog_add_wishlist,
      });
    }
  });

  const handleLayoutChange = async (l: string) => {
    setLayout(l);
    try { await collectionApi.update(collection.id, { binder_layout: l }); } catch {/* nicht kritisch */}
  };

  const renderSlotTile = (slot: SollSlot) => {
    const name = slotName(slot);
    const foil = slot.soll_folierung ?? collection.ziel_folierung;
    const image = (
      <div className="aspect-[63/88] relative bg-gray-800">
        {slot.erfuellt && slot.karte ? (() => {
          const { src, isPlaceholder } = cardImageSrc(slot.karte, API_BASE);
          return src ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={src} alt={name} loading="lazy"
              className={`w-full h-full ${isPlaceholder ? "object-contain p-2 opacity-70" : "object-cover"}`} />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-600 text-[11px] text-center p-2">{name}</div>
          );
        })() : slot.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={slot.image_url} alt={name} loading="lazy"
            className="w-full h-full object-cover opacity-30 grayscale" />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600 text-[11px] text-center p-2 opacity-60">{name}</div>
        )}
        {!slot.erfuellt && (
          <span className="absolute top-1 left-1 bg-black/70 text-gray-300 text-[10px] px-1.5 py-0.5 rounded">
            {t.soll_missing}
          </span>
        )}
      </div>
    );

    return (
      <div
        key={slot.id}
        className={`relative rounded-lg border overflow-hidden bg-pokemon-card ${
          slot.erfuellt ? "border-green-700" : "border-gray-700"
        }`}
      >
        {slot.erfuellt && slot.karte_id && !curate ? (
          <Link href={`/cards/${slot.karte_id}`} className="block">{image}</Link>
        ) : !slot.erfuellt && !curate ? (
          <button type="button" onClick={() => setSelected(slotToCatalogItem(slot))} className="block w-full text-left">
            {image}
          </button>
        ) : (
          image
        )}

        <div className="px-1.5 py-1">
          <div className="flex items-center gap-1">
            <span className="text-xs text-white truncate flex-1">{name}</span>
            {slot.erfuellt && <span className="w-2 h-2 rounded-full bg-green-400 shrink-0" title={t.field_owned} />}
          </div>
          <div className="flex items-center justify-between text-[10px] text-gray-400 gap-1">
            <span className="font-mono shrink-0">{slot.local_id ?? ""}</span>
            <span className="truncate text-right">{foil ?? ""}</span>
            <RarityBadge rarity={slot.rarity} language={collection.ziel_sprache} size="sm" />
          </div>
        </div>

        {/* Fehlend → Wunschliste (außerhalb des Kuratier-Modus) */}
        {!slot.erfuellt && !curate && (
          <button
            type="button"
            onClick={() => handleWishlist(slot)}
            title={t.catalog_add_wishlist}
            className="absolute top-1 right-1 rounded-full p-1.5 bg-black/60 text-white hover:bg-black/80"
          >
            <Star size={14} />
          </button>
        )}

        {/* Kuratier-Modus: Folierung je Slot + Entfernen */}
        {curate && (
          <div className="px-1.5 pb-1.5 flex items-center gap-1">
            <select
              value={slot.soll_folierung ?? ""}
              onChange={(e) => handleFoilChange(slot, e.target.value)}
              className="flex-1 min-w-0 bg-gray-800 border border-gray-700 rounded px-1 py-1 text-gray-200 text-[11px]"
            >
              <option value="">{t.soll_foil_rule}</option>
              {(enums?.folierung ?? []).map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => handleRemove(slot)}
              title={t.soll_remove_title}
              className="shrink-0 text-red-400 hover:text-red-200 bg-red-950/60 rounded px-2 py-1 text-xs"
            >
              ✕
            </button>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
        <ViewToggle value={view} onChange={setView} />
        <button
          type="button"
          onClick={() => setCurate((v) => !v)}
          className={`text-sm rounded px-3 py-1.5 ${
            curate ? "bg-green-600 text-white hover:bg-green-700" : "bg-pokemon-card text-gray-300 hover:text-white"
          }`}
        >
          {curate ? t.binder_done : t.soll_curate}
        </button>
      </div>

      {/* Kuratier-Modus: Karten aus dem Katalog hinzufügen (bestehende Katalog-Suche) */}
      {curate && (
        <div className="bg-pokemon-card rounded-lg p-4 mb-4">
          <p className="text-gray-400 text-xs mb-2">{t.soll_search_hint}</p>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.catalog_search_placeholder}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-white text-sm mb-3"
          />
          {searching ? (
            <div className="text-gray-500 text-sm py-4 text-center">{t.detail_loading}</div>
          ) : results.length === 0 ? (
            <div className="text-gray-500 text-sm py-4 text-center">{t.catalog_empty}</div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2 max-h-[28rem] overflow-y-auto pr-1">
              {results.map((c) => {
                const name = lang === "EN" && c.name_en ? c.name_en : (c.name ?? c.name_en ?? c.card_id);
                return (
                  <button
                    type="button"
                    key={c.card_id}
                    onClick={() => handleAdd(c)}
                    title={t.soll_added}
                    className="group text-left bg-gray-800/40 rounded-lg overflow-hidden border border-transparent hover:border-green-500"
                  >
                    <div className="aspect-[63/88] relative bg-gray-800">
                      {c.image_url && (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={c.image_url} alt={name} loading="lazy" className="w-full h-full object-cover" />
                      )}
                      <div className="absolute inset-0 bg-green-600/0 group-hover:bg-green-600/20 flex items-center justify-center opacity-0 group-hover:opacity-100 transition">
                        <span className="bg-green-700 text-white text-xs px-2 py-1 rounded">+ {t.collection_add}</span>
                      </div>
                    </div>
                    <div className="px-1 py-1">
                      <div className="text-white text-[11px] truncate">{name}</div>
                      <div className="text-gray-500 text-[10px] font-mono">{c.local_id ?? ""}</div>
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
      ) : slots.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.soll_empty}</div>
      ) : view === "binder" ? (
        <BinderView
          items={binderItems}
          ghosts={ghosts}
          apiBase={API_BASE}
          layout={layout}
          onLayoutChange={handleLayoutChange}
          storageKey={`binder_page_soll_${collection.id}`}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {slots.map(renderSlotTile)}
        </div>
      )}

      {/* Katalog-Detail (bestehendes Modal) für fehlende Slots */}
      {selected && (
        <CatalogCardModal card={selected} collections={[]} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
