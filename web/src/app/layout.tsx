import type { Metadata } from "next";
import "./globals.css";
import { I18nProvider } from "@/lib/i18n";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "PokéCollect",
  description: "Pokémon TCG Sammlungs-App",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-pokemon-dark">
        <I18nProvider>
          <Navbar />
          <main className="max-w-screen-2xl mx-auto px-4 py-6">
            {children}
          </main>
        </I18nProvider>
      </body>
    </html>
  );
}
