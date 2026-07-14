"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import { API_BASE, cardApi, pricesApi, Card } from "@/lib/api";
import RarityBadge from "@/components/RarityBadge";
import PriceChart from "@/components/PriceChart";
import PhotoPanel from "@/components/carddetail/PhotoPanel";
import EditForm from "@/components/carddetail/EditForm";
import CollectionsPanel from "@/components/carddetail/CollectionsPanel";
import { cardImageSrc } from "@/lib/utils";
import { useEnums } from "@/lib/useEnums";
import { useSets } from "@/lib/useSets";
import { useI18n } from "@/lib/i18n";
import toast from "react-hot-toast";

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
          <button type="button" onClick={onCancel} className="px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 text-sm">
            {t.form_cancel}
          </button>
          <button type="button" onClick={onConfirm} className="px-4 py-2 bg-pokemon-pokedex text-white rounded hover:opacity-80 text-sm font-medium">
            {t.pokedex_replace_confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
// ─────────────────────────────────────────────────────────────────────────────

// Kartendetailseite — orchestriert nur noch (Issue #14): Kartenzustand +
// Formular-Sync, Quick-Aktionen (Pokédex-Flag, Wunschliste), Preis-Historie.
// Foto/Edit/Sammlungen leben in components/carddetail/.
export default function CardDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const { t } = useI18n();
  const [card, setCard] = useState<Card | null>(null);
  const { enums } = useEnums();
  const { sets, refresh: refreshSets } = useSets();
  const [history, setHistory] = useState<unknown[]>([]);
  const [form, setForm] = useState<Partial<Card>>({});
  const [editingPriority, setEditingPriority] = useState(false);
  const [conflictCard, setConflictCard] = useState<Card | null>(null);
  const [showPokedexModal, setShowPokedexModal] = useState(false);

  useEffect(() => {
    cardApi.get(Number(id)).then((r) => { setCard(r.data); setForm(r.data); });
    pricesApi.history(Number(id)).then((r) => setHistory(r.data));
  }, [id]);

  const doSetPokedex = async (value: boolean) => {
    if (!card) return;
    try {
      const r = await cardApi.update(Number(id), { im_pokedex: value });
      // Nur das Flag übernehmen – nicht gespeicherte Formular-Eingaben NICHT überschreiben
      setCard(r.data);
      setForm((f) => ({ ...f, im_pokedex: r.data.im_pokedex }));
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

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push("/");
  };

  const handleDelete = async () => {
    if (!confirm(t.detail_delete_confirm(card.kartenname))) return;
    await cardApi.delete(Number(id));
    handleBack();
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-4">
        <button type="button" onClick={handleBack} className="text-gray-500 hover:text-white text-sm">{t.detail_back_generic}</button>
      </div>

      <div className="flex flex-col md:flex-row gap-6 md:gap-8">
        {/* Kartenbild */}
        <PhotoPanel
          card={card}
          onCardUpdated={(c) => setCard(c)}
          onCardSaved={(c) => { setCard(c); setForm(c); }}
        />

        {/* Details */}
        <EditForm
          card={card}
          form={form}
          setForm={setForm}
          enums={enums}
          sets={sets}
          onSetsRefresh={() => { void refreshSets(); }}
          onCardUpdated={(c) => setCard(c)}
          onDelete={handleDelete}
        />
      </div>

      {/* Pokédex-Flag + Wunschliste + Sammlungen */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Pokédex-Flag — nur wenn Pokédex-Nr. vorhanden */}
        {card.pokedex_nr && (
          <div className="bg-pokemon-card rounded-lg p-4">
            <h2 className="text-gray-300 font-medium mb-1">{t.detail_pokedex_flag}</h2>
            <p className="text-gray-500 text-xs mb-3">{t.detail_pokedex_flag_hint}</p>
            <button type="button"
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
            <button type="button"
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
                  <button type="button"
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
        <CollectionsPanel cardId={Number(id)} />
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
