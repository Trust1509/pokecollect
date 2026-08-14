import type { APIRequestContext } from "@playwright/test";
import { expect } from "@playwright/test";

/** Adressen + Zugang kommen aus der Umgebung (docker-compose.smoke.yml). */
export const API = process.env.API_URL ?? "http://localhost:3020";
export const PASSWORT = process.env.APP_PASSWORD ?? "teststand";
export const STATE_PFAD = ".auth/state.json";

/**
 * Alle Oberflächen-Texte an EINER Stelle.
 *
 * Der Rauchtest greift so weit wie möglich strukturell (IDs, href, Rolle) — nur
 * dort, wo es keinen stabilen Griff gibt, über sichtbaren Text. Ändert sich eine
 * Formulierung, ist es hier eine Zeile statt einer Suche durch alle Tests. Die
 * UI startet ohne gespeicherte Sprache auf Deutsch (web/src/lib/i18n.tsx).
 */
export const T = {
  anmelden: "Anmelden",
  anmeldung_fehlgeschlagen: "Anmeldung fehlgeschlagen",
  bearbeiten: "Bearbeiten",
  speichern: "Speichern",
  loeschen: "Löschen",
  anlegen: "Anlegen",
  karte_gespeichert: "Karte gespeichert",
  neue_karte: "Neue Karte",
  notizen: "Notizen",
  katalog_titel: "Alle Karten",
  katalog_suche: "Name, Nr. oder Illustrator …",
  sealed_neu: "+ Neues Produkt",
  sealed_name: "z.B. Obsidianflammen Display",
  produkt_gespeichert: "Produkt gespeichert",
  sammlung_neu: "+ Neue Sammlung",
  sammlung_name: "z.B. Glurak-Sammlung",
  karten_pro_seite: "Karten pro Seite",
  gespeichert: "Gespeichert",
  scan_titel: "Karten scannen",
  statistik_titel: "Statistiken",
};

/** Eindeutiger Name je Lauf — Rauchtests dürfen sich nie an Altlasten stoßen. */
export const einmalName = (praefix: string) =>
  `${praefix}-${Date.now().toString(36)}-${Math.floor(Math.random() * 1e4)}`;

/** Anmeldung auf API-Ebene — nur zum Vorbereiten/Aufräumen von Testdaten. */
export async function token(request: APIRequestContext): Promise<string> {
  const r = await request.post(`${API}/api/v1/auth/login`, {
    data: { username: "admin", password: PASSWORT },
  });
  expect(r.ok(), `Login an der API fehlgeschlagen: ${r.status()}`).toBeTruthy();
  return (await r.json()).access_token;
}

const auth = (t: string) => ({ Authorization: `Bearer ${t}` });

/**
 * Testkarte per API anlegen. Vorbereiten geht bewusst NICHT durchs Formular:
 * ein Rauchtest soll an der geprüften Stelle scheitern, nicht am Aufbau.
 */
export async function karteAnlegen(
  request: APIRequestContext, t: string, daten: Record<string, unknown>,
): Promise<number> {
  const r = await request.post(`${API}/api/v1/cards`, {
    headers: auth(t),
    data: { besessen: true, ...daten },
  });
  expect(r.status(), await r.text()).toBe(201);
  return (await r.json()).id;
}

/** Aufräumen; ein bereits gelöschter Datensatz ist kein Fehler. */
export async function karteLoeschen(request: APIRequestContext, t: string, id: number) {
  await request.delete(`${API}/api/v1/cards/${id}`, { headers: auth(t) });
}

export async function sammlungLoeschen(request: APIRequestContext, t: string, id: number) {
  await request.delete(`${API}/api/v1/collections/${id}`, { headers: auth(t) });
}

export async function sammlungIdFinden(
  request: APIRequestContext, t: string, name: string,
): Promise<number | null> {
  const r = await request.get(`${API}/api/v1/collections`, { headers: auth(t) });
  if (!r.ok()) return null;
  const treffer = (await r.json()).find((c: { name: string }) => c.name === name);
  return treffer?.id ?? null;
}

export async function sealedIdFinden(
  request: APIRequestContext, t: string, name: string,
): Promise<number | null> {
  const r = await request.get(`${API}/api/v1/sealed`, { headers: auth(t) });
  if (!r.ok()) return null;
  const treffer = (await r.json()).find((p: { name: string }) => p.name === name);
  return treffer?.id ?? null;
}

export async function sealedLoeschen(request: APIRequestContext, t: string, id: number) {
  await request.delete(`${API}/api/v1/sealed/${id}`, { headers: auth(t) });
}
