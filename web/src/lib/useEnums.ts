"use client";
import { Enums, cardApi } from "@/lib/api";
import { createCachedResource } from "@/lib/apiCache";

// Enums (Seltenheit, Sprache, Zustand, …) — ein Fetch pro Session,
// geteilt über alle Seiten; refreshEnums() zum Invalidieren (Issue #14).
const resource = createCachedResource<Enums>(() =>
  cardApi.enums().then((r) => r.data)
);

export function useEnums(): { enums: Enums | null; refresh: () => Promise<Enums> } {
  const { data, refresh } = resource.useResource();
  return { enums: data, refresh };
}

export const refreshEnums = resource.refresh;
