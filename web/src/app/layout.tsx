import type { Metadata, Viewport } from "next";
import "./globals.css";
import { I18nProvider } from "@/lib/i18n";
import Navbar from "@/components/Navbar";
import BottomNav from "@/components/BottomNav";
import PWARegister from "@/components/PWARegister";

export const metadata: Metadata = {
  title: "PokéCollect",
  description: "Pokémon TCG Sammlungs-App",
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, statusBarStyle: "black-translucent", title: "PokéCollect" },
  icons: {
    icon: [
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [{ url: "/icon-192.png" }],
  },
};

export const viewport: Viewport = {
  themeColor: "#16213e",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body className="min-h-screen bg-pokemon-dark">
        <I18nProvider>
          <Navbar />
          <main className="max-w-screen-2xl mx-auto px-4 py-6 pb-24 md:pb-6">
            {children}
          </main>
          <BottomNav />
          <PWARegister />
        </I18nProvider>
      </body>
    </html>
  );
}
