"use client";
import { useRef, useState } from "react";
import Image from "next/image";
import toast from "react-hot-toast";
import { API_BASE, Card, cardApi } from "@/lib/api";
import CornerEditor from "@/components/CornerEditor";
import { cropToCardPhoto, normalizeOrientation, CropTransform } from "@/lib/cardCrop";
import { imageUrl, cardImageSrc } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

// Foto-Spalte der Kartendetailseite (Issue #14): Anzeige, Aufnahme/Upload,
// Eck-Editor (Zuschnitt/Entzerrung), Bild-URL und Löschen. Herausgeschnitten
// aus cards/[id]/page.tsx — Verhalten 1:1.

type Props = {
  card: Card;
  /** Server-Antwort übernehmen (nur Kartenzustand). */
  onCardUpdated: (card: Card) => void;
  /** Server-Antwort übernehmen UND Formular synchronisieren (URL-Änderungen). */
  onCardSaved: (card: Card) => void;
  /** Klick/Tap aufs Kartenbild → Vollbild-Lightbox öffnen (Issue #24). */
  onImageClick?: (src: string) => void;
  /** Horizontales Wischen aufs Kartenbild → Vor/Zurück blättern (Issue #24, Mobil). */
  onSwipeCard?: (dir: "prev" | "next") => void;
};

export default function PhotoPanel({ card, onCardUpdated, onCardSaved, onImageClick, onSwipeCard }: Props) {
  const { t } = useI18n();
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [urlInput, setUrlInput] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  // Foto-Zuschnitt/Entzerrung vor dem Upload (CornerEditor)
  const [editorUrl, setEditorUrl] = useState<string | null>(null);
  const [editorInitQuad, setEditorInitQuad] = useState<number[][]>(
    [[0.06, 0.05], [0.94, 0.05], [0.94, 0.95], [0.06, 0.95]]);
  const editorBlobRef = useRef<Blob | null>(null);
  const editorOriginalRef = useRef<Blob | null>(null);  // Original mit-hochladen (nur bei neuem Foto)
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  // Tap-vs-Wisch aufs Kartenbild (Issue #24): Tap öffnet die Lightbox, ein
  // horizontaler Wisch blättert zur Nachbarkarte und unterdrückt den Folge-Klick.
  const swipeStart = useRef<{ x: number; y: number } | null>(null);
  const swipeSuppressClick = useRef(false);

  const onPhotoTouchStart = (e: React.TouchEvent) => {
    if (editorUrl) return;               // Foto-Editor offen → nicht blättern
    const tch = e.touches[0];
    swipeStart.current = { x: tch.clientX, y: tch.clientY };
  };
  const onPhotoTouchEnd = (e: React.TouchEvent) => {
    const start = swipeStart.current;
    swipeStart.current = null;
    if (!start || editorUrl || !onSwipeCard) return;
    const tch = e.changedTouches[0];
    const dx = tch.clientX - start.x;
    const dy = tch.clientY - start.y;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      swipeSuppressClick.current = true; // folgenden Zoom-Klick unterdrücken
      onSwipeCard(dx < 0 ? "next" : "prev");
    }
  };
  // Bild-Prioritätskette zentral in cardImageSrc (Vertrag mit dem Backend,
  // siehe backend/app/services/card_image_service.py:14-18) — Issue #10
  const { src: imgSrc, isPlaceholder } = cardImageSrc(card, API_BASE, true, "full");
  const isAutoCard = !card.bild_karte_pfad && !card.bild_pokedex_url && !!card.bild_karte_url;
  // Tap/Klick aufs Bild öffnet die Lightbox — außer direkt nach einem Wisch.
  const handleImageClick = () => {
    if (swipeSuppressClick.current) { swipeSuppressClick.current = false; return; }
    if (imgSrc && onImageClick) onImageClick(imgSrc);
  };

  // Foto gewählt/aufgenommen → erst im Eck-Editor zuschneiden/entzerren,
  // dann hochladen. So lässt sich das Foto vor dem Speichern bearbeiten.
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    // EXIF einbacken → Editor-Anzeige == gespeicherter Zuschnitt
    const norm = await normalizeOrientation(file);
    editorBlobRef.current = norm;
    editorOriginalRef.current = norm;   // neues Foto → Original mitspeichern
    setEditorInitQuad([[0.06, 0.05], [0.94, 0.05], [0.94, 0.95], [0.06, 0.95]]);
    setEditorUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(norm);
    });
  };

  // Bereits hochgeladenes eigenes Foto nachträglich bearbeiten (Zuschnitt /
  // Flip / Drehen). Bevorzugt das ungeschnittene Original (falls vorhanden),
  // damit man großzügiger neu zuschneiden kann.
  const handleEditExisting = async () => {
    if (!card.bild_karte_pfad) return;
    const fromOriginal = !!card.bild_original_pfad;
    const src = imageUrl(card.bild_original_pfad ?? card.bild_karte_pfad, API_BASE, card.aktualisiert_am);
    if (!src) return;
    try {
      const resp = await fetch(src);
      const blob = await resp.blob();
      editorBlobRef.current = blob;
      editorOriginalRef.current = null;   // Bearbeitung → Original NICHT überschreiben
      // Original: Karte freistellen (Ecken setzen). Bereits-Zuschnitt: nur Flip/Drehen.
      setEditorInitQuad(fromOriginal
        ? [[0.1, 0.08], [0.9, 0.08], [0.9, 0.92], [0.1, 0.92]]
        : [[0.01, 0.01], [0.99, 0.01], [0.99, 0.99], [0.01, 0.99]]);
      setEditorUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(blob);
      });
    } catch {
      toast.error(t.detail_upload_error);
    }
  };

  const closePhotoEditor = () => {
    setEditorUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return null;
    });
    editorBlobRef.current = null;
    editorOriginalRef.current = null;
  };

  const handleApplyPhoto = async (quad: number[][], transform: CropTransform) => {
    const blob = editorBlobRef.current;
    if (!blob) { closePhotoEditor(); return; }
    setUploadingPhoto(true);
    try {
      const file = await cropToCardPhoto(blob, { quad, ...transform });
      const original = editorOriginalRef.current
        ? new File([editorOriginalRef.current], "orig.jpg", { type: "image/jpeg" })
        : undefined;
      const r = await cardApi.uploadImage(card.id, file, original);
      onCardUpdated(r.data);
      toast.success(t.detail_photo_saved);
      closePhotoEditor();
    } catch {
      toast.error(t.detail_upload_error);
    } finally {
      setUploadingPhoto(false);
    }
  };

  const handleSaveUrl = async () => {
    const url = urlInput.trim();
    if (!url) return;
    try {
      const r = await cardApi.update(card.id, { bild_pokedex_url: url });
      onCardSaved(r.data);
      setShowUrlInput(false);
      setUrlInput("");
      toast.success(t.detail_url_saved);
    } catch {
      toast.error(t.detail_url_save_error);
    }
  };

  const handleClearPokedexUrl = async () => {
    if (!confirm(t.detail_delete_url_confirm)) return;
    try {
      const r = await cardApi.update(card.id, { bild_pokedex_url: null });
      onCardSaved(r.data);
      toast.success(t.detail_url_deleted);
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  const handleDeleteImage = async () => {
    if (!confirm(t.detail_delete_photo_confirm)) return;
    try {
      const r = await cardApi.deleteImage(card.id);
      onCardUpdated(r.data);
      toast.success(t.detail_photo_saved);
      // Server stößt direkt nach der Antwort den TCGdex-Nachladejob an →
      // Karte explizit neu laden statt setTimeout-Polling (Issue #14).
      const r2 = await cardApi.get(card.id);
      onCardUpdated(r2.data);
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  return (
    <div className="shrink-0 w-full max-w-[13rem] mx-auto md:mx-0 md:w-52">
      <div
        className="aspect-[63/88] relative bg-gray-800 rounded-lg overflow-hidden"
        onTouchStart={onPhotoTouchStart}
        onTouchEnd={onPhotoTouchEnd}
      >
        {imgSrc ? (
          <>
            <Image
              src={imgSrc}
              alt={card.kartenname}
              fill
              className={isPlaceholder ? "object-contain p-4 opacity-75" : "object-cover"}
            />
            {isAutoCard && (
              <div className="absolute bottom-0 inset-x-0 bg-black/60 text-center text-blue-400 text-xs py-1">
                TCGdex
              </div>
            )}
            {isPlaceholder && (
              <div className="absolute bottom-0 inset-x-0 bg-black/60 text-center text-gray-400 text-xs py-1">
                {t.detail_placeholder}
              </div>
            )}
            {onImageClick && (
              // Transparente Ebene über dem Bild: Tap/Klick öffnet die Lightbox
              // (Wisch-Gesten laufen über die onTouch-Handler des Containers).
              <button
                type="button"
                onClick={handleImageClick}
                aria-label={t.detail_zoom_image}
                className="absolute inset-0 z-10 cursor-zoom-in"
              />
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600">{t.detail_no_image}</div>
        )}
      </div>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
      <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleImageUpload} />
      <div className="mt-2 grid grid-cols-2 gap-1">
        <button type="button"
          onClick={() => cameraRef.current?.click()}
          className="text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
        >
          {t.detail_take_photo}
        </button>
        <button type="button"
          onClick={() => fileRef.current?.click()}
          className="text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
        >
          {card.bild_karte_pfad ? t.detail_replace_photo : t.detail_upload_photo}
        </button>
      </div>
      {card.bild_karte_pfad && (
        <button type="button"
          onClick={() => void handleEditExisting()}
          className="w-full mt-1 text-sm bg-gray-800 text-pokemon-blue hover:text-white rounded px-3 py-1.5"
        >
          ✥ {t.detail_edit_photo}
        </button>
      )}
      {!card.bild_karte_pfad && (
        <button type="button"
          onClick={() => { setShowUrlInput((v) => !v); setUrlInput(card.bild_pokedex_url ?? ""); }}
          className="w-full mt-1 text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
        >
          {card.bild_pokedex_url ? t.detail_change_url : t.detail_set_url}
        </button>
      )}
      {showUrlInput && (
        <div className="mt-1 flex gap-1">
          <input
            type="url"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            placeholder="https://…"
            className="flex-1 min-w-0 bg-gray-900 border border-gray-600 rounded px-2 py-1 text-white text-xs"
            onKeyDown={(e) => e.key === "Enter" && handleSaveUrl()}
          />
          <button type="button" onClick={handleSaveUrl} className="text-xs bg-green-700 text-white rounded px-2 py-1 hover:bg-green-600">OK</button>
        </div>
      )}
      {(card.bild_karte_pfad || card.bild_pokedex_url) && (
        <button type="button"
          onClick={card.bild_karte_pfad ? handleDeleteImage : handleClearPokedexUrl}
          className="w-full mt-1 text-sm bg-red-950 text-red-400 hover:text-red-200 rounded px-3 py-1.5"
        >
          {card.bild_karte_pfad ? t.detail_delete_photo : t.detail_delete_url}
        </button>
      )}

      {editorUrl && (
        <CornerEditor
          imageUrl={editorUrl}
          initialQuad={editorInitQuad}
          onCancel={closePhotoEditor}
          onApply={(quad, transform) => { if (!uploadingPhoto) void handleApplyPhoto(quad, transform); }}
        />
      )}
    </div>
  );
}
