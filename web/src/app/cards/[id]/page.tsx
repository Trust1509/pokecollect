"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import toast from "react-hot-toast";
import { cardApi, pricesApi, Card, Collection, Enums, PokemonSet, setsApi, collectionApi } from "@/lib/api";
import { fetchPokemonNames } from "@/lib/pokedex";
import RarityBadge from "@/components/RarityBadge";
import RaritySelect from "@/components/RaritySelect";
import PriceChart from "@/components/PriceChart";
import SetPicker from "@/components/SetPicker";
import { formatEur, imageUrl, pokemonPlaceholderUrl, cardImageSrc } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

// ── Inline-Komponente: Pokédex-Ersetzungs-Bestätigungsdialog ─────────────────
function PokedexReplaceModal({
  conflictCard, currentCard, apiBase, onConfirm, onCancel, t,
}: {
  conflictCard: Card;
  currentCard: Card;
  apiBase: string;
  onConfirm: () => void;
  onCancel: () => void;
  t: ReturnType<typeof useI18n>["t"];
}) {
  const { src: conflictSrc } = cardImageSrc(conflictCard, apiBase, true);
  const { src: newSrc } = cardImageSrc(currentCard, apiBase, true);
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 max-w-xl w-full shadow-2xl">
        <h3 className="text-white font-bold text-lg mb-1">⚠️ {t.pokedex_replace_title}</h3>
        <p className="text-gray-400 text-sm mb-5">
          {t.pokedex_replace_desc(currentCard.pokedex_nr!, currentCard.kartenname)}
        </p>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-3 text-center">
            <div className="text-xs text-gray-400 mb-2">{t.pokedex_replace_current}</div>
            <div className="aspect-[63/88] relative w-20 mx-auto bg-gray-700 rounded overflow-hidden mb-2">
              {conflictSrc && (
                <Image src={conflictSrc} alt={conflictCard.kartenname} fill className="object-cover" />
              )}
            </div>
            <div className="text-white text-xs font-medium truncate">{conflictCard.kartenname}</div>
            <div className="text-gray-500 text-[10px] truncate">{conflictCard.set_edition ?? "–"}</div>
            {conflictCard.karten_nr && (
              <div className="text-gray-400 text-[10px]">{conflictCard.karten_nr}</div>
            )}
            {conflictCard.seltenheit && (
              <div className="mt-1 flex justify-center">
                <RarityBadge rarity={conflictCard.seltenheit} language={conflictCard.sprache} size="sm" />
              </div>
            )}
          </div>
          <div className="bg-gray-800 rounded-lg p-3 text-center border-2 border-pokemon-pokedex">
            <div className="text-xs text-pokemon-pokedex mb-2">{t.pokedex_replace_new}</div>
            <div className="aspect-[63/88] relative w-20 mx-auto bg-gray-700 rounded overflow-hidden mb-2">
              {newSrc && (
                <Image src={newSrc} alt={currentCard.kartenname} fill className="object-cover" />
              )}
            </div>
            <div className="text-white text-xs font-medium truncate">{currentCard.kartenname}</div>
            <div className="text-gray-500 text-[10px] truncate">{currentCard.set_edition ?? "–"}</div>
            {currentCard.karten_nr && (
              <div className="text-gray-400 text-[10px]">{currentCard.karten_nr}</div>
            )}
            {currentCard.seltenheit && (
              <div className="mt-1 flex justify-center">
                <RarityBadge rarity={currentCard.seltenheit} language={currentCard.sprache} size="sm" />
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 text-sm">
            {t.form_cancel}
          </button>
          <button onClick={onConfirm} className="px-4 py-2 bg-pokemon-pokedex text-white rounded hover:opacity-80 text-sm font-medium">
            {t.pokedex_replace_confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
// ─────────────────────────────────────────────────────────────────────────────

export default function CardDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const { t } = useI18n();
  const [card, setCard] = useState<Card | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<PokemonSet | null>(null);
  const [history, setHistory] = useState<unknown[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Card>>({});
  const [cardNrError, setCardNrError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);
  const autoFilled = useRef({ kartenname: false, englischer_name: false });
  const lookupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [urlInput, setUrlInput] = useState("");
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [cardCollections, setCardCollections] = useState<Collection[]>([]);
  const [allCollections, setAllCollections] = useState<Collection[]>([]);
  const [editingPriority, setEditingPriority] = useState(false);
  const [conflictCard, setConflictCard] = useState<Card | null>(null);
  const [showPokedexModal, setShowPokedexModal] = useState(false);

  const loadCollections = () => {
    collectionApi.forCard(Number(id)).then((r) => setCardCollections(r.data)).catch(() => {});
  };

  useEffect(() => {
    cardApi.get(Number(id)).then((r) => { setCard(r.data); setForm(r.data); });
    cardApi.enums().then((r) => setEnums(r.data));
    setsApi.list().then((r) => setSets(r.data));
    pricesApi.history(Number(id)).then((r) => setHistory(r.data));
    collectionApi.forCard(Number(id)).then((r) => setCardCollections(r.data)).catch(() => {});
    collectionApi.list().then((r) => setAllCollections(r.data)).catch(() => {});
  }, [id]);

  const handleAddToCollection = async (collectionId: number) => {
    try {
      await collectionApi.addCard(collectionId, Number(id));
      loadCollections();
      toast.success(t.collection_added);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const handleRemoveFromCollection = async (collectionId: number) => {
    try {
      await collectionApi.removeCard(collectionId, Number(id));
      loadCollections();
      toast.success(t.collection_removed);
    } catch {
      toast.error(t.collections_error);
    }
  };

  const doSetPokedex = async (value: boolean) => {
    if (!card) return;
    try {
      const r = await cardApi.update(Number(id), { im_pokedex: value });
      setCard(r.data); setForm(r.data);
      setShowPokedexModal(false); setConflictCard(null);
      toast.success(value ? t.detail_pokedex_flag_added : t.detail_pokedex_flag_removed);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  const togglePokedex = async () => {
    if (!card) return;
    const next = !card.im_pokedex;
    // Beim Setzen prüfen ob ein anderes Pokémon schon diesen Slot hat → Bestätigungsdialog
    if (next && card.pokedex_nr) {
      try {
        const r = await cardApi.list({ pokedex_nr: card.pokedex_nr, im_pokedex: true, limit: 5 });
        const others = (r.data.items as Card[]).filter((c) => c.id !== card.id);
        if (others.length > 0) {
          setConflictCard(others[0]);
          setShowPokedexModal(true);
          return; // Warten auf Bestätigung im Modal
        }
      } catch {/* Fehler ignorieren, direkt setzen */}
    }
    await doSetPokedex(next);
  };

  const toggleWishlist = async () => {
    if (!card) return;
    const next = !card.wunschliste;
    // Beim Deaktivieren Priorität zurücksetzen
    const payload = next ? { wunschliste: true } : { wunschliste: false, prioritaet: null };
    try {
      const r = await cardApi.update(Number(id), payload);
      setCard(r.data); setForm(r.data); setEditingPriority(false);
      toast.success(next ? t.detail_wishlist_added : t.detail_wishlist_removed);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  const handleSetPriority = async (p: string) => {
    try {
      const r = await cardApi.update(Number(id), { prioritaet: p || null });
      setCard(r.data); setForm(r.data); setEditingPriority(false);
      toast.success(t.detail_wishlist_priority_saved);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  if (!card) return <div className="text-gray-500 p-8">{t.detail_loading}</div>;

  const imgSrc =
    imageUrl(card.bild_karte_pfad, API_BASE)
    ?? card.bild_pokedex_url
    ?? card.bild_karte_url
    ?? pokemonPlaceholderUrl(card.pokedex_nr);
  const isPlaceholder = !card.bild_karte_pfad && !card.bild_pokedex_url && !card.bild_karte_url && !!imgSrc;
  const isAutoCard = !card.bild_karte_pfad && !card.bild_pokedex_url && !!card.bild_karte_url;

  const validateCardNr = (nr: string): boolean => {
    if (!nr || !selectedSet?.max_card_nr) return true;
    if (!nr.match(/^(\d{1,4})\/(\d{1,4})$/)) {
      setCardNrError(t.form_card_nr_invalid(selectedSet.max_card_nr));
      return false;
    }
    setCardNrError(null);
    return true;
  };

  const handleSave = async () => {
    const nr = (form as Record<string, unknown>).karten_nr as string | undefined;
    if (nr && !validateCardNr(nr)) return;
    try {
      const r = await cardApi.update(Number(id), form);
      setCard(r.data);
      setEditing(false);
      toast.success(t.detail_saved);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const r = await cardApi.uploadImage(Number(id), file);
      setCard(r.data);
      toast.success(t.detail_photo_saved);
    } catch {
      toast.error(t.detail_upload_error);
    }
  };

  const handleSaveUrl = async () => {
    const url = urlInput.trim();
    if (!url) return;
    try {
      const r = await cardApi.update(Number(id), { bild_pokedex_url: url });
      setCard(r.data); setForm(r.data); setShowUrlInput(false); setUrlInput("");
      toast.success(t.detail_url_saved);
    } catch {
      toast.error(t.detail_url_save_error);
    }
  };

  const handleClearPokedexUrl = async () => {
    if (!confirm(t.detail_delete_url_confirm)) return;
    try {
      const r = await cardApi.update(Number(id), { bild_pokedex_url: null });
      setCard(r.data); setForm(r.data);
      toast.success(t.detail_url_deleted);
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  const handleDeleteImage = async () => {
    if (!confirm(t.detail_delete_photo_confirm)) return;
    try {
      const r = await cardApi.deleteImage(Number(id));
      setCard(r.data);
      toast.success(t.detail_photo_saved);
      // Server holt das TCGdex-Bild im Hintergrund nach → kurz danach neu laden
      setTimeout(() => {
        cardApi.get(Number(id)).then((r2) => setCard(r2.data)).catch(() => {});
      }, 2000);
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push("/");
  };

  const handleDelete = async () => {
    if (!confirm(t.detail_delete_confirm(card.kartenname))) return;
    await cardApi.delete(Number(id));
    handleBack();
  };

  const handlePokedexNr = (nr: number | null) => {
    setForm((f) => ({ ...f, pokedex_nr: nr }));
    if (lookupTimeout.current) clearTimeout(lookupTimeout.current);

    if (!nr || nr < 1 || nr > 1025) {
      const af = { ...autoFilled.current };
      autoFilled.current = { kartenname: false, englischer_name: false };
      setForm((f) => ({
        ...f,
        kartenname: af.kartenname ? "" : f.kartenname,
        englischer_name: af.englischer_name ? "" : f.englischer_name,
      }));
      return;
    }

    lookupTimeout.current = setTimeout(async () => {
      setNameLoading(true);
      try {
        const names = await fetchPokemonNames(nr);
        if (names) {
          setForm((f) => ({
            ...f,
            kartenname: (!(f.kartenname as string) || autoFilled.current.kartenname) ? names.de : f.kartenname,
            englischer_name: (!(f.englischer_name as string) || autoFilled.current.englischer_name) ? names.en : f.englischer_name,
          }));
          autoFilled.current = { kartenname: true, englischer_name: true };
        }
      } finally {
        setNameLoading(false);
      }
    }, 500);
  };

  const handleSetChange = (setEdition: string, s: PokemonSet | null) => {
    setForm((f) => ({ ...f, set_edition: setEdition || null }));
    setSelectedSet(s);
    setCardNrError(null);
  };

  const field = (key: keyof Card, label: string, type: "text" | "number" | "select" | "boolean" | "textarea" = "text", options?: string[]) => {
    const value = (form as Record<string, unknown>)[key];
    if (!editing) {
      return (
        <div key={key}>
          <dt className="text-gray-500 text-xs">{label}</dt>
          <dd className="text-white">
            {type === "boolean" ? (value ? t.field_yes : t.field_no) : (String(value ?? "–"))}
          </dd>
        </div>
      );
    }
    if (type === "select" && options) {
      if (key === "seltenheit") {
        return (
          <RaritySelect
            key={key}
            label={label}
            value={String(value ?? "")}
            onChange={(v) => setForm((f) => ({ ...f, [key]: v }))}
            options={options}
            language={(form as Record<string, unknown>).sprache as string | null}
          />
        );
      }
      return (
        <div key={key}>
          <label className="text-gray-500 text-xs block">{label}</label>
          <select
            value={String(value ?? "")}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value || null }))}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
          >
            <option value="">–</option>
            {options.map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
        </div>
      );
    }
    if (type === "boolean") {
      return (
        <div key={key}>
          <label className="text-gray-500 text-xs block">{label}</label>
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.checked }))}
            className="mt-1"
          />
        </div>
      );
    }
    if (type === "textarea") {
      return (
        <div key={key} className="col-span-2">
          <label className="text-gray-500 text-xs block">{label}</label>
          <textarea
            value={String(value ?? "")}
            onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
            rows={3}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
          />
        </div>
      );
    }
    return (
      <div key={key}>
        <label className="text-gray-500 text-xs block">{label}</label>
        <input
          type={type}
          value={String(value ?? "")}
          onChange={(e) => setForm((f) => ({ ...f, [key]: type === "number" ? Number(e.target.value) || null : e.target.value }))}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
        />
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-4">
        <button onClick={handleBack} className="text-gray-500 hover:text-white text-sm">{t.detail_back_generic}</button>
      </div>

      <div className="flex gap-8">
        {/* Kartenbild */}
        <div className="shrink-0 w-52">
          <div className="aspect-[63/88] relative bg-gray-800 rounded-lg overflow-hidden">
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
                    pokemon.com
                  </div>
                )}
                {isPlaceholder && (
                  <div className="absolute bottom-0 inset-x-0 bg-black/60 text-center text-gray-400 text-xs py-1">
                    {t.detail_placeholder}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-600">{t.detail_no_image}</div>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
          <input ref={cameraRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleImageUpload} />
          <div className="mt-2 grid grid-cols-2 gap-1">
            <button
              onClick={() => cameraRef.current?.click()}
              className="text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
            >
              {t.detail_take_photo}
            </button>
            <button
              onClick={() => fileRef.current?.click()}
              className="text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
            >
              {card.bild_karte_pfad ? t.detail_replace_photo : t.detail_upload_photo}
            </button>
          </div>
          {!card.bild_karte_pfad && (
            <button
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
              <button onClick={handleSaveUrl} className="text-xs bg-green-700 text-white rounded px-2 py-1 hover:bg-green-600">OK</button>
            </div>
          )}
          {(card.bild_karte_pfad || card.bild_pokedex_url) && (
            <button
              onClick={card.bild_karte_pfad ? handleDeleteImage : handleClearPokedexUrl}
              className="w-full mt-1 text-sm bg-red-950 text-red-400 hover:text-red-200 rounded px-3 py-1.5"
            >
              {card.bild_karte_pfad ? t.detail_delete_photo : t.detail_delete_url}
            </button>
          )}
        </div>

        {/* Details */}
        <div className="flex-1">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-white">{card.kartenname}</h1>
              {card.pokedex_nr && (
                <p className="text-gray-400">#{String(card.pokedex_nr).padStart(4, "0")} · {card.englischer_name ?? ""}</p>
              )}
            </div>
            <div className="flex gap-2">
              {editing ? (
                <>
                  <button onClick={handleSave} className="bg-green-600 text-white text-sm px-3 py-1.5 rounded hover:bg-green-700">{t.form_save}</button>
                  <button onClick={() => { setEditing(false); setForm(card); setCardNrError(null); }} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded">{t.form_cancel}</button>
                </>
              ) : (
                <button onClick={() => setEditing(true)} className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700">{t.detail_edit}</button>
              )}
              {card.besessen && (
                <button onClick={handleDelete} className="bg-red-900 text-red-300 text-sm px-3 py-1.5 rounded hover:bg-red-800">{t.detail_delete}</button>
              )}
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-3 text-sm">
            {field("kartenname", t.field_card_name)}
            {/* Pokédex-Nr. mit Auto-Namens-Lookup */}
            {editing ? (
              <div key="pokedex_nr">
                <label className="text-gray-500 text-xs block">
                  {t.field_pokedex_nr}
                  {nameLoading && <span className="ml-2 text-gray-500 animate-pulse">…</span>}
                </label>
                <input
                  type="number"
                  value={String((form as Record<string, unknown>).pokedex_nr ?? "")}
                  onChange={(e) => handlePokedexNr(Number(e.target.value) || null)}
                  className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
                />
              </div>
            ) : (
              <div key="pokedex_nr">
                <dt className="text-gray-500 text-xs">{t.field_pokedex_nr}</dt>
                <dd className="text-white">{String(card.pokedex_nr ?? "–")}</dd>
              </div>
            )}
            {field("englischer_name", t.field_english_name)}

            {/* Set/Edition: im Edit-Modus SetPicker, sonst normales Feld */}
            {editing ? (
              <div className="col-span-2">
                <SetPicker
                  value={String((form as Record<string, unknown>).set_edition ?? "")}
                  onChange={handleSetChange}
                  sets={sets}
                  onSetAdded={(s) => setSets((prev) => [...prev, s].sort((a, b) => a.code.localeCompare(b.code)))}
                />
              </div>
            ) : (
              <div>
                <dt className="text-gray-500 text-xs">{t.field_set}</dt>
                <dd className="text-white">{String(card.set_edition ?? "–")}</dd>
              </div>
            )}

            {/* Karten-Nr. mit Hinweis im Edit-Modus */}
            {editing ? (
              <div>
                <label className="text-gray-500 text-xs block">{t.field_card_nr}</label>
                <input
                  type="text"
                  value={String((form as Record<string, unknown>).karten_nr ?? "")}
                  onChange={(e) => { setForm((f) => ({ ...f, karten_nr: e.target.value })); setCardNrError(null); }}
                  onBlur={(e) => validateCardNr(e.target.value)}
                  placeholder={selectedSet?.max_card_nr ? `001/${String(selectedSet.max_card_nr).padStart(3, "0")}` : "z.B. 001/091"}
                  className={`w-full bg-gray-800 border rounded px-2 py-1 text-white text-sm ${cardNrError ? "border-red-500" : "border-gray-700"}`}
                />
                {selectedSet?.max_card_nr && !cardNrError && (
                  <p className="text-gray-500 text-xs mt-0.5">{t.form_card_nr_hint(selectedSet.max_card_nr)}</p>
                )}
                {cardNrError && <p className="text-red-400 text-xs mt-0.5">{cardNrError}</p>}
              </div>
            ) : (
              <div>
                <dt className="text-gray-500 text-xs">{t.field_card_nr}</dt>
                <dd className="text-white">{String(card.karten_nr ?? "–")}</dd>
              </div>
            )}

            {editing ? (
              field("seltenheit", t.field_rarity, "select", enums?.seltenheit)
            ) : (
              <div key="seltenheit">
                <dt className="text-gray-500 text-xs">{t.field_rarity}</dt>
                <dd className="text-white flex items-center gap-2">
                  {card.seltenheit ?? "–"}
                  {card.seltenheit && (
                    <RarityBadge rarity={card.seltenheit} language={card.sprache} size="sm" />
                  )}
                </dd>
              </div>
            )}
            {field("kartenversion", t.field_card_version, "select", enums?.kartenversion)}
            {field("folierung", t.field_foiling, "select", enums?.folierung)}
            {field("sprache", t.field_language, "select", enums?.sprache)}
            {field("zustand", t.field_condition, "select", enums?.zustand)}
            {field("besessen", t.field_owned, "boolean")}
            {field("notizen", t.field_notes, "textarea")}
          </dl>

          {card.wert_eur && (
            <div className="mt-4 p-3 bg-pokemon-card rounded-lg">
              <div className="text-gray-400 text-xs">{t.detail_value_label}</div>
              <div className="text-yellow-400 text-xl font-bold">{formatEur(card.wert_eur)}</div>
              {card.wert_aktualisiert && (
                <div className="text-gray-500 text-xs mt-0.5">
                  {t.detail_value_updated}: {new Date(card.wert_aktualisiert).toLocaleDateString("de-AT")}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Pokédex-Flag + Wunschliste + Sammlungen */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pokédex-Flag — nur wenn Pokédex-Nr. vorhanden */}
        {card.pokedex_nr && (
          <div className="bg-pokemon-card rounded-lg p-4">
            <h2 className="text-gray-300 font-medium mb-1">{t.detail_pokedex_flag}</h2>
            <p className="text-gray-500 text-xs mb-3">{t.detail_pokedex_flag_hint}</p>
            <button
              onClick={togglePokedex}
              className={`text-sm px-3 py-1.5 rounded ${
                card.im_pokedex
                  ? "bg-pokemon-pokedex text-white hover:opacity-80"
                  : "bg-gray-800 text-gray-300 hover:text-white"
              }`}
            >
              {card.im_pokedex ? `● ${t.detail_pokedex_flag_on}` : `○ ${t.detail_pokedex_flag}`}
            </button>
          </div>
        )}

        {/* Wunschliste Quick-Toggle */}
        <div className="bg-pokemon-card rounded-lg p-4">
          <h2 className="text-gray-300 font-medium mb-3">{t.detail_wishlist}</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={toggleWishlist}
              className={`text-sm px-3 py-1.5 rounded ${
                card.wunschliste
                  ? "bg-yellow-600 text-white hover:bg-yellow-700"
                  : "bg-gray-800 text-gray-300 hover:text-white"
              }`}
            >
              {card.wunschliste ? `⭐ ${t.detail_wishlist_on}` : `☆ ${t.detail_wishlist_on}`}
            </button>
          </div>
          {card.wunschliste && (
            <div className="mt-3">
              {(!card.prioritaet || editingPriority) ? (
                <div>
                  <label className="text-gray-500 text-xs block mb-1">{t.detail_wishlist_priority}</label>
                  <select
                    value={card.prioritaet ?? ""}
                    onChange={(e) => handleSetPriority(e.target.value)}
                    className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
                  >
                    <option value="">{t.detail_wishlist_choose_priority}</option>
                    {(enums?.prioritaet ?? []).map((p) => (
                      <option key={p} value={p}>{p === "Chase" ? `🔥 ${p}` : p}</option>
                    ))}
                  </select>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400">
                    {t.detail_wishlist_priority}:{" "}
                    <span className={card.prioritaet === "Chase" ? "text-orange-400 font-semibold" : "text-white"}>
                      {card.prioritaet === "Chase" ? `🔥 ${card.prioritaet}` : card.prioritaet}
                    </span>
                  </span>
                  <button
                    onClick={() => setEditingPriority(true)}
                    className="text-xs text-gray-500 hover:text-white underline"
                  >
                    {t.detail_wishlist_edit_priority}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Sammlungen-Zuordnung */}
        <div className="bg-pokemon-card rounded-lg p-4">
          <h2 className="text-gray-300 font-medium mb-3">{t.detail_collections}</h2>
          {cardCollections.length === 0 ? (
            <p className="text-gray-500 text-sm mb-3">{t.detail_collections_none}</p>
          ) : (
            <div className="flex flex-wrap gap-2 mb-3">
              {cardCollections.map((c) => (
                <span key={c.id} className="inline-flex items-center gap-1 bg-gray-800 rounded-full px-3 py-1 text-sm text-white">
                  <Link href={`/collections/${c.id}`} className="hover:text-pokemon-yellow">{c.name}</Link>
                  <button
                    onClick={() => handleRemoveFromCollection(c.id)}
                    className="text-gray-500 hover:text-red-400 ml-1"
                    title={t.collection_remove}
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
          <select
            value=""
            onChange={(e) => { if (e.target.value) handleAddToCollection(Number(e.target.value)); }}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          >
            <option value="">{t.detail_collections_add}</option>
            {allCollections
              .filter((c) => !cardCollections.some((cc) => cc.id === c.id))
              .map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
          </select>
        </div>
      </div>

      <div className="mt-4 bg-pokemon-card rounded-lg p-4">
        <h2 className="text-gray-300 font-medium mb-3">{t.detail_price_history}</h2>
        <PriceChart history={history as { erfasst_am: string; wert_eur: string | null }[]} />
      </div>

      {/* Pokédex-Ersetzungs-Dialog */}
      {showPokedexModal && conflictCard && (
        <PokedexReplaceModal
          conflictCard={conflictCard}
          currentCard={card}
          apiBase={API_BASE}
          onConfirm={() => doSetPokedex(true)}
          onCancel={() => { setShowPokedexModal(false); setConflictCard(null); }}
          t={t}
        />
      )}
    </div>
  );
}
