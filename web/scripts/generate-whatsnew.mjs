#!/usr/bin/env node
// Generiert src/lib/whatsnew.generated.ts aus dem CHANGELOG (Issue #99).
//
// Deutsch wird automatisch aus CHANGELOG.md für den Abschnitt der AKTUELLEN
// APP_VERSION erzeugt (nie aus "[Unreleased]" — das ist die nächste, noch
// nicht ausgelieferte Version). Englisch ist Handarbeit (whatsnew.en.json) —
// wir übersetzen den CHANGELOG bewusst nicht maschinell — und wird nur
// übernommen, wenn die dort eingetragene Version zur aktuellen passt; sonst
// bleibt "en" ABSICHTLICH leer, statt eine veraltete Übersetzung zu zeigen.
// web/scripts/check-whatsnew.mjs prüft genau das in den Gates nach.
//
// Aufruf: sh scripts/generate-whatsnew.sh (Wegwerf-Node-Container — kein
// lokales npm/node). Teil des Release-Rituals (docs/agents/release-ritual.md).
//
// "### Intern"-Unterabschnitte werden ausgelassen: sie sind ausdrücklich
// fürs Team geschrieben, nicht für Mitnutzer:innen (Befund Bau-Brief #99).

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(WEB_ROOT, "..");

function fail(msg) {
  console.error(`FEHLER (generate-whatsnew): ${msg}`);
  process.exit(1);
}

// ── 1) aktuelle Version ─────────────────────────────────────────────────────
const versionSrc = readFileSync(path.join(WEB_ROOT, "src/lib/version.ts"), "utf8");
const versionMatch = versionSrc.match(/APP_VERSION\s*=\s*"([^"]+)"/);
if (!versionMatch) fail("APP_VERSION nicht in src/lib/version.ts gefunden.");
const version = versionMatch[1];

// ── 2) CHANGELOG-Abschnitt der aktuellen Version finden ─────────────────────
// NICHT "den obersten Abschnitt" nehmen — der oberste ist "[Unreleased]"
// (Befund Bau-Brief #99, Block 2) und damit fast immer die FALSCHE Version.
const changelog = readFileSync(path.join(REPO_ROOT, "CHANGELOG.md"), "utf8");
const lines = changelog.split(/\r?\n/);
const escapedVersion = version.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const headerRe = new RegExp(`^##\\s+\\[v${escapedVersion}\\]`);
const startIdx = lines.findIndex((l) => headerRe.test(l));

let title = "";
let risk = null;
const paragraphs = []; // string[][] — rohe Zeilen je Absatz (leerzeilengetrennt)

if (startIdx === -1) {
  console.warn(`WARNUNG (generate-whatsnew): Kein CHANGELOG-Abschnitt für v${version} gefunden — DE bleibt leer.`);
} else {
  // Titel = Text in der ERSTEN Klammer nach "## [vX.Y.Z] – DATUM"; Risiko-
  // Stufe = Text NACH der schließenden Klammer, getrennt per Geviertstrich.
  // v1.7.0 zeigt: ein Geviertstrich INNERHALB der Klammer gehört zum Titel
  // ("(Scan: … — Gemini · OpenAI …)") — deshalb zuerst auf die Klammer
  // ankern ([^)]* kann keinen ")" überspringen), erst danach auf den Suffix.
  const headerMatch = lines[startIdx].match(/\(([^)]*)\)\s*(?:—\s*(.+))?\s*$/);
  if (headerMatch) {
    title = headerMatch[1].trim();
    const risikoWort = (headerMatch[2] ?? "").trim();
    // Nur die drei kanonischen Stufen aus release-ritual.md zählen — ältere
    // freitextige Warnungen ("⚠️ enthält Migration" u. ä.) sind KEINE Instanz
    // dieser Stufe und werden nicht geraten (Auftrag Block 2/5: "eine
    // fehlende Stufe aushalten, ohne zu raten").
    risk = ["gefahrlos", "backup", "breaking"].includes(risikoWort) ? risikoWort : null;
  }

  // Ende des Abschnitts = nächste "## "-Überschrift (oder Dateiende).
  let endIdx = lines.findIndex((l, i) => i > startIdx && /^##\s+/.test(l));
  if (endIdx === -1) endIdx = lines.length;

  // Zeilen zwischen Leerzeilen zu "Absätzen" gruppieren. Ein Absatz ist im
  // CHANGELOG-Stil entweder eine (bei ~80 Zeichen umgebrochene) Aufzählung
  // ODER ein Fließtext-Absatz — beides gemischt kommt hier nicht vor. Eine
  // Bullet-Fortsetzungszeile beginnt NICHT mit "- " (nur die erste Zeile
  // eines Punkts tut das) — deshalb erst nach Absätzen gruppieren und dann
  // INNERHALB des Absatzes zwischen neuem Punkt und Umbruch unterscheiden,
  // statt pro Zeile zu entscheiden (das hätte jede Umbruchzeile als eigenen
  // Fließtext-Block missverstanden).
  let skip = false; // true innerhalb von "### Intern"
  let curPara = null;
  for (let i = startIdx + 1; i < endIdx; i++) {
    const line = lines[i];
    const subHeader = line.match(/^###\s+(.*)$/);
    if (subHeader) {
      skip = /^Intern\b/.test(subHeader[1].trim());
      curPara = null; // Abschnittswechsel beendet einen offenen Absatz
      continue;
    }
    if (skip) continue;
    if (line.trim().length === 0) {
      curPara = null; // Leerzeile trennt Absätze
      continue;
    }
    if (!curPara) {
      curPara = [];
      paragraphs.push(curPara);
    }
    curPara.push(line);
  }
}

function cleanText(s) {
  return s
    .replace(/\*\*(.*?)\*\*/g, "$1") // Markdown-Fettung entfernen (ZUERST, vor Kursiv)
    .replace(/\*(.*?)\*/g, "$1")     // Markdown-Kursiv entfernen (z. B. "*kritisch*")
    .replace(/`([^`]*)`/g, "$1")     // Inline-Code-Backticks entfernen
    .trim();
}

// Das ist eine bewusste Vereinfachung, kein vollständiger Markdown-Renderer
// — für eine kurze "Was ist neu"-Box reicht das.
const de = paragraphs
  .map((paraLines) => {
    if (/^-\s+/.test(paraLines[0])) {
      // Aufzählung: eine neue "- "-Zeile beginnt einen Punkt, jede andere
      // Zeile ist die umgebrochene Fortsetzung des VORHERIGEN Punkts.
      // .trim() ist hier Pflicht, nicht Kosmetik: Markdown rückt umgebrochene
      // Listenzeilen mit zwei Leerzeichen ein (Befund am Bestand,
      // CHANGELOG.md:37f.) — ungetrimmt entstünden Dreifach-Leerzeichen an
      // jeder Umbruchstelle.
      const items = [];
      for (const l of paraLines) {
        if (/^-\s+/.test(l)) {
          items.push(l.replace(/^-\s+/, "").trim());
        } else if (items.length > 0) {
          items[items.length - 1] += " " + l.trim();
        } else {
          items.push(l.trim()); // defensiv, sollte strukturell nicht vorkommen
        }
      }
      return items.map((it) => "• " + cleanText(it)).join("\n");
    }
    return cleanText(paraLines.map((l) => l.trim()).join(" "));
  })
  .join("\n\n")
  .trim();

// ── 3) Englisch: handgepflegt, nur bei Versionsgleichstand übernehmen ───────
let en = "";
const enPath = path.join(WEB_ROOT, "src/lib/whatsnew.en.json");
try {
  const enData = JSON.parse(readFileSync(enPath, "utf8"));
  if (enData.version === version && typeof enData.en === "string" && enData.en.trim()) {
    en = enData.en.trim();
  } else {
    console.warn(
      `WARNUNG (generate-whatsnew): whatsnew.en.json passt nicht zu v${version} ` +
        `(dort: v${enData.version ?? "?"}) — EN bleibt leer.`,
    );
  }
} catch (e) {
  console.warn(`WARNUNG (generate-whatsnew): whatsnew.en.json nicht lesbar (${e.message}) — EN bleibt leer.`);
}

// ── 4) Ausgabe schreiben ─────────────────────────────────────────────────────
// Jedes Feld bewusst auf EINER Zeile (JSON.stringify escaped echte
// Zeilenumbrüche zu "\n") — web/scripts/check-whatsnew.mjs liest das über
// ein simples zeilen-verankertes Regex, ganz ohne TS-Parser.
const out = `// AUTO-GENERIERT von web/scripts/generate-whatsnew.mjs — NICHT von Hand bearbeiten.
// Quelle: CHANGELOG.md (Abschnitt "## [v${version}]") + src/lib/whatsnew.en.json.
// Neu erzeugen: sh scripts/generate-whatsnew.sh (Release-Ritual).
export type WhatsNewRisk = "gefahrlos" | "backup" | "breaking" | null;

export const WHATS_NEW: { version: string; title: string; risk: WhatsNewRisk; de: string; en: string } = {
  version: ${JSON.stringify(version)},
  title: ${JSON.stringify(title)},
  risk: ${risk ? JSON.stringify(risk) : "null"},
  de: ${JSON.stringify(de)},
  en: ${JSON.stringify(en)},
};
`;

writeFileSync(path.join(WEB_ROOT, "src/lib/whatsnew.generated.ts"), out, "utf8");
console.log(
  `✓ whatsnew.generated.ts erzeugt für v${version} ` +
    `(DE ${de.length} Zeichen, EN ${en.length} Zeichen, Risiko: ${risk ?? "–"})`,
);
