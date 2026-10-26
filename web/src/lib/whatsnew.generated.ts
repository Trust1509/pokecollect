// AUTO-GENERIERT von web/scripts/generate-whatsnew.mjs — NICHT von Hand bearbeiten.
// Quelle: CHANGELOG.md (Abschnitt "## [v1.9.3]") + src/lib/whatsnew.en.json.
// Neu erzeugen: sh scripts/generate-whatsnew.sh (Release-Ritual).
export type WhatsNewRisk = "gefahrlos" | "backup" | "breaking" | null;

export const WHATS_NEW: { version: string; title: string; titleEn: string; risk: WhatsNewRisk; de: string; en: string } = {
  version: "1.9.3",
  title: "Sicherheits-Hotfix: Bild-Optimierung abgeschaltet",
  titleEn: "Security hotfix: image optimization switched off",
  risk: "gefahrlos",
  de: "Keine Migration, keine Änderung an deinen Daten. Kartenbilder werden ab jetzt in Originalgröße geladen statt vom Server verkleinert. Das kann auf dem Handy etwas mehr Datenvolumen kosten; sonst ändert sich nichts.\n\n• Bild-Optimierung vorübergehend abgeschaltet. Im Bild-Dienst des Frontend-Frameworks (Next.js) sind zwei kritische Lücken bekannt geworden, über die ein Angreifer im Netzwerk ohne Anmeldung Code auf dem Server ausführen könnte. Behoben sind sie erst in einer neueren Hauptversion des Frameworks; der Umstieg darauf folgt. Bis dahin ist der Bild-Dienst aus — der betroffene Endpunkt antwortet nicht mehr, die Bilder kommen direkt von ihrer Quelle.",
  en: "No migration, no change to your data. Card images now load in their original size instead of being scaled down by the server. On a phone this may use a little more data; nothing else changes.\n\n• Security: image optimization is switched off for now. Two critical flaws became known in the image service of the frontend framework (Next.js) that could let an attacker on the network run code on the server without logging in. They are only fixed in a newer major version of the framework; the move to it follows. Until then the image service is off — the affected endpoint no longer answers, and images come straight from their source.",
};
