"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Collection, collectionApi, cardApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function CollectionsPage() {
  const { t } = useI18n();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [ownedCount, setOwnedCount] = useState<number | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  // Inline-Umbenennen
  const [editId, setEditId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const load = () => {
    setLoading(true);
    collectionApi
      .list()
      .then((r) => setCollections(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    cardApi.list({ besessen: true, limit: 1 }).then((r) => setOwnedCount(r.data.total)).catch(() => {});
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) { toast.error(t.collections_name_required); return; }
    try {
      await collectionApi.create({ name: newName.trim(), beschreibung: newDesc.trim() || null });
      toast.success(t.collections_created);
      setNewName(""); setNewDesc(""); setShowNew(false);
      load();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const startEdit = (c: Collection) => {
    setEditId(c.id);
    setEditName(c.name);
    setEditDesc(c.beschreibung ?? "");
  };

  const handleSaveEdit = async () => {
    if (editId === null) return;
    if (!editName.trim()) { toast.error(t.collections_name_required); return; }
    try {
      await collectionApi.update(editId, { name: editName.trim(), beschreibung: editDesc.trim() || null });
      toast.success(t.collections_updated);
      setEditId(null);
      load();
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleDelete = async (c: Collection) => {
    if (!confirm(t.collections_delete_confirm(c.name))) return;
    try {
      await collectionApi.delete(c.id);
      toast.success(t.collections_deleted);
      load();
    } catch {
      toast.error(t.collections_error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">{t.collections_title}</h1>
          <p className="text-gray-400 text-sm">{t.collections_subtitle}</p>
        </div>
        <button type="button"
          onClick={() => setShowNew((v) => !v)}
          className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600"
        >
          {t.collections_new}
        </button>
      </div>

      {showNew && (
        <div className="bg-pokemon-card rounded-lg p-4 mb-6 space-y-3">
          <div>
            <label className="text-gray-400 text-xs block mb-1">{t.collections_name}</label>
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder={t.collections_name_placeholder}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
          </div>
          <div>
            <label className="text-gray-400 text-xs block mb-1">{t.collections_description}</label>
            <input
              type="text"
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder={t.collections_description_placeholder}
              className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={handleCreate} className="bg-green-600 text-white text-sm px-3 py-1.5 rounded hover:bg-green-700">
              {t.collections_create}
            </button>
            <button type="button" onClick={() => setShowNew(false)} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded">
              {t.form_cancel}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Virtuelle Standard-Sammlung: alle besessenen Karten */}
          <Link href="/owned">
            <div className="bg-pokemon-card rounded-lg p-4 border-2 border-dashed border-blue-800 hover:border-blue-500 transition-colors cursor-pointer">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h2 className="text-lg font-semibold text-blue-300 hover:text-pokemon-yellow truncate">
                    📚 {t.collections_all_owned}
                  </h2>
                  <p className="text-gray-400 text-sm truncate">{t.collections_all_owned_desc}</p>
                  {ownedCount !== null && (
                    <p className="text-gray-500 text-xs mt-1">{t.collections_card_count(ownedCount)}</p>
                  )}
                </div>
              </div>
            </div>
          </Link>

          {/* TCGdex-Katalog: alle Karten zum Durchsuchen */}
          <Link href="/catalog">
            <div className="bg-pokemon-card rounded-lg p-4 border-2 border-dashed border-yellow-800 hover:border-pokemon-yellow transition-colors cursor-pointer h-full">
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-semibold text-yellow-300 hover:text-pokemon-yellow truncate">
                  🔎 {t.catalog_tile}
                </h2>
                <p className="text-gray-400 text-sm">{t.catalog_tile_desc}</p>
              </div>
            </div>
          </Link>

          {collections.length === 0 ? null : collections.map((c) => (
            <div key={c.id} className="bg-pokemon-card rounded-lg p-4">
              {editId === c.id ? (
                <div className="space-y-2">
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                  />
                  <input
                    type="text"
                    value={editDesc}
                    onChange={(e) => setEditDesc(e.target.value)}
                    placeholder={t.collections_description_placeholder}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                  />
                  <div className="flex gap-2">
                    <button type="button" onClick={handleSaveEdit} className="bg-green-600 text-white text-xs px-3 py-1.5 rounded hover:bg-green-700">
                      {t.collections_save}
                    </button>
                    <button type="button" onClick={() => setEditId(null)} className="bg-gray-700 text-white text-xs px-3 py-1.5 rounded">
                      {t.form_cancel}
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between gap-2">
                    <Link href={`/collections/${c.id}`} className="flex-1 min-w-0">
                      <h2 className="text-lg font-semibold text-white hover:text-pokemon-yellow truncate">{c.name}</h2>
                      {c.beschreibung && <p className="text-gray-400 text-sm truncate">{c.beschreibung}</p>}
                      <p className="text-gray-500 text-xs mt-1">{t.collections_card_count(c.karten_anzahl)}</p>
                    </Link>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Link href={`/collections/${c.id}`} className="text-pokemon-accent hover:text-blue-400 text-xs">
                      {t.collection_add_existing} →
                    </Link>
                    <button type="button" onClick={() => startEdit(c)} className="text-gray-400 hover:text-white text-xs ml-auto">
                      {t.collections_rename}
                    </button>
                    <button type="button" onClick={() => handleDelete(c)} className="text-red-400 hover:text-red-300 text-xs">
                      {t.collections_delete}
                    </button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
