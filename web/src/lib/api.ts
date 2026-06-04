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
  wert_eur: string | null;
  wert_aktualisiert: string | null;
  notizen: string | null;
  zustand: string | null;
  bild_pokedex_url: string | null;
  bild_karte_url: string | null;       // auto: pokemon.com
  bild_karte_pfad: string | null;
  bild_thumbnail_pfad: string | null;
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
};

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
};

export const settingsApi = {
  get: () => api.get<AppSettings>("/settings"),
  update: (data: Partial<AppSettings>) => api.put<AppSettings>("/settings", data),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/settings/change-password", { current_password, new_password }),
};
