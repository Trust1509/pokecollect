"use client";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { cardApi, collectionApi, Enums, PokemonSet, setsApi, settingsApi } from "@/lib/api";
import SetPicker from "@/components/SetPicker";
import { CardNrField, PokedexNrField, SelectField, TextareaField, TextField } from "@/components/CardFormFields";
import { useI18n } from "@/lib/i18n";
import { CardFormValues, useCardForm } from "@/lib/useCardForm";

function NewCardForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const collectionId = searchParams?.get("collection") ?? null;
  const { t } = useI18n();
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [form, setForm] = useState<CardFormValues>({
    sprache: "DE",
    besessen: false,
    folierung: "Normal",
  });
  // Gemeinsame Formular-Logik (Lookup, Validierung, Set-Auswahl) — Issue #5
  const {
    selectedSet, cardNrError, setCardNrError, nameLoading,
    noteManualEdit, handlePokedexNr, validateCardNr, handleSetChange,
  } = useCardForm(setForm);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    setsApi.list().then((r) => setSets(r.data));
    // Standard-Sprache/-Zustand aus den Einstellungen vorbelegen
    // (nur solange der Nutzer die Felder noch nicht angefasst hat).
    settingsApi.get().then((r) => {
      setForm((f) => ({
        ...f,
        sprache: f.sprache === "DE" ? (r.data.default_language || "DE") : f.sprache,
        zustand: f.zustand ?? (r.data.default_condition || null),
      }));
    }).catch(() => {});
  }, []);

  const set = (key: string, value: unknown) => {
    // Manuelle Eingabe in Namensfelder → auto-fill-Flag zurücksetzen
    noteManualEdit(key);
    setForm((f) => ({ ...f, [key]: value }));
    if (key === "karten_nr") setCardNrError(null);
  };

  const handleSave = async () => {
    if (!form.kartenname) { toast.error(t.form_card_name_required); return; }
    const nr = form.karten_nr as string | undefined;
    if (nr && !validateCardNr(nr)) return;
    try {
      const r = await cardApi.create(form);
      // Wenn aus einer Sammlung heraus angelegt: direkt zuweisen
      if (collectionId) {
        try { await collectionApi.addCard(Number(collectionId), r.data.id); } catch {/* nicht kritisch */}
      }
      toast.success(t.form_saved);
      router.push(collectionId ? `/collections/${collectionId}` : `/cards/${r.data.id}`);
    } catch {
      toast.error(t.form_save_error);
    }
  };

  const sel = (key: string, label: string, options: string[]) => (
    <SelectField
      key={key}
      fieldKey={key}
      label={label}
      value={form[key]}
      onChange={(v) => set(key, v)}
      options={options}
      language={String(form.sprache ?? "DE")}
    />
  );

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-4">
        <Link href="/" className="text-gray-500 hover:text-white text-sm">{t.form_back}</Link>
      </div>
      <h1 className="text-xl font-bold text-white mb-6">{t.form_new_card}</h1>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label htmlFor="kartenname" className="text-gray-400 text-xs block mb-1">{t.form_card_name} *</label>
          <input
            id="kartenname"
            type="text"
            value={String(form.kartenname ?? "")}
            onChange={(e) => set("kartenname", e.target.value)}
            placeholder="z.B. Glumanda"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white"
          />
        </div>
        <PokedexNrField
          value={form.pokedex_nr}
          onChange={handlePokedexNr}
          nameLoading={nameLoading}
        />
        <TextField
          label={t.form_english_name}
          value={form.englischer_name}
          onChange={(v) => set("englischer_name", v)}
        />

        {/* Set-Picker */}
        <SetPicker
          value={String(form.set_edition ?? "")}
          onChange={handleSetChange}
          sets={sets}
          onSetAdded={(s) => setSets((prev) => [...prev, s].sort((a, b) => a.code.localeCompare(b.code)))}
        />

        {/* Karten-Nr. mit Hinweis */}
        <CardNrField
          value={form.karten_nr}
          onChange={(v) => set("karten_nr", v)}
          validate={validateCardNr}
          selectedSet={selectedSet}
          error={cardNrError}
        />
        <div /> {/* spacer */}

        {sel("seltenheit", t.form_rarity, enums?.seltenheit ?? [])}
        {sel("kartenversion", t.form_card_version, enums?.kartenversion ?? [])}
        {sel("folierung", t.form_foiling, enums?.folierung ?? [])}
        {sel("sprache", t.form_language, enums?.sprache ?? [])}
        {sel("zustand", t.form_condition, enums?.zustand ?? [])}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="besessen"
            checked={Boolean(form.besessen)}
            onChange={(e) => set("besessen", e.target.checked)}
          />
          <label htmlFor="besessen" className="text-white text-sm">{t.form_owned}</label>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="wunschliste"
            checked={Boolean(form.wunschliste)}
            onChange={(e) => set("wunschliste", e.target.checked)}
          />
          <label htmlFor="wunschliste" className="text-white text-sm">{t.form_wishlist}</label>
        </div>
        {Boolean(form.wunschliste) && sel("prioritaet", t.form_priority, enums?.prioritaet ?? [])}
        <TextareaField
          label={t.form_notes}
          value={form.notizen}
          onChange={(v) => set("notizen", v)}
        />
      </div>

      <div className="flex gap-3 mt-6">
        <button type="button" onClick={handleSave} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
          {t.form_save}
        </button>
        <Link href="/" className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
          {t.form_cancel}
        </Link>
      </div>
    </div>
  );
}

export default function NewCardPage() {
  return (
    <Suspense fallback={null}>
      <NewCardForm />
    </Suspense>
  );
}
