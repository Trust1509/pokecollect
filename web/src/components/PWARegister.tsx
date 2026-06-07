"use client";
import { useEffect } from "react";

/**
 * Registriert den Service Worker (nur im sicheren Kontext: HTTPS oder localhost).
 * Über reines HTTP im LAN registriert der Browser keinen SW – dann passiert
 * einfach nichts (kein Fehler).
 */
export default function PWARegister() {
  useEffect(() => {
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    const register = () => {
      navigator.serviceWorker.register("/sw.js").catch(() => {/* SW optional */});
    };
    if (document.readyState === "complete") register();
    else {
      window.addEventListener("load", register);
      return () => window.removeEventListener("load", register);
    }
  }, []);
  return null;
}
