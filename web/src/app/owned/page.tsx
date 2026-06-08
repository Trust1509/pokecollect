"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { cardApi, setsApi, CardListResponse, Enums, PokemonSet, settingsApi, AppSettings } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import { formatEur } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function AllOwnedPage() {
  const { t } = useI18n();
  const [data, setData] = useState<CardListResponse | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [value, setValue] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({ besessen: true });
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await cardApi.list({ ...filters, page, limit: appSettings?.cards_per_page ?? 48 });
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, [filters, page, appSettings]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    setsApi.list().then((r) => setSets(r.data)).catch(() => {});
    cardApi.stats().then((r) => setValue(r.data.gesamtwert_eur)).catch(() => {});
    settingsApi.get().then((r) => {
      setAppSettings(r.data);
      setFilters((f) => ({ ...f, sort: f.sort ?? r.data.default_sort }));
    }).catch(() => {});
    if (typeof window !== "undefined" && window.innerWidth >= 768) setFiltersOpen(true);
  }, []);

  const handleFilters = (f: Filters) => { setPage(1); setFilters(f); };

  return (
    <div>
      <div className="mb-2">
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">← {t.nav_collections}</Link>
      </div>

      <div className="sticky top-0 z-30 bg-pokemon-dark pt-1 pb-3">
        <h1 className="text-xl sm:text-2xl font-bold text-white mb-2">📚 {t.collections_all_owned}</h1>

        {/* Mobile: Anzahl + Lupe + Wert */}
        <div className="sm:hidden flex items-center justify-between gap-2 bg-pokemon-card rounded-lg px-3 py-2 mb-3 text-sm">
          <span className="font-semibold text-white">{t.home_cards_count(data?.total ?? 0)}</span>
          <button onClick={() => setFiltersOpen((o) => !o)} className="text-gray-300 hover:text-white p-1" title={t.filter_title}>
            <Search size={18} />
          </button>
          {value && <span className="font-semibold text-yellow-400">{formatEur(value)}</span>}
        </div>

        {/* Desktop: Karten + Lupe */}
        <div className="hidden sm:flex items-center gap-4 mb-3 text-sm">
          <div className="bg-pokemon-card rounded-lg px-4 py-3">
            <div className="text-gray-400">{t.home_collected}</div>
            <div className="text-2xl font-bold text-white">{data?.total ?? 0}</div>
          </div>
          {value && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400">{t.home_total_value}</div>
              <div className="text-2xl font-bold text-yellow-400">{formatEur(value)}</div>
            </div>
          )}
          <button
            onClick={() => setFiltersOpen((o) => !o)}
            className="self-start flex items-center gap-2 bg-pokemon-card border border-gray-700 rounded px-3 py-2 text-gray-200 hover:text-white"
          >
            <Search size={16} /> {t.filter_title}
          </button>
        </div>

        <FilterSidebar
          filters={filters}
          onChange={handleFilters}
          enums={enums}
          sets={sets}
          open={filtersOpen}
          onOpenChange={setFiltersOpen}
        />

        {data && data.pages > 1 && (
          <div className="flex justify-end gap-2 text-sm items-center mt-3">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">‹</button>
            <span className="text-gray-400">{page} / {data.pages}</span>
            <button disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)} className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">›</button>
          </div>
        )}
      </div>

      <div className="mt-3">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
        ) : (
          <CardGrid cards={data?.items ?? []} apiBase={API_BASE} placeholderEnabled={appSettings?.placeholder_images_enabled ?? true} />
        )}
      </div>
    </div>
  );
}
