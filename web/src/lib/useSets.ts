"use client";
import { PokemonSet, setsApi } from "@/lib/api";
import { createCachedResource } from "@/lib/apiCache";

// Set-Stammdaten — ein Fetch pro Session, geteilt über alle Seiten;
// refreshSets() nach dem Anlegen eines Sets (SetPicker) aufrufen (Issue #14).
const resource = createCachedResource<PokemonSet[]>(() =>
  setsApi.list().then((r) => r.data)
);

export function useSets(): { sets: PokemonSet[]; refresh: () => Promise<PokemonSet[]> } {
  const { data, refresh } = resource.useResource();
  return { sets: data ?? [], refresh };
}

export const refreshSets = resource.refresh;
