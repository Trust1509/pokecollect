/**
 * Gemeinsame Bild-Helfer für das Zuschneiden/Entzerren von Kartenfotos.
 * Wird vom Scan-Review UND der Karten-Detailseite genutzt.
 *
 * Kernstück: cropToCardPhoto() schneidet/entzerrt ein Foto auf Karten-Format
 * (63:88). Bei 4 Eckpunkten (quad) echte perspektivische Entzerrung via
 * Homographie (feines Gitter), sonst achsenparalleler/zentrierter Zuschnitt.
 */

export const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

export function loadImg(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const i = new Image();
    i.onload = () => resolve(i);
    i.onerror = reject;
    i.src = url;
  });
}

/** Löst X_i = A*u_i + C*v_i + E (3 Punkte) → [A, C, E]. */
function solveAffine(u: number[], v: number[], X: number[]): [number, number, number] | null {
  const det = u[0] * (v[1] - v[2]) - v[0] * (u[1] - u[2]) + (u[1] * v[2] - u[2] * v[1]);
  if (Math.abs(det) < 1e-9) return null;
  const A = (X[0] * (v[1] - v[2]) - v[0] * (X[1] - X[2]) + (X[1] * v[2] - X[2] * v[1])) / det;
  const C = (u[0] * (X[1] - X[2]) - X[0] * (u[1] - u[2]) + (u[1] * X[2] - u[2] * X[1])) / det;
  const E = (u[0] * (v[1] * X[2] - v[2] * X[1]) - v[0] * (u[1] * X[2] - u[2] * X[1]) + X[0] * (u[1] * v[2] - u[2] * v[1])) / det;
  return [A, C, E];
}

/** Zeichnet ein Quell-Dreieck so, dass es auf das Ziel-Dreieck abgebildet wird (affin). */
function drawTriangle(
  ctx: CanvasRenderingContext2D, img: HTMLImageElement,
  s: number[][], d: number[][],
) {
  const u = [s[0][0], s[1][0], s[2][0]];
  const v = [s[0][1], s[1][1], s[2][1]];
  const ace = solveAffine(u, v, [d[0][0], d[1][0], d[2][0]]);
  const bdf = solveAffine(u, v, [d[0][1], d[1][1], d[2][1]]);
  if (!ace || !bdf) return;
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(d[0][0], d[0][1]); ctx.lineTo(d[1][0], d[1][1]); ctx.lineTo(d[2][0], d[2][1]);
  ctx.closePath();
  ctx.clip();
  ctx.setTransform(ace[0], bdf[0], ace[1], bdf[1], ace[2], bdf[2]);
  ctx.drawImage(img, 0, 0);
  ctx.restore();
}

/** Schiebt die drei Ecken um `px` Pixel vom Schwerpunkt weg (gegen Hairline-Nähte). */
function inflateTri(tri: number[][], px: number): number[][] {
  const cx = (tri[0][0] + tri[1][0] + tri[2][0]) / 3;
  const cy = (tri[0][1] + tri[1][1] + tri[2][1]) / 3;
  return tri.map(([x, y]) => {
    const dx = x - cx, dy = y - cy;
    const len = Math.hypot(dx, dy) || 1;
    return [x + (dx / len) * px, y + (dy / len) * px];
  });
}

/**
 * Löst die projektive Abbildung src→dst (3×3-Homographie, 8 Koeffizienten)
 * via Gauß-Elimination eines 8×8-Systems. null bei degenerierten Punkten.
 */
function solveHomography(src: number[][], dst: number[][]): number[] | null {
  const M: number[][] = [];
  const r: number[] = [];
  for (let i = 0; i < 4; i++) {
    const [x, y] = src[i];
    const [X, Y] = dst[i];
    M.push([x, y, 1, 0, 0, 0, -X * x, -X * y]); r.push(X);
    M.push([0, 0, 0, x, y, 1, -Y * x, -Y * y]); r.push(Y);
  }
  for (let col = 0; col < 8; col++) {
    let piv = col;
    for (let row = col + 1; row < 8; row++) {
      if (Math.abs(M[row][col]) > Math.abs(M[piv][col])) piv = row;
    }
    if (Math.abs(M[piv][col]) < 1e-9) return null;
    [M[col], M[piv]] = [M[piv], M[col]];
    [r[col], r[piv]] = [r[piv], r[col]];
    const d = M[col][col];
    for (let k = col; k < 8; k++) M[col][k] /= d;
    r[col] /= d;
    for (let row = 0; row < 8; row++) {
      if (row === col) continue;
      const factor = M[row][col];
      if (!factor) continue;
      for (let k = col; k < 8; k++) M[row][k] -= factor * M[col][k];
      r[row] -= factor * r[col];
    }
  }
  return r;
}

/**
 * Echte perspektivische Entzerrung: bildet das Quell-Viereck `srcQuad`
 * (Pixel, Reihenfolge TL,TR,BR,BL) auf das Rechteck 0,0–W,H ab (feines Gitter
 * → konvergiert gegen die echte Homographie, keine Diagonal-Verzerrung).
 */
function warpPerspective(
  ctx: CanvasRenderingContext2D, img: HTMLImageElement,
  srcQuad: number[][], W: number, H: number, divisions = 16,
): boolean {
  const dstQuad = [[0, 0], [W, 0], [W, H], [0, H]];
  const Hinv = solveHomography(dstQuad, srcQuad);
  if (!Hinv) return false;
  const map = (X: number, Y: number): number[] => {
    const den = Hinv[6] * X + Hinv[7] * Y + 1;
    return [(Hinv[0] * X + Hinv[1] * Y + Hinv[2]) / den, (Hinv[3] * X + Hinv[4] * Y + Hinv[5]) / den];
  };
  const N = divisions;
  for (let r = 0; r < N; r++) {
    for (let c = 0; c < N; c++) {
      const x0 = (c / N) * W, x1 = ((c + 1) / N) * W;
      const y0 = (r / N) * H, y1 = ((r + 1) / N) * H;
      const d = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
      const s = d.map(([X, Y]) => map(X, Y));
      drawTriangle(ctx, img, [s[0], s[1], s[2]], inflateTri([d[0], d[1], d[2]], 0.6));
      drawTriangle(ctx, img, [s[0], s[2], s[3]], inflateTri([d[0], d[2], d[3]], 0.6));
    }
  }
  return true;
}

/**
 * Sortiert 4 Punkte (Pixel) nach Bildposition in die Reihenfolge
 * TL,TR,BR,BL. Robust gegen falsche Eck-Reihenfolge der Erkennung (verhindert
 * gespiegelte/auf-dem-Kopf-stehende Zuschnitte). Nur für den Auto-Pfad – bei
 * manueller Eingabe legt der Nutzer die Reihenfolge selbst fest.
 */
function orderQuad(pts: number[][]): number[][] {
  const byY = [...pts].sort((a, b) => a[1] - b[1]);
  const top = byY.slice(0, 2).sort((a, b) => a[0] - b[0]);    // TL, TR
  const bottom = byY.slice(2, 4).sort((a, b) => a[0] - b[0]); // BL, BR
  return [top[0], top[1], bottom[1], bottom[0]];
}

export type CropTransform = { flipH?: boolean; flipV?: boolean; rotate?: number };

/** Wendet Spiegelung/Drehung (90°-Schritte) auf ein fertiges Canvas an. */
function applyOrient(srcCanvas: HTMLCanvasElement, o: CropTransform): HTMLCanvasElement {
  const rot = (((o.rotate ?? 0) % 360) + 360) % 360;
  if (!o.flipH && !o.flipV && rot === 0) return srcCanvas;
  const swap = rot === 90 || rot === 270;
  const out = document.createElement("canvas");
  out.width = swap ? srcCanvas.height : srcCanvas.width;
  out.height = swap ? srcCanvas.width : srcCanvas.height;
  const ctx = out.getContext("2d")!;
  ctx.translate(out.width / 2, out.height / 2);
  ctx.rotate((rot * Math.PI) / 180);
  ctx.scale(o.flipH ? -1 : 1, o.flipV ? -1 : 1);
  ctx.drawImage(srcCanvas, -srcCanvas.width / 2, -srcCanvas.height / 2);
  return out;
}

/**
 * Schneidet/entzerrt das Kartenfoto zu Karten-Format (63:88):
 *  - quad (4 Ecken, normiert 0..1) → perspektivische Entzerrung (auch schräg)
 *  - bbox [x,y,w,h] → achsenparalleler Zuschnitt (Querformat → 90° gedreht)
 *  - sonst zentrierter Zuschnitt
 * autoOrient: Ecken nach Bildposition sortieren (Auto-/Gemini-Pfad).
 * flipH/flipV/rotate: nachträgliche manuelle Korrektur der Ausrichtung.
 */
export async function cropToCardPhoto(
  blob: Blob,
  opts?: { bbox?: number[] | null; quad?: number[][] | null; autoOrient?: boolean } & CropTransform,
): Promise<File> {
  const url = URL.createObjectURL(blob);
  try {
    const img = await loadImg(url);
    const W = 460, H = Math.round((W * 88) / 63);
    let canvas = document.createElement("canvas");

    if (opts?.quad && opts.quad.length === 4) {
      let src = opts.quad.map(([x, y]) => [clamp(x, 0, 1) * img.width, clamp(y, 0, 1) * img.height]);
      // Auto-Pfad: Ecken nach Bildposition sortieren (gegen Spiegelung/Kopfstand).
      if (opts.autoOrient) src = orderQuad(src);
      // Karten sind Hochformat: liegt die Karte quer, Ecken um 1 rotieren.
      const dist = (a: number[], b: number[]) => Math.hypot(a[0] - b[0], a[1] - b[1]);
      if (dist(src[0], src[1]) > dist(src[0], src[3])) {
        src = [src[1], src[2], src[3], src[0]];
      }
      canvas.width = W; canvas.height = H;
      const ctx = canvas.getContext("2d")!;
      if (!warpPerspective(ctx, img, src, W, H)) {
        const dst = [[0, 0], [W, 0], [W, H], [0, H]];
        drawTriangle(ctx, img, [src[0], src[1], src[2]], [dst[0], dst[1], dst[2]]);
        drawTriangle(ctx, img, [src[0], src[2], src[3]], [dst[0], dst[2], dst[3]]);
      }
    } else {
      let sx: number, sy: number, sw: number, sh: number;
      const bbox = opts?.bbox;
      if (bbox && bbox.length === 4) {
        const pad = 0.03;
        const [bx, by, bw, bh] = bbox;
        sx = clamp((bx - pad) * img.width, 0, img.width);
        sy = clamp((by - pad) * img.height, 0, img.height);
        sw = clamp((bw + 2 * pad) * img.width, 1, img.width - sx);
        sh = clamp((bh + 2 * pad) * img.height, 1, img.height - sy);
      } else {
        const ratio = 63 / 88;
        sw = img.width;
        sh = Math.round(sw / ratio);
        if (sh > img.height) { sh = img.height; sw = Math.round(sh * ratio); }
        sx = Math.round((img.width - sw) / 2);
        sy = Math.round((img.height - sh) / 2);
      }
      const maxW = 600;
      const scale = sw > maxW ? maxW / sw : 1;
      const dw = Math.round(sw * scale);
      const dh = Math.round(sh * scale);
      const ctx = canvas.getContext("2d")!;
      if (dw > dh) {
        canvas.width = dh; canvas.height = dw;
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.drawImage(img, sx, sy, sw, sh, -dw / 2, -dh / 2, dw, dh);
      } else {
        canvas.width = dw; canvas.height = dh;
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, dw, dh);
      }
    }

    // Manuelle Ausrichtungs-Korrektur (Flip/Rotate) zuletzt anwenden.
    canvas = applyOrient(canvas, { flipH: opts?.flipH, flipV: opts?.flipV, rotate: opts?.rotate });
    const out = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", 0.9));
    return new File([out ?? blob], "card.jpg", { type: "image/jpeg" });
  } finally {
    URL.revokeObjectURL(url);
  }
}
