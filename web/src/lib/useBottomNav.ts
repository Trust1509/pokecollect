"use client";
// BottomNav-Konfiguration: welche Ziele als Schnellzugriff unten erscheinen.
// Speicherung in localStorage (per-Gerät, keine DB-Migration — Issue #34).
// Live-Sync zwischen BottomNav und der Konfig-UI in den Einstellungen über ein
// eigenes Window-Event (das native "storage"-Event feuert nur tab-übergreifend).
import { useCallback, useEffect, useState } from "react";
import {
  DEFAULT_BOTTOM_NAV,
  MAX_BOTTOM_NAV,
  NAV_KEYS_IN_ORDER,
  NavKey,
  isNavKey,
} from "./navRegistry";

const STORAGE_KEY = "pokecollect.bottomNav";
const CHANGE_EVENT = "pokecollect:bottomnav-change";

// Gespeicherte Auswahl bereinigen: nur bekannte Keys, ohne Duplikate, in
// kanonischer Reihenfolge, gedeckelt. Eine leere Auswahl bleibt leer (bewusst),
// nur ein fehlender Eintrag fällt auf den Default zurück.
function normalize(keys: NavKey[]): NavKey[] {
  return NAV_KEYS_IN_ORDER.filter((k) => keys.includes(k)).slice(0, MAX_BOTTOM_NAV);
}

function readStored(): NavKey[] {
  if (typeof window === "undefined") return DEFAULT_BOTTOM_NAV;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) return DEFAULT_BOTTOM_NAV;
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return DEFAULT_BOTTOM_NAV;
    return normalize(parsed.filter(isNavKey));
  } catch {
    return DEFAULT_BOTTOM_NAV;
  }
}

export function useBottomNavConfig() {
  // Start mit dem Default → server- und erste Client-Render sind identisch
  // (keine Hydration-Diskrepanz); der echte Wert kommt im Effect nach.
  const [keys, setKeysState] = useState<NavKey[]>(DEFAULT_BOTTOM_NAV);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setKeysState(readStored());
    setMounted(true);
    const onChange = () => setKeysState(readStored());
    window.addEventListener(CHANGE_EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(CHANGE_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const setKeys = useCallback((next: NavKey[]) => {
    const ordered = normalize(next);
    setKeysState(ordered);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ordered));
      // Andere Hook-Instanzen (BottomNav) im selben Tab benachrichtigen.
      window.dispatchEvent(new Event(CHANGE_EVENT));
    }
  }, []);

  const toggle = useCallback(
    (key: NavKey) => {
      const has = keys.includes(key);
      // Deckel: nicht mehr als MAX_BOTTOM_NAV aktivieren.
      if (!has && keys.length >= MAX_BOTTOM_NAV) return;
      setKeys(has ? keys.filter((k) => k !== key) : [...keys, key]);
    },
    [keys, setKeys],
  );

  return { keys, toggle, setKeys, mounted };
}
