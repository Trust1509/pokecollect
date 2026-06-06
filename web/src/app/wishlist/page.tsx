"use client";
import { useCallback, useEffect, useState } from "react";
import { Card, Enums, cardApi } from "@/lib/api";
import CardGrid from "@/components/CardGrid";
import BinderView from "@/components/BinderView";
import ViewToggle, { ViewMode } from "@/components/ViewToggle";
import { useI18n } from "@/lib/i18n";

const LAYOUT_KEY = "wishlist_binder_layout";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function WishlistPage() {
  const { t } = useI18n();
  const [cards, setCards] = useState<Card[]>([]);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [priority, setPriority] = useState<string>("");
  const [view, setView] = useState<ViewMode>("grid");
  const [layout, setLayout] = useState("3x3");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const s = sessionStorage.getItem("wishlist_view");
    if (s === "binder" || s === "grid") setView(s);
  }, []);

  useEffect(() => {
    const s = localStorage.getItem(LAYOUT_KEY);
    if (s) setLayout(s);
  }, []);

  useEffect(() => { try { sessionStorage.setItem("wishlist_view", view); } catch {} }, [view]);

  const handleLayoutChange = (l: string) => {
    setLayout(l);
    if (typeof window !== "undefined") localStorage.setItem(LAYOUT_KEY, l);
  };

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, unknown> = { wunschliste: true, limit: 200 };
    if (priority) params.prioritaet = priority;
    cardApi.list(params).then((r) => setCards(r.data.items)).finally(() => setLoading(false));
  }, [priority]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { cardApi.enums().then((r) => setEnums(r.data)); }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">⭐ {t.wishlist_title}</h1>
          <p className="text-gray-400 text-sm">{t.wishlist_subtitle}</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          >
            <option value="">{t.wishlist_all_priorities}</option>
            {(enums?.prioritaet ?? []).map((p) => (
              <option key={p} value={p}>{p === "Chase" ? `🔥 ${p}` : p}</option>
            ))}
          </select>
          <ViewToggle value={view} onChange={setView} />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : cards.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.wishlist_empty}</div>
      ) : view === "binder" ? (
        <BinderView
          items={cards.map((c, idx) => ({ card: c, position: idx }))}
          apiBase={API_BASE}
          layout={layout}
          onLayoutChange={handleLayoutChange}
        />
      ) : (
        <CardGrid cards={cards} apiBase={API_BASE} />
      )}
    </div>
  );
}
