"use client";
import { useCallback, useEffect, useState } from "react";
import Image from "next/image";
import { API_BASE, SealedEnums, SealedProduct, sealedApi } from "@/lib/api";
import SearchableSelect from "@/components/SearchableSelect";
import SealedFormModal from "@/components/sealed/SealedFormModal";
import { useSets } from "@/lib/useSets";
import { useSetOptions } from "@/lib/useSetOptions";
import { formatEur, imageUrl } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

// Sealed-Produkte-Seite (Issue #35): Grid mit Foto/Typ/Set(s)/Zustand/Wert,
// Filter nach Typ/Set/Zustand, Anlage-/Detail-Formular als Modal. Mobile-first.
// Die /sealed-Navigation baut #34 (Nav-Registry) — hier NUR die Seite.

// Tile eines Sealed-Produkts.
function SealedTile({
  product, setLabel, onOpen, t,
}: {
  product: SealedProduct;
  setLabel: (code: string) => string;
  onOpen: () => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const src = product.bild_thumbnail_pfad
    ? imageUrl(product.bild_thumbnail_pfad, API_BASE, product.hinzugefuegt_am)
    : null;
  const gv = product.unrealisierter_gv_eur != null ? parseFloat(product.unrealisierter_gv_eur) : null;

  return (
    <button type="button" onClick={onOpen}
      className="text-left bg-pokemon-card rounded-lg border-2 border-gray-700 overflow-hidden hover:scale-[1.02] hover:shadow-lg transition-transform">
      <div className="aspect-square relative bg-gray-800">
        {src ? (
          <Image src={src} alt={product.name} fill className="object-cover" sizes="(max-width: 640px) 45vw, 20vw" />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600 text-5xl">📦</div>
        )}
        {product.typ && (
          <span className="absolute top-1 left-1 bg-black/70 text-white text-[10px] px-1.5 py-0.5 rounded">
            {product.typ}
          </span>
        )}
      </div>
      <div className="px-2 pt-1.5 pb-2 space-y-0.5">
        <div className="text-sm text-white font-medium truncate">{product.name}</div>
        <div className="flex items-center gap-1 text-xs text-gray-400">
          <span className="truncate flex-1">
            {product.set_codes.length ? product.set_codes.map(setLabel).join(", ") : "–"}
          </span>
          {product.zustand && <span className="shrink-0 text-gray-500">{product.zustand}</span>}
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-yellow-400">{product.wert_eur ? formatEur(product.wert_eur) : ""}</span>
          {gv != null && (
            <span className={gv >= 0 ? "text-green-400" : "text-red-400"}>
              {gv > 0 ? "+" : ""}{formatEur(gv.toFixed(2))}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

export default function SealedPage() {
  const { t } = useI18n();
  const { sets } = useSets();
  const setOptions = useSetOptions(sets);
  const [items, setItems] = useState<SealedProduct[]>([]);
  const [enums, setEnums] = useState<SealedEnums | null>(null);
  const [loading, setLoading] = useState(true);

  // Filter
  const [typ, setTyp] = useState("");
  const [setFilter, setSetFilter] = useState("");
  const [zustand, setZustand] = useState("");

  // Modal: undefined = zu, null = Neuanlage, Produkt = Bearbeiten
  const [editing, setEditing] = useState<SealedProduct | null | undefined>(undefined);

  const setLabel = useCallback(
    (code: string) => setOptions.find((o) => o.value === code)?.label ?? code,
    [setOptions],
  );

  useEffect(() => { sealedApi.enums().then((r) => setEnums(r.data)).catch(() => {}); }, []);

  const load = useCallback(() => {
    setLoading(true);
    const params: Record<string, unknown> = {};
    if (typ) params.typ = typ;
    if (setFilter) params.set = setFilter;
    if (zustand) params.zustand = zustand;
    sealedApi.list(params).then((r) => setItems(r.data)).finally(() => setLoading(false));
  }, [typ, setFilter, zustand]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-start justify-between mb-6 flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">📦 {t.sealed_title}</h1>
          <p className="text-gray-400 text-sm">{t.sealed_subtitle}</p>
        </div>
        <button type="button" onClick={() => setEditing(null)}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 text-sm shrink-0">
          {t.sealed_new}
        </button>
      </div>

      {/* Filter: Typ / Set / Zustand — mobil einspaltig */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-5">
        <select value={typ} onChange={(e) => setTyp(e.target.value)}
          className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
          <option value="">{t.sealed_all_types}</option>
          {(enums?.typ ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <SearchableSelect
          value={setFilter}
          onChange={setSetFilter}
          options={setOptions}
          allLabel={t.filter_all_sets}
          placeholder={t.filter_set}
        />
        <select value={zustand} onChange={(e) => setZustand(e.target.value)}
          className="bg-pokemon-card border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
          <option value="">{t.sealed_all_conditions}</option>
          {(enums?.zustand ?? []).map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-500">{t.detail_loading}</div>
      ) : items.length === 0 ? (
        <div className="flex items-center justify-center h-48 text-gray-500 text-center px-4">{t.sealed_empty}</div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {items.map((p) => (
            <SealedTile key={p.id} product={p} setLabel={setLabel} onOpen={() => setEditing(p)} t={t} />
          ))}
        </div>
      )}

      {editing !== undefined && (
        <SealedFormModal
          product={editing}
          enums={enums}
          onClose={() => setEditing(undefined)}
          onSaved={load}
        />
      )}
    </div>
  );
}
