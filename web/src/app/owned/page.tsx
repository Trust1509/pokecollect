"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cardApi, setsApi, CardListResponse, Enums, PokemonSet, settingsApi, AppSettings } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import ListPageHeader from "@/components/ListPageHeader";
import { formatEur } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";
import { useIsDesktop } from "@/lib/useIsDesktop";

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
  }, []);

  // Auf Desktop standardmäßig geöffnete Filter
  const isDesktop = useIsDesktop();
  useEffect(() => { if (isDesktop) setFiltersOpen(true); }, [isDesktop]);

  const handleFilters = (f: Filters) => { setPage(1); setFilters(f); };

  return (
    <div>
      <div className="mb-2">
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">← {t.nav_collections}</Link>
      </div>

      <ListPageHeader
        title={<h1 className="text-xl sm:text-2xl font-bold text-white mb-2">📚 {t.collections_all_owned}</h1>}
        mobileLeft={<span className="font-semibold text-white">{t.home_cards_count(data?.total ?? 0)}</span>}
        mobileRight={value && <span className="font-semibold text-yellow-400">{formatEur(value)}</span>}
        tiles={[
          { label: t.home_collected, value: data?.total ?? 0 },
          ...(value ? [{
            label: t.home_total_value,
            value: formatEur(value),
            valueClass: "text-yellow-400",
          }] : []),
        ]}
        onToggleFilters={() => setFiltersOpen((o) => !o)}
        pager={data ? { page, pages: data.pages, onPage: setPage } : null}
      >
        <FilterSidebar
          filters={filters}
          onChange={handleFilters}
          enums={enums}
          sets={sets}
          open={filtersOpen}
          onOpenChange={setFiltersOpen}
        />
      </ListPageHeader>

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
