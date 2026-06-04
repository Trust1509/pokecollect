"use client";
import { useCallback, useEffect, useState } from "react";
import { cardApi, CardListResponse, Enums } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import FilterSidebar, { Filters } from "@/components/FilterSidebar";
import { formatEur } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function HomePage() {
  const [data, setData] = useState<CardListResponse | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<string[]>([]);
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [statsTotal, setStatsTotal] = useState<{
    gesamt: number;
    besessen: number;
    wert: string | null;
  } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      // Pokédex-Nummer Suche: wenn search eine reine Zahl ist, als pokedex_nr filtern
      const params: Record<string, unknown> = { ...filters, page, limit: 48 };
      if (filters.search && /^\d+$/.test(filters.search.trim())) {
        params.pokedex_nr = Number(filters.search.trim());
        delete params.search;
      }
      const res = await cardApi.list(params);
      setData(res.data);
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    cardApi.sets().then((r) => setSets(r.data));
    cardApi.stats().then((r) =>
      setStatsTotal({
        gesamt: r.data.gesamt,
        besessen: r.data.besessen,
        wert: r.data.gesamtwert_eur,
      })
    );
  }, []);

  const handleFilters = (f: Filters) => {
    setPage(1);
    setFilters(f);
  };

  return (
    <div>
      {statsTotal && (
        <div className="flex gap-6 mb-6 text-sm flex-wrap">
          <div className="bg-pokemon-card rounded-lg px-4 py-3">
            <div className="text-gray-400">Gesammelt</div>
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
          {statsTotal.wert && (
            <div className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400">Gesamtwert</div>
              <div className="text-2xl font-bold text-yellow-400">
                {formatEur(statsTotal.wert)}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-6">
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
                <span className="text-gray-400 text-sm">
                  {data?.total ?? 0} Karten
                </span>
                {data && data.pages > 1 && (
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
              <CardGrid cards={data?.items ?? []} apiBase={API_BASE} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
