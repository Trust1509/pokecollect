"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { cardApi, Enums } from "@/lib/api";

export default function NewCardPage() {
  const router = useRouter();
  const [enums, setEnums] = useState<Enums | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({
    sprache: "DE",
    besessen: false,
    folierung: "Normal",
  });

  useEffect(() => {
    cardApi.enums().then((r) => setEnums(r.data));
  }, []);

  const set = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const handleSave = async () => {
    if (!form.kartenname) { toast.error("Kartenname ist Pflichtfeld"); return; }
    try {
      const r = await cardApi.create(form);
      toast.success("Karte gespeichert");
      router.push(`/cards/${r.data.id}`);
    } catch {
      toast.error("Fehler beim Speichern");
    }
  };

  const sel = (key: string, label: string, options: string[]) => (
    <div>
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
        <Link href="/" className="text-gray-500 hover:text-white text-sm">← Sammlung</Link>
      </div>
      <h1 className="text-xl font-bold text-white mb-6">Neue Karte</h1>

      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className="text-gray-400 text-xs block mb-1">Kartenname *</label>
          <input
            type="text"
            value={String(form.kartenname ?? "")}
            onChange={(e) => set("kartenname", e.target.value)}
            placeholder="z.B. Glumanda"
            className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white"
          />
        </div>
        {txt("pokedex_nr", "Pokédex-Nr.", "number")}
        {txt("englischer_name", "Englischer Name")}
        {txt("set_edition", "Set/Edition")}
        {txt("karten_nr", "Karten-Nr.")}
        {sel("seltenheit", "Seltenheit", enums?.seltenheit ?? [])}
        {sel("kartenversion", "Kartenversion", enums?.kartenversion ?? [])}
        {sel("folierung", "Folierung", enums?.folierung ?? [])}
        {sel("sprache", "Sprache", enums?.sprache ?? [])}
        {sel("zustand", "Zustand", enums?.zustand ?? [])}
        <div className="col-span-2 flex items-center gap-2">
          <input
            type="checkbox"
            id="besessen"
            checked={Boolean(form.besessen)}
            onChange={(e) => set("besessen", e.target.checked)}
          />
          <label htmlFor="besessen" className="text-white text-sm">Besossen (physisch vorhanden)</label>
        </div>
        <div className="col-span-2">
          <label className="text-gray-400 text-xs block mb-1">Notizen</label>
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
          Speichern
        </button>
        <Link href="/" className="bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-600">
          Abbrechen
        </Link>
      </div>
    </div>
  );
}
