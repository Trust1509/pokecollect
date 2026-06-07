"use client";
import { useState } from "react";
import toast from "react-hot-toast";
import { CatalogItem, Collection, catalogApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Props = {
  card: CatalogItem;
  collections: Collection[];
  onClose: () => void;
};

export default function CatalogCardModal({ card, collections, onClose }: Props) {
  const { t, lang } = useI18n();
  const [busy, setBusy] = useState(false);
  const [collId, setCollId] = useState("");
  const name = lang === "EN" && card.name_en ? card.name_en : (card.name ?? card.name_en ?? card.card_id);

  const wish = async () => {
    setBusy(true);
    try { await catalogApi.addWishlist(card.card_id); toast.success(t.catalog_added_wishlist); }
    catch { toast.error(t.collections_error); }
    finally { setBusy(false); }
  };
  const addColl = async () => {
    if (!collId) return;
    setBusy(true);
    try { await catalogApi.addCollection(card.card_id, Number(collId)); toast.success(t.catalog_added_collection); }
    catch { toast.error(t.collections_error); }
    finally { setBusy(false); }
  };

  const row = (label: string, val: React.ReactNode) =>
    val ? <div className="flex justify-between gap-3"><dt className="text-gray-500">{label}</dt><dd className="text-white text-right">{val}</dd></div> : null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-pokemon-card rounded-lg p-4 max-w-md w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-3">
          <h2 className="text-white font-bold text-lg">{name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">✕</button>
        </div>

        <div className="flex gap-4">
          <div className="w-40 shrink-0">
            {card.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={card.image_url} alt={name} className="w-full rounded" />
            ) : (
              <div className="aspect-[63/88] bg-gray-800 rounded flex items-center justify-center text-gray-600 text-xs text-center p-2">{name}</div>
            )}
          </div>
          <dl className="flex-1 text-sm space-y-1 min-w-0">
            {row(t.field_set, card.set_name ? `${card.set_name} (${card.set_code})` : card.set_code)}
            {row(t.field_card_nr, card.local_id)}
            {row(t.field_pokedex_nr, card.dex_id ? `#${card.dex_id}` : null)}
            {row(t.field_rarity, card.rarity)}
            {row(t.catalog_illustrator, card.illustrator)}
            {row(t.field_english_name, card.name_en)}
          </dl>
        </div>

        <div className="mt-4 space-y-2">
          <button onClick={wish} disabled={busy}
            className="w-full bg-pokemon-yellow text-black font-medium rounded px-3 py-2 hover:opacity-90 disabled:opacity-50">
            ★ {t.catalog_add_wishlist}
          </button>
          <div className="flex gap-2">
            <select value={collId} onChange={(e) => setCollId(e.target.value)}
              className="flex-1 min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
              <option value="">{t.catalog_add_collection} …</option>
              {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button onClick={addColl} disabled={busy || !collId}
              className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50">
              {t.collection_add}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
