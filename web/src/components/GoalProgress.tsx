"use client";
import { CollectionProgress } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

// Fortschrittsbalken "X / Soll" einer Set-Sammlung (Issue #16) —
// eine Routine für Sammlungs-Liste und Detailseite (DRY).
export default function GoalProgress({
  progress,
  className = "",
}: {
  progress: CollectionProgress;
  className?: string;
}) {
  const { t } = useI18n();
  const pct = progress.soll > 0 ? Math.round((progress.erfuellt / progress.soll) * 100) : 0;
  return (
    <div className={className}>
      <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
        <span>{t.collections_progress(progress.erfuellt, progress.soll)}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${pct >= 100 ? "bg-green-500" : "bg-pokemon-yellow"}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}
