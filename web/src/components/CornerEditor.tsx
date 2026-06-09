"use client";
import { useEffect, useRef, useState } from "react";
import { clamp } from "@/lib/cardCrop";
import { useI18n } from "@/lib/i18n";

/**
 * Manuelle Eck-Korrektur eines Kartenfotos.
 * - 4 ziehbare Punkte (TL,TR,BR,BL, normiert 0..1)
 * - Lupe beim Ziehen (Finger verdeckt den Punkt nicht mehr)
 * - Zoom + Pan (bei mehreren Karten auf einem Bild genauer platzierbar)
 * Wird im Scan-Review und auf der Detailseite verwendet.
 */
export default function CornerEditor({
  imageUrl, initialQuad, onCancel, onApply,
}: {
  imageUrl: string;
  initialQuad: number[][];
  onCancel: () => void;
  onApply: (quad: number[][]) => void;
}) {
  const { t } = useI18n();
  const [quad, setQuad] = useState<number[][]>(initialQuad);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [active, setActive] = useState<number | null>(null);
  const [aspect, setAspect] = useState(88 / 63); // natH/natW, bis Bild geladen ist

  const vpRef = useRef<HTMLDivElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const activeRef = useRef<number | null>(null);
  const panningRef = useRef(false);
  const lastRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });

  // Globale Pointer-Listener (nur Refs lesen → keine veralteten Closures).
  useEffect(() => {
    const move = (e: PointerEvent) => {
      if (activeRef.current != null) {
        const el = imgRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        const nx = clamp((e.clientX - rect.left) / rect.width, 0, 1);
        const ny = clamp((e.clientY - rect.top) / rect.height, 0, 1);
        const i = activeRef.current;
        setQuad((prev) => prev.map((p, k) => (k === i ? [nx, ny] : p)));
      } else if (panningRef.current) {
        const dx = e.clientX - lastRef.current.x;
        const dy = e.clientY - lastRef.current.y;
        lastRef.current = { x: e.clientX, y: e.clientY };
        setPan((prev) => ({ x: prev.x + dx, y: prev.y + dy }));
      }
    };
    const up = () => {
      activeRef.current = null;
      panningRef.current = false;
      setActive(null);
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    window.addEventListener("pointercancel", up);
    return () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      window.removeEventListener("pointercancel", up);
    };
  }, []);

  // Zoom um die Viewport-Mitte (transformOrigin 0 0).
  const applyZoom = (next: number) => {
    const z = clamp(next, 1, 5);
    const vp = vpRef.current;
    setPan((prev) => {
      if (!vp) return prev;
      const cx = vp.clientWidth / 2, cy = vp.clientHeight / 2;
      return {
        x: cx - (z / zoom) * (cx - prev.x),
        y: cy - (z / zoom) * (cy - prev.y),
      };
    });
    setZoom(z);
  };
  const resetView = () => { setZoom(1); setPan({ x: 0, y: 0 }); };

  const startHandle = (e: React.PointerEvent, i: number) => {
    e.preventDefault();
    e.stopPropagation();
    activeRef.current = i;
    setActive(i);
  };
  const startPan = (e: React.PointerEvent) => {
    if (zoom <= 1) return; // ohne Zoom nichts zu schieben
    panningRef.current = true;
    lastRef.current = { x: e.clientX, y: e.clientY };
  };

  // Lupe: zeigt den Bereich um den aktiven Punkt vergrößert (unabhängig von
  // Pan/Zoom, direkt aus dem Originalbild). Position oben, gegenüber dem Punkt.
  const LOUPE = 124, FRAC = 0.16;
  const ap = active != null ? quad[active] : null;
  const loupeOnRight = ap ? ap[0] < 0.5 : true;
  const bgW = LOUPE / FRAC;
  const bgH = bgW * aspect;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-3"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className="bg-pokemon-card border border-gray-700 rounded-lg p-3 sm:p-4 max-w-lg w-full">
        <h3 className="text-white text-sm font-medium mb-1">{t.scan_corners_title}</h3>
        <p className="text-gray-400 text-xs mb-3">{t.scan_corners_hint}</p>

        <div
          ref={vpRef}
          className="relative mx-auto overflow-hidden rounded select-none touch-none bg-black"
          style={{ width: "100%", maxHeight: "60vh" }}
          onPointerDown={startPan}
          onWheel={(e) => applyZoom(zoom * (e.deltaY < 0 ? 1.15 : 0.87))}
        >
          <div
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: "0 0",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={imageUrl}
              alt=""
              draggable={false}
              className="w-full block"
              onLoad={(e) => {
                const im = e.currentTarget;
                if (im.naturalWidth > 0) setAspect(im.naturalHeight / im.naturalWidth);
              }}
            />
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 1 1" preserveAspectRatio="none"
            >
              <polygon
                points={quad.map(([x, y]) => `${x},${y}`).join(" ")}
                fill="rgba(250,204,21,0.12)" stroke="#facc15" strokeWidth={2}
                vectorEffect="non-scaling-stroke"
              />
            </svg>
            {quad.map(([x, y], i) => (
              <button
                key={i}
                type="button"
                onPointerDown={(e) => startHandle(e, i)}
                className={`absolute w-7 h-7 rounded-full border-2 text-[10px] font-bold flex items-center justify-center touch-none ${
                  active === i ? "bg-pokemon-blue text-white border-white" : "bg-pokemon-yellow/90 text-black border-black"
                }`}
                style={{
                  left: `${x * 100}%`,
                  top: `${y * 100}%`,
                  transform: `translate(-50%, -50%) scale(${1 / zoom})`,
                }}
              >
                {i + 1}
              </button>
            ))}
          </div>

          {/* Lupe */}
          {ap && (
            <div
              className="absolute pointer-events-none rounded-full border-2 border-white shadow-lg overflow-hidden"
              style={{
                width: LOUPE, height: LOUPE,
                top: 8,
                left: loupeOnRight ? undefined : 8,
                right: loupeOnRight ? 8 : undefined,
                backgroundImage: `url(${imageUrl})`,
                backgroundRepeat: "no-repeat",
                backgroundSize: `${bgW}px ${bgH}px`,
                backgroundPosition: `${LOUPE / 2 - ap[0] * bgW}px ${LOUPE / 2 - ap[1] * bgH}px`,
              }}
            >
              <div className="absolute left-1/2 top-0 h-full w-px bg-pokemon-yellow/70" />
              <div className="absolute top-1/2 left-0 w-full h-px bg-pokemon-yellow/70" />
            </div>
          )}
        </div>

        {/* Zoom-Steuerung */}
        <div className="flex items-center justify-center gap-2 mt-3 text-sm">
          <button onClick={() => applyZoom(zoom * 0.8)} disabled={zoom <= 1}
            className="w-9 h-9 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-40">−</button>
          <span className="text-gray-300 text-xs w-12 text-center">{Math.round(zoom * 100)}%</span>
          <button onClick={() => applyZoom(zoom * 1.25)} disabled={zoom >= 5}
            className="w-9 h-9 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-40">+</button>
          <button onClick={resetView} disabled={zoom === 1 && pan.x === 0 && pan.y === 0}
            className="ml-1 px-2 h-9 rounded bg-gray-700 text-white text-xs hover:bg-gray-600 disabled:opacity-40">
            {t.scan_corners_reset_view}
          </button>
        </div>

        <div className="flex gap-2 justify-end mt-3 flex-wrap">
          <button onClick={() => { setQuad(initialQuad); resetView(); }}
            className="text-gray-400 hover:text-white text-sm px-3 py-1.5">
            {t.scan_corners_reset}
          </button>
          <button onClick={onCancel} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded hover:bg-gray-600">
            {t.scan_corners_cancel}
          </button>
          <button onClick={() => onApply(quad)} className="bg-green-600 text-white text-sm px-4 py-1.5 rounded hover:bg-green-700">
            {t.scan_corners_apply}
          </button>
        </div>
      </div>
    </div>
  );
}
