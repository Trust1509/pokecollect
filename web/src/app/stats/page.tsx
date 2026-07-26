"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { cardApi, StatsResponse } from "@/lib/api";
import StatsDonut from "@/components/StatsDonut";
import { formatEur } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

export default function StatsPage() {
  const { t } = useI18n();
  const [stats, setStats] = useState<StatsResponse | null>(null);

  useEffect(() => {
    cardApi.stats().then((r) => setStats(r.data));
  }, []);

  if (!stats) return <div className="text-gray-500 p-8">{t.detail_loading}</div>;

  const pct = stats.gesamt ? Math.round((stats.besessen / stats.gesamt) * 100) : 0;

  // Wertentwicklung (#26): nur zeigen, wenn Kaufpreise erfasst sind.
  const hasFinance = stats.gesamt_einstand_eur != null || stats.unrealisierter_gv_eur != null;
  const gv = stats.unrealisierter_gv_eur != null ? parseFloat(stats.unrealisierter_gv_eur) : null;
  // Sealed-Produkte (#35): getrennt ausgewiesen + Karten+Sealed kombiniert
  const hasSealed = stats.sealed_anzahl > 0;
  const sealedGv = stats.sealed_unrealisierter_gv_eur != null ? parseFloat(stats.sealed_unrealisierter_gv_eur) : null;

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <h1 className="text-2xl font-bold text-white">{t.stats_title}</h1>

      {/* Übersicht — mobil einspaltig (Mobile-First, #10) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-pokemon-card rounded-lg p-4">
          <div className="text-gray-400 text-sm">{t.stats_total}</div>
          <div className="text-3xl font-bold text-white">{stats.gesamt}</div>
          <div className="text-gray-500 text-xs mt-1">{t.stats_cards_recorded}</div>
        </div>
        <div className="bg-pokemon-card rounded-lg p-4">
          <div className="text-gray-400 text-sm">{t.stats_owned}</div>
          <div className="text-3xl font-bold text-green-400">{stats.besessen}</div>
          <div className="text-gray-500 text-xs mt-1">{t.stats_pct_of_collection(pct)}</div>
          <div className="mt-2 h-1.5 bg-gray-700 rounded-full">
            <div className="h-full bg-green-500 rounded-full" style={{ width: `${pct}%` }} />
          </div>
        </div>
        <div className="bg-pokemon-card rounded-lg p-4">
          <div className="text-gray-400 text-sm">{t.stats_total_value}</div>
          <div className="text-3xl font-bold text-yellow-400">{formatEur(stats.gesamtwert_eur)}</div>
          <div className="text-gray-500 text-xs mt-1">{t.stats_cardmarket_owned}</div>
        </div>
      </div>

      {/* Wertentwicklung: Einstand vs. Gesamtwert vs. unrealisierter G/V (#26) */}
      {hasFinance && (
        <div>
          <h2 className="text-gray-300 font-medium mb-3">{t.stats_performance}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_cost_basis}</div>
              <div className="text-3xl font-bold text-white">{formatEur(stats.gesamt_einstand_eur)}</div>
              <div className="text-gray-500 text-xs mt-1">{t.stats_cost_basis_hint}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_total_value}</div>
              <div className="text-3xl font-bold text-yellow-400">{formatEur(stats.gesamtwert_eur)}</div>
              <div className="text-gray-500 text-xs mt-1">{t.stats_cardmarket_owned}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_unrealized_gain}</div>
              <div className={`text-3xl font-bold ${gv == null ? "text-gray-500" : gv >= 0 ? "text-green-400" : "text-red-400"}`}>
                {gv == null ? "–" : `${gv > 0 ? "+" : ""}${formatEur(gv.toFixed(2))}`}
              </div>
              <div className="text-gray-500 text-xs mt-1">{t.stats_unrealized_gain_hint}</div>
            </div>
          </div>
        </div>
      )}

      {/* Sealed-Produkte (#35): Sealed-Wert / Einstand / unrealisierter G/V */}
      {hasSealed && (
        <div>
          <h2 className="text-gray-300 font-medium mb-3">
            {t.stats_sealed_section} · {t.stats_sealed_products(stats.sealed_anzahl)}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_sealed_value}</div>
              <div className="text-3xl font-bold text-yellow-400">{formatEur(stats.sealed_wert_eur)}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_cost_basis}</div>
              <div className="text-3xl font-bold text-white">{formatEur(stats.sealed_einstand_eur)}</div>
              <div className="text-gray-500 text-xs mt-1">{t.stats_cost_basis_hint}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_unrealized_gain}</div>
              <div className={`text-3xl font-bold ${sealedGv == null ? "text-gray-500" : sealedGv >= 0 ? "text-green-400" : "text-red-400"}`}>
                {sealedGv == null ? "–" : `${sealedGv > 0 ? "+" : ""}${formatEur(sealedGv.toFixed(2))}`}
              </div>
              <div className="text-gray-500 text-xs mt-1">{t.stats_unrealized_gain_hint}</div>
            </div>
          </div>
        </div>
      )}

      {/* Gesamt (Karten + Sealed): Karten-Wert / Sealed-Wert / Gesamt (#35) */}
      {hasSealed && (
        <div>
          <h2 className="text-gray-300 font-medium mb-3">{t.stats_combined_section}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_cards_value}</div>
              <div className="text-3xl font-bold text-yellow-400">{formatEur(stats.gesamtwert_eur)}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_sealed_value}</div>
              <div className="text-3xl font-bold text-yellow-400">{formatEur(stats.sealed_wert_eur)}</div>
            </div>
            <div className="bg-pokemon-card rounded-lg p-4">
              <div className="text-gray-400 text-sm">{t.stats_combined_total}</div>
              <div className="text-3xl font-bold text-yellow-300">{formatEur(stats.kombiniert_wert_eur)}</div>
            </div>
          </div>
        </div>
      )}

      {/* Charts — mobil einspaltig (Mobile-First, #10) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
        <div className="bg-pokemon-card rounded-lg p-4">
          <StatsDonut data={stats.seltenheiten} title={t.stats_rarity} />
        </div>
        <div className="bg-pokemon-card rounded-lg p-4">
          <StatsDonut data={stats.sprachen} title={t.stats_languages} />
        </div>
      </div>

      {/* Top 10 */}
      <div className="bg-pokemon-card rounded-lg p-4">
        <h2 className="text-gray-300 font-medium mb-3">{t.stats_top10}</h2>
        <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 text-xs border-b border-gray-800">
              <th className="text-left pb-2">{t.stats_col_card}</th>
              <th className="text-left pb-2">{t.stats_col_set}</th>
              <th className="text-right pb-2">{t.stats_col_value}</th>
            </tr>
          </thead>
          <tbody>
            {stats.top10_teuerste.map((c) => (
              <tr key={c.id} className="border-b border-gray-800 hover:bg-gray-800">
                <td className="py-1.5">
                  <Link href={`/cards/${c.id}`} className="text-white hover:text-yellow-400">
                    {c.kartenname}
                  </Link>
                </td>
                <td className="text-gray-400">{c.set_edition ?? "–"}</td>
                <td className="text-right text-yellow-400">{formatEur(c.wert_eur)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      </div>

      {/* Zuletzt hinzugefügt */}
      <div className="bg-pokemon-card rounded-lg p-4">
        <h2 className="text-gray-300 font-medium mb-3">{t.stats_recent}</h2>
        <div className="space-y-1 text-sm">
          {stats.zuletzt_hinzugefuegt.map((c) => (
            <div key={c.id} className="flex justify-between items-center py-1 border-b border-gray-800">
              <Link href={`/cards/${c.id}`} className="text-white hover:text-yellow-400">{c.kartenname}</Link>
              <span className="text-gray-500 text-xs">
                {new Date(c.hinzugefuegt_am).toLocaleDateString(t.date_locale)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
