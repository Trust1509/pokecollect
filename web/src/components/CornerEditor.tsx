"use client";
import { useEffect, useRef, useState } from "react";
import { clamp, CropTransform } from "@/lib/cardCrop";
import { useI18n } from "@/lib/i18n";

/**
 * Manuelle Eck-Korrektur eines Kartenfotos.
 * - 4 ziehbare Punkte (TL,TR,BR,BL, normiert 0..1) + Lupe beim Ziehen
 * - Zoom & Verschieben per Fingergesten (Pinch/1-Finger-Drag) und am Desktop
 *   per Mausrad / Linksklick-halten
 * - Flip/Rotate als manuelle Ausrichtungs-Korrektur
 * Wird im Scan-Review und auf der Detailseite verwendet.
 */
export default function CornerEditor({
  imageUrl, initialQuad, onCancel, onApply,
}: {
  imageUrl: string;
  initialQuad: number[][];
  onCancel: () => void;
  onApply: (quad: number[][], transform: CropTransform) => void;
}) {
  const { t } = useI18n();
  const [quad, setQuad] = useState<number[][]>(initialQuad);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [active, setActive] = useState<number | null>(null);
  const [aspect, setAspect] = useState(88 / 63);
  const [flipH, setFlipH] = useState(false);
  const [flipV, setFlipV] = useState(false);
  const [rotate, setRotate] = useState(0);

  const vpRef = useRef<HTMLDivElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);
  const zoomRef = useRef(1);
  const panRef = useRef({ x: 0, y: 0 });
  const activeRef = useRef<number | null>(null);
  const pointersRef = useRef<Map<number, { x: number; y: number }>>(new Map());
  const pinchRef = useRef<{ dist: number; mid: { x: number; y: number } } | null>(null);

  const setView = (z: number, p: { x: number; y: number }) => {
    zoomRef.current = z; panRef.current = p;
    setZoom(z); setPan(p);
  };

  // Bild mittig in den Viewport setzen (Ausgangszustand).
  const centerView = () => {
    const vp = vpRef.current, im = imgRef.current;
    if (!vp || !im) return;
    setView(1, {
      x: (vp.clientWidth - im.offsetWidth) / 2,
      y: (vp.clientHeight - im.offsetHeight) / 2,
    });
  };

  const zoomAround = (px: number, py: number, factor: number) => {
    const z0 = zoomRef.current;
    const z = clamp(z0 * factor, 1, 8);
    const f = z / z0;
    const p0 = panRef.current;
    setView(z, { x: px - f * (px - p0.x), y: py - f * (py - p0.y) });
  };

  const vpCenterZoom = (factor: number) => {
    const vp = vpRef.current;
    if (!vp) return;
    zoomAround(vp.clientWidth / 2, vp.clientHeight / 2, factor);
  };

  useEffect(() => {
    const dist2 = (a: { x: number; y: number }, b: { x: number; y: number }) =>
      Math.hypot(a.x - b.x, a.y - b.y);

    const move = (e: PointerEvent) => {
      // 1) Eckpunkt ziehen
      if (activeRef.current != null) {
        const el = imgRef.current;
        if (!el) return;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        const nx = clamp((e.clientX - rect.left) / rect.width, 0, 1);
        const ny = clamp((e.clientY - rect.top) / rect.height, 0, 1);
        const i = activeRef.current;
        setQuad((prev) => prev.map((p, k) => (k === i ? [nx, ny] : p)));
        return;
      }
      // 2) Pan / Pinch
      const ptrs = pointersRef.current;
      if (!ptrs.has(e.pointerId)) return;
      const prev = ptrs.get(e.pointerId)!;
      const cur = { x: e.clientX, y: e.clientY };
      ptrs.set(e.pointerId, cur);
      if (ptrs.size >= 2) {
        const [a, b] = Array.from(ptrs.values());
        const off = vpRef.current?.getBoundingClientRect();
        const offLeft = off?.left ?? 0, offTop = off?.top ?? 0;
        const mid = { x: (a.x + b.x) / 2 - offLeft, y: (a.y + b.y) / 2 - offTop };
        const d = dist2(a, b);
        if (pinchRef.current) {
          const factor = d / (pinchRef.current.dist || d);
          zoomAround(mid.x, mid.y, factor);
          const dmx = mid.x - pinchRef.current.mid.x;
          const dmy = mid.y - pinchRef.current.mid.y;
          setView(zoomRef.current, { x: panRef.current.x + dmx, y: panRef.current.y + dmy });
        }
        pinchRef.current = { dist: d, mid };
      } else {
        const dx = cur.x - prev.x, dy = cur.y - prev.y;
        setView(zoomRef.current, { x: panRef.current.x + dx, y: panRef.current.y + dy });
      }
    };
    const up = (e: PointerEvent) => {
      pointersRef.current.delete(e.pointerId);
      if (pointersRef.current.size < 2) pinchRef.current = null;
      activeRef.current = null;
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startHandle = (e: React.PointerEvent, i: number) => {
    e.preventDefault();
    e.stopPropagation();
    activeRef.current = i;
    setActive(i);
  };
  const startPanPointer = (e: React.PointerEvent) => {
    pointersRef.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (pointersRef.current.size === 2) {
      const [a, b] = Array.from(pointersRef.current.values());
      const off = vpRef.current?.getBoundingClientRect();
      const offLeft = off?.left ?? 0, offTop = off?.top ?? 0;
      pinchRef.current = {
        dist: Math.hypot(a.x - b.x, a.y - b.y),
        mid: { x: (a.x + b.x) / 2 - offLeft, y: (a.y + b.y) / 2 - offTop },
      };
    }
  };

  // Lupe (oben, gegenüber dem aktiven Punkt; direkt aus dem Originalbild).
  const LOUPE = 124, FRAC = 0.16;
  const ap = active != null ? quad[active] : null;
  const loupeOnRight = ap ? ap[0] < 0.5 : true;
  const bgW = LOUPE / FRAC;
  const bgH = bgW * aspect;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-2 sm:p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}
    >
      <div className="bg-pokemon-card border border-gray-700 rounded-lg p-3 sm:p-4 w-full max-w-lg max-h-[95vh] flex flex-col">
        <h3 className="text-white text-sm font-medium mb-1">{t.scan_corners_title}</h3>
        <p className="text-gray-400 text-xs mb-2">{t.scan_corners_hint}</p>

        <div
          ref={vpRef}
          className="relative mx-auto overflow-hidden rounded select-none touch-none bg-black w-full"
          style={{ height: "56vh" }}
          onPointerDown={startPanPointer}
          onWheel={(e) => {
            const vp = vpRef.current;
            const off = vp ? vp.getBoundingClientRect() : null;
            if (off) zoomAround(e.clientX - off.left, e.clientY - off.top, e.deltaY < 0 ? 1.12 : 0.89);
          }}
        >
          <div
            className="absolute top-0 left-0"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`, transformOrigin: "0 0" }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={imgRef}
              src={imageUrl}
              alt=""
              draggable={false}
              className="block"
              style={{ maxHeight: "56vh", maxWidth: "100%" }}
              onLoad={(e) => {
                const im = e.currentTarget;
                if (im.naturalWidth > 0) setAspect(im.naturalHeight / im.naturalWidth);
                centerView();
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
                style={{ left: `${x * 100}%`, top: `${y * 100}%`, transform: `translate(-50%, -50%) scale(${1 / zoom})` }}
              >
                {i + 1}
              </button>
            ))}
          </div>

          {ap && (
            <div
              className="absolute pointer-events-none rounded-full border-2 border-white shadow-lg overflow-hidden"
              style={{
                width: LOUPE, height: LOUPE, top: 8,
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

        {/* Zoom + Ausrichtung */}
        <div className="flex items-center justify-center gap-1.5 mt-2 flex-wrap text-sm">
          <button onClick={() => vpCenterZoom(0.8)} disabled={zoom <= 1}
            className="w-9 h-9 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-40">−</button>
          <span className="text-gray-300 text-xs w-11 text-center">{Math.round(zoom * 100)}%</span>
          <button onClick={() => vpCenterZoom(1.25)} disabled={zoom >= 8}
            className="w-9 h-9 rounded bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-40">+</button>
          <span className="w-2" />
          <button onClick={() => setRotate((r) => (r + 90) % 360)} title={t.scan_corners_rotate}
            className="px-2 h-9 rounded bg-gray-700 text-white text-xs hover:bg-gray-600">⟳ 90°</button>
          <button onClick={() => setFlipH((v) => !v)} title={t.scan_corners_fliph}
            className={`w-9 h-9 rounded text-white ${flipH ? "bg-pokemon-blue" : "bg-gray-700 hover:bg-gray-600"}`}>⇋</button>
          <button onClick={() => setFlipV((v) => !v)} title={t.scan_corners_flipv}
            className={`w-9 h-9 rounded text-white ${flipV ? "bg-pokemon-blue" : "bg-gray-700 hover:bg-gray-600"}`}>⇅</button>
          <button onClick={centerView} disabled={zoom === 1 && pan.x >= 0}
            className="px-2 h-9 rounded bg-gray-700 text-white text-xs hover:bg-gray-600 disabled:opacity-40">
            {t.scan_corners_reset_view}
          </button>
        </div>

        <div className="flex gap-2 justify-end mt-3 flex-wrap">
          <button onClick={() => { setQuad(initialQuad); setFlipH(false); setFlipV(false); setRotate(0); centerView(); }}
            className="text-gray-400 hover:text-white text-sm px-3 py-1.5">
            {t.scan_corners_reset}
          </button>
          <button onClick={onCancel} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded hover:bg-gray-600">
            {t.scan_corners_cancel}
          </button>
          <button onClick={() => onApply(quad, { flipH, flipV, rotate })}
            className="bg-green-600 text-white text-sm px-4 py-1.5 rounded hover:bg-green-700">
            {t.scan_corners_apply}
          </button>
        </div>
      </div>
    </div>
  );
}
