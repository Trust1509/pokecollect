"use client";
import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import toast from "react-hot-toast";
import { cardApi, pricesApi, Card, Enums } from "@/lib/api";
import PriceChart from "@/components/PriceChart";
import { formatEur } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3010";

export default function CardDetailPage() {
  const params = useParams();
  const id = params?.id as string;
  const router = useRouter();
  const [card, setCard] = useState<Card | null>(null);
  const [enums, setEnums] = useState<Enums | null>(null);
  const [history, setHistory] = useState<unknown[]>([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Card>>({});
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    cardApi.get(Number(id)).then((r) => {
      setCard(r.data);
      setForm(r.data);
    });
    cardApi.enums().then((r) => setEnums(r.data));
    pricesApi.history(Number(id)).then((r) => setHistory(r.data));
  }, [id]);

  if (!card) return <div className="text-gray-500 p-8">Lädt …</div>;

  const imgSrc = card.bild_karte_pfad
    ? `${API_BASE}/images/${card.bild_karte_pfad.replace(/^.*\/images\//, "")}`
    : card.bild_pokedex_url ?? null;

  const handleSave = async () => {
    try {
      const r = await cardApi.update(Number(id), form);
      setCard(r.data);
      setEditing(false);
      toast.success("Gespeichert");
    } catch {
      toast.error("Fehler beim Speichern");
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const r = await cardApi.uploadImage(Number(id), file);
      setCard(r.data);
      toast.success("Foto gespeichert");
    } catch {
      toast.error("Upload fehlgeschlagen");
    }
  };

  const handleDelete = async () => {
    if (!confirm(`"${card.kartenname}" wirklich löschen?`)) return;
    await cardApi.delete(Number(id));
    router.push("/");
  };

  const field = (key: keyof Card, label: string, type: "text" | "number" | "select" | "boolean" | "textarea" = "text", options?: string[]) => {
    const value = (form as Record<string, unknown>)[key];
    if (!editing) {
      return (
        <div key={key}>
          <dt className="text-gray-500 text-xs">{label}</dt>
          <dd className="text-white">
            {type === "boolean" ? (value ? "✓ Ja" : "✗ Nein") : (String(value ?? "–"))}
          </dd>
        </div>
      );
    }
    if (type === "select" && options) {
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
        <Link href="/" className="text-gray-500 hover:text-white text-sm">← Sammlung</Link>
      </div>

      <div className="flex gap-8">
        {/* Kartenbild */}
        <div className="shrink-0 w-52">
          <div className="aspect-[63/88] relative bg-gray-800 rounded-lg overflow-hidden">
            {imgSrc ? (
              <Image src={imgSrc} alt={card.kartenname} fill className="object-cover" />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-600">Kein Bild</div>
            )}
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImageUpload} />
          <button
            onClick={() => fileRef.current?.click()}
            className="w-full mt-2 text-sm bg-gray-800 text-gray-300 hover:text-white rounded px-3 py-1.5"
          >
            Foto {card.bild_karte_pfad ? "austauschen" : "hochladen"}
          </button>
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
                  <button onClick={handleSave} className="bg-green-600 text-white text-sm px-3 py-1.5 rounded hover:bg-green-700">Speichern</button>
                  <button onClick={() => { setEditing(false); setForm(card); }} className="bg-gray-700 text-white text-sm px-3 py-1.5 rounded">Abbrechen</button>
                </>
              ) : (
                <button onClick={() => setEditing(true)} className="bg-pokemon-accent text-white text-sm px-3 py-1.5 rounded hover:bg-blue-700">Bearbeiten</button>
              )}
              <button onClick={handleDelete} className="bg-red-900 text-red-300 text-sm px-3 py-1.5 rounded hover:bg-red-800">Löschen</button>
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-3 text-sm">
            {field("kartenname", "Kartenname")}
            {field("pokedex_nr", "Pokédex-Nr.", "number")}
            {field("englischer_name", "Englischer Name")}
            {field("set_edition", "Set/Edition")}
            {field("karten_nr", "Karten-Nr.")}
            {field("seltenheit", "Seltenheit", "select", enums?.seltenheit)}
            {field("kartenversion", "Kartenversion", "select", enums?.kartenversion)}
            {field("folierung", "Folierung", "select", enums?.folierung)}
            {field("sprache", "Sprache", "select", enums?.sprache)}
            {field("zustand", "Zustand", "select", enums?.zustand)}
            {field("besessen", "Besossen", "boolean")}
            {field("notizen", "Notizen", "textarea")}
          </dl>

          {card.wert_eur && (
            <div className="mt-4 p-3 bg-pokemon-card rounded-lg">
              <div className="text-gray-400 text-xs">Wert (Cardmarket 30-Tage-Ø)</div>
              <div className="text-yellow-400 text-xl font-bold">{formatEur(card.wert_eur)}</div>
              {card.wert_aktualisiert && (
                <div className="text-gray-500 text-xs mt-0.5">
                  Aktualisiert: {new Date(card.wert_aktualisiert).toLocaleDateString("de-AT")}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Preishistorie */}
      <div className="mt-8 bg-pokemon-card rounded-lg p-4">
        <h2 className="text-gray-300 font-medium mb-3">Preisverlauf</h2>
        <PriceChart history={history as { erfasst_am: string; wert_eur: string | null }[]} />
      </div>
    </div>
  );
}
