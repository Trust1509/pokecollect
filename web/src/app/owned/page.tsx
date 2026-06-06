"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { cardApi, CardListResponse, Enums, settingsApi, AppSettings } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function AllOwnedPage() {
  const { t } = useI18n();
  const [data, setData] = useState<CardListResponse | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<string[]>([]);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  // Standardmäßig besessen=true, aber der User kann weiter filtern
  const [filters, setFilters] = useState<Filters>({ besessen: true });
  const [page, setPage] = useState(1);
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [loading, setLoading] = useState(false);

  // Session-Storage: View-Präferenz merken
  useEffect(() => {
    try {
      const sv = sessionStorage.getItem("owned_view");
      if (sv === "binder" || sv === "grid") setView(sv);
      const sl = localStorage.getItem("owned_binder_layout");
      if (sl) setLayout(sl);
    } catch {}
  }, []);
  useEffect(() => { try { sessionStorage.setItem("owned_view", view); } catch {} }, [view]);

  const handleLayoutChange = (l: string) => {
    setLayout(l);
    try { localStorage.setItem("owned_binder_layout", l); } catch {}
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, unknown> = {
        ...filters,
        page,
        limit: appSettings?.cards_per_page ?? 48,
      };
      const res = await cardApi.list(params);
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, [filters, page, appSettings]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    cardApi.sets().then((r) => setSets(r.data));
    settingsApi.get().then((r) => {
      setAppSettings(r.data);
      setFilters((f) => ({ ...f, sort: f.sort ?? r.data.default_sort }));
    }).catch(() => {});
  }, []);

  const handleFilters = (f: Filters) => {
    setPage(1);
    setFilters(f);
  };

  return (
    <div>
      <div className="mb-4">
        <Link href="/collections" className="text-gray-500 hover:text-white text-sm">
          ← {t.nav_collections}
        </Link>
      </div>
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-white">📚 {t.collections_all_owned}</h1>
        <p className="text-gray-400 text-sm">{t.collections_all_owned_desc}</p>
      </div>

      <div className="flex gap-6">
        <FilterSidebar
          filters={filters}
          onChange={handleFilters}
          enums={enums}
          sets={sets}
        />

        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-sm">{t.home_cards_count(data?.total ?? 0)}</span>
                  <ViewToggle value={view} onChange={setView} />
                </div>
                {data && data.pages > 1 && (
                  <div className="flex gap-2 text-sm items-center">
                    <button
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                      className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40"
                    >
                      ‹
                    </button>
                    <span className="text-gray-400">{page} / {data.pages}</span>
                    <button
                      disabled={page >= data.pages}
                      onClick={() => setPage((p) => p + 1)}
                      className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40"
                    >
                      ›
                    </button>
                  </div>
                )}
              </div>
              {view === "binder" ? (
                <BinderView
                  items={(data?.items ?? []).map((c, idx) => ({ card: c, position: idx }))}
                  apiBase={API_BASE}
                  layout={layout}
                  onLayoutChange={handleLayoutChange}
                  placeholderEnabled={appSettings?.placeholder_images_enabled ?? true}
                />
              ) : (
                <CardGrid
                  cards={data?.items ?? []}
                  apiBase={API_BASE}
                  placeholderEnabled={appSettings?.placeholder_images_enabled ?? true}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
