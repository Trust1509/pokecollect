"use client";
import { useI18n } from "@/lib/i18n";

// Dezenter „1st Ed."-Badge — auf der Kachel (CardGrid) und der Detailseite (#25).
// Eine Routine für beide Stellen (Kredo DRY); die Positionierung übernimmt der
// jeweilige Aufrufer per className.
export default function FirstEditionBadge({ className = "" }: { className?: string }) {
  const { t } = useI18n();
  return (
    <span
      className={`inline-block bg-amber-500/90 text-black text-[9px] font-bold leading-none px-1 py-0.5 rounded ${className}`}
      title={t.first_edition_label}
    >
      {t.first_edition_badge}
    </span>
  );
}
