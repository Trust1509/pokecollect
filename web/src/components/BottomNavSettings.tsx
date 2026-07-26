"use client";
// Konfig-UI der BottomNav (Einstellungen → Abschnitt "Navigation"): der Nutzer
// wählt per Checkbox, welche Ziele als Schnellzugriff unten erscheinen. Deckel
// bei MAX_BOTTOM_NAV; alles Nicht-Gewählte bleibt über das Burger-Menü (☰)
// erreichbar. Speicherung per-Gerät in localStorage (Issue #34).
import { MAX_BOTTOM_NAV, NAV_TARGETS } from "@/lib/navRegistry";
import { useBottomNavConfig } from "@/lib/useBottomNav";
import { useI18n } from "@/lib/i18n";

export default function BottomNavSettings() {
  const { t } = useI18n();
  const { keys, toggle } = useBottomNavConfig();
  const atMax = keys.length >= MAX_BOTTOM_NAV;

  return (
    <div className="space-y-3">
      <p className="text-gray-400 text-xs">{t.settings_nav_hint}</p>
      <p className="text-gray-600 text-xs">{t.settings_nav_max(MAX_BOTTOM_NAV)}</p>
      <div className="space-y-1">
        {NAV_TARGETS.map((target) => {
          const { key, Icon, labelKey } = target;
          const checked = keys.includes(key);
          // Bei erreichtem Deckel nicht-gewählte Optionen sperren.
          const disabled = !checked && atMax;
          return (
            <label
              key={key}
              className={`flex items-center gap-3 py-1.5 text-sm ${
                disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"
              }`}
            >
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled}
                onChange={() => toggle(key)}
                className="h-4 w-4 shrink-0"
              />
              <Icon size={18} className="text-gray-400 shrink-0" />
              <span className="text-gray-200">{t[labelKey]}</span>
            </label>
          );
        })}
      </div>
      <p className="text-gray-600 text-xs">
        {t.settings_nav_count(keys.length, MAX_BOTTOM_NAV)}
      </p>
    </div>
  );
}
