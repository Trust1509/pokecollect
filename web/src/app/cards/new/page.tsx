"use client";
import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { cardApi, collectionApi, Enums, PokemonSet, setsApi } from "@/lib/api";
import SetPicker from "@/components/SetPicker";
import { useI18n } from "@/lib/i18n";
import { fetchPokemonNames } from "@/lib/pokedex";
import RaritySelect from "@/components/RaritySelect";

function NewCardForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const collectionId = searchParams?.get("collection") ?? null;
  const { t } = useI18n();
  const [enums, setEnums] = useState<Enums | null>(null);
  const [sets, setSets] = useState<PokemonSet[]>([]);
  const [selectedSet, setSelectedSet] = useState<PokemonSet | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({
    sprache: "DE",
    besessen: false,
    folierung: "Normal",
  });
  const [cardNrError, setCardNrError] = useState<string | null>(null);
  const [nameLoading, setNameLoading] = useState(false);
  // Tracking ob Name auto-befüllt wurde — dann darf er bei Nr.-Änderung überschrieben werden
  const autoFilled = useRef({ kartenname: false, englischer_name: false });
  const lookupTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
    setsApi.list().then((r) => setSets(r.data));
  }, []);

  const set = (key: string, value: unknown) => {
    // Manuelle Eingabe in Namensfelder → auto-fill-Flag zurücksetzen
    if (key === "kartenname") autoFilled.current.kartenname = false;
    if (key === "englischer_name") autoFilled.current.englischer_name = false;
    setForm((f) => ({ ...f, [key]: value }));
    if (key === "karten_nr") setCardNrError(null);
  };

  const handlePokedexNr = (nr: number | null) => {
    setForm((f) => ({ ...f, pokedex_nr: nr }));
    if (lookupTimeout.current) clearTimeout(lookupTimeout.current);

    if (!nr || nr < 1 || nr > 1025) {
      // Wert sichern BEVOR der Ref zurückgesetzt wird, sonst liest setForm schon false
      const af = { ...autoFilled.current };
      autoFilled.current = { kartenname: false, englischer_name: false };
      setForm((f) => ({
        ...f,
        kartenname: af.kartenname ? "" : f.kartenname,
        englischer_name: af.englischer_name ? "" : f.englischer_name,
      }));
      return;
    }

    // Debounce: erst nach 500ms Tippen-Pause den Lookup starten
    lookupTimeout.current = setTimeout(async () => {
      setNameLoading(true);
      try {
        const names = await fetchPokemonNames(nr);
        if (names) {
          setForm((f) => ({
            ...f,
            kartenname: (!f.kartenname || autoFilled.current.kartenname) ? names.de : f.kartenname,
            englischer_name: (!(f.englischer_name as string) || autoFilled.current.englischer_name) ? names.en : f.englischer_name,
          }));
          autoFilled.current = { kartenname: true, englischer_name: true };
        }
      } finally {
        setNameLoading(false);
      }
    }, 500);
  };

  const validateCardNr = (nr: string): boolean => {
    if (!nr || !selectedSet?.max_card_nr) return true;
    const m = nr.match(/^(\d{1,4})\/(\d{1,4})$/);
    if (!m) {
      setCardNrError(t.form_card_nr_invalid(selectedSet.max_card_nr));
      return false;
    }
    return true;
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

  const handleSetChange = (setEdition: string, s: PokemonSet | null) => {
    setForm((f) => ({ ...f, set_edition: setEdition || null }));
    setSelectedSet(s);
    setCardNrError(null);
  };

  const sel = (key: string, label: string, options: string[]) => {
    if (key === "seltenheit") {
      return (
        <RaritySelect
          key={key}
          label={label}
          value={String(form[key] ?? "")}
          onChange={(v) => set(key, v)}
          options={options}
          language={String(form.sprache ?? "DE")}
        />
      );
    }
    return (
      <div key={key}>
        <label className="text-gray-400 text-xs block mb-1">{label}</label>
        <select
          value={String(form[key] ?? "")}
          onChange={(e) => set(key, e.target.value || null)}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
        >
          <option value="">–</option>
          {options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  };

  const txt = (key: string, label: string, type: "text" | "number" = "text") => (
    <div>
      <label className="text-gray-400 text-xs block mb-1">{label}</label>
      <input
        type={type}
        value={String(form[key] ?? "")}
        onChange={(e) => set(key, type === "number" ? Number(e.target.value) || null : e.target.value)}
        className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
      />
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-4">
        <Link href="/" className="text-gray-500 hover:text-white text-sm">{t.form_back}</Link>
      </div>
      <h1 className="text-xl font-bold text-white mb-6">{t.form_new_card}</h1>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="text-gray-400 text-xs block mb-1">{t.form_card_name} *</label>
          <input
            type="text"
            value={String(form.kartenname ?? "")}
            onChange={(e) => set("kartenname", e.target.value)}
            placeholder="z.B. Glumanda"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white"
          />
        </div>
        <div>
          <label className="text-gray-400 text-xs block mb-1">
            {t.form_pokedex_nr}
            {nameLoading && <span className="ml-2 text-gray-500 animate-pulse">…</span>}
          </label>
          <input
            type="number"
            value={String(form.pokedex_nr ?? "")}
            onChange={(e) => handlePokedexNr(Number(e.target.value) || null)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          />
        </div>
        {txt("englischer_name", t.form_english_name)}

        {/* Set-Picker */}
        <SetPicker
          value={String(form.set_edition ?? "")}
          onChange={handleSetChange}
          sets={sets}
          onSetAdded={(s) => setSets((prev) => [...prev, s].sort((a, b) => a.code.localeCompare(b.code)))}
        />

        {/* Karten-Nr. mit Hinweis */}
        <div>
          <label className="text-gray-400 text-xs block mb-1">{t.form_card_nr}</label>
          <input
            type="text"
            value={String(form.karten_nr ?? "")}
            onChange={(e) => set("karten_nr", e.target.value)}
            onBlur={(e) => validateCardNr(e.target.value)}
            placeholder={selectedSet?.max_card_nr ? `001/${String(selectedSet.max_card_nr).padStart(3, "0")}` : "z.B. 001/091"}
            className={`w-full bg-gray-800 border rounded px-2 py-1.5 text-white text-sm ${cardNrError ? "border-red-500" : "border-gray-700"}`}
          />
          {selectedSet?.max_card_nr && !cardNrError && (
            <p className="text-gray-500 text-xs mt-1">{t.form_card_nr_hint(selectedSet.max_card_nr)}</p>
          )}
          {cardNrError && (
            <p className="text-red-400 text-xs mt-1">{cardNrError}</p>
          )}
        </div>
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
        <div className="col-span-2">
          <label className="text-gray-400 text-xs block mb-1">{t.form_notes}</label>
          <textarea
            value={String(form.notizen ?? "")}
            onChange={(e) => set("notizen", e.target.value)}
            rows={3}
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
          />
        </div>
      </div>

      <div className="flex gap-3 mt-6">
        <button onClick={handleSave} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
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
