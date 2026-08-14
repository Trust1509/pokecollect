"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { useI18n } from "@/lib/i18n";
import {
  PRICE_SOURCE_COLOR as SOURCE_COLOR, PriceSourceKey as SourceKey,
  priceSourceKey as sourceKey, priceSourceRate as kursOf,
} from "@/lib/priceSource";

// quelle kommt seit v1.7.1 auditierbar mit (z. B. "tcgplayer-usd@0.8666") —
// ein Basiswechsel Cardmarket→TCGplayer sähe sonst wie eine Preisbewegung aus (#65).
type HistoryEntry = { erfasst_am: string; wert_eur: string | null; quelle?: string | null };

type Props = { history: HistoryEntry[] };

export default function PriceChart({ history }: Props) {
  const { t } = useI18n();
  if (!history.length) return <p className="text-gray-500 text-sm">{t.price_history_empty}</p>;

  const data = history.map((h) => ({
    date: new Date(h.erfasst_am).toLocaleDateString(t.date_locale),
    wert: h.wert_eur ? parseFloat(h.wert_eur) : null,
    source: sourceKey(h.quelle),
    kurs: kursOf(h.quelle),
  }));

  // Nur GEZEICHNETE Punkte zählen; „unbekannt" (Alt-Daten ohne Quelle) löst
  // die Mehrquellen-Anzeige nie aus — erst ZWEI bekannte Basen gelten als
  // echter Quellenwechsel (Panel-Fund).
  const sources = Array.from(new Set(data.filter((d) => d.wert != null).map((d) => d.source)));
  const multiSource = sources.filter((s) => s !== "unbekannt").length > 1;

  const sourceLabel = (s: SourceKey, kurs?: string | null) =>
    s === "tcgplayer" ? t.price_source_tcgplayer(kurs ?? null)
    : s === "oauth" ? t.price_source_oauth
    : s === "cardmarket" ? t.price_source_cardmarket
    : t.price_source_unknown;

  return (
    <div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 11 }} />
          <YAxis
            tickFormatter={(v) => `€${v}`}
            tick={{ fill: "#9ca3af", fontSize: 11 }}
            width={50}
          />
          <Tooltip
            formatter={(v: number, _name, item) => {
              const p = (item as { payload?: { source: SourceKey; kurs: string | null } }).payload;
              const label = p ? sourceLabel(p.source, p.kurs) : "";
              return [`€${v.toFixed(2)}${label ? ` · ${label}` : ""}`, t.price_chart_value];
            }}
            contentStyle={{ background: "#1f2937", border: "none", color: "#fff" }}
          />
          <Line
            type="monotone"
            dataKey="wert"
            stroke="#FFCA28"
            strokeWidth={2}
            connectNulls
            // Punkte nur einfärben, wenn wirklich mehrere Quellen vorkommen —
            // sonst bleibt der Chart so ruhig wie bisher.
            dot={multiSource ? (props) => {
              const { cx, cy, payload, index } = props as unknown as {
                cx?: number; cy?: number; index: number;
                payload: { source: SourceKey; wert: number | null };
              };
              if (cx == null || cy == null || payload.wert == null) return <g key={index} />;
              return (
                <circle key={index} cx={cx} cy={cy} r={3}
                        fill={SOURCE_COLOR[payload.source]} stroke="#1f2937" strokeWidth={1} />
              );
            } : false}
          />
        </LineChart>
      </ResponsiveContainer>
      {multiSource && (
        <div className="flex flex-wrap gap-3 mt-1 text-xs text-gray-400">
          {sources.map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span className="w-2 h-2 rounded-full inline-block" style={{ background: SOURCE_COLOR[s] }} />
              {sourceLabel(s)}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
