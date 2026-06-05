"use client";
import { useI18n } from "@/lib/i18n";

export type ViewMode = "grid" | "binder";

type Props = {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
};

export default function ViewToggle({ value, onChange }: Props) {
  const { t } = useI18n();
  const base = "text-xs px-2.5 py-1 rounded transition-colors";
  return (
    <div className="inline-flex gap-1 bg-pokemon-card rounded p-0.5">
      <button
        onClick={() => onChange("grid")}
        className={`${base} ${value === "grid" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`}
      >
        ▦ {t.view_grid}
      </button>
      <button
        onClick={() => onChange("binder")}
        className={`${base} ${value === "binder" ? "bg-gray-700 text-white" : "text-gray-400 hover:text-white"}`}
      >
        📒 {t.view_binder}
      </button>
    </div>
  );
}
