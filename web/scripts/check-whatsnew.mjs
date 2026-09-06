#!/usr/bin/env node
// Wächter (Issue #99, lehren.md Klasse 1/13): Der Generierungsschritt darf
// nicht lautlos ausfallen. Prüft NUR das bereits generierte
// src/lib/whatsnew.generated.ts gegen die aktuelle APP_VERSION — braucht
// darum KEIN CHANGELOG.md (im Web-Docker-Build-Kontext ohnehin nicht
// vorhanden, web/Dockerfile kopiert nur den web/-Ordner selbst).
//
// Zwei unabhängige Fehlerbilder, beide rot:
//   1. version.ts wurde gebumpt, der Generator aber nie erneut gelaufen
//      (whatsnew.generated.ts zeigt noch die ALTE Version).
//   2. Die generierte Datei ist aktuell, aber DE oder EN ist leer — der
//      wahrscheinlichere Fall ist EN (von Hand geschrieben, siehe
//      web/scripts/generate-whatsnew.mjs).
//
// Aufruf: npm run check:whatsnew (aus web/) — siehe package.json,
// scripts/gates.sh (Gate 2/2) und .github/workflows/ci.yml (Job "web").
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");

function fail(msg) {
  console.error(`FEHLER (check-whatsnew): ${msg}`);
  process.exit(1);
}

const versionSrc = readFileSync(path.join(WEB_ROOT, "src/lib/version.ts"), "utf8");
const versionMatch = versionSrc.match(/APP_VERSION\s*=\s*"([^"]+)"/);
if (!versionMatch) fail("APP_VERSION nicht in src/lib/version.ts gefunden.");
const appVersion = versionMatch[1];

let generatedSrc;
try {
  generatedSrc = readFileSync(path.join(WEB_ROOT, "src/lib/whatsnew.generated.ts"), "utf8");
} catch {
  fail(
    "src/lib/whatsnew.generated.ts fehlt. Generator laufen lassen: " +
      "sh scripts/generate-whatsnew.sh",
  );
}

// Jedes Feld steht (dank generate-whatsnew.mjs) auf GENAU einer Zeile —
// JSON.stringify() escaped echte Zeilenumbrüche im Text zu "\n". Deshalb
// reicht ein zeilen-verankertes Regex, ganz ohne TS-Parser/dritten Runner.
function field(name) {
  const re = new RegExp(`^\\s*${name}:\\s*(.+),$`, "m");
  const m = generatedSrc.match(re);
  if (!m) fail(`Feld "${name}" nicht in whatsnew.generated.ts gefunden — Datei beschädigt/veraltet?`);
  return m[1] === "null" ? null : JSON.parse(m[1]);
}

const genVersion = field("version");
const de = field("de") ?? "";
const en = field("en") ?? "";
const titleEn = field("titleEn") ?? "";
const risk = field("risk");

if (genVersion !== appVersion) {
  fail(
    `whatsnew.generated.ts steht auf Version "${genVersion}", src/lib/version.ts (APP_VERSION) ` +
      `aber auf "${appVersion}". Generator erneut laufen lassen: sh scripts/generate-whatsnew.sh`,
  );
}
if (!de.trim()) {
  fail(
    `Kein deutscher "Was ist neu"-Text für Version ${appVersion} — ` +
      `CHANGELOG.md-Abschnitt "## [v${appVersion}]" fehlt oder ist leer?`,
  );
}
if (!en.trim()) {
  fail(
    `Kein englischer "Was ist neu"-Text für Version ${appVersion}. ` +
      `Vermutlich vergessen: web/src/lib/whatsnew.en.json auf diese Version bringen ` +
      `und den Text von Hand schreiben, danach sh scripts/generate-whatsnew.sh erneut laufen lassen.`,
  );
}

// Panel-Nacharbeit (#99, Zweitstimme WICHTIG): Die Risiko-Stufe ist im
// Release-Ritual verbindlich, wurde hier aber nie geprüft — fehlte sie in der
// CHANGELOG-Überschrift, erzeugte der Generator `risk: null`, das Modal ließ
// das Abzeichen weg und alle Gates blieben grün. (Historisch tragen nur 5 von
// 57 Versionen eine Stufe; verbindlich ist sie erst seit v1.9.0 — geprüft wird
// deshalb nur die AKTUELLE Version, nicht die Historie.)
if (risk === null) {
  fail(
    `Keine Risiko-Stufe für Version ${appVersion}. Die Überschrift in CHANGELOG.md muss ` +
      `auf "— gefahrlos", "— backup" oder "— breaking" enden ` +
      `(docs/agents/release-ritual.md). Danach: sh scripts/generate-whatsnew.sh`,
  );
}

// Panel-Nacharbeit (#99, BEIDE Stimmen): Der Untertitel stand im englischen
// Dialog auf Deutsch, weil es nur ein Titel-Feld gab. Jetzt gibt es titleEn —
// und ein Wächter, der eine vergessene Übersetzung rot macht.
if (!titleEn.trim()) {
  fail(
    `Kein englischer Titel für Version ${appVersion}. In web/src/lib/whatsnew.en.json ` +
      `das Feld "title" auf dieser Version füllen, danach sh scripts/generate-whatsnew.sh`,
  );
}

console.log(
  `✓ whatsnew.generated.ts passt zu v${appVersion} ` +
    `(DE ${de.length} / EN ${en.length} Zeichen, Risiko: ${risk}).`,
);
