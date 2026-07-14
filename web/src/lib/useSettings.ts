"use client";
import { AppSettings, settingsApi } from "@/lib/api";
import { createCachedResource } from "@/lib/apiCache";

// App-Einstellungen — ein Fetch pro Session, geteilt über alle Seiten;
// die Einstellungs-Seite ruft refreshSettings() nach dem Speichern auf,
// damit gecachte Werte (default_sort, placeholder, …) nicht veralten (Issue #14).
const resource = createCachedResource<AppSettings>(() =>
  settingsApi.get().then((r) => r.data)
);

export function useSettings(): { settings: AppSettings | null; refresh: () => Promise<AppSettings> } {
  const { data, refresh } = resource.useResource();
  return { settings: data, refresh };
}

export const refreshSettings = resource.refresh;
