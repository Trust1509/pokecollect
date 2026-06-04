export type PokemonNames = { de: string; en: string };

const cache = new Map<number, PokemonNames>();

export async function fetchPokemonNames(nr: number): Promise<PokemonNames | null> {
  if (cache.has(nr)) return cache.get(nr)!;
  try {
    const res = await fetch(`https://pokeapi.co/api/v2/pokemon-species/${nr}`);
    if (!res.ok) return null;
    const data = await res.json();
    const find = (lang: string) =>
      (data.names as { language: { name: string }; name: string }[])
        .find((n) => n.language.name === lang)?.name ?? null;
    const de = find("de");
    const en = find("en");
    if (!de || !en) return null;
    const result = { de, en };
    cache.set(nr, result);
    return result;
  } catch {
    return null;
  }
}
