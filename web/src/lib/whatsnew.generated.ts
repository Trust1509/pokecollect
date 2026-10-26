// AUTO-GENERIERT von web/scripts/generate-whatsnew.mjs — NICHT von Hand bearbeiten.
// Quelle: CHANGELOG.md (Abschnitt "## [v1.9.3]") + src/lib/whatsnew.en.json.
// Neu erzeugen: sh scripts/generate-whatsnew.sh (Release-Ritual).
export type WhatsNewRisk = "gefahrlos" | "backup" | "breaking" | null;

export const WHATS_NEW: { version: string; title: string; titleEn: string; risk: WhatsNewRisk; de: string; en: string } = {
  version: "1.9.3",
  title: "Sicherheits-Hotfix: Bild-Optimierung abgeschaltet",
  titleEn: "Security hotfix: image optimization switched off",
  risk: "gefahrlos",
  de: "Keine Migration, keine Änderung an deinen Daten. Kartenbilder werden ab jetzt in Originalgröße geladen statt vom Server verkleinert. Das kostet auf dem Handy deutlich mehr Datenvolumen, und Bilder von Karten-Datenbanken und Platzhalter holt jetzt dein Browser selbst bei deren Bild-Servern (bisher holte sie der PokéCollect-Server). Eine von Hand eingetragene Bild-Adresse zu einer fremden Seite wird jetzt angezeigt; bisher blieb sie leer.\n\n• Bild-Optimierung vorübergehend abgeschaltet. Im Bild-Dienst des Frontend-Frameworks (Next.js) sind zwei kritische Lücken bekannt geworden, über die ein Angreifer im Netzwerk ohne Anmeldung Code auf dem Server ausführen könnte. Behoben sind sie erst in einer neueren Hauptversion des Frameworks; der Umstieg darauf folgt. Bis dahin ist der Bild-Dienst aus — der betroffene Endpunkt ist abgeschaltet, die Bilder kommen direkt von ihrer Quelle.",
  en: "No migration, no change to your data. Card images now load in their original size instead of being scaled down by the server. On a phone this uses noticeably more data, and images from card databases as well as placeholders are now fetched by your browser directly from their image servers (until now the PokéCollect server fetched them). An image address you entered by hand that points to another site is now shown; until now it stayed empty.\n\n• Security: image optimization is switched off for now. Two critical flaws became known in the image service of the frontend framework (Next.js) that could let an attacker on the network run code on the server without logging in. They are only fixed in a newer major version of the framework; the move to it follows. Until then the image service is off — the affected endpoint is switched off, and images come straight from their source.",
};
