"use client";
import "./globals.css";
import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { clearToken } from "@/lib/auth";
import { APP_VERSION } from "@/lib/version";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const isLogin = pathname === "/login";

  const handleLogout = () => {
    clearToken();
    router.push("/login");
  };

  return (
    <html lang="de">
      <head>
        <title>PokéCollect</title>
        <meta name="description" content="Pokémon TCG Sammlungs-App" />
      </head>
      <body className="min-h-screen bg-pokemon-dark">
        {!isLogin && (
          <nav className="border-b border-gray-800 bg-pokemon-card px-6 py-3 flex items-center gap-6">
            <Link href="/" className="text-xl font-bold text-pokemon-yellow">
              PokéCollect
            </Link>
            <span className="text-gray-600 text-xs">v{APP_VERSION}</span>
            <Link href="/" className="text-gray-300 hover:text-white text-sm">Sammlung</Link>
            <Link href="/stats" className="text-gray-300 hover:text-white text-sm">Statistiken</Link>
            <div className="ml-auto flex items-center gap-3">
              <Link href="/settings" className="text-gray-400 hover:text-white text-sm">⚙ Einstellungen</Link>
              <Link
                href="/cards/new"
                className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600"
              >
                + Karte
              </Link>
              <button
                onClick={handleLogout}
                className="text-gray-500 hover:text-gray-300 text-sm"
              >
                Abmelden
              </button>
            </div>
          </nav>
        )}
        <main className="max-w-screen-2xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
