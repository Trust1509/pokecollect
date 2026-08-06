"use client";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { CatalogItem, CatalogDetail, Collection, catalogApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { useEnums } from "@/lib/useEnums";
import { useSettings } from "@/lib/useSettings";
import { SelectField } from "@/components/CardFormFields";
import { fetchPokemonNames, PokemonNames } from "@/lib/pokedex";

type Props = {
  card: CatalogItem;
  collections: Collection[];
  onClose: () => void;
  // Nach erfolgreicher Übernahme: Aufrufer schließt/aktualisiert (Fallback onClose).
  onAdded?: () => void;
};

export default function CatalogCardModal({ card, collections, onClose, onAdded }: Props) {
  const { t, lang } = useI18n();
  const { enums } = useEnums();
  const { settings } = useSettings();
  const [busy, setBusy] = useState(false);
  const [collId, setCollId] = useState("");
  // Kleines Anlege-Formular (#28) — mit Einstellungs-Defaults vorbelegt (#27).
  const [sprache, setSprache] = useState("DE");
  const [zustand, setZustand] = useState<string | null>(null);
  const [folierung, setFolierung] = useState<string | null>("Normal");
  const [ersteEdition, setErsteEdition] = useState(false);
  // Angereichertes Detail beim Öffnen live von TCGdex holen (dex/rarity/illustrator/
  // kategorie/varianten fehlender Karten + Preise €/$). Fehlertolerant.
  const [detail, setDetail] = useState<CatalogDetail | null>(null);
  // Pokémon-Artname (DE/EN) aus der Pokédex-Nr. — identifiziert auch JP-Karten,
  // die keinen DE/EN-Kartennamen haben (PokéAPI, gecacht).
  const [species, setSpecies] = useState<PokemonNames | null>(null);

  useEffect(() => {
    if (!settings) return;
    setSprache(settings.default_language || "DE");
    setZustand(settings.default_condition || null);
  }, [settings]);

  useEffect(() => {
    const ctrl = new AbortController();
    setDetail(null);  // Kartenwechsel: kein stale Detail der Vorkarte zeigen
    catalogApi.detail(card.card_id, { signal: ctrl.signal })
      .then((r) => setDetail(r.data))
      .catch(() => {});           // Abbruch/Fehler still schlucken
    return () => ctrl.abort();    // bricht beim Schließen/Wechsel auch den TCGdex-Abruf ab
  }, [card.card_id]);

  useEffect(() => {
    const dexId = detail?.dex_id ?? card.dex_id;
    let alive = true;
    setSpecies(null);
    if (dexId) fetchPokemonNames(dexId).then((n) => { if (alive) setSpecies(n); });
    return () => { alive = false; };
  }, [detail?.dex_id, card.dex_id]);

  const name = lang === "EN" && card.name_en ? card.name_en : (card.name ?? card.name_en ?? card.card_id);
  const done = onAdded ?? onClose;
  const opts = () => ({ sprache, zustand, folierung, erste_edition: ersteEdition });

  // Live-Detail ist reicher (dex/rarity/illustrator/kategorie/varianten); card ist der Sofort-Fallback.
  const d = detail ?? card;
  const fmtEur = (n?: number | null) => (n != null ? `${n.toFixed(2).replace(".", ",")} €` : null);
  const fmtUsd = (n?: number | null) => (n != null ? `$ ${n.toFixed(2)}` : null);
  const variantsStr =
    [d.variants_normal ? "Normal" : null, d.variants_reverse ? "Reverse" : null,
     d.variants_holo ? "Holo" : null, d.variants_firstedition ? "1st Ed." : null]
      .filter(Boolean).join(", ") || null;
  const eurMain = detail?.price_eur ?? detail?.price_eur_trend ?? null;
  const eurNode = eurMain != null ? (
    <span>{fmtEur(eurMain)}
      {detail?.price_eur != null && detail?.price_eur_trend != null && (
        <span className="text-gray-400"> · Trend {fmtEur(detail.price_eur_trend)}</span>)}
    </span>
  ) : null;
  const fmtDate = (iso?: string | null) => {
    if (!iso) return null;
    const dt = new Date(iso);
    return isNaN(dt.getTime()) ? null : dt.toLocaleDateString(lang === "EN" ? "en-GB" : "de-DE");
  };
  const withStand = (val: React.ReactNode, iso?: string | null) => {
    const s = fmtDate(iso);
    return val != null
      ? <span>{val}{s && <span className="text-gray-500 text-xs"> · {t.catalog_price_asof} {s}</span>}</span>
      : null;
  };
  const speciesStr = species ? `${species.de} / ${species.en}` : null;

  const wish = async () => {
    setBusy(true);
    try { await catalogApi.addWishlist(card.card_id, opts()); toast.success(t.catalog_added_wishlist); done(); }
    catch { toast.error(t.collections_error); }
    finally { setBusy(false); }
  };
  const addColl = async () => {
    if (!collId) return;
    setBusy(true);
    try { await catalogApi.addCollection(card.card_id, Number(collId), opts()); toast.success(t.catalog_added_collection); done(); }
    catch { toast.error(t.collections_error); }
    finally { setBusy(false); }
  };

  const row = (label: string, val: React.ReactNode) =>
    val ? <div className="flex justify-between gap-3"><dt className="text-gray-500">{label}</dt><dd className="text-white text-right">{val}</dd></div> : null;

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-pokemon-card rounded-lg p-4 max-w-md w-full max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-start mb-3">
          <h2 className="text-white font-bold text-lg">{name}</h2>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white text-xl leading-none">✕</button>
        </div>

        <div className="flex gap-4">
          <div className="w-40 shrink-0">
            {card.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={card.image_url} alt={name} className="w-full rounded" />
            ) : (
              <div className="aspect-[63/88] bg-gray-800 rounded flex items-center justify-center text-gray-600 text-xs text-center p-2">{name}</div>
            )}
          </div>
          <dl className="flex-1 text-sm space-y-1 min-w-0">
            {row(t.field_set, d.set_name ? `${d.set_name} (${d.set_code})` : d.set_code)}
            {row(t.field_card_nr, d.local_id)}
            {row(t.field_pokedex_nr, d.dex_id ? `#${d.dex_id}` : null)}
            {row(t.catalog_species, speciesStr)}
            {row(t.field_rarity, d.rarity)}
            {row(t.field_category, d.category)}
            {row(t.catalog_illustrator, d.illustrator)}
            {row(t.field_english_name, d.name_en)}
            {row(t.catalog_variants, variantsStr)}
            {row(t.catalog_price_eur, withStand(eurNode, detail?.price_eur_updated))}
            {row(t.catalog_price_usd, withStand(fmtUsd(detail?.price_usd), detail?.price_usd_updated))}
          </dl>
        </div>

        {/* Anlege-Formular (#28): Zustand/Sprache/Folierung/1st Edition, mit
            Einstellungs-Defaults vorbelegt (#27). */}
        <div className="mt-4 grid grid-cols-2 gap-2">
          <SelectField fieldKey="zustand" label={t.form_condition} value={zustand}
            onChange={setZustand} options={enums?.zustand ?? []} dense />
          <SelectField fieldKey="sprache" label={t.form_language} value={sprache}
            onChange={(v) => setSprache(v ?? "DE")} options={enums?.sprache ?? []} dense />
          <SelectField fieldKey="folierung" label={t.form_foiling} value={folierung}
            onChange={setFolierung} options={enums?.folierung ?? []} dense />
          <label className="flex items-end gap-2 pb-1.5 text-white text-sm cursor-pointer select-none">
            <input type="checkbox" checked={ersteEdition} onChange={(e) => setErsteEdition(e.target.checked)} />
            {t.first_edition_label}
          </label>
        </div>

        <div className="mt-4 space-y-2">
          <button type="button" onClick={wish} disabled={busy}
            className="w-full bg-pokemon-yellow text-black font-medium rounded px-3 py-2 hover:opacity-90 disabled:opacity-50">
            ★ {t.catalog_add_wishlist}
          </button>
          <div className="flex gap-2">
            <select value={collId} onChange={(e) => setCollId(e.target.value)}
              className="flex-1 min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm">
              <option value="">{t.catalog_add_collection} …</option>
              {collections.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <button type="button" onClick={addColl} disabled={busy || !collId}
              className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700 disabled:opacity-50">
              {t.collection_add}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
