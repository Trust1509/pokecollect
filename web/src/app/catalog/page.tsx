"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Star } from "lucide-react";
import { CatalogItem, CatalogListResponse, PokemonSet, catalogApi, setsApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export default function CatalogPage() {
  const { t, lang } = useI18n();
  const [data, setData] = useState<CatalogListResponse | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [meta, setMeta] = useState<{ total: number; enriched: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState<Record<string, boolean>>({});

  const [q, setQ] = useState("");
  const [setCode, setSetCode] = useState("");
  const [generation, setGeneration] = useState("");
  const [sort, setSort] = useState<"set" | "name" | "dex">("set");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setsApi.list().then((r) => setSets(r.data)).catch(() => {});
    catalogApi.meta().then((r) => setMeta(r.data)).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { sort, page, limit: 60 };
      if (q.trim()) params.q = q.trim();
      if (setCode) params.set_code = setCode;
      if (generation) params.generation = Number(generation);
      const r = await catalogApi.list(params);
      setData(r.data);
    } finally {
      setLoading(false);
    }
  }, [q, setCode, generation, sort, page]);

  // Debounce Suche/Filter
  useEffect(() => {
    const h = setTimeout(load, 300);
    return () => clearTimeout(h);
  }, [load]);

  useEffect(() => { setPage(1); }, [q, setCode, generation, sort]);

  const addWishlist = async (c: CatalogItem) => {
    try {
      await catalogApi.addWishlist(c.card_id);
      setAdded((a) => ({ ...a, [c.card_id]: true }));
      toast.success(t.catalog_added_wishlist);
    } catch {
      toast.error(t.collections_error);
    }
  };

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">{t.catalog_title}</h1>
          <p className="text-gray-400 text-sm">
            {t.catalog_subtitle}{meta ? ` · ${meta.total.toLocaleString("de")} ${t.catalog_cards}` : ""}
          </p>
        </div>
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">{t.collection_back}</Link>
      </div>

      {/* Filterleiste */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t.catalog_search_placeholder}
          className="col-span-2 md:col-span-1 bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
        />
        <select value={setCode} onChange={(e) => setSetCode(e.target.value)}
          className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
          <option value="">{t.filter_all_sets}</option>
          {sets.map((s) => <option key={s.code} value={s.code}>{s.code} · {s.name}</option>)}
        </select>
        <select value={generation} onChange={(e) => setGeneration(e.target.value)}
          className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
          <option value="">{t.filter_generation}: {t.filter_all}</option>
          {GENERATIONS.map((g) => <option key={g} value={g}>Gen {g}</option>)}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value as "set" | "name" | "dex")}
          className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
          <option value="set">{t.catalog_sort_set}</option>
          <option value="name">{t.catalog_sort_name}</option>
          <option value="dex">{t.catalog_sort_dex}</option>
        </select>
      </div>

      {/* Paginierung oben */}
      {data && data.pages > 1 && (
        <div className="flex justify-end items-center gap-2 text-sm mb-2">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
            className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">‹</button>
          <span className="text-gray-400">{page} / {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}
            className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">›</button>
        </div>
      )}

      {loading && !data ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : !data?.items.length ? (
        <div className="flex items-center justify-center h-48 text-gray-500">{t.catalog_empty}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {data.items.map((c) => {
            const name = lang === "EN" && c.name_en ? c.name_en : (c.name ?? c.name_en ?? c.card_id);
            const isAdded = added[c.card_id];
            return (
              <div key={c.card_id} className="relative rounded-lg border border-gray-700 overflow-hidden bg-pokemon-card">
                <div className="aspect-[63/88] relative bg-gray-800">
                  {c.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.image_url} alt={name} className="w-full h-full object-cover" loading="lazy" />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-600 text-[11px] text-center p-2">{name}</div>
                  )}
                  {/* Stern → Wunschliste */}
                  <button
                    onClick={() => addWishlist(c)}
                    title={t.catalog_add_wishlist}
                    className={`absolute top-1 right-1 rounded-full p-1.5 ${isAdded ? "bg-pokemon-yellow text-black" : "bg-black/60 text-white hover:bg-black/80"}`}
                  >
                    <Star size={16} fill={isAdded ? "currentColor" : "none"} />
                  </button>
                </div>
                <div className="px-1.5 py-1">
                  <div className="text-xs text-white truncate">{name}</div>
                  <div className="flex items-center justify-between text-[10px] text-gray-400">
                    <span className="font-mono">{c.set_code ?? c.set_id}</span>
                    <span>{c.local_id ?? ""}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Paginierung unten */}
      {data && data.pages > 1 && (
        <div className="flex justify-center items-center gap-2 text-sm mt-4 pb-2">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40">‹</button>
          <span className="text-gray-400">{page} / {data.pages}</span>
          <button disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1.5 bg-pokemon-card rounded disabled:opacity-40">›</button>
        </div>
      )}
    </div>
  );
}
