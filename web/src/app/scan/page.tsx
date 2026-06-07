"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import toast from "react-hot-toast";
import {
  Collection, Enums, ScanCandidate, ScanCommitItem, ScanMode, ScanStatus,
  cardApi, collectionApi, scanApi,
} from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Step = "setup" | "review" | "done";

type EditableCandidate = ScanCandidate & { include: boolean };

const LANGS = ["DE", "EN", "CN", "JP", "FR", "ES", "IT"];

function parseLayout(layout: string): { cols: number; rows: number } {
  const m = layout.match(/^(\d+)x(\d+)$/);
  if (!m) return { cols: 3, rows: 3 };
  return { cols: Number(m[1]), rows: Number(m[2]) };
}

export default function ScanPage() {
  const { t } = useI18n();
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [collections, setCollections] = useState<Collection[]>([]);

  const [mode, setMode] = useState<ScanMode>("single");
  const [target, setTarget] = useState<"pokedex" | "collection">("pokedex");
  const [collectionId, setCollectionId] = useState<number | null>(null);
  const [layout, setLayout] = useState("3x3");
  const [setPokedexRep, setSetPokedexRep] = useState(false);

  const [step, setStep] = useState<Step>("setup");
  const [busy, setBusy] = useState(false);
  const [candidates, setCandidates] = useState<EditableCandidate[]>([]);
  const [savedCount, setSavedCount] = useState(0);

  // Kamera (nur in sicherem Kontext verfügbar – sonst Datei-Fallback)
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [cameraOn, setCameraOn] = useState(false);
  const canUseCamera = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  useEffect(() => {
    scanApi.status().then((r) => setStatus(r.data)).catch(() => {});
    cardApi.enums().then((r) => setEnums(r.data)).catch(() => {});
    collectionApi.list().then((r) => setCollections(r.data)).catch(() => {});
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
    if (!canUseCamera) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraOn(true);
    } catch {
      toast.error(t.scan_camera_unavailable);
    }
  };

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

  const runScan = useCallback(async (blob: Blob) => {
    setBusy(true);
    try {
      const { cols, rows } = parseLayout(layout);
      const res = await scanApi.scan(blob, {
        mode,
        rows: mode === "binder" ? rows : 0,
        cols: mode === "binder" ? cols : 0,
        default_language: "DE",
      });
      const list = res.data.candidates.map((c) => ({ ...c, include: true }));
      if (!list.length) {
        toast.error(t.scan_no_results);
        return;
      }
      setCandidates(list);
      setStep("review");
    } catch {
      toast.error(t.scan_error);
    } finally {
      setBusy(false);
    }
  }, [layout, mode, t]);

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

  const updateField = (idx: number, key: string, value: unknown) => {
    setCandidates((prev) =>
      prev.map((c, i) => (i === idx ? { ...c, suggested: { ...c.suggested, [key]: value } } : c))
    );
  };
  const toggleInclude = (idx: number) =>
    setCandidates((prev) => prev.map((c, i) => (i === idx ? { ...c, include: !c.include } : c)));

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
          dex_id: c.match?.dex_id ?? null,
          bild_karte_url: c.match?.image_url ?? null,
          position: c.position ?? null,
        };
      });
      const res = await scanApi.commit({
        target,
        collection_id: target === "collection" ? collectionId : null,
        set_im_pokedex: setPokedexRep,
        items,
      });
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
                <button
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
                onChange={(e) => setTarget(e.target.value as "pokedex" | "collection")}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
              >
                <option value="pokedex">{t.scan_target_pokedex}</option>
                <option value="collection">{t.scan_target_collection}</option>
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

          <label className="flex items-center gap-2 text-sm text-white">
            <input type="checkbox" checked={setPokedexRep} onChange={(e) => setSetPokedexRep(e.target.checked)} />
            {t.scan_set_pokedex_rep}
          </label>

          {/* Kamera / Datei */}
          <div className="rounded-lg border border-gray-700 bg-pokemon-card p-4">
            {cameraOn ? (
              <div className="space-y-3">
                <div className="relative mx-auto" style={{ maxWidth: 360 }}>
                  <video ref={videoRef} playsInline muted className="w-full rounded" />
                  <div className="pointer-events-none absolute inset-4 border-2 border-pokemon-yellow/70 rounded" />
                </div>
                <p className="text-center text-gray-500 text-xs">{t.scan_camera_hint}</p>
                <div className="flex gap-2 justify-center">
                  <button onClick={handleCapture} disabled={busy}
                    className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
                    {busy ? t.scan_analyzing : t.scan_capture}
                  </button>
                  <button onClick={stopCamera} className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
                    {t.scan_stop_camera}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3 text-center">
                <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
                  onChange={handleFile} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()} disabled={busy || engineActive === "none"}
                  className="bg-pokemon-blue text-white px-5 py-3 rounded-lg hover:bg-blue-500 disabled:opacity-50 w-full sm:w-auto">
                  {busy ? t.scan_analyzing : t.scan_take_photo}
                </button>
                {canUseCamera && (
                  <div>
                    <button onClick={startCamera} disabled={engineActive === "none"}
                      className="text-pokemon-blue hover:underline text-sm disabled:opacity-50">
                      {t.scan_start_camera}
                    </button>
                  </div>
                )}
                {!canUseCamera && (
                  <p className="text-gray-500 text-xs">{t.scan_camera_unavailable}</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {step === "review" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-white font-medium">{t.scan_results_title(candidates.length)}</h2>
            <button onClick={reset} className="text-gray-500 hover:text-white text-sm">{t.scan_back}</button>
          </div>

          {candidates.map((c, idx) => {
            const s = c.suggested as Record<string, unknown>;
            const uncertain = c.uncertain_fields.length > 0;
            const foilOptions = c.foil_options.length ? c.foil_options : (enums?.folierung ?? ["Normal"]);
            return (
              <div key={idx}
                className={`rounded-lg border p-3 flex gap-3 ${
                  !c.include ? "border-gray-800 opacity-50" : uncertain ? "border-pokemon-red" : "border-gray-700"
                } bg-pokemon-card`}>
                {/* Bild */}
                <div className="w-20 shrink-0">
                  {c.match?.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={c.match.image_url} alt="" className="w-full rounded" />
                  ) : (
                    <div className="aspect-[63/88] bg-gray-800 rounded flex items-center justify-center text-gray-600 text-xs">?</div>
                  )}
                  <div className="mt-1 text-center text-[10px] text-gray-500">
                    {t.scan_confidence}: {Math.round(c.confidence * 100)}%
                  </div>
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
                  <div className="grid grid-cols-2 gap-1.5">
                    <input
                      value={String(s.set_edition ?? "")}
                      onChange={(e) => updateField(idx, "set_edition", e.target.value)}
                      placeholder={t.scan_field_set}
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                    />
                    <input
                      value={String(s.karten_nr ?? "")}
                      onChange={(e) => updateField(idx, "karten_nr", e.target.value)}
                      placeholder={t.scan_field_nr}
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs font-mono"
                    />
                    <select
                      value={String(s.sprache ?? "DE")}
                      onChange={(e) => updateField(idx, "sprache", e.target.value)}
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                    >
                      {LANGS.map((l) => <option key={l} value={l}>{l}</option>)}
                    </select>
                    <select
                      value={String(s.folierung ?? "")}
                      onChange={(e) => updateField(idx, "folierung", e.target.value)}
                      className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-xs"
                    >
                      <option value="">{t.scan_field_foiling}</option>
                      {foilOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                    </select>
                  </div>
                </div>

                {/* Übernehmen-Toggle */}
                <div className="shrink-0 flex items-start">
                  <label className="flex items-center gap-1 text-xs text-gray-300">
                    <input type="checkbox" checked={c.include} onChange={() => toggleInclude(idx)} />
                    {t.scan_include}
                  </label>
                </div>
              </div>
            );
          })}

          <div className="fixed bottom-0 inset-x-0 bg-pokemon-dark/95 border-t border-gray-800 p-3">
            <div className="max-w-3xl mx-auto flex gap-3">
              <button onClick={handleSave} disabled={busy || !candidates.some((c) => c.include)}
                className="flex-1 bg-green-600 text-white px-4 py-2.5 rounded hover:bg-green-700 disabled:opacity-50">
                {busy ? t.scan_saving : t.scan_save_all}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === "done" && (
        <div className="text-center py-16 space-y-4">
          <div className="text-4xl">✅</div>
          <p className="text-white text-lg">{t.scan_saved(savedCount)}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={reset} className="bg-pokemon-blue text-white px-4 py-2 rounded hover:bg-blue-500">
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
