"use client";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { APP_VERSION } from "@/lib/version";

export default function Navbar() {
  const { t, lang, setLang } = useI18n();

  return (
    <nav className="border-b border-gray-800 bg-pokemon-card px-6 py-3 flex items-center gap-6">
      <Link href="/" className="text-xl font-bold text-pokemon-yellow">
        PokéCollect
      </Link>
      <span className="text-gray-600 text-xs">v{APP_VERSION}</span>
      <Link href="/" className="text-gray-300 hover:text-white text-sm">{t.nav_collection}</Link>
      <Link href="/stats" className="text-gray-300 hover:text-white text-sm">{t.nav_statistics}</Link>
      <div className="ml-auto flex items-center gap-3">
        <button
          onClick={() => setLang(lang === "DE" ? "EN" : "DE")}
          className="text-gray-400 hover:text-white text-xs border border-gray-700 rounded px-2 py-1"
          title={lang === "DE" ? "Switch to English" : "Zu Deutsch wechseln"}
        >
          {lang === "DE" ? "EN" : "DE"}
        </button>
        <Link href="/settings" className="text-gray-400 hover:text-white text-sm">⚙ {t.nav_settings}</Link>
        <Link
          href="/cards/new"
          className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600"
        >
          {t.nav_add_card}
        </Link>
      </div>
    </nav>
  );
}
