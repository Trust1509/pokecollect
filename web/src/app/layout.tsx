import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "PokéCollect",
  description: "Pokémon TCG Sammlungs-App",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-pokemon-dark">
        <nav className="border-b border-gray-800 bg-pokemon-card px-6 py-3 flex items-center gap-6">
          <Link href="/" className="text-xl font-bold text-pokemon-yellow">
            PokéCollect
          </Link>
          <Link href="/" className="text-gray-300 hover:text-white text-sm">Sammlung</Link>
          <Link href="/stats" className="text-gray-300 hover:text-white text-sm">Statistiken</Link>
          <div className="ml-auto">
            <Link
              href="/cards/new"
              className="bg-pokemon-red text-white text-sm px-3 py-1.5 rounded hover:bg-red-600"
            >
              + Karte
            </Link>
          </div>
        </nav>
        <main className="max-w-screen-2xl mx-auto px-4 py-6">
          {children}
        </main>
      </body>
    </html>
  );
}
