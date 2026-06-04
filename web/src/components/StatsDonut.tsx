"use client";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

const COLORS = [
  "#EF5350", "#FFCA28", "#42A5F5", "#66BB6A", "#AB47BC",
  "#26C6DA", "#FF7043", "#8D6E63", "#78909C", "#EC407A",
];

type Props = { data: Record<string, number>; title: string };

export default function StatsDonut({ data, title }: Props) {
  const entries = Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, value]) => ({ name, value }));

  return (
    <div>
      <h3 className="text-gray-300 font-medium mb-2">{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={entries}
            innerRadius={55}
            outerRadius={85}
            dataKey="value"
            paddingAngle={2}
          >
            {entries.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(v: number, name: string) => [v, name]}
            contentStyle={{ background: "#1f2937", border: "none", color: "#fff" }}
          />
          <Legend
            iconType="circle"
            iconSize={8}
            formatter={(value) => <span className="text-xs text-gray-300">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
