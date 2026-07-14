"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Star } from "lucide-react";
import {
  CatalogItem, CatalogListResponse, Collection,
  catalogApi, collectionApi,
} from "@/lib/api";
import SearchableSelect, { SelectOption } from "@/components/SearchableSelect";
import CatalogCardModal from "@/components/CatalogCardModal";
import ListPageHeader, { Pager } from "@/components/ListPageHeader";
import { useI18n } from "@/lib/i18n";
import { useIsDesktop } from "@/lib/useIsDesktop";
import { useSetOptions } from "@/lib/useSetOptions";
import { useSets } from "@/lib/useSets";

const GENERATIONS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

export default function CatalogPage() {
  const { t, lang } = useI18n();
  const [data, setData] = useState<CatalogListResponse | null>(null);
  const { sets } = useSets();
  const [illustrators, setIllustrators] = useState<string[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [meta, setMeta] = useState<{ total: number; enriched: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [added, setAdded] = useState<Record<string, boolean>>({});
  const [selected, setSelected] = useState<CatalogItem | null>(null);

  const [q, setQ] = useState("");
  const [setCode, setSetCode] = useState("");
  const [illustrator, setIllustrator] = useState("");
  const [generation, setGeneration] = useState("");
  const [sort, setSort] = useState<"set" | "name" | "dex">("set");
  const [page, setPage] = useState(1);
  const [filterOpen, setFilterOpen] = useState(false);

  useEffect(() => {
    catalogApi.meta().then((r) => setMeta(r.data)).catch(() => {});
    catalogApi.illustrators().then((r) => setIllustrators(r.data)).catch(() => {});
    collectionApi.list().then((r) => setCollections(r.data)).catch(() => {});
  }, []);

  // Auf Desktop standardmäßig geöffnete Filter
  const isDesktop = useIsDesktop();
  useEffect(() => { if (isDesktop) setFilterOpen(true); }, [isDesktop]);

  const setOptions = useSetOptions(sets);

  const illuOptions: SelectOption[] = useMemo(
    () => illustrators.map((i) => ({ value: i, label: i })), [illustrators]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = { sort, page, limit: 60 };
      if (q.trim()) params.q = q.trim();
      if (setCode) params.set_code = setCode;
      if (illustrator) params.illustrator = illustrator;
      if (generation) params.generation = Number(generation);
      const r = await catalogApi.list(params);
      setData(r.data);
    } finally {
      setLoading(false);
    }
  }, [q, setCode, illustrator, generation, sort, page]);

  useEffect(() => { const h = setTimeout(load, 300); return () => clearTimeout(h); }, [load]);
  useEffect(() => { setPage(1); }, [q, setCode, illustrator, generation, sort]);

  const addWishlist = async (c: CatalogItem) => {
    try {
      await catalogApi.addWishlist(c.card_id);
      setAdded((a) => ({ ...a, [c.card_id]: true }));
      toast.success(t.catalog_added_wishlist);
    } catch { toast.error(t.collections_error); }
  };

  return (
    <div>
      <ListPageHeader
        title={
          <div className="mb-3 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h1 className="text-xl font-bold text-white">{t.catalog_title}</h1>
              <p className="text-gray-400 text-sm">
                {t.catalog_subtitle}{meta ? ` · ${meta.total.toLocaleString(t.date_locale)} ${t.catalog_cards}` : ""}
              </p>
            </div>
            <Link href="/collections" className="text-gray-500 hover:text-white text-sm">{t.collection_back}</Link>
          </div>
        }
      >
      {/* Filterleiste (ein-/ausklappbar wie überall) */}
      <button type="button"
        onClick={() => setFilterOpen((o) => !o)}
        className="w-full md:w-auto flex items-center justify-between gap-3 bg-pokemon-card border border-gray-700 rounded px-3 py-2 text-gray-200 mb-3"
      >
        <span>🔍 {t.filter_title}</span>
        <span className="text-gray-500">{filterOpen ? "▲" : "▼"}</span>
      </button>
      <div className={`${filterOpen ? "grid" : "hidden"} grid-cols-2 md:grid-cols-5 gap-2 mb-4`}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t.catalog_search_placeholder}
          className="col-span-2 md:col-span-1 bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
        />
        <SearchableSelect
          value={setCode} onChange={setSetCode} options={setOptions}
          allLabel={t.filter_all_sets} placeholder={t.filter_set}
        />
        <SearchableSelect
          value={illustrator} onChange={setIllustrator} options={illuOptions}
          allLabel={t.catalog_all_illustrators} placeholder={t.catalog_illustrator}
        />
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

      {(q || setCode || illustrator || generation || sort !== "set") && (
        <button type="button"
          onClick={() => { setQ(""); setSetCode(""); setIllustrator(""); setGeneration(""); setSort("set"); }}
          className="text-gray-400 hover:text-white text-xs underline"
        >
          {t.filter_reset}
        </button>
      )}
      </ListPageHeader>

      {data && <Pager page={page} pages={data.pages} onPage={setPage} className="justify-end mb-2" />}

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
                <button type="button" onClick={() => setSelected(c)} className="block w-full text-left" title={name}>
                  <div className="aspect-[63/88] relative bg-gray-800">
                    {c.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={c.image_url} alt={name} className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                      <div className="flex items-center justify-center h-full text-gray-600 text-[11px] text-center p-2">{name}</div>
                    )}
                  </div>
                  <div className="px-1.5 py-1">
                    <div className="flex items-center gap-1">
                      <span className="text-xs text-white truncate flex-1">{name}</span>
                      {c.in_pokedex && <span className="w-2 h-2 rounded-full bg-pokemon-pokedex shrink-0" title={t.detail_pokedex_flag} />}
                      {c.owned && <span className="w-2 h-2 rounded-full bg-green-400 shrink-0" title={t.field_owned} />}
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-gray-400">
                      <span className="font-mono">{c.set_code ?? c.set_id}</span>
                      <span>{c.local_id ?? ""}</span>
                    </div>
                  </div>
                </button>
                <button type="button"
                  onClick={() => addWishlist(c)}
                  title={t.catalog_add_wishlist}
                  className={`absolute top-1 right-1 rounded-full p-1.5 ${isAdded ? "bg-pokemon-yellow text-black" : "bg-black/60 text-white hover:bg-black/80"}`}
                >
                  <Star size={16} fill={isAdded ? "currentColor" : "none"} />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {data && <Pager page={page} pages={data.pages} onPage={setPage} size="lg" className="justify-center mt-4 pb-2" />}

      {selected && (
        <CatalogCardModal card={selected} collections={collections} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}
