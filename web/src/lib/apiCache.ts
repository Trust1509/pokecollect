"use client";
import { useEffect, useState } from "react";

/**
 * Modul-Cache für API-Ressourcen (Issue #14): eine Routine für
 * useEnums/useSets/useSettings (Kredo: DRY).
 *
 * - Ein Fetch pro Session (Modul-Lebensdauer), geteilt über alle Komponenten.
 * - refresh() invalidiert und lädt neu; alle eingehängten Komponenten
 *   bekommen den neuen Wert.
 * - Fehler werden nicht gecacht — der nächste Mount versucht es erneut.
 */
export function createCachedResource<T>(fetcher: () => Promise<T>) {
  let cache: T | null = null;
  let pending: Promise<T> | null = null;
  const listeners = new Set<(value: T) => void>();

  const load = (): Promise<T> => {
    if (!pending) {
      pending = fetcher()
        .then((value) => {
          cache = value;
          listeners.forEach((l) => l(value));
          return value;
        })
        .catch((err) => {
          pending = null;
          throw err;
        });
    }
    return pending;
  };

  const refresh = (): Promise<T> => {
    pending = null;
    return load();
  };

  function useResource(): { data: T | null; refresh: () => Promise<T> } {
    const [data, setData] = useState<T | null>(cache);
    useEffect(() => {
      listeners.add(setData);
      load().catch(() => {});
      return () => {
        listeners.delete(setData);
      };
    }, []);
    return { data, refresh };
  }

  return { useResource, refresh };
}
