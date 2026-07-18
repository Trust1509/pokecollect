"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import { Star, Check } from "lucide-react";
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
  // Auswahl-Modus (Issue #23): additiv zur Einzel-Kachel-Aktion
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkCollId, setBulkCollId] = useState("");

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

  // ── Auswahl-Modus + Bulk-Add (Issue #23) ─────────────────────────────────
  const toggleSelectMode = () => {
    setSelectMode((m) => {
      if (m) { setSelectedIds(new Set()); setBulkCollId(""); }
      return !m;
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const pageIds = useMemo(() => (data?.items ?? []).map((c) => c.card_id), [data]);
  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.has(id));

  const toggleSelectAllPage = () => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      const allSel = pageIds.every((id) => next.has(id));
      pageIds.forEach((id) => (allSel ? next.delete(id) : next.add(id)));
      return next;
    });
  };

  // Bulk = bestehende Einzel-Endpunkte in einer Schleife (DRY, kein Bulk-API).
  const runBulk = async (
    action: (id: string) => Promise<unknown>,
    doneMsg: (n: number) => string,
  ) => {
    const ids = Array.from(selectedIds);
    if (!ids.length || bulkBusy) return;
    setBulkBusy(true);
    let ok = 0;
    for (const id of ids) {
      try { await action(id); ok += 1; } catch { /* Fehler unten gezählt */ }
    }
    const fail = ids.length - ok;
    if (fail === 0) toast.success(doneMsg(ok));
    else if (ok > 0) toast.error(t.catalog_bulk_partial(ok, fail));
    else toast.error(t.collections_error);
    setBulkBusy(false);
    // Nach Erfolg Auswahl leeren + Katalog/meta refetchen (#14-State)
    setSelectedIds(new Set());
    setBulkCollId("");
    catalogApi.meta().then((r) => setMeta(r.data)).catch(() => {});
    load();
  };

  const bulkWishlist = () =>
    runBulk((id) => catalogApi.addWishlist(id), (n) => t.catalog_bulk_wishlist_done(n));

  const bulkCollection = () => {
    const cid = Number(bulkCollId);
    if (!cid) return;
    return runBulk((id) => catalogApi.addCollection(id, cid), (n) => t.catalog_bulk_collection_done(n));
  };

  return (
    <div className={selectMode && selectedIds.size > 0 ? "pb-24 md:pb-20" : undefined}>
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

      {/* Auswahl-Umschalter + Pager (Issue #23) */}
      <div className="flex items-center justify-between gap-2 flex-wrap mb-2">
        <div className="flex items-center gap-3">
          <button type="button"
            onClick={toggleSelectMode}
            className={`text-sm rounded px-3 py-1.5 border ${selectMode ? "bg-pokemon-accent border-pokemon-accent text-white" : "bg-pokemon-card border-gray-700 text-gray-200 hover:text-white"}`}
          >
            {selectMode ? t.catalog_select_done : t.catalog_select_mode}
          </button>
          {selectMode && !!data?.items.length && (
            <button type="button"
              onClick={toggleSelectAllPage}
              className="text-xs text-gray-400 hover:text-white underline"
            >
              {allOnPageSelected ? t.catalog_select_none_page : t.catalog_select_all_page}
            </button>
          )}
        </div>
        {data && <Pager page={page} pages={data.pages} onPage={setPage} />}
      </div>

      {loading && !data ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : !data?.items.length ? (
        <div className="flex items-center justify-center h-48 text-gray-500">{t.catalog_empty}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
          {data.items.map((c) => {
            const name = lang === "EN" && c.name_en ? c.name_en : (c.name ?? c.name_en ?? c.card_id);
            const isAdded = added[c.card_id];
            const isSelected = selectedIds.has(c.card_id);
            return (
              <div key={c.card_id} className={`relative rounded-lg border overflow-hidden bg-pokemon-card ${isSelected ? "border-pokemon-accent ring-2 ring-pokemon-accent" : "border-gray-700"}`}>
                <button type="button"
                  onClick={() => (selectMode ? toggleSelect(c.card_id) : setSelected(c))}
                  className="block w-full text-left" title={name}>
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
                {selectMode ? (
                  <div aria-hidden
                    className={`absolute top-1 right-1 w-6 h-6 rounded-md flex items-center justify-center pointer-events-none ${isSelected ? "bg-pokemon-accent text-white" : "bg-black/60 text-white/70 border border-white/60"}`}
                  >
                    {isSelected && <Check size={16} />}
                  </div>
                ) : (
                  <button type="button"
                    onClick={() => addWishlist(c)}
                    title={t.catalog_add_wishlist}
                    className={`absolute top-1 right-1 rounded-full p-1.5 ${isAdded ? "bg-pokemon-yellow text-black" : "bg-black/60 text-white hover:bg-black/80"}`}
                  >
                    <Star size={16} fill={isAdded ? "currentColor" : "none"} />
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {data && <Pager page={page} pages={data.pages} onPage={setPage} size="lg" className="justify-center mt-4 pb-2" />}

      {selected && (
        <CatalogCardModal card={selected} collections={collections} onClose={() => setSelected(null)} />
      )}

      {/* Aktionsleiste bei Auswahl (Issue #23) — auf dem Handy über der Bottom-Nav */}
      {selectMode && selectedIds.size > 0 && (
        <div className="fixed inset-x-0 z-40 bottom-[calc(3.5rem_+_env(safe-area-inset-bottom))] md:bottom-0 bg-pokemon-dark/95 backdrop-blur border-t border-gray-800 p-3">
          <div className="max-w-screen-2xl mx-auto flex items-center gap-2 flex-wrap">
            <span className="text-sm text-gray-200 font-medium shrink-0">{t.catalog_bulk_selected(selectedIds.size)}</span>
            <div className="flex items-center gap-2 flex-wrap justify-end flex-1 min-w-0">
              <button type="button"
                onClick={bulkWishlist}
                disabled={bulkBusy}
                className="bg-pokemon-yellow text-black text-sm font-medium rounded px-3 py-1.5 hover:opacity-90 disabled:opacity-50 flex items-center gap-1 whitespace-nowrap"
              >
                <Star size={15} /> {t.catalog_bulk_wishlist(selectedIds.size)}
              </button>
              <select
                value={bulkCollId}
                onChange={(e) => setBulkCollId(e.target.value)}
                disabled={bulkBusy}
                className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm max-w-[40vw] md:max-w-none disabled:opacity-50"
              >
                <option value="">{t.catalog_add_collection} …</option>
                {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
              <button type="button"
                onClick={bulkCollection}
                disabled={bulkBusy || !bulkCollId}
                className="bg-pokemon-accent text-white text-sm rounded px-3 py-1.5 hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
              >
                {t.catalog_bulk_collection(selectedIds.size)}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
