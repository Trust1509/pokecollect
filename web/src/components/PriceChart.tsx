"use client";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

type HistoryEntry = { erfasst_am: string; wert_eur: string | null };

type Props = { history: HistoryEntry[] };

export default function PriceChart({ history }: Props) {
  if (!history.length) return <p className="text-gray-500 text-sm">Keine Preishistorie vorhanden.</p>;

  const data = history.map((h) => ({
    date: new Date(h.erfasst_am).toLocaleDateString("de-AT"),
    wert: h.wert_eur ? parseFloat(h.wert_eur) : null,
  }));

  return (
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
          formatter={(v: number) => [`€${v.toFixed(2)}`, "Wert"]}
          contentStyle={{ background: "#1f2937", border: "none", color: "#fff" }}
        />
        <Line
          type="monotone"
          dataKey="wert"
          stroke="#FFCA28"
          strokeWidth={2}
          dot={false}
          connectNulls
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
