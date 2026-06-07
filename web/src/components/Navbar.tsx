"use client";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { APP_VERSION } from "@/lib/version";

export default function Navbar() {
  const { t, lang, setLang } = useI18n();

  return (
    <nav className="border-b border-gray-800 bg-pokemon-card px-4 sm:px-6 py-3 flex items-center gap-4 sm:gap-6">
      <Link href="/" className="text-lg sm:text-xl font-bold text-pokemon-yellow shrink-0">
        PokéCollect
      </Link>
      <span className="text-gray-600 text-xs hidden sm:inline">v{APP_VERSION}</span>

      {/* Desktop-Links (auf Mobile übernimmt die Bottom-Nav) */}
      <div className="hidden md:flex items-center gap-6">
        <Link href="/" className="text-gray-300 hover:text-white text-sm">{t.nav_collection}</Link>
        <Link href="/collections" className="text-gray-300 hover:text-white text-sm">{t.nav_collections}</Link>
        <Link href="/wishlist" className="text-gray-300 hover:text-white text-sm">{t.nav_wishlist}</Link>
        <Link href="/stats" className="text-gray-300 hover:text-white text-sm">{t.nav_statistics}</Link>
      </div>

      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        <button
          onClick={() => setLang(lang === "DE" ? "EN" : "DE")}
          className="text-gray-400 hover:text-white text-xs border border-gray-700 rounded px-2 py-1"
          title={lang === "DE" ? "Switch to English" : "Zu Deutsch wechseln"}
        >
          {lang === "DE" ? "EN" : "DE"}
        </button>
        <Link href="/settings" className="hidden md:inline-block text-gray-400 hover:text-white text-sm">⚙ {t.nav_settings}</Link>
        <Link
          href="/scan"
          className="hidden md:inline-block bg-pokemon-blue text-white text-sm px-3 py-1.5 rounded hover:bg-blue-500 text-center"
        >
          {t.nav_scan}
        </Link>
        <Link
          href="/cards/new"
          className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600 inline-block text-center"
        >
          {t.nav_add_card}
        </Link>
      </div>
    </nav>
  );
}
