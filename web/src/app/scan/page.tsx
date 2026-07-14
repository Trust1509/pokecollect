"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  Collection, Enums, PokemonSet, ScanCandidate, ScanCommitItem, ScanMode, ScanStatus,
  cardApi, collectionApi, scanApi, setsApi, settingsApi,
} from "@/lib/api";
import SetPicker from "@/components/SetPicker";
import RaritySelect from "@/components/RaritySelect";
import CornerEditor from "@/components/CornerEditor";
import { cropToCardPhoto, loadImg, normalizeOrientation, CropTransform } from "@/lib/cardCrop";
import { setCodeFromEdition } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

type Step = "setup" | "review" | "done";

type EditableCandidate = ScanCandidate & {
  include: boolean;
  usePhoto: boolean;        // eigenes Foto (true) vs. API-Bild (false)
  cropUrl: string | null;   // Vorschau des zugeschnittenen eigenen Fotos
  imPokedex: boolean;       // je Karte: in den Pokédex
  editedQuad?: number[][] | null;  // manuell korrigierte Ecken (normiert 0..1, TL,TR,BR,BL)
  editedOrient?: CropTransform;    // manuelle Flip/Rotate-Korrektur
};

const LANGS = ["DE", "EN", "CN", "JP", "FR", "ES", "IT"];

function parseLayout(layout: string): { cols: number; rows: number } {
  const m = layout.match(/^(\d+)x(\d+)$/);
  if (!m) return { cols: 3, rows: 3 };
  return { cols: Number(m[1]), rows: Number(m[2]) };
}

/** Verkleinert das Bild vor dem Upload (schnellere Analyse), max. Kantenlänge maxDim. */
async function downscaleImage(blob: Blob, maxDim = 1600): Promise<Blob> {
  const url = URL.createObjectURL(blob);
  try {
    const img = await loadImg(url);
    const longest = Math.max(img.width, img.height);
    if (longest <= maxDim) return blob;
    const scale = maxDim / longest;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(img.width * scale);
    canvas.height = Math.round(img.height * scale);
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    const out = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", 0.88));
    return out ?? blob;
  } catch {
    return blob;
  } finally {
    URL.revokeObjectURL(url);
  }
}

export default function ScanPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [sets, setSets] = useState<PokemonSet[]>([]);

  const [mode, setMode] = useState<ScanMode>("single");
  const [target, setTarget] = useState<"pokedex" | "collection" | "wishlist">("pokedex");
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [layout, setLayout] = useState("3x3");
  const [setPokedexRep, setSetPokedexRep] = useState(false);
  const [priority, setPriority] = useState("");  // für Wunschkarten-Scan

  const [step, setStep] = useState<Step>("setup");
  const [defaultLang, setDefaultLang] = useState("DE");
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<EditableCandidate[]>([]);
  const [savedCount, setSavedCount] = useState(0);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);
  const [editorIdx, setEditorIdx] = useState<number | null>(null);
  const sourceBlobRef = useRef<Blob | null>(null);
  const [camMsg, setCamMsg] = useState<string | null>(null);
  const [autoCapture, setAutoCapture] = useState(true);
  const busyRef = useRef(false);
  useEffect(() => { busyRef.current = busy; }, [busy]);

  // Kamera (nur in sicherem Kontext verfügbar – sonst Datei-Fallback)
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [cameraOn, setCameraOn] = useState(false);

  useEffect(() => {
    scanApi.status().then((r) => setStatus(r.data)).catch(() => {});
    cardApi.enums().then((r) => setEnums(r.data)).catch(() => {});
    collectionApi.list().then((r) => setCollections(r.data)).catch(() => {});
    setsApi.list().then((r) => setSets(r.data)).catch(() => {});
    settingsApi.get().then((r) => setDefaultLang(r.data.default_language || "DE")).catch(() => {});
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Layout aus gewählter Sammlung übernehmen
  useEffect(() => {
    if (target === "collection" && collectionId) {
      const c = collections.find((x) => x.id === collectionId);
      if (c?.binder_layout) setLayout(c.binder_layout);
    }
  }, [target, collectionId, collections]);

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((tr) => tr.stop());
    streamRef.current = null;
    setCameraOn(false);
  };

  const startCamera = async () => {
    setCamMsg(null);
    if (!navigator.mediaDevices?.getUserMedia) {
      // Unsicherer Kontext (HTTP über LAN) → getUserMedia ist gesperrt.
      setCamMsg(t.scan_camera_insecure);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOn(true); // Video wird erst jetzt gerendert → Stream im Effect anhängen
    } catch {
      setCamMsg(t.scan_camera_insecure);
    }
  };

  // Stream an das Video hängen, sobald es im DOM ist (sonst bleibt das Bild schwarz)
  useEffect(() => {
    if (cameraOn && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
      videoRef.current.play().catch(() => {});
    }
  }, [cameraOn]);

  // Auto-Aufnahme: löst aus, wenn das Bild ruhig (Kamera still gehalten),
  // scharf und hell genug ist. Best-effort-Heuristik; manuell geht immer.
  useEffect(() => {
    if (!cameraOn || !autoCapture) return;
    const W = 160, H = 224;
    const canvas = document.createElement("canvas");
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;
    let prev: Float32Array | null = null;
    let steady = 0;
    const id = setInterval(() => {
      const v = videoRef.current;
      if (!v || v.videoWidth === 0 || busyRef.current) return;
      ctx.drawImage(v, 0, 0, W, H);
      const data = ctx.getImageData(0, 0, W, H).data;
      const gray = new Float32Array(W * H);
      let bright = 0;
      for (let i = 0, p = 0; i < data.length; i += 4, p++) {
        const g = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
        gray[p] = g; bright += g;
      }
      bright /= W * H;
      let sharp = 0;
      for (let y = 1; y < H - 1; y++) {
        for (let x = 1; x < W - 1; x++) {
          const idx = y * W + x;
          const lap = 4 * gray[idx] - gray[idx - 1] - gray[idx + 1] - gray[idx - W] - gray[idx + W];
          sharp += Math.abs(lap);
        }
      }
      sharp /= (W - 2) * (H - 2);
      let diff = Infinity;
      if (prev) {
        let s = 0;
        for (let i = 0; i < gray.length; i++) s += Math.abs(gray[i] - prev[i]);
        diff = s / gray.length;
      }
      prev = gray;
      if (diff < 3.5 && sharp > 7 && bright > 30) steady++; else steady = 0;
      if (steady >= 3) { steady = 0; void handleCapture(); }
    }, 400);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cameraOn, autoCapture]);

  const blobFromVideo = (): Promise<Blob | null> =>
    new Promise((resolve) => {
      const v = videoRef.current;
      if (!v) return resolve(null);
      const canvas = document.createElement("canvas");
      canvas.width = v.videoWidth;
      canvas.height = v.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) return resolve(null);
      ctx.drawImage(v, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((b) => resolve(b), "image/jpeg", 0.9);
    });

  const runScan = useCallback(async (rawBlob: Blob) => {
    setBusy(true);
    try {
      // EXIF-Orientierung fest einbacken (Anzeige == Zuschnitt) und vor dem
      // Senden verkleinern → schnellere Analyse. bbox/quad beziehen sich auf
      // genau dieses Bild, daher merken wir es als Quelle für die Zuschnitte.
      const blob = await downscaleImage(await normalizeOrientation(rawBlob));
      sourceBlobRef.current = blob;
      setSourceUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(blob);
      });
      const { cols, rows } = parseLayout(layout);
      const res = await scanApi.scan(blob, {
        mode,
        rows: mode === "binder" ? rows : 0,
        cols: mode === "binder" ? cols : 0,
        default_language: defaultLang,
      });
      const list: EditableCandidate[] = res.data.candidates.map((c) => ({
        ...c,
        include: true,
        usePhoto: !!(c.raw?.bbox || c.raw?.quad),
        cropUrl: null,
        imPokedex: setPokedexRep,
      }));
      if (res.data.limit_erreicht) {
        toast(t.scan_limit_fallback, { icon: "⚠️" });
      }
      if (!list.length) {
        toast.error(t.scan_no_results);
        return;
      }
      setCandidates(list);
      setStep("review");
      // Foto-Zuschnitte je Karte (aus der bbox) für Vorschau erzeugen
      list.forEach(async (c, idx) => {
        const blob = sourceBlobRef.current;
        if ((!c.raw?.bbox && !c.raw?.quad) || !blob) return;
        try {
          const f = await cropToCardPhoto(blob, { bbox: c.raw.bbox, quad: c.raw.quad, autoOrient: true });
          const u = URL.createObjectURL(f);
          setCandidates((prev) => prev.map((cc, i) => (i === idx ? { ...cc, cropUrl: u } : cc)));
        } catch { /* Vorschau optional */ }
      });
    } catch {
      toast.error(t.scan_error);
    } finally {
      setBusy(false);
    }
  }, [layout, mode, t, setPokedexRep, defaultLang]);

  const handleCapture = async () => {
    const blob = await blobFromVideo();
    stopCamera();
    if (blob) runScan(blob);
  };

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) runScan(f);
    e.target.value = "";
  };

  const toggleUsePhoto = (idx: number) =>
    setCandidates((prev) => prev.map((c, i) => (i === idx ? { ...c, usePhoto: !c.usePhoto } : c)));
  const togglePokedex = (idx: number) =>
    setCandidates((prev) => prev.map((c, i) => (i === idx ? { ...c, imPokedex: !c.imPokedex } : c)));

  const updateField = (idx: number, key: string, value: unknown) => {
    setCandidates((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, suggested: { ...c.suggested, [key]: value } } : c))
    );
  };
  const toggleInclude = (idx: number) =>
    setCandidates((prev) => prev.map((c, i) => (i === idx ? { ...c, include: !c.include } : c)));

  // Start-Viereck für den Eck-Editor: korrigierte Ecken › erkannte Ecken ›
  // Bounding-Box › grober Default.
  const initialQuadFor = (c: EditableCandidate): number[][] => {
    if (c.editedQuad && c.editedQuad.length === 4) return c.editedQuad;
    if (c.raw?.quad && c.raw.quad.length === 4) return c.raw.quad;
    const b = c.raw?.bbox;
    if (b && b.length === 4) {
      const [x, y, w, h] = b;
      return [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
    }
    return [[0.15, 0.1], [0.85, 0.1], [0.85, 0.9], [0.15, 0.9]];
  };

  // Crop-Optionen je Karte: manuelle Ecken (mit Flip/Rotate) bevorzugt, sonst
  // die Auto-Erkennung (Gemini) mit Eck-Sortierung nach Bildposition.
  const cropOptsFor = (c: EditableCandidate) =>
    c.editedQuad
      ? { quad: c.editedQuad, ...(c.editedOrient ?? {}) }
      : { bbox: c.raw?.bbox, quad: c.raw?.quad, autoOrient: true };

  // Manuell gesetzte Ecken/Ausrichtung übernehmen → Foto neu entzerren.
  const applyCorners = async (idx: number, quad: number[][], transform: CropTransform) => {
    setEditorIdx(null);
    const blob = sourceBlobRef.current;
    if (!blob) return;
    try {
      const f = await cropToCardPhoto(blob, { quad, ...transform });
      const u = URL.createObjectURL(f);
      setCandidates((prev) => prev.map((cc, i) =>
        i === idx ? { ...cc, editedQuad: quad, editedOrient: transform, cropUrl: u, usePhoto: true } : cc));
    } catch { /* Entzerrung optional */ }
  };

  // Karte anhand der (geänderten) Set/Nummer neu auflösen → Live-Bild + Treffer.
  // Behält die Nutzer-Auswahl für Set/Nummer/Sprache bei.
  const refreshCandidate = async (idx: number, overrides: Record<string, unknown> = {}) => {
    const c = candidates[idx];
    if (!c) return;
    const s = { ...(c.suggested as Record<string, unknown>), ...overrides };
    try {
      const r = await scanApi.resolve({
        name: String(s.kartenname ?? c.raw.name ?? ""),
        set_code: setCodeFromEdition(s.set_edition as string),
        number: (s.karten_nr as string) ?? null,
        language: (s.sprache as string) ?? "DE",
      });
      const nc = r.data;
      setCandidates((prev) => prev.map((cc, i) => i === idx ? {
        ...cc,
        match: nc.match,
        foil_options: nc.foil_options,
        uncertain_fields: nc.uncertain_fields,
        confidence: nc.confidence,
        suggested: {
          ...nc.suggested,
          // Nutzer-Eingaben behalten
          set_edition: s.set_edition,
          karten_nr: s.karten_nr,
          sprache: s.sprache,
          // manuell gesetzte Pokédex-Nr. nicht verlieren, wenn die Auflösung keine findet
          pokedex_nr: (nc.suggested as Record<string, unknown>).pokedex_nr ?? s.pokedex_nr,
        },
      } : cc));
    } catch { /* Live-Auflösung ist optional */ }
  };

  const handleSave = async () => {
    const chosen = candidates.filter((c) => c.include);
    if (!chosen.length) return;
    setBusy(true);
    try {
      const items: ScanCommitItem[] = chosen.map((c) => {
        const s = c.suggested as Record<string, unknown>;
        return {
          kartenname: String(s.kartenname ?? c.raw.name ?? "?"),
          pokedex_nr: (s.pokedex_nr as number) ?? c.match?.dex_id ?? null,
          englischer_name: (s.englischer_name as string) ?? c.match?.englischer_name ?? null,
          set_edition: (s.set_edition as string) ?? null,
          karten_nr: (s.karten_nr as string) ?? null,
          seltenheit: (s.seltenheit as string) ?? c.match?.rarity ?? null,
          folierung: (s.folierung as string) ?? null,
          sprache: (s.sprache as string) ?? "DE",
          tcgdex_card_id: c.match?.tcgdex_card_id ?? null,
          set_id: c.match?.set_id ?? null,
          dex_id: c.match?.dex_id ?? (s.dex_id as number) ?? null,
          // API-Bild nur senden, wenn der Nutzer NICHT sein eigenes Foto will
          bild_karte_url: c.usePhoto ? null : (c.match?.image_url ?? null),
          position: c.position ?? null,
          im_pokedex: target !== "wishlist" && c.imPokedex,
          prioritaet: target === "wishlist" ? (priority || null) : null,
        };
      });
      const res = await scanApi.commit({
        target,
        collection_id: target === "collection" ? collectionId : null,
        items,
      });
      // Für jede Karte mit „eigenes Foto" die Aufnahme (per bbox zugeschnitten)
      // als Kartenfoto hochladen – hat in der App Anzeige-Vorrang.
      const ids = res.data.card_ids;
      await Promise.all(chosen.map(async (c, k) => {
        const blob = sourceBlobRef.current;
        if (!c.usePhoto || !blob || ids[k] == null) return;
        try {
          const file = await cropToCardPhoto(blob, cropOptsFor(c));
          // Originalfoto (ganze Aufnahme) mitspeichern → spätere Nachbearbeitung
          const original = new File([blob], "orig.jpg", { type: "image/jpeg" });
          await cardApi.uploadImage(ids[k], file, original);
        } catch { /* Foto-Upload optional */ }
      }));
      setSavedCount(res.data.created);
      setStep("done");
      toast.success(t.scan_saved(res.data.created));
    } catch {
      toast.error(t.scan_save_error);
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setCandidates([]);
    setSavedCount(0);
    setStep("setup");
  };

  // ── Render ────────────────────────────────────────────────────────────────
  const engineActive = status?.active ?? "none";

  return (
    <div className="max-w-3xl mx-auto pb-24">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">{t.scan_title}</h1>
        <Link href="/" className="text-gray-500 hover:text-white text-sm">{t.scan_back}</Link>
      </div>
      <p className="text-gray-400 text-sm mb-1">{t.scan_subtitle}</p>
      <p className="text-xs mb-6">
        {engineActive === "none"
          ? <span className="text-red-400">{t.scan_engine_none}</span>
          : <span className="text-gray-500">{t.scan_engine_active(engineActive)}</span>}
      </p>

      {step === "setup" && (
        <div className="space-y-6">
          {/* Modus */}
          <div>
            <label className="text-gray-400 text-xs block mb-2">{t.scan_mode}</label>
            <div className="grid grid-cols-3 gap-2">
              {([
                ["single", t.scan_mode_single, t.scan_mode_single_desc],
                ["multi", t.scan_mode_multi, t.scan_mode_multi_desc],
                ["binder", t.scan_mode_binder, t.scan_mode_binder_desc],
              ] as const).map(([m, label, desc]) => (
                <button type="button"
                  key={m}
                  onClick={() => setMode(m)}
                  className={`rounded-lg border p-3 text-left transition ${
                    mode === m ? "border-pokemon-blue bg-pokemon-accent" : "border-gray-700 bg-pokemon-card hover:border-gray-500"
                  }`}
                >
                  <div className="text-white text-sm font-medium">{label}</div>
                  <div className="text-gray-400 text-xs mt-0.5">{desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Ziel */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-gray-400 text-xs block mb-1">{t.scan_target}</label>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value as "pokedex" | "collection" | "wishlist")}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
              >
                <option value="pokedex">{t.scan_target_pokedex}</option>
                <option value="collection">{t.scan_target_collection}</option>
                <option value="wishlist">{t.scan_target_wishlist}</option>
              </select>
            </div>
            {target === "collection" && (
              <div>
                <label className="text-gray-400 text-xs block mb-1">{t.scan_target_collection}</label>
                <select
                  value={collectionId ?? ""}
                  onChange={(e) => setCollectionId(e.target.value ? Number(e.target.value) : null)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                >
                  <option value="">–</option>
                  {collections.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            )}
            {target === "wishlist" && (
              <div>
                <label className="text-gray-400 text-xs block mb-1">{t.form_priority}</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                >
                  <option value="">–</option>
                  {(enums?.prioritaet ?? []).map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
            )}
            {mode === "binder" && (
              <div>
                <label className="text-gray-400 text-xs block mb-1">{t.scan_layout}</label>
                <input
                  type="text"
                  value={layout}
                  onChange={(e) => setLayout(e.target.value)}
                  placeholder="3x3"
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm font-mono"
                />
              </div>
            )}
          </div>

          {target !== "wishlist" && (
            <label className="flex items-center gap-2 text-sm text-white">
              <input type="checkbox" checked={setPokedexRep} onChange={(e) => setSetPokedexRep(e.target.checked)} />
              {t.scan_set_pokedex_rep} <span className="text-gray-500 text-xs">({t.scan_default_all})</span>
            </label>
          )}

          {/* Kamera / Datei */}
          <div className="rounded-lg border border-gray-700 bg-pokemon-card p-4">
            {cameraOn ? (
              <div className="space-y-3">
                <div className="relative mx-auto" style={{ maxWidth: 480 }}>
                  <video ref={videoRef} autoPlay playsInline muted className="w-full rounded bg-black" />
                  <div className="pointer-events-none absolute inset-4 border-2 border-pokemon-yellow/70 rounded" />
                </div>
                <p className="text-center text-gray-500 text-xs">{t.scan_camera_hint}</p>
                <div className="flex gap-2 justify-center items-center flex-wrap">
                  <button type="button" onClick={() => void handleCapture()} disabled={busy}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
                    {busy ? t.scan_analyzing : t.scan_capture}
                  </button>
                  <button type="button" onClick={stopCamera} className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
                    {t.scan_stop_camera}
                  </button>
                  <label className="flex items-center gap-1 text-xs text-gray-300 ml-2">
                    <input type="checkbox" checked={autoCapture} onChange={(e) => setAutoCapture(e.target.checked)} />
                    {t.scan_autocapture}
                  </label>
                </div>
              </div>
            ) : (
              <div className="space-y-3 text-center">
                <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
                  onChange={handleFile} className="hidden" />
                <button type="button" onClick={() => fileInputRef.current?.click()} disabled={busy || engineActive === "none"}
                  className="bg-pokemon-blue text-white px-5 py-3 rounded-lg hover:bg-blue-500 disabled:opacity-50 w-full sm:w-auto">
                  {busy ? t.scan_analyzing : t.scan_take_photo}
                </button>
                <div>
                  <button type="button" onClick={startCamera} disabled={engineActive === "none"}
                    className="text-pokemon-blue hover:underline text-sm disabled:opacity-50">
                    {t.scan_start_camera}
                  </button>
                </div>
                {camMsg && <p className="text-gray-400 text-xs whitespace-pre-line">{camMsg}</p>}
              </div>
            )}
          </div>
        </div>
      )}

      {step === "review" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-white font-medium">{t.scan_results_title(candidates.length)}</h2>
            <button type="button" onClick={reset} className="text-gray-500 hover:text-white text-sm">{t.scan_back}</button>
          </div>

          {candidates.map((c, idx) => {
            const s = c.suggested as Record<string, unknown>;
            const uncertain = c.uncertain_fields.length > 0;
            const foilOptions = c.foil_options.length ? c.foil_options : (enums?.folierung ?? ["Normal"]);
            const pokedexNr = (s.pokedex_nr as number) ?? c.match?.dex_id ?? null;
            return (
              <div key={idx}
                className={`rounded-lg border p-3 ${
                  !c.include ? "border-gray-800 opacity-50" : uncertain ? "border-pokemon-red" : "border-gray-700"
                } bg-pokemon-card`}>
                {/* Kopfzeile: Pokédex-Nr. + Übernehmen / Im Pokédex */}
                <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
                  <span className="text-xs text-gray-400">
                    {pokedexNr != null ? `#${String(pokedexNr).padStart(4, "0")}` : <span className="text-gray-600">{t.scan_no_dex}</span>}
                  </span>
                  <div className="flex items-center gap-3 text-xs">
                    {target !== "wishlist" && pokedexNr != null && (
                      <label className="flex items-center gap-1 text-gray-300">
                        <input type="checkbox" checked={c.imPokedex} onChange={() => togglePokedex(idx)} />
                        {t.detail_pokedex_flag}
                      </label>
                    )}
                    <label className="flex items-center gap-1 text-gray-300">
                      <input type="checkbox" checked={c.include} onChange={() => toggleInclude(idx)} />
                      {t.scan_include}
                    </label>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3">
                  {/* Bild – eigenes Foto (Zuschnitt) oder TCGdex-Treffer, je nach Wahl. */}
                  <div className="w-32 mx-auto sm:mx-0 sm:w-36 shrink-0">
                    {(() => {
                      const own = c.cropUrl ?? (mode === "single" ? sourceUrl : null);
                      const big = c.usePhoto ? (own ?? c.match?.image_url ?? null)
                                             : (c.match?.image_url ?? own ?? null);
                      return big ? (
                        <a href={big} target="_blank" rel="noreferrer" title={t.scan_view_large}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={big} alt="" className="w-full rounded hover:opacity-90" />
                        </a>
                      ) : (
                        <div className="aspect-[63/88] bg-gray-800 rounded flex items-center justify-center text-gray-600 text-xs">?</div>
                      );
                    })()}
                    <div className="mt-1 text-center text-[10px] text-gray-500">
                      {t.scan_confidence}: {Math.round(c.confidence * 100)}%
                    </div>
                    {(c.cropUrl || (mode === "single" && sourceUrl)) && c.match?.image_url && (
                      <label className="mt-1 flex items-center justify-center gap-1 text-[10px] text-gray-300">
                        <input type="checkbox" checked={c.usePhoto} onChange={() => toggleUsePhoto(idx)} />
                        {t.scan_use_photo}
                      </label>
                    )}
                    {sourceUrl && (
                      <button type="button"
                        onClick={() => setEditorIdx(idx)}
                        className="mt-1 w-full text-[10px] text-pokemon-blue hover:underline"
                      >
                        ✥ {t.scan_edit_corners}
                      </button>
                    )}
                  </div>

                  {/* Felder */}
                  <div className="flex-1 min-w-0 space-y-1.5">
                    {uncertain && (
                      <div className="text-pokemon-red text-xs">⚠ {t.scan_uncertain} ({c.uncertain_fields.join(", ")})</div>
                    )}
                    <input
                      value={String(s.kartenname ?? "")}
                      onChange={(e) => updateField(idx, "kartenname", e.target.value)}
                      placeholder={t.scan_field_name}
                      className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
                    />
                    {/* Set-Auswahl (Dropdown wie beim manuellen Anlegen) */}
                    <SetPicker
                      value={String(s.set_edition ?? "")}
                      sets={sets}
                      onChange={(setEdition) => {
                        updateField(idx, "set_edition", setEdition || null);
                        void refreshCandidate(idx, { set_edition: setEdition || null });
                      }}
                      onSetAdded={(ns) => setSets((prev) => [...prev, ns].sort((a, b) => a.code.localeCompare(b.code)))}
                    />
                    <div className="grid grid-cols-2 gap-1.5">
                      <input
                        type="number"
                        value={String(s.pokedex_nr ?? "")}
                        onChange={(e) => updateField(idx, "pokedex_nr", e.target.value ? Number(e.target.value) : null)}
                        placeholder={t.form_pokedex_nr}
                        className="min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                      />
                      <input
                        value={String(s.karten_nr ?? "")}
                        onChange={(e) => updateField(idx, "karten_nr", e.target.value)}
                        onBlur={() => void refreshCandidate(idx)}
                        placeholder={t.scan_field_nr}
                        className="min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs font-mono"
                      />
                      <select
                        value={String(s.sprache ?? "DE")}
                        onChange={(e) => { updateField(idx, "sprache", e.target.value); void refreshCandidate(idx, { sprache: e.target.value }); }}
                        className="min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                      >
                        {LANGS.map((l) => <option key={l} value={l}>{l}</option>)}
                      </select>
                    </div>
                    <div className="grid grid-cols-2 gap-1.5 items-start">
                      {/* Folierung – alle Möglichkeiten; laut Karte mögliche zuerst */}
                      <select
                        value={String(s.folierung ?? "")}
                        onChange={(e) => updateField(idx, "folierung", e.target.value)}
                        className="min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-xs"
                      >
                        <option value="">{t.scan_field_foiling}</option>
                        {(() => {
                          const all = enums?.folierung ?? foilOptions;
                          const pref = foilOptions.filter((f) => all.includes(f));
                          const rest = all.filter((f) => !pref.includes(f));
                          return [...pref, ...rest].map((f) => <option key={f} value={f}>{f}</option>);
                        })()}
                      </select>
                      {/* Seltenheit mit Symbol (wie beim manuellen Anlegen) */}
                      <div className="min-w-0">
                        <RaritySelect
                          value={String(s.seltenheit ?? "")}
                          onChange={(v) => updateField(idx, "seltenheit", v)}
                          options={(() => {
                            const opts = enums?.seltenheit ?? [];
                            const cur = String(s.seltenheit ?? "");
                            return cur && !opts.includes(cur) ? [cur, ...opts] : opts;
                          })()}
                          language={String(s.sprache ?? "DE")}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          <div className="fixed bottom-0 inset-x-0 bg-pokemon-dark/95 border-t border-gray-800 p-3">
            <div className="max-w-3xl mx-auto flex gap-3">
              <button type="button" onClick={handleSave} disabled={busy || !candidates.some((c) => c.include)}
                className="flex-1 bg-green-600 text-white px-4 py-2.5 rounded hover:bg-green-700 disabled:opacity-50">
                {busy ? t.scan_saving : t.scan_save_all}
              </button>
            </div>
          </div>
        </div>
      )}

      {editorIdx != null && sourceUrl && candidates[editorIdx] && (
        <CornerEditor
          imageUrl={sourceUrl}
          initialQuad={initialQuadFor(candidates[editorIdx])}
          onCancel={() => setEditorIdx(null)}
          onApply={(quad, transform) => void applyCorners(editorIdx, quad, transform)}
        />
      )}

      {step === "done" && (
        <div className="text-center py-16 space-y-4">
          <div className="text-4xl">✅</div>
          <p className="text-white text-lg">{t.scan_saved(savedCount)}</p>
          <div className="flex gap-3 justify-center">
            <button type="button" onClick={reset} className="bg-pokemon-blue text-white px-4 py-2 rounded hover:bg-blue-500">
              {t.scan_scan_again}
            </button>
            <Link href="/" className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
              {t.scan_back}
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
