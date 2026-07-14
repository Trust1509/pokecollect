"use client";
import { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { PokemonSet, setsApi } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

type Props = {
  value: string;
  onChange: (setEdition: string, set: PokemonSet | null) => void;
  sets: PokemonSet[];
  onSetAdded: (set: PokemonSet) => void;
};

function parseSetEdition(val: string): { code: string; name: string } | null {
  const m = val.match(/^(.+)\s+\(([A-Z0-9]{1,6})\)$/);
  if (!m) return null;
  return { name: m[1], code: m[2] };
}

export default function SetPicker({ value, onChange, sets, onSetAdded }: Props) {
  const { t } = useI18n();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newName, setNewName] = useState("");
  const [newMax, setNewMax] = useState("");
  const wrapRef = useRef<HTMLDivElement>(null);

  const parsed = parseSetEdition(value);
  const selectedCode = parsed?.code ?? "";
  const selectedName = parsed?.name ?? "";

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowNew(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const filtered = query
    ? sets.filter(
        (s) =>
          s.code.toLowerCase().includes(query.toLowerCase()) ||
          s.name.toLowerCase().includes(query.toLowerCase())
      )
    : sets;

  const select = (s: PokemonSet) => {
    onChange(`${s.name} (${s.code})`, s);
    setQuery("");
    setOpen(false);
    setShowNew(false);
  };

  const clear = () => {
    onChange("", null);
    setQuery("");
  };

  const handleAddSet = async () => {
    if (!newCode || !newName) return;
    try {
      const r = await setsApi.create({
        code: newCode.toUpperCase(),
        name: newName,
        max_card_nr: newMax ? Number(newMax) : null,
      });
      onSetAdded(r.data);
      select(r.data);
      setNewCode("");
      setNewName("");
      setNewMax("");
      setShowNew(false);
    } catch {
      toast.error("Set konnte nicht angelegt werden");
    }
  };

  return (
    <div ref={wrapRef} className="col-span-2 grid grid-cols-2 gap-3">
      {/* Code-Dropdown */}
      <div className="relative min-w-0">
        <label className="text-gray-400 text-xs block mb-1">{t.form_set_code}</label>
        <input
          type="text"
          value={open ? query : selectedCode}
          placeholder={t.form_set_search_placeholder}
          onFocus={() => { setOpen(true); setQuery(selectedCode); }}
          onChange={(e) => { setQuery(e.target.value); setOpen(true); }}
          className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white text-sm"
        />
        {open && (
          <ul className="absolute z-50 w-full bg-gray-900 border border-gray-700 rounded mt-1 max-h-52 overflow-y-auto shadow-xl">
            {filtered.map((s) => (
              <li
                key={s.code}
                onClick={() => select(s)}
                className="px-3 py-2 text-sm text-white hover:bg-gray-700 cursor-pointer flex justify-between"
              >
                <span className="font-mono text-yellow-400">{s.code}</span>
                <span className="text-gray-400 truncate ml-2">{s.name}</span>
              </li>
            ))}
            <li
              onClick={() => { setShowNew(true); setOpen(false); }}
              className="px-3 py-2 text-sm text-blue-400 hover:bg-gray-700 cursor-pointer border-t border-gray-700"
            >
              + {t.form_set_new}
            </li>
          </ul>
        )}
      </div>

      {/* Auto-befüllter Set-Name */}
      <div className="min-w-0">
        <label className="text-gray-400 text-xs block mb-1">{t.form_set_name}</label>
        <div className="flex gap-1">
          <input
            type="text"
            value={selectedName}
            readOnly
            placeholder="—"
            className="flex-1 min-w-0 bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-gray-400 text-sm cursor-not-allowed"
          />
          {value && (
            <button type="button"
              onClick={clear}
              className="text-gray-500 hover:text-red-400 px-2 text-sm"
              title="Set-Auswahl löschen"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Neues Set anlegen */}
      {showNew && (
        <div className="col-span-2 bg-gray-900 border border-gray-700 rounded p-3 space-y-2">
          <p className="text-xs text-gray-400">{t.form_set_new}</p>
          <div className="grid grid-cols-3 gap-2">
            <div>
              <label className="text-gray-500 text-xs block mb-1">{t.form_set_code}</label>
              <input
                type="text"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value.toUpperCase())}
                placeholder="PAF"
                maxLength={6}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm font-mono"
              />
            </div>
            <div>
              <label className="text-gray-500 text-xs block mb-1">{t.form_set_name}</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Set-Name"
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
              />
            </div>
            <div>
              <label className="text-gray-500 text-xs block mb-1">Max. Karten-Nr.</label>
              <input
                type="number"
                value={newMax}
                onChange={(e) => setNewMax(e.target.value)}
                placeholder="z.B. 91"
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button type="button"
              onClick={handleAddSet}
              disabled={!newCode || !newName}
              className="bg-blue-700 text-white text-xs px-3 py-1.5 rounded hover:bg-blue-600 disabled:opacity-40"
            >
              {t.form_set_add}
            </button>
            <button type="button"
              onClick={() => setShowNew(false)}
              className="text-gray-400 text-xs px-3 py-1.5 rounded hover:text-white"
            >
              {t.form_cancel}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
