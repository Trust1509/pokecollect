import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Types ─────────────────────────────────────────────────────────────────

export type Card = {
  id: number;
  kartenname: string;
  pokedex_nr: number | null;
  englischer_name: string | null;
  set_edition: string | null;
  karten_nr: string | null;
  seltenheit: string | null;
  kartenversion: string | null;
  folierung: string | null;
  sprache: string;
  besessen: boolean;
  wunschliste: boolean;
  im_pokedex: boolean;
  prioritaet: string | null;
  wert_eur: string | null;
  wert_aktualisiert: string | null;
  notizen: string | null;
  zustand: string | null;
  bild_pokedex_url: string | null;
  bild_karte_url: string | null;       // auto: TCGdex high.webp
  bild_karte_pfad: string | null;
  bild_thumbnail_pfad: string | null;
  // TCGdex-Anreicherung (v0.7.0)
  tcgdex_card_id: string | null;
  set_id: string | null;
  dex_id: number | null;
  variants_normal: boolean | null;
  variants_reverse: boolean | null;
  variants_holo: boolean | null;
  variants_firstedition: boolean | null;
  hinzugefuegt_am: string;
  aktualisiert_am: string;
};

export type CardListResponse = {
  items: Card[];
  total: number;
  page: number;
  limit: number;
  pages: number;
};

export type StatsResponse = {
  gesamt: number;
  besessen: number;
  nicht_besessen: number;
  gesamtwert_eur: string | null;
  sets: Record<string, number>;
  seltenheiten: Record<string, number>;
  sprachen: Record<string, number>;
  top10_teuerste: Card[];
  zuletzt_hinzugefuegt: Card[];
};

export type Enums = {
  seltenheit: string[];
  kartenversion: string[];
  folierung: string[];
  sprache: string[];
  zustand: string[];
  prioritaet: string[];
};

export type Collection = {
  id: number;
  name: string;
  beschreibung: string | null;
  binder_layout: string | null;
  binder_slots: number | null;
  erstellt_am: string | null;
  karten_anzahl: number;
};

export type CollectionCard = Card & { position: number | null };

export const BINDER_LAYOUTS = ["1x1", "2x2", "3x3", "4x3", "3x4", "4x4"] as const;

// ── API Calls ─────────────────────────────────────────────────────────────

export const cardApi = {
  list: (params: Record<string, unknown> = {}) =>
    api.get<CardListResponse>("/cards", { params }),

  get: (id: number) => api.get<Card>(`/cards/${id}`),

  create: (data: Partial<Card>) => api.post<Card>("/cards", data),

  update: (id: number, data: Partial<Card>) => api.put<Card>(`/cards/${id}`, data),

  delete: (id: number) => api.delete(`/cards/${id}`),

  uploadImage: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post<Card>(`/cards/${id}/image`, form);
  },

  deleteImage: (id: number) => api.delete<Card>(`/cards/${id}/image`),

  stats: () => api.get<StatsResponse>("/cards/meta/stats"),

  sets: () => api.get<string[]>("/cards/meta/sets"),

  enums: () => api.get<Enums>("/cards/meta/enums"),

  byPokedex: (nr: number) => api.get<Card[]>(`/cards/pokedex/${nr}`),

  backfillImages: (force = false) =>
    api.post(`/cards/meta/backfill-images?force=${force}`),
};

export const pricesApi = {
  refresh: () => api.post("/prices/refresh"),
  history: (id: number) => api.get(`/prices/history/${id}`),
};

export const authApi = {
  login: (username: string, password: string) =>
    api.post<{ access_token: string }>("/auth/login", { username, password }),
};

export type PokemonSet = {
  code: string;
  name: string;
  max_card_nr: number | null;
  // TCGdex-Anreicherung (v0.7.0)
  set_id?: string | null;
  name_en?: string | null;
  series_id?: string | null;
  card_count_official?: number | null;
  card_count_total?: number | null;
  logo_url?: string | null;
  symbol_url?: string | null;
};

export const setsApi = {
  list: () => api.get<PokemonSet[]>("/sets"),
  create: (data: Partial<PokemonSet>) => api.post<PokemonSet>("/sets", data),
  update: (code: string, data: Partial<PokemonSet>) => api.put<PokemonSet>(`/sets/${code}`, data),
  sync: () => api.post("/sets/sync"),
};

export type AppSettings = {
  placeholder_images_enabled: boolean;
  cards_per_page: number;
  default_sort: string;
  price_update_enabled: boolean;
  price_update_hour: number;
  price_source: string;
  default_language: string;
  default_condition: string;
  cardmarket_app_token: string;
  cardmarket_app_secret: string;
  cardmarket_access_token: string;
  cardmarket_access_secret: string;
  pokemontcg_api_key: string;
  gemini_api_key: string;
  gemini_model: string;
  gemini_daily_limit: number;
};

export const collectionApi = {
  list: () => api.get<Collection[]>("/collections"),
  get: (id: number) => api.get<Collection>(`/collections/${id}`),
  create: (data: { name: string; beschreibung?: string | null }) =>
    api.post<Collection>("/collections", data),
  update: (id: number, data: { name?: string; beschreibung?: string | null; binder_layout?: string; binder_slots?: number }) =>
    api.put<Collection>(`/collections/${id}`, data),
  delete: (id: number) => api.delete(`/collections/${id}`),
  cards: (id: number) => api.get<CollectionCard[]>(`/collections/${id}/cards`),
  addCard: (id: number, cardId: number) =>
    api.post<CollectionCard>(`/collections/${id}/cards`, { card_id: cardId }),
  removeCard: (id: number, cardId: number) =>
    api.delete(`/collections/${id}/cards/${cardId}`),
  reorder: (id: number, order: number[]) =>
    api.put(`/collections/${id}/cards/order`, { order }),
  moveToSlot: (id: number, cardId: number, slot: number) =>
    api.put(`/collections/${id}/cards/${cardId}/slot`, { slot }),
  setPositions: (id: number, positions: { card_id: number; position: number }[]) =>
    api.put(`/collections/${id}/cards/positions`, { positions }),
  forCard: (cardId: number) => api.get<Collection[]>(`/cards/${cardId}/collections`),
};

export const settingsApi = {
  get: () => api.get<AppSettings>("/settings"),
  update: (data: Partial<AppSettings>) => api.put<AppSettings>("/settings", data),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/settings/change-password", { current_password, new_password }),
};

// ── Scan ──────────────────────────────────────────────────────────────────

export type ScanMode = "single" | "multi" | "binder";

export type ScanMatch = {
  tcgdex_card_id: string | null;
  name: string | null;
  englischer_name: string | null;
  set_id: string | null;
  set_code: string | null;
  set_name: string | null;
  local_id: string | null;
  rarity: string | null;
  dex_id: number | null;
  image_url: string | null;
  variants_normal: boolean | null;
  variants_reverse: boolean | null;
  variants_holo: boolean | null;
  variants_firstedition: boolean | null;
};

export type ScanCandidate = {
  position: number | null;
  confidence: number;
  uncertain_fields: string[];
  raw: {
    name: string | null;
    set_code: string | null;
    number: string | null;
    language: string | null;
    position: number | null;
    confidence: number | null;
    bbox: number[] | null;
    quad: number[][] | null;
  };
  match: ScanMatch | null;
  suggested: Record<string, unknown>;
  foil_options: string[];
};

export type ScanResponse = {
  engine: string;
  mode: ScanMode;
  candidates: ScanCandidate[];
};

export type ScanStatus = { gemini: boolean; ocr: boolean; active: string };

export type ScanCommitItem = {
  kartenname: string;
  pokedex_nr?: number | null;
  englischer_name?: string | null;
  set_edition?: string | null;
  karten_nr?: string | null;
  seltenheit?: string | null;
  kartenversion?: string | null;
  folierung?: string | null;
  sprache?: string | null;
  zustand?: string | null;
  notizen?: string | null;
  tcgdex_card_id?: string | null;
  set_id?: string | null;
  dex_id?: number | null;
  bild_karte_url?: string | null;
  position?: number | null;
  im_pokedex?: boolean;
  prioritaet?: string | null;
};

export type ScanCommitRequest = {
  target: "pokedex" | "collection" | "wishlist";
  collection_id?: number | null;
  items: ScanCommitItem[];
};

export type ScanRawRead = {
  name?: string | null;
  set_code?: string | null;
  number?: string | null;
  language?: string | null;
};

export type ScanUsage = {
  today: { day: string; requests: number; tokens: number };
  total: { requests: number; tokens: number };
  avg_tokens_per_scan: number;
  model: string;
  limits: { rpd: number; rpm: number; tpm: number };
  days: { day: string; requests: number; tokens: number }[];
};

// ── Katalog (alle TCGdex-Karten) ────────────────────────────────────────────

export type CatalogItem = {
  card_id: string;
  set_id: string | null;
  set_code: string | null;
  set_name: string | null;
  local_id: string | null;
  name: string | null;
  name_en: string | null;
  dex_id: number | null;
  rarity: string | null;
  illustrator: string | null;
  category: string | null;
  image_url: string | null;
  variants_normal: boolean | null;
  variants_reverse: boolean | null;
  variants_holo: boolean | null;
  variants_firstedition: boolean | null;
  enriched: boolean | null;
};

export type CatalogListResponse = {
  items: CatalogItem[];
  total: number;
  page: number;
  limit: number;
  pages: number;
};

export const catalogApi = {
  list: (params: Record<string, unknown> = {}) => api.get<CatalogListResponse>("/catalog", { params }),
  meta: () => api.get<{ total: number; enriched: number }>("/catalog/meta"),
  illustrators: () => api.get<string[]>("/catalog/illustrators"),
  sync: () => api.post("/catalog/sync"),
  enrich: (limit = 500) => api.post(`/catalog/enrich?limit=${limit}`),
  enrichAll: () => api.post("/catalog/enrich-all"),
  addWishlist: (cardId: string, prioritaet?: string | null) =>
    api.post<{ card_id: number }>(`/catalog/${encodeURIComponent(cardId)}/wishlist`, { prioritaet: prioritaet ?? null }),
  addCollection: (cardId: string, collectionId: number) =>
    api.post<{ card_id: number }>(`/catalog/${encodeURIComponent(cardId)}/collection?collection_id=${collectionId}`),
};

export const scanApi = {
  status: () => api.get<ScanStatus>("/scan/status"),
  usage: () => api.get<ScanUsage>("/scan/usage"),
  scan: (file: Blob, opts: { mode: ScanMode; rows?: number; cols?: number; default_language?: string }) => {
    const form = new FormData();
    form.append("file", file, "scan.jpg");
    form.append("mode", opts.mode);
    form.append("rows", String(opts.rows ?? 0));
    form.append("cols", String(opts.cols ?? 0));
    form.append("default_language", opts.default_language ?? "DE");
    return api.post<ScanResponse>("/scan", form);
  },
  resolve: (read: ScanRawRead) => api.post<ScanCandidate>("/scan/resolve", read),
  commit: (payload: ScanCommitRequest) =>
    api.post<{ created: number; card_ids: number[] }>("/scan/commit", payload),
};
