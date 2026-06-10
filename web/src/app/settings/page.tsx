"use client";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { settingsApi, cardApi, scanApi, AppSettings, ScanUsage } from "@/lib/api";
import { APP_VERSION } from "@/lib/version";

const SECTION = "bg-pokemon-card rounded-lg p-5 space-y-4";
const LABEL = "block text-gray-400 text-xs mb-1";
const INPUT = "w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-blue-500";
const TOGGLE_BASE = "relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer";

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className={`${TOGGLE_BASE} ${checked ? "bg-blue-600" : "bg-gray-600"}`}
    >
      <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-6" : "translate-x-1"}`} />
    </button>
  );
}

function Field({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div>
      <label className={LABEL}>{label}</label>
      {children}
      {hint && <p className="text-gray-600 text-xs mt-1">{hint}</p>}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={SECTION}>
      <h2 className="text-white font-semibold text-sm border-b border-gray-700 pb-2">{title}</h2>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const [s, setS] = useState<AppSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwSaving, setPwSaving] = useState(false);
  const [usage, setUsage] = useState<ScanUsage | null>(null);

  useEffect(() => {
    settingsApi.get().then((r) => setS(r.data)).catch(() => toast.error("Einstellungen konnten nicht geladen werden"));
    scanApi.usage().then((r) => setUsage(r.data)).catch(() => {});
  }, []);

  const save = async (patch: Partial<AppSettings>) => {
    if (!s) return;
    setSaving(true);
    try {
      const r = await settingsApi.update(patch);
      setS(r.data);
      toast.success("Gespeichert");
    } catch {
      toast.error("Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  };

  const set = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    if (!s) return;
    setS({ ...s, [key]: value });
  };

  const handlePasswordChange = async () => {
    if (pw.next !== pw.confirm) { toast.error("Passwörter stimmen nicht überein"); return; }
    if (pw.next.length < 8) { toast.error("Neues Passwort muss mind. 8 Zeichen haben"); return; }
    setPwSaving(true);
    try {
      await settingsApi.changePassword(pw.current, pw.next);
      setPw({ current: "", next: "", confirm: "" });
      toast.success("Passwort geändert");
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg ?? "Fehler beim Ändern");
    } finally {
      setPwSaving(false);
    }
  };

  if (!s) return <div className="text-gray-500 p-8">Lädt …</div>;

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Einstellungen</h1>
        <span className="text-gray-500 text-xs">PokéCollect v{APP_VERSION}</span>
      </div>

      {/* Anzeige */}
      <Section title="🖼️ Anzeige">
        <Field label="Pokédex-Platzhalterbilder" hint="Zeigt automatisch das offizielle Pokémon-Bild wenn kein eigenes Foto hinterlegt ist.">
          <div className="flex items-center gap-3 mt-1">
            <Toggle checked={s.placeholder_images_enabled} onChange={(v) => { set("placeholder_images_enabled", v); save({ placeholder_images_enabled: v }); }} />
            <span className="text-sm text-gray-300">{s.placeholder_images_enabled ? "Aktiviert" : "Deaktiviert"}</span>
          </div>
        </Field>
        <Field label="Karten pro Seite">
          <select value={s.cards_per_page} onChange={(e) => set("cards_per_page", Number(e.target.value))} className={INPUT} style={{ width: "auto" }}>
            {[24, 48, 96, 200].map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </Field>
        <Field label="Standard-Sortierung">
          <select value={s.default_sort} onChange={(e) => set("default_sort", e.target.value)} className={INPUT} style={{ width: "auto" }}>
            <option value="pokedex_nr">Pokédex-Nr.</option>
            <option value="wert">Wert</option>
            <option value="hinzugefuegt_am">Hinzugefügt</option>
          </select>
        </Field>
        <div className="pt-1">
          <button onClick={() => save({ cards_per_page: s.cards_per_page, default_sort: s.default_sort })} disabled={saving} className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50">
            Speichern
          </button>
        </div>
      </Section>

      {/* Preise */}
      <Section title="💰 Preise">
        <Field label="Automatische Preisaktualisierung" hint="Aktualisiert täglich die Cardmarket-Preise aller besessenen Karten.">
          <div className="flex items-center gap-3 mt-1">
            <Toggle checked={s.price_update_enabled} onChange={(v) => { set("price_update_enabled", v); save({ price_update_enabled: v }); }} />
            <span className="text-sm text-gray-300">{s.price_update_enabled ? "Aktiviert" : "Deaktiviert"}</span>
          </div>
        </Field>
        <Field label="Uhrzeit der Aktualisierung" hint="Stunde (0–23). Änderung wird nach einem API-Neustart aktiv.">
          <input type="number" min={0} max={23} value={s.price_update_hour} onChange={(e) => set("price_update_hour", Number(e.target.value))} className={INPUT} style={{ width: "80px" }} />
        </Field>
        <Field label="Preisquelle">
          <select value={s.price_source} onChange={(e) => set("price_source", e.target.value)} className={INPUT} style={{ width: "auto" }}>
            <option value="30d_avg">Cardmarket 30-Tage-Durchschnitt</option>
            <option value="current">Cardmarket Tagespreis</option>
          </select>
        </Field>
        <div className="pt-1">
          <button onClick={() => save({ price_update_hour: s.price_update_hour, price_source: s.price_source })} disabled={saving} className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50">
            Speichern
          </button>
        </div>
      </Section>

      {/* Sammlung */}
      <Section title="📦 Sammlung">
        {/* Listen entsprechen den Backend-Enums (schemas/card.py) */}
        <Field label="Standard-Sprache für neue Karten">
          <select value={s.default_language} onChange={(e) => set("default_language", e.target.value)} className={INPUT} style={{ width: "auto" }}>
            {["DE", "EN", "CN", "JP", "FR", "ES", "IT"].map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </Field>
        <Field label="Standard-Zustand für neue Karten">
          <select value={s.default_condition} onChange={(e) => set("default_condition", e.target.value)} className={INPUT} style={{ width: "auto" }}>
            <option value="">– keiner –</option>
            {["Mint", "Near Mint", "Excellent", "Good", "Played"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </Field>
        <div className="pt-1">
          <button onClick={() => save({ default_language: s.default_language, default_condition: s.default_condition })} disabled={saving} className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50">
            Speichern
          </button>
        </div>
      </Section>

      {/* API-Keys */}
      <Section title="🔑 API-Keys">
        <p className="text-gray-500 text-xs">Keys werden in der Datenbank gespeichert (nicht im Code oder der .env-Datei). Alle Keys sind optional – die App läuft vollständig über die kostenlose TCGdex-API.</p>
        <div className="space-y-3">
          <p className="text-gray-400 text-xs font-medium pt-1">Cardmarket (OAuth 1.0a)</p>
          <Field label="App Token">
            <input type="password" value={s.cardmarket_app_token} onChange={(e) => set("cardmarket_app_token", e.target.value)} className={INPUT} autoComplete="off" />
          </Field>
          <Field label="App Secret">
            <input type="password" value={s.cardmarket_app_secret} onChange={(e) => set("cardmarket_app_secret", e.target.value)} className={INPUT} autoComplete="off" />
          </Field>
          <Field label="Access Token">
            <input type="password" value={s.cardmarket_access_token} onChange={(e) => set("cardmarket_access_token", e.target.value)} className={INPUT} autoComplete="off" />
          </Field>
          <Field label="Access Secret">
            <input type="password" value={s.cardmarket_access_secret} onChange={(e) => set("cardmarket_access_secret", e.target.value)} className={INPUT} autoComplete="off" />
          </Field>
          <p className="text-gray-400 text-xs font-medium pt-2">PokémonTCG.io</p>
          <Field label="API Key">
            <input type="password" value={s.pokemontcg_api_key} onChange={(e) => set("pokemontcg_api_key", e.target.value)} className={INPUT} autoComplete="off" />
          </Field>
        </div>
        <div className="pt-1">
          <button
            onClick={() => save({
              cardmarket_app_token: s.cardmarket_app_token,
              cardmarket_app_secret: s.cardmarket_app_secret,
              cardmarket_access_token: s.cardmarket_access_token,
              cardmarket_access_secret: s.cardmarket_access_secret,
              pokemontcg_api_key: s.pokemontcg_api_key,
            })}
            disabled={saving}
            className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50"
          >
            API-Keys speichern
          </button>
        </div>
      </Section>

      {/* Scan / Gemini */}
      <Section title="📷 Scan (Gemini)">
        <p className="text-gray-400 text-xs">
          Mit hinterlegtem Gemini-API-Key nutzt der Karten-Scan die starke Gemini-Bilderkennung
          (ideal für ganze Binderseiten). Ohne Key läuft die lokale OCR. Key:{" "}
          <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">aistudio.google.com/apikey</a>
        </p>
        <Field label="Gemini API Key">
          <input type="password" value={s.gemini_api_key} onChange={(e) => set("gemini_api_key", e.target.value)} className={INPUT} autoComplete="off" placeholder="AIza…" />
        </Field>
        <Field label="Gemini Modell" hint="Standard: gemini-2.5-flash">
          <input type="text" value={s.gemini_model} onChange={(e) => set("gemini_model", e.target.value)} className={INPUT} placeholder="gemini-2.5-flash" />
        </Field>
        <Field label="Tägliches Limit (Anfragen)" hint="Aus deinem Google-AI-Plan. 0 = nicht anzeigen. Wird nur zur Anzeige des Verbrauchs genutzt.">
          <input type="number" min={0} value={s.gemini_daily_limit} onChange={(e) => set("gemini_daily_limit", Number(e.target.value))} className={INPUT} style={{ width: "120px" }} />
        </Field>
        <div className="pt-1">
          <button
            onClick={() => save({ gemini_api_key: s.gemini_api_key, gemini_model: s.gemini_model, gemini_daily_limit: s.gemini_daily_limit })}
            disabled={saving}
            className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50"
          >
            Scan-Einstellungen speichern
          </button>
        </div>
        {usage && (
          <div className="mt-3 border-t border-gray-700 pt-3 text-sm">
            <p className="text-gray-400 text-xs mb-2">Gemini-Nutzung & Free-Tier ({usage.model})</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-gray-900 rounded p-2">
                <div className="text-gray-500 text-xs">Heute (Anfragen/Tag)</div>
                <div className="text-white">{usage.today.requests} / {usage.limits.rpd}</div>
                <div className="mt-1 h-1.5 bg-gray-700 rounded-full">
                  <div
                    className={`h-full rounded-full ${usage.today.requests >= usage.limits.rpd ? "bg-pokemon-red" : "bg-green-500"}`}
                    style={{ width: `${Math.min(100, (usage.today.requests / usage.limits.rpd) * 100)}%` }}
                  />
                </div>
                <div className="text-gray-500 text-xs mt-0.5">
                  {Math.max(0, usage.limits.rpd - usage.today.requests)} Scans übrig heute
                </div>
                <div className="text-gray-400 text-xs mt-1">{usage.today.tokens.toLocaleString("de")} Tokens heute</div>
              </div>
              <div className="bg-gray-900 rounded p-2">
                <div className="text-gray-500 text-xs">Pro Scan / Limits</div>
                <div className="text-white">≈ {usage.avg_tokens_per_scan.toLocaleString("de")} Tokens/Scan</div>
                <div className="text-gray-400 text-xs mt-1">{usage.limits.rpm} Anfragen/Min</div>
                <div className="text-gray-400 text-xs">{(usage.limits.tpm / 1_000_000).toLocaleString("de")} Mio Tokens/Min</div>
                <div className="text-gray-500 text-xs mt-1">Gesamt: {usage.total.requests} Scans</div>
              </div>
            </div>
            <p className="text-gray-600 text-xs mt-2">
              Free-Tier: Limit pro Tag (RPD) wird täglich zurückgesetzt (~09:00 MEZ).
              „Tägliches Limit" oben überschreibt die RPD-Anzeige.
            </p>
          </div>
        )}
      </Section>

      {/* Bilder */}
      <Section title="🖼️ Kartenbilder (TCGdex)">
        <p className="text-gray-400 text-xs">
          Lädt automatisch das exakte Kartenbild von TCGdex für alle Karten ohne eigenes Foto oder manuelle URL.
          Priorität: Eigenes Foto → Manuelle URL → TCGdex → Pokédex-Artwork.
        </p>
        <div className="flex gap-3 pt-1 flex-wrap">
          <button
            onClick={async () => {
              try { await cardApi.backfillImages(false); toast.success("Backfill gestartet — läuft im Hintergrund"); }
              catch { toast.error("Fehler beim Starten"); }
            }}
            className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600"
          >
            Fehlende Bilder abrufen
          </button>
          <button
            onClick={async () => {
              if (!confirm("Alle vorhandenen Kartenbild-URLs neu von TCGdex abrufen?")) return;
              try { await cardApi.backfillImages(true); toast.success("Vollständiger Backfill gestartet"); }
              catch { toast.error("Fehler beim Starten"); }
            }}
            className="bg-gray-700 text-white text-sm px-4 py-1.5 rounded hover:bg-gray-600"
          >
            Alle Bilder neu abrufen
          </button>
        </div>
        <p className="text-gray-600 text-xs">API-Logs zeigen den Fortschritt: <code>docker logs pokecollect-api-1 -f</code></p>
      </Section>

      {/* Konto */}
      <Section title="👤 Konto">
        <Field label="Aktuelles Passwort">
          <input type="password" value={pw.current} onChange={(e) => setPw((p) => ({ ...p, current: e.target.value }))} className={INPUT} autoComplete="current-password" />
        </Field>
        <Field label="Neues Passwort" hint="Mindestens 8 Zeichen.">
          <input type="password" value={pw.next} onChange={(e) => setPw((p) => ({ ...p, next: e.target.value }))} className={INPUT} autoComplete="new-password" />
        </Field>
        <Field label="Neues Passwort bestätigen">
          <input type="password" value={pw.confirm} onChange={(e) => setPw((p) => ({ ...p, confirm: e.target.value }))} className={INPUT} autoComplete="new-password" />
        </Field>
        <div className="pt-1">
          <button onClick={handlePasswordChange} disabled={pwSaving || !pw.current || !pw.next} className="bg-blue-700 text-white text-sm px-4 py-1.5 rounded hover:bg-blue-600 disabled:opacity-50">
            Passwort ändern
          </button>
        </div>
      </Section>
    </div>
  );
}
