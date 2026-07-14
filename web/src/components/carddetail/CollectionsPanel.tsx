"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Collection, collectionApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Sammlungs-Zuordnung der Kartendetailseite (Issue #14): zeigt die Sammlungen
// der Karte und erlaubt Zuweisen/Entfernen. Herausgeschnitten aus
// cards/[id]/page.tsx — Verhalten 1:1, lädt seine Daten selbst.

type Props = {
  cardId: number;
};

export default function CollectionsPanel({ cardId }: Props) {
  const { t } = useI18n();
  const [cardCollections, setCardCollections] = useState<Collection[]>([]);
  const [allCollections, setAllCollections] = useState<Collection[]>([]);

  const loadCollections = () => {
    collectionApi.forCard(cardId).then((r) => setCardCollections(r.data)).catch(() => {});
  };

  useEffect(() => {
    collectionApi.forCard(cardId).then((r) => setCardCollections(r.data)).catch(() => {});
    collectionApi.list().then((r) => setAllCollections(r.data)).catch(() => {});
  }, [cardId]);

  const handleAddToCollection = async (collectionId: number) => {
    try {
      await collectionApi.addCard(collectionId, cardId);
      loadCollections();
      toast.success(t.collection_added);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemoveFromCollection = async (collectionId: number) => {
    try {
      await collectionApi.removeCard(collectionId, cardId);
      loadCollections();
      toast.success(t.collection_removed);
    } catch {
      toast.error(t.collections_error);
    }
  };

  return (
    <div className="bg-pokemon-card rounded-lg p-4">
      <h2 className="text-gray-300 font-medium mb-3">{t.detail_collections}</h2>
      {cardCollections.length === 0 ? (
        <p className="text-gray-500 text-sm mb-3">{t.detail_collections_none}</p>
      ) : (
        <div className="flex flex-wrap gap-2 mb-3">
          {cardCollections.map((c) => (
            <span key={c.id} className="inline-flex items-center gap-1 bg-gray-800 rounded-full px-3 py-1 text-sm text-white">
              <Link href={`/collections/${c.id}`} className="hover:text-pokemon-yellow">{c.name}</Link>
              <button type="button"
                onClick={() => handleRemoveFromCollection(c.id)}
                className="text-gray-500 hover:text-red-400 ml-1"
                title={t.collection_remove}
              >
                ✕
              </button>
            </span>
          ))}
        </div>
      )}
      <select
        value=""
        onChange={(e) => { if (e.target.value) handleAddToCollection(Number(e.target.value)); }}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
      >
        <option value="">{t.detail_collections_add}</option>
        {allCollections
          .filter((c) => !cardCollections.some((cc) => cc.id === c.id))
          .map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
      </select>
    </div>
  );
}
