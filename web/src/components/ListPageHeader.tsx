"use client";
import { ReactNode } from "react";
import { Search } from "lucide-react";
import { useI18n } from "@/lib/i18n";

// Gemeinsamer Listen-Kopf für Pokédex / Besessen / Katalog (Issue #8):
// Sticky-Wrapper + Mobile-Statuszeile (Wert · Lupe · Wert) + Desktop-Kacheln
// + Filter-Knopf + Steuerzeile mit Pager. Seiten liefern nur noch Inhalte.

export type PagerProps = {
  page: number;
  pages: number;
  onPage: (p: number) => void;
  size?: "sm" | "lg";
  className?: string;
};

/** Einheitlicher ‹ n / m ›-Pager (vorher 5-fach dupliziert). */
export function Pager({ page, pages, onPage, size = "sm", className = "" }: PagerProps) {
  if (pages <= 1) return null;
  const btn = `${size === "lg" ? "px-3 py-1.5" : "px-2 py-1"} bg-pokemon-card rounded disabled:opacity-40`;
  return (
    <div className={`flex gap-2 text-sm items-center ${className}`}>
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)} className={btn}>‹</button>
      <span className="text-gray-400">{page} / {pages}</span>
      <button type="button" disabled={page >= pages} onClick={() => onPage(page + 1)} className={btn}>›</button>
    </div>
  );
}

export type HeaderTile = {
  label: ReactNode;
  value: ReactNode;
  valueClass?: string;
  /** Fortschrittsbalken 0–100 (optional), z. B. Pokédex-Fortschritt. */
  bar?: { pct: number; cls: string } | null;
};

type Props = {
  /** Optionale Titelzeile oberhalb der Statuszeile (Besessen, Katalog). */
  title?: ReactNode;
  /** Linker/rechter Inhalt der Mobile-Statuszeile (Lupe sitzt dazwischen). */
  mobileLeft?: ReactNode;
  mobileRight?: ReactNode;
  /** Desktop-Kacheln; ohne Angabe entfällt die Kachelzeile. */
  tiles?: HeaderTile[];
  onToggleFilters?: () => void;
  /** Punkt-Indikator am Filter-Knopf bei aktiven Filtern. */
  filterActive?: boolean;
  /** FilterSidebar bzw. seitenspezifische Filter-UI. */
  children?: ReactNode;
  /** Linke Seite der Steuerzeile (z. B. Anzahl + ViewToggle). */
  controls?: ReactNode;
  pager?: PagerProps | null;
};

export default function ListPageHeader({
  title, mobileLeft, mobileRight, tiles, onToggleFilters, filterActive,
  children, controls, pager,
}: Props) {
  const { t } = useI18n();
  const showMobileRow = mobileLeft !== undefined || mobileRight !== undefined;
  return (
    <div className="sticky top-0 z-30 bg-pokemon-dark pt-1 pb-3">
      {title}

      {/* Mobile: Statuswert + Lupe + Statuswert in einer Zeile */}
      {showMobileRow && (
        <div className="sm:hidden flex items-center justify-between gap-2 bg-pokemon-card rounded-lg px-3 py-2 mb-3 text-sm">
          {mobileLeft}
          {onToggleFilters && (
            <button type="button" onClick={onToggleFilters} className="text-gray-300 hover:text-white p-1" title={t.filter_title}>
              <Search size={18} />
            </button>
          )}
          {mobileRight}
        </div>
      )}

      {/* Desktop: Kacheln + Lupe */}
      {tiles && (
        <div className="hidden sm:flex items-center gap-4 mb-3 text-sm flex-wrap">
          {tiles.map((tile, i) => (
            <div key={i} className="bg-pokemon-card rounded-lg px-4 py-3">
              <div className="text-gray-400 flex items-center gap-1.5">{tile.label}</div>
              <div className={`text-2xl font-bold ${tile.valueClass ?? "text-white"}`}>{tile.value}</div>
              {tile.bar && (
                <div className="mt-1 h-1.5 bg-gray-700 rounded-full w-48">
                  <div className={`h-full rounded-full ${tile.bar.cls}`} style={{ width: `${tile.bar.pct}%` }} />
                </div>
              )}
            </div>
          ))}
          {onToggleFilters && (
            <button
              type="button"
              onClick={onToggleFilters}
              className="self-start flex items-center gap-2 bg-pokemon-card border border-gray-700 rounded px-3 py-2 text-gray-200 hover:text-white"
            >
              <Search size={16} /> {t.filter_title}{filterActive ? " •" : ""}
            </button>
          )}
        </div>
      )}

      {children}

      {/* Steuerzeile: linke Controls + Pager */}
      {(controls || pager) && (
        <div className={`flex items-center ${controls ? "justify-between" : "justify-end"} mt-3`}>
          {controls}
          {pager && <Pager {...pager} />}
        </div>
      )}
    </div>
  );
}
