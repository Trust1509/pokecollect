"use client";
import { useCallback, useEffect, useState } from "react";
import { cardApi, CardListResponse, Enums, settingsApi, AppSettings } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import { formatEur } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function HomePage() {
  const { t } = useI18n();
  const [data, setData] = useState<CardListResponse | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<string[]>([]);
  const [appSettings, setAppSettings] = useState<AppSettings | null>(null);
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState<number>(1);
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [loading, setLoading] = useState(false);

  // Filter / Seite / Ansicht aus sessionStorage lesen (nach Hydration)
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
  }, []);

  // Filter / Seite / Ansicht über Navigation hinweg speichern
  useEffect(() => { try { sessionStorage.setItem("pokedex_filters", JSON.stringify(filters)); } catch {} }, [filters]);
  useEffect(() => { try { sessionStorage.setItem("pokedex_page", String(page)); } catch {} }, [page]);
  useEffect(() => { try { sessionStorage.setItem("pokedex_view", view); } catch {} }, [view]);

  const handleLayoutChange = (l: string) => {
    setLayout(l);
    try { localStorage.setItem("pokedex_binder_layout", l); } catch {}
  };
  const [statsTotal, setStatsTotal] = useState<{
    gesamt: number;
    besessen: number;
    wert: string | null;
  } | null>(null);
  const [pokedexCollected, setPokedexCollected] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Im Binder paginiert die Binder-Ansicht selbst → alle Karten laden,
      // damit es nicht zwei konkurrierende Seitenwechsler gibt und neue Karten
      // auf späteren Seiten sichtbar sind.
      const isBinder = view === "binder";
      const params: Record<string, unknown> = {
        ...filters,
        page: isBinder ? 1 : page,
        limit: isBinder ? 2000 : (appSettings?.cards_per_page ?? 48),
        pokedex_view: true,
      };
      const res = await cardApi.list(params);
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, [filters, page, appSettings, view]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    cardApi.sets().then((r) => setSets(r.data));
    settingsApi.get().then((r) => {
      setAppSettings(r.data);
      setFilters((f) => ({ ...f, sort: f.sort ?? r.data.default_sort }));
    }).catch(() => {/* Settings optional – Defaults gelten */});
    cardApi.stats().then((r) =>
      setStatsTotal({
        gesamt: r.data.gesamt,
        besessen: r.data.besessen,
        wert: r.data.gesamtwert_eur,
      })
    );
    // Pokédex-Fortschritt: Anzahl gesammelter Pokémon (im_pokedex=True ≙ je 1 pro Pokémon)
    cardApi.list({ im_pokedex: true, limit: 1 }).then((r) => setPokedexCollected(r.data.total));
  }, []);

  const handleFilters = (f: Filters) => {
    setPage(1);
    setFilters(f);
  };

  return (
    <div>
      {(statsTotal || pokedexCollected !== null) && (
        <div className="flex gap-4 mb-6 text-sm flex-wrap">
          {/* Pokédex-Fortschritt */}
          {pokedexCollected !== null && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-pokemon-pokedex inline-block" />
                Pokédex
              </div>
              <div className="text-2xl font-bold text-pokemon-pokedex">
                {pokedexCollected}{" "}
                <span className="text-gray-500 text-base">/ 1025</span>
              </div>
              <div className="mt-1 h-1.5 bg-gray-700 rounded-full w-48">
                <div
                  className="h-full bg-pokemon-pokedex rounded-full"
                  style={{ width: `${(pokedexCollected / 1025) * 100}%` }}
                />
              </div>
            </div>
          )}
          {/* Gesamtzahl besessener Karten (inkl. Duplikate) */}
          {statsTotal && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400">{t.home_collected}</div>
              <div className="text-2xl font-bold text-white">
                {statsTotal.besessen}{" "}
                <span className="text-gray-500 text-base">/ {statsTotal.gesamt}</span>
              </div>
              <div className="mt-1 h-1.5 bg-gray-700 rounded-full w-48">
                <div
                  className="h-full bg-green-500 rounded-full"
                  style={{
                    width: `${statsTotal.gesamt ? (statsTotal.besessen / statsTotal.gesamt) * 100 : 0}%`,
                  }}
                />
              </div>
            </div>
          )}
          {statsTotal?.wert && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400">{t.home_total_value}</div>
              <div className="text-2xl font-bold text-yellow-400">
                {formatEur(statsTotal.wert)}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-col md:flex-row gap-4 md:gap-6">
        <FilterSidebar
          filters={filters}
          onChange={handleFilters}
          enums={enums}
          sets={sets}
        />

        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-gray-500">
              Lädt …
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-gray-400 text-sm">
                    {t.home_cards_count(data?.total ?? 0)}
                  </span>
                  <ViewToggle value={view} onChange={setView} />
                </div>
                {view !== "binder" && data && data.pages > 1 && (
                  <div className="flex gap-2 text-sm items-center">
                    <button
                      disabled={page <= 1}
                      onClick={() => setPage((p) => p - 1)}
                      className="px-2 py-1 bg-pokemon-card rounded disabled:opacity-40"
                    >
                      ‹
                    </button>
                    <span className="text-gray-400">
                      {page} / {data.pages}
                    </span>
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
                  storageKey="binder_page_home"
                />
              ) : (
                <CardGrid cards={data?.items ?? []} apiBase={API_BASE} placeholderEnabled={appSettings?.placeholder_images_enabled ?? true} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
