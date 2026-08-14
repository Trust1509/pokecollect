"use client";
import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import toast from "react-hot-toast";
import { API_BASE, SealedCatalogItem, SealedEnums, SealedProduct, sealedApi } from "@/lib/api";
import { CurrencyField, DateField, SelectField, TextareaField } from "@/components/CardFormFields";
import SearchableSelect from "@/components/SearchableSelect";
import { useSets } from "@/lib/useSets";
import { useSetOptions } from "@/lib/useSetOptions";
import { formatEur, imageUrl } from "@/lib/utils";
import { useI18n } from "@/lib/i18n";

// Anlage-/Detail-Formular für Sealed-Produkte (Issue #35). EIN Formular für
// Neuanlage UND Bearbeiten (DRY): `product=null` = Neuanlage. Mehrfach-Set-
// Auswahl über SearchableSelect (Picker) + entfernbare Chips.

type Props = {
  product: SealedProduct | null;
  enums: SealedEnums | null;
  onClose: () => void;
  onSaved: () => void;
};

export default function SealedFormModal({ product, enums, onClose, onSaved }: Props) {
  const { t } = useI18n();
  const { sets } = useSets();
  const setOptions = useSetOptions(sets);
  const fileRef = useRef<HTMLInputElement>(null);

  // Lokaler Produktzustand: bei Neuanlage null, nach dem Create gesetzt (dann
  // ist Bild-Upload + G/V-Anzeige möglich).
  const [current, setCurrent] = useState<SealedProduct | null>(product);
  const isEdit = !!current;

  const [name, setName] = useState(product?.name ?? "");
  const [typ, setTyp] = useState<string | null>(product?.typ ?? null);
  const [zustand, setZustand] = useState<string | null>(product?.zustand ?? "Versiegelt");
  const [setCodes, setSetCodes] = useState<string[]>(product?.set_codes ?? []);
  const [kaufpreis, setKaufpreis] = useState<string | null>(product?.kaufpreis_eur ?? null);
  const [kaufdatum, setKaufdatum] = useState<string | null>(product?.kaufdatum ?? null);
  const [wert, setWert] = useState<string | null>(product?.wert_eur ?? null);
  const [notizen, setNotizen] = useState<string | null>(product?.notizen ?? null);
  const [saving, setSaving] = useState(false);

  // Foto: im Edit sofort hochladen; bei Neuanlage bis zum Speichern halten.
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [photoVersion, setPhotoVersion] = useState(0);

  // Sealed-Katalog-Picker (#46): Suche gegen echte TCGplayer-Produkte.
  // linkId = aktuelle Verknüpfung (0 = beim Speichern lösen).
  const [linkId, setLinkId] = useState<number | null>(product?.tcgplayer_product_id ?? null);
  const [linkImage, setLinkImage] = useState<string | null>(product?.bild_url ?? null);
  const [catSearch, setCatSearch] = useState("");
  const [catResults, setCatResults] = useState<SealedCatalogItem[]>([]);
  useEffect(() => {
    const q = catSearch.trim();
    if (q.length < 2) { setCatResults([]); return; }
    let alive = true;   // späte Antwort einer alten Suche nicht übernehmen
    const timer = setTimeout(() => {
      sealedApi.catalog(q)
        .then((r) => { if (alive) setCatResults(r.data); })
        .catch(() => { if (alive) setCatResults([]); });
    }, 300);
    return () => { alive = false; clearTimeout(timer); };
  }, [catSearch]);

  const pickCatalog = (item: SealedCatalogItem) => {
    setLinkId(item.product_id);
    setLinkImage(item.image_url);
    if (!name.trim()) setName(item.name);
    setCatSearch("");
    setCatResults([]);
  };

  const setLabel = (code: string) => setOptions.find((o) => o.value === code)?.label ?? code;

  // Eigenes Foto (hochgeladen/gewählt) vs. CDN-Bild aus dem Katalog — die
  // Foto-Aktionen (ersetzen/löschen) gelten NUR fürs eigene Foto (Panel-Fund).
  const hatEigenesFoto = Boolean(current?.bild_thumbnail_pfad || photoPreview);
  const imgSrc =
    current?.bild_thumbnail_pfad
      ? imageUrl(current.bild_thumbnail_pfad, API_BASE, photoVersion)
      : (photoPreview ?? (linkId ? linkImage : null));

  const gv = wert != null && kaufpreis != null ? parseFloat(wert) - parseFloat(kaufpreis) : null;

  const addSet = (code: string) => {
    if (code && !setCodes.includes(code)) setSetCodes((cs) => [...cs, code]);
  };
  const removeSet = (code: string) => setSetCodes((cs) => cs.filter((c) => c !== code));

  const handlePhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    if (current) {
      // Edit: direkt hochladen
      try {
        const r = await sealedApi.uploadImage(current.id, file);
        setCurrent(r.data);
        setPhotoVersion((v) => v + 1);
        toast.success(t.detail_photo_saved);
      } catch {
        toast.error(t.detail_upload_error);
      }
    } else {
      // Neuanlage: Foto bis zum Speichern zwischenhalten
      setPhotoFile(file);
      setPhotoPreview((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return URL.createObjectURL(file);
      });
    }
  };

  const handleDeletePhoto = async () => {
    if (!current) {
      setPhotoFile(null);
      setPhotoPreview((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
      return;
    }
    if (!confirm(t.detail_delete_photo_confirm)) return;
    try {
      const r = await sealedApi.deleteImage(current.id);
      setCurrent(r.data);
      toast.success(t.detail_photo_saved);
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  const payload = (): Partial<SealedProduct> => ({
    name: name.trim(),
    typ,
    zustand,
    set_codes: setCodes,
    kaufpreis_eur: kaufpreis,
    kaufdatum,
    wert_eur: wert,
    notizen,
    // Verknüpfung (#46): id = verknüpfen, null = lösen (Server-Semantik:
    // explizit gesetztes leeres Feld löst; weggelassen = unverändert)
    tcgplayer_product_id: linkId,
  });

  const handleSave = async () => {
    if (!name.trim()) { toast.error(t.sealed_name_required); return; }
    setSaving(true);
    try {
      if (current) {
        await sealedApi.update(current.id, payload());
      } else {
        const r = await sealedApi.create(payload());
        if (photoFile) {
          try { await sealedApi.uploadImage(r.data.id, photoFile); } catch { /* Foto nicht kritisch */ }
        }
      }
      toast.success(t.sealed_saved);
      onSaved();
      onClose();
    } catch {
      toast.error(t.form_save_error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!current) return;
    if (!confirm(t.detail_delete_confirm(current.name))) return;
    try {
      await sealedApi.delete(current.id);
      toast.success(t.sealed_deleted);
      onSaved();
      onClose();
    } catch {
      toast.error(t.detail_delete_error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-start sm:items-center justify-center z-50 p-2 sm:p-4 overflow-y-auto">
      <div className="bg-gray-900 rounded-xl border border-gray-700 p-4 sm:p-6 max-w-2xl w-full shadow-2xl my-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold text-white">{isEdit ? t.sealed_form_edit : t.sealed_form_new}</h2>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-white text-xl leading-none">×</button>
        </div>

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Foto */}
          <div className="shrink-0 w-full sm:w-40 mx-auto sm:mx-0">
            <div className="aspect-square relative bg-gray-800 rounded-lg overflow-hidden">
              {imgSrc ? (
                // TCGplayer-CDN funktioniert auch mit next/Image (remotePatterns "**")
                <Image src={imgSrc} alt={name || "Sealed"} fill
                  className={hatEigenesFoto ? "object-cover" : "object-contain"} />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-600 text-4xl">📦</div>
              )}
            </div>
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handlePhoto} />
            <input type="file" accept="image/*" capture="environment" className="hidden"
              id="sealed-camera" onChange={handlePhoto} />
            <div className="mt-2 grid grid-cols-2 gap-1">
              <button type="button"
                onClick={() => document.getElementById("sealed-camera")?.click()}
                className="text-xs bg-gray-800 text-gray-300 hover:text-white rounded px-2 py-1.5">
                {t.detail_take_photo}
              </button>
              <button type="button"
                onClick={() => fileRef.current?.click()}
                className="text-xs bg-gray-800 text-gray-300 hover:text-white rounded px-2 py-1.5">
                {imgSrc ? t.detail_replace_photo : t.detail_upload_photo}
              </button>
            </div>
            {hatEigenesFoto && (
              <button type="button" onClick={handleDeletePhoto}
                className="w-full mt-1 text-xs bg-red-950 text-red-400 hover:text-red-200 rounded px-2 py-1.5">
                {t.detail_delete_photo}
              </button>
            )}
          </div>

          {/* Felder */}
          <div className="flex-1 min-w-0 grid grid-cols-2 gap-3">
            {/* Sealed-Katalog-Picker (#46): echte TCGplayer-Produkte statt Freitext */}
            <div className="col-span-2">
              <label htmlFor="sealed-cat" className="text-gray-400 text-xs block mb-1">{t.sealed_catalog_search}</label>
              {linkId ? (
                <div className="flex items-center justify-between bg-gray-800/60 border border-green-900 rounded px-2 py-1.5 text-sm">
                  <span className="text-green-400 text-xs">{t.sealed_catalog_linked(linkId)}</span>
                  <button type="button" onClick={() => { setLinkId(null); setLinkImage(null); }}
                    className="text-gray-400 hover:text-red-300 text-xs">{t.sealed_catalog_unlink}</button>
                </div>
              ) : (
                <>
                  <input id="sealed-cat" type="text" value={catSearch}
                    onChange={(e) => setCatSearch(e.target.value)}
                    placeholder={t.sealed_catalog_placeholder}
                    className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm" />
                  {catResults.length > 0 && (
                    <div className="mt-1 max-h-44 overflow-y-auto border border-gray-700 rounded divide-y divide-gray-800 bg-gray-900">
                      {catResults.map((item) => (
                        <button key={item.product_id} type="button" onClick={() => pickCatalog(item)}
                          className="w-full text-left px-2 py-1.5 hover:bg-gray-800 flex items-center justify-between gap-2">
                          <span className="text-white text-xs truncate">
                            {item.name}
                            {item.region === "ja" && <span className="ml-1 text-[9px] uppercase text-gray-500">JP</span>}
                          </span>
                          {item.price_usd != null && (
                            <span className="text-gray-400 text-xs shrink-0">$ {item.price_usd.toFixed(2)}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  <p className="text-gray-600 text-xs mt-1">{t.sealed_catalog_hint}</p>
                </>
              )}
            </div>
            <div className="col-span-2">
              <label htmlFor="sealed-name" className="text-gray-400 text-xs block mb-1">{t.sealed_name} *</label>
              <input id="sealed-name" type="text" value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t.sealed_name_placeholder}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm" />
            </div>

            <SelectField fieldKey="typ" label={t.sealed_typ} value={typ}
              onChange={setTyp} options={enums?.typ ?? []} />
            <SelectField fieldKey="zustand" label={t.sealed_zustand} value={zustand}
              onChange={setZustand} options={enums?.zustand ?? []} />

            {/* Mehrfach-Set-Auswahl */}
            <div className="col-span-2">
              <label className="text-gray-400 text-xs block mb-1">{t.sealed_sets}</label>
              {setCodes.length > 0 ? (
                <div className="flex flex-wrap gap-1 mb-1.5">
                  {setCodes.map((code) => (
                    <span key={code} className="inline-flex items-center gap-1 bg-gray-800 border border-gray-700 rounded-full px-2 py-0.5 text-xs text-white">
                      <span className="truncate max-w-[12rem]">{setLabel(code)}</span>
                      <button type="button" onClick={() => removeSet(code)}
                        className="text-gray-400 hover:text-red-300 leading-none">×</button>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-gray-600 text-xs mb-1.5">{t.sealed_sets_none}</p>
              )}
              <SearchableSelect
                value=""
                onChange={addSet}
                options={setOptions.filter((o) => !setCodes.includes(o.value))}
                placeholder={t.sealed_sets_add}
              />
              <p className="text-gray-600 text-xs mt-1">{t.sealed_sets_hint}</p>
            </div>

            <CurrencyField label={t.form_purchase_price} value={kaufpreis} onChange={setKaufpreis} />
            <DateField label={t.form_purchase_date} value={kaufdatum} onChange={setKaufdatum} />

            <div className="col-span-2">
              <CurrencyField label={t.sealed_value} value={wert} onChange={setWert} />
              <p className="text-gray-600 text-xs mt-1">
                {linkId ? t.sealed_value_auto_hint : t.sealed_value_hint}
                {current?.wert_aktualisiert && !isNaN(new Date(current.wert_aktualisiert).getTime()) && (
                  <> · {t.detail_value_updated}: {new Date(current.wert_aktualisiert).toLocaleDateString(t.date_locale)}</>
                )}
              </p>
            </div>

            {/* G/V-Anzeige (nur wenn Kaufpreis + Wert gesetzt) */}
            {gv != null && (
              <div className="col-span-2 flex items-center justify-between bg-gray-800/60 rounded px-3 py-2 text-sm">
                <span className="text-gray-400">{t.detail_gain_loss}</span>
                <span className={`font-semibold ${gv >= 0 ? "text-green-400" : "text-red-400"}`}>
                  {gv > 0 ? "+" : ""}{formatEur(gv.toFixed(2))}
                </span>
              </div>
            )}

            <TextareaField label={t.form_notes} value={notizen} onChange={setNotizen} />
          </div>
        </div>

        <div className="flex flex-wrap gap-3 mt-5 justify-between">
          <div className="flex gap-3">
            <button type="button" onClick={handleSave} disabled={saving}
              className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-50">
              {t.form_save}
            </button>
            <button type="button" onClick={onClose}
              className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
              {t.form_cancel}
            </button>
          </div>
          {isEdit && (
            <button type="button" onClick={handleDelete}
              className="bg-red-950 text-red-400 hover:text-red-200 px-4 py-2 rounded">
              {t.detail_delete}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
