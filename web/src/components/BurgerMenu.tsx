"use client";
// Burger-Menü (☰, oben links): Slide-out mit ALLEN Navigationszielen aus der
// zentralen Registry — die vollständige Navigation, mobil wie am Desktop.
// Behebt den Ur-Bug: Ziele wie Statistiken/Sealed, die nicht in der BottomNav
// liegen, sind hierüber immer erreichbar (Issue #34).
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useI18n } from "@/lib/i18n";
import { NAV_TARGETS, isNavActive } from "@/lib/navRegistry";

export default function BurgerMenu() {
  const { t } = useI18n();
  const pathname = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const btnRef = useRef<HTMLButtonElement>(null);

  // Bei Pfadwechsel schließen (Navigation aus dem Menü heraus).
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  // Offen: ESC schließt, Fokus wandert ins Panel und bleibt gefangen (Tab-Zyklus),
  // Body-Scroll gesperrt; beim Schließen Fokus zurück auf den Öffnen-Button.
  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    const btn = btnRef.current;

    const focusables = () =>
      Array.from(
        panel?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])') ?? [],
      );

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        return;
      }
      if (e.key === "Tab") {
        const els = focusables();
        if (els.length === 0) return;
        const first = els[0];
        const last = els[els.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    focusables()[0]?.focus();

    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
      btn?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={() => setOpen(true)}
        aria-label={t.nav_menu_open}
        aria-haspopup="dialog"
        aria-expanded={open}
        className="shrink-0 -ml-1 p-1.5 text-gray-300 hover:text-white rounded focus:outline-none focus:ring-2 focus:ring-pokemon-blue"
      >
        <Menu size={22} />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50"
          role="dialog"
          aria-modal="true"
          aria-label={t.nav_menu_title}
        >
          {/* Overlay-Klick schließt */}
          <button
            type="button"
            aria-label={t.nav_menu_close}
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-black/60"
          />
          <div
            ref={panelRef}
            className="absolute left-0 top-0 h-full w-72 max-w-[80%] bg-pokemon-card border-r border-gray-800 shadow-xl flex flex-col pb-[env(safe-area-inset-bottom)]"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
              <span className="font-bold text-pokemon-yellow">PokéCollect</span>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label={t.nav_menu_close}
                className="text-gray-400 hover:text-white rounded focus:outline-none focus:ring-2 focus:ring-pokemon-blue"
              >
                <X size={20} />
              </button>
            </div>
            <nav className="flex-1 overflow-y-auto py-2" aria-label={t.nav_menu_title}>
              {NAV_TARGETS.map((target) => {
                const active = isNavActive(pathname, target);
                const { key, href, Icon, labelKey } = target;
                return (
                  <Link
                    key={key}
                    href={href}
                    onClick={() => setOpen(false)}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-3 px-4 py-3 text-sm ${
                      active
                        ? "text-pokemon-yellow bg-gray-800/60"
                        : "text-gray-300 hover:text-white hover:bg-gray-800/40"
                    }`}
                  >
                    <Icon size={20} className="shrink-0" />
                    <span>{t[labelKey]}</span>
                  </Link>
                );
              })}
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
