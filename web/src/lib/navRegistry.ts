// Zentrale Navigations-Registry — die EINE Quelle aller Navigationsziele (DRY,
// CONTEXT.md Grundsatz 1). Burger-Menü, BottomNav und die BottomNav-Konfig in
// den Einstellungen lesen ausschließlich aus dieser Liste. Neue Seiten werden
// nur hier eingetragen, nie in den einzelnen Nav-Komponenten dupliziert.
import type { LucideIcon } from "lucide-react";
import {
  LayoutGrid,
  Library,
  BookOpen,
  ScanLine,
  Star,
  BarChart3,
  Package,
  Settings,
} from "lucide-react";

// Stabile Schlüssel für localStorage — bewusst getrennt vom Pfad, damit ein
// späterer Pfad-Umbau die gespeicherte BottomNav-Konfig nicht entwertet.
export type NavKey =
  | "pokedex"
  | "collections"
  | "catalog"
  | "scan"
  | "wishlist"
  | "stats"
  | "sealed"
  | "settings";

// i18n-Keys der Labels (alle string-wertig in web/src/lib/i18n.tsx) — als Union
// getippt, damit t[labelKey] ohne Cast wieder ein string ist.
export type NavLabelKey =
  | "nav_collection"
  | "nav_collections"
  | "nav_catalog"
  | "nav_scan_short"
  | "nav_wishlist"
  | "nav_statistics"
  | "nav_sealed"
  | "nav_settings";

export type NavTarget = {
  key: NavKey;
  href: string;
  Icon: LucideIcon;
  labelKey: NavLabelKey;
  // exact: aktiver Zustand nur bei exakter Pfadgleichheit (nötig für "/", das
  // sonst jeden Pfad als Präfix matchen würde).
  exact?: boolean;
};

export const NAV_TARGETS: NavTarget[] = [
  { key: "pokedex", href: "/", Icon: LayoutGrid, labelKey: "nav_collection", exact: true },
  { key: "collections", href: "/collections", Icon: Library, labelKey: "nav_collections" },
  { key: "catalog", href: "/catalog", Icon: BookOpen, labelKey: "nav_catalog" },
  { key: "scan", href: "/scan", Icon: ScanLine, labelKey: "nav_scan_short" },
  { key: "wishlist", href: "/wishlist", Icon: Star, labelKey: "nav_wishlist" },
  { key: "stats", href: "/stats", Icon: BarChart3, labelKey: "nav_statistics" },
  // Sealed-Seite baut Issue #35 parallel — Link jetzt schon aufnehmen, auch wenn
  // die Route bis zum Merge von #35 noch 404t.
  { key: "sealed", href: "/sealed", Icon: Package, labelKey: "nav_sealed" },
  { key: "settings", href: "/settings", Icon: Settings, labelKey: "nav_settings" },
];

// Kanonische Reihenfolge der Schlüssel — die BottomNav zeigt gewählte Ziele
// immer in dieser Reihenfolge (deterministisch, unabhängig von der Klickfolge).
export const NAV_KEYS_IN_ORDER: NavKey[] = NAV_TARGETS.map((t) => t.key);

// Technischer Default der BottomNav = die bisherigen 5 Schnellzugriffe.
export const DEFAULT_BOTTOM_NAV: NavKey[] = [
  "pokedex",
  "collections",
  "scan",
  "wishlist",
  "settings",
];

// Sinnvolle Obergrenze für Schnellzugriffe unten (Platz am Handy).
export const MAX_BOTTOM_NAV = 5;

export function isNavKey(x: unknown): x is NavKey {
  return typeof x === "string" && NAV_KEYS_IN_ORDER.includes(x as NavKey);
}

// Aktiver Zustand eines Ziels für den aktuellen Pfad — eine Routine für Burger
// und BottomNav (DRY), damit beide identisch highlighten.
export function isNavActive(pathname: string, target: NavTarget): boolean {
  if (target.exact) return pathname === target.href;
  return pathname === target.href || pathname.startsWith(target.href + "/");
}
