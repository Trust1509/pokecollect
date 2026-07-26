"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useI18n } from "@/lib/i18n";
import { NAV_TARGETS, NavTarget, isNavActive } from "@/lib/navRegistry";
import { useBottomNavConfig } from "@/lib/useBottomNav";

export default function BottomNav() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";
  // Konfigurierbare Schnellzugriffe (localStorage, Issue #34). Alle Ziele lesen
  // aus der zentralen Registry — nichts hier hartkodiert (DRY).
  const { keys } = useBottomNavConfig();

  // Scan-Seite hat eine eigene fixierte Aktionsleiste → Bottom-Nav ausblenden;
  // vor dem Login (Issue #1) ebenfalls kein App-Chrome
  if (pathname.startsWith("/scan") || pathname === "/login") return null;

  const items = keys
    .map((k) => NAV_TARGETS.find((target) => target.key === k))
    .filter((x): x is NavTarget => Boolean(x));

  // Leere Auswahl → keine Leiste (alles bleibt über das Burger-Menü erreichbar).
  if (items.length === 0) return null;

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-pokemon-card border-t border-gray-800 flex items-stretch justify-around pb-[env(safe-area-inset-bottom)]">
      {items.map((target) => {
        const { key, href, Icon, labelKey } = target;
        const active = isNavActive(pathname, target);
        // Scan behält seinen hervorgehobenen "primären" Look, wo immer er sitzt.
        const primary = key === "scan";
        return (
          <Link
            key={key}
            href={href}
            aria-current={active ? "page" : undefined}
            className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] text-[10px] ${
              active ? "text-pokemon-yellow" : "text-gray-400"
            }`}
          >
            <span className={primary ? "bg-pokemon-blue text-white rounded-full p-1.5 -mt-3 shadow-lg" : ""}>
              <Icon size={primary ? 22 : 20} />
            </span>
            <span className="truncate max-w-[64px]">{t[labelKey]}</span>
          </Link>
        );
      })}
    </nav>
  );
}
