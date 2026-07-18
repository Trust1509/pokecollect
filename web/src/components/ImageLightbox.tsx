"use client";
import { useEffect } from "react";
import { useI18n } from "@/lib/i18n";

type Props = {
  /** Bildquelle; null = Lightbox geschlossen (nichts gerendert). */
  src: string | null;
  alt: string;
  onClose: () => void;
};

// Wiederverwendbare Vollbild-Lightbox (Issue #24): zeigt ein Bild formatfüllend
// über einem abdunkelnden Hintergrund. Schließen per Klick auf den Hintergrund,
// per Schließen-Knopf oder mit ESC. Wird nur gerendert, wenn `src` gesetzt ist.
export default function ImageLightbox({ src, alt, onClose }: Props) {
  const { t } = useI18n();

  useEffect(() => {
    if (!src) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    // Hintergrund-Scroll sperren, solange die Lightbox offen ist
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [src, onClose]);

  if (!src) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={alt}
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4 cursor-zoom-out"
    >
      <button
        type="button"
        onClick={onClose}
        aria-label={t.detail_close_image}
        className="absolute top-3 right-3 w-10 h-10 flex items-center justify-center rounded-full bg-black/40 text-white/80 hover:bg-black/60 hover:text-white text-3xl leading-none"
      >
        ×
      </button>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        onClick={(e) => e.stopPropagation()}
        className="max-w-full max-h-full object-contain rounded-lg shadow-2xl cursor-default"
      />
    </div>
  );
}
