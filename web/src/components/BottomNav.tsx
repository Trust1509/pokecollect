"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, Library, ScanLine, Star, Settings } from "lucide-react";
import { useI18n } from "@/lib/i18n";

export default function BottomNav() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";

  // Scan-Seite hat eine eigene fixierte Aktionsleiste → Bottom-Nav ausblenden
  if (pathname.startsWith("/scan")) return null;

  const items = [
    { href: "/", label: t.nav_collection, Icon: LayoutGrid, exact: true },
    { href: "/collections", label: t.nav_collections, Icon: Library },
    { href: "/scan", label: t.nav_scan_short, Icon: ScanLine, primary: true },
    { href: "/wishlist", label: t.nav_wishlist, Icon: Star },
    { href: "/settings", label: t.nav_settings, Icon: Settings },
  ];

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(href + "/");

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 bg-pokemon-card border-t border-gray-800 flex items-stretch justify-around pb-[env(safe-area-inset-bottom)]">
      {items.map(({ href, label, Icon, primary }) => {
        const active = isActive(href, (href === "/"));
        return (
          <Link
            key={href}
            href={href}
            className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2 min-h-[56px] text-[10px] ${
              active ? "text-pokemon-yellow" : "text-gray-400"
            }`}
          >
            <span className={primary ? "bg-pokemon-blue text-white rounded-full p-1.5 -mt-3 shadow-lg" : ""}>
              <Icon size={primary ? 22 : 20} />
            </span>
            <span className="truncate max-w-[64px]">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
