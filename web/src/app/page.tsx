"use client";
import { useEffect, useMemo, useState } from "react";
import { Search } from "lucide-react";
import { cardApi, setsApi, CardListResponse, Enums, PokemonSet, settingsApi, AppSettings } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import { formatEur, cardMatchesFilters, hasActiveFilters } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function HomePage() {
  const { t } = useI18n();
  const [data, setData] = useState<CardListResponse | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState<number>(1);
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [loading, setLoading] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [statsTotal, setStatsTotal] = useState<{ wert: string | null } | null>(null);
  const [pokedexCollected, setPokedexCollected] = useState<number | null>(null);

  // Persistenz
  useEffect(() => {
    try {
      const sf = sessionStorage.getItem("pokedex_filters");
      if (sf) setFilters(JSON.parse(sf) as Filters);
      const sp = sessionStorage.getItem("pokedex_page");
      if (sp) setPage(Number(sp) || 1);
      const sv = sessionStorage.getItem("pokedex_view");
      if (sv === "binder" || sv === "grid") setView(sv);
      const sl = localStorage.getItem("pokedex_binder_layout");
      if (sl) setLayout(sl);
    } catch {}
    if (typeof window !== "undefined" && window.innerWidth >= 768) setFiltersOpen(true);
  }, []);
  useEffect(() => { try { sessionStorage.setItem("pokedex_filters", JSON.stringify(filters)); } catch {} }, [filters]);
  useEffect(() => { try { sessionStorage.setItem("pokedex_page", String(page)); } catch {} }, [page]);
  useEffect(() => { try { sessionStorage.setItem("pokedex_view", view); } catch {} }, [view]);

  const handleLayoutChange = (l: string) => {
    setLayout(l);
    try { localStorage.setItem("pokedex_binder_layout", l); } catch {}
  };

  // Raster: serverseitig gefiltert + paginiert
  useEffect(() => {
    if (view !== "grid") return;
    let cancel = false;
    setLoading(true);
    cardApi.list({ ...filters, page, limit: appSettings?.cards_per_page ?? 48, pokedex_view: true })
      .then((r) => { if (!cancel) setData(r.data); })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [view, filters, page, appSettings]);

  // Binder: ALLE Karten laden (fixe Plätze) – Filter dimmt nur, statt zu entfernen
  useEffect(() => {
    if (view !== "binder") return;
    let cancel = false;
    setLoading(true);
    cardApi.list({ page: 1, limit: 2000, pokedex_view: true })
      .then((r) => { if (!cancel) setData(r.data); })
      .finally(() => { if (!cancel) setLoading(false); });
    return () => { cancel = true; };
  }, [view, appSettings]);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    setsApi.list().then((r) => setSets(r.data)).catch(() => {});
    settingsApi.get().then((r) => {
      setAppSettings(r.data);
      setFilters((f) => ({ ...f, sort: f.sort ?? r.data.default_sort }));
    }).catch(() => {});
    cardApi.stats().then((r) => setStatsTotal({ wert: r.data.gesamtwert_eur }));
    cardApi.list({ im_pokedex: true, limit: 1 }).then((r) => setPokedexCollected(r.data.total));
  }, []);

  const handleFilters = (f: Filters) => { setPage(1); setFilters(f); };

  // Dimmen im Binder: nur Karten hervorheben, die dem Filter entsprechen
  const highlightIds = useMemo(() => {
    if (view !== "binder" || !data || !hasActiveFilters(filters)) return null;
    const s = new Set<number>();
    for (const c of data.items) if (cardMatchesFilters(c, filters)) s.add(c.id);
    return s;
  }, [view, data, filters]);

  const placeholderEnabled = appSettings?.placeholder_images_enabled ?? true;

  return (
    <div>
      {/* Fixierte Kopfzeile: Statistik + Filter + Steuerung; nur Karten scrollen */}
      <div className="sticky top-0 z-30 bg-pokemon-dark pt-1 pb-3">
        {/* Mobile: Pokédex + Lupe + Wert in einer Zeile */}
        <div className="sm:hidden flex items-center justify-between gap-2 bg-pokemon-card rounded-lg px-3 py-2 mb-3 text-sm">
          <span className="flex items-center gap-1.5 font-semibold text-pokemon-pokedex">
            <span className="w-2 h-2 rounded-full bg-pokemon-pokedex inline-block" />
            {pokedexCollected ?? 0} <span className="text-gray-500 font-normal">/ 1025</span>
          </span>
          <button type="button" onClick={() => setFiltersOpen((o) => !o)} className="text-gray-300 hover:text-white p-1" title={t.filter_title}>
            <Search size={18} />
          </button>
          {statsTotal?.wert && <span className="font-semibold text-yellow-400">{formatEur(statsTotal.wert)}</span>}
        </div>

        {/* Desktop: Karten + Lupe */}
        <div className="hidden sm:flex items-center gap-4 mb-3 text-sm flex-wrap">
          {pokedexCollected !== null && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-pokemon-pokedex inline-block" />Pokédex
              </div>
              <div className="text-2xl font-bold text-pokemon-pokedex">
                {pokedexCollected} <span className="text-gray-500 text-base">/ 1025</span>
              </div>
              <div className="mt-1 h-1.5 bg-gray-700 rounded-full w-48">
                <div className="h-full bg-pokemon-pokedex rounded-full" style={{ width: `${(pokedexCollected / 1025) * 100}%` }} />
              </div>
            </div>
          )}
          {statsTotal?.wert && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400">{t.home_total_value}</div>
              <div className="text-2xl font-bold text-yellow-400">{formatEur(statsTotal.wert)}</div>
            </div>
          )}
          <button type="button"
            onClick={() => setFiltersOpen((o) => !o)}
            className="self-start flex items-center gap-2 bg-pokemon-card border border-gray-700 rounded px-3 py-2 text-gray-200 hover:text-white"
          >
            <Search size={16} /> {t.filter_title}{hasActiveFilters(filters) ? " •" : ""}
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

        {/* Steuerung: Anzahl + Ansicht + (Raster-)Pager */}
        <div className="flex items-center justify-between mt-3">
          <div className="flex items-center gap-3">
            <span className="text-gray-400 text-sm">{t.home_cards_count(data?.total ?? 0)}</span>
            <ViewToggle value={view} onChange={setView} />
          </div>
          {view !== "binder" && data && data.pages > 1 && (
            <div className="flex gap-2 text-sm items-center">
              <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">‹</button>
              <span className="text-gray-400">{page} / {data.pages}</span>
              <button type="button" disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)} className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40">›</button>
            </div>
          )}
        </div>
      </div>

      {/* Scrollbereich: Karten / Binder */}
      <div className="mt-3">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
        ) : view === "binder" ? (
          <BinderView
            items={(data?.items ?? []).map((c, idx) => ({ card: c, position: idx }))}
            apiBase={API_BASE}
            layout={layout}
            onLayoutChange={handleLayoutChange}
            placeholderEnabled={placeholderEnabled}
            storageKey="binder_page_home"
            highlightIds={highlightIds}
          />
        ) : (
          <CardGrid cards={data?.items ?? []} apiBase={API_BASE} placeholderEnabled={placeholderEnabled} />
        )}
      </div>
    </div>
  );
}
