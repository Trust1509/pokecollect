#!/usr/bin/env python3
"""Prueft, dass jeder Verweis der Form "§N" einen Abschnitt trifft, den es gibt.

    python docs/vorlagen/lehren-verweise-pruefen.py --lehren <lehren.md> <datei> …
    python docs/vorlagen/lehren-verweise-pruefen.py --lehren <lehren.md> --ausser "B-KUVG|ASVG" <datei> …
    python docs/vorlagen/lehren-verweise-pruefen.py --selbstprobe

Exit 0 = jeder gepruefte Verweis trifft einen Abschnitt; **1 = mindestens einer
nicht ODER die Ausnahme hat einen treffenden Verweis mitgenommen** (dann ist das
Muster zu weit, siehe unten); 2 = Aufruf- oder Lesefehler (fehlende Argumente,
Datei nicht lesbar).

WOFUER: Beim Uebernehmen einer Lehre aus der Vorlage werden die Nummern
repo-lokal (abgleich.md, Schritt 2d). Die Verweise IM TEXT der uebernommenen
Lehre bleiben dabei leicht stehen — und ein Verweis auf eine Vorlagen-Nummer
trifft im Kind-Repo eine ANDERE, meist existierende Lehre. Das erzeugt keine
Fehlermeldung, nur eine falsche Begruendung. Gemeldet aus einem Kind-Repo, das
elf Lehren uebernahm: acht interne Verweise in fuenf von ihnen, und ein
Altbestand-Verweis hatte zwei Abgleiche ueberlebt.

WAS ES PRUEFT
-------------
Abschnitte sind Zeilen der Form "## N." oder "## N " am Zeilenanfang der
Lehren-Datei. Verweise sind "§N" und "§§N-M" (beide Enden) in allen genannten
Dateien, die Lehren-Datei eingeschlossen. Ein Verweis auf eine Nummer ohne
Abschnitt ist ROT. Das faengt eine Richtung: einen Verweis ueber die eigene
Zaehlung hinaus. Zaehlt das Repo HOEHER als die Quelle des Verweises, trifft ein
stehen gelassener Verweis eine existierende andere Lehre — dazu unten.

VERWEISE IN DIE ZAEHLUNG DER VORLAGE (abgleich.md 2d: "Vorlage §N") werden
erkannt und NICHT gegen die eigene Zaehlung geprueft. Ein Verweis gehoert der
Vorlage, wenn das Wort "Vorlage" am Wortanfang hoechstens 20 Zeichen vor ihm
steht, ohne Satzteil-Trenner (Komma, Semikolon, Strich, Satzende) und ohne
anderen Verweis dazwischen. Die Meldung nennt ihre Zahl.

WAS ES NICHT PRUEFT — hier steht die Grenze, nicht im Urteil des Lesers
----------------------------------------------------------------------
- **Einen Verweis auf eine existierende, aber falsche Lehre.** Zeigt "§21" im
  Kind-Repo auf eine andere Lehre als in der Vorlage, sieht dieses Skript
  nichts: Die Nummer existiert. Genau dieser Fall war der teuerste der Meldung.
  Dagegen hilft nur, beim Uebernehmen jeden Verweis einzeln nachzuschlagen.
- **Verweise in anderer Schreibweise** ("Abschnitt 21", "Lehre 21", "siehe 21").
  Das Skript kennt nur das Zeichen §.
- **Fremde Paragrafen-Zaehlungen — die gefaehrlichste Klasse, weil sie FALSCHEN
  ALARM erzeugt.** In einem Projekttext steht "§ 43 B-KUVG" oder "§205 BAO";
  das Skript sieht eine Lehren-Nummer und meldet sie als Verweis ins Leere. Zwei
  Vorkehrungen: Eine Zahl mit unmittelbar folgendem Buchstaben (§32b) gilt nicht
  als Verweis, und `--ausser <muster>` nimmt Zeilen aus (Python-Regex, gegen die
  ganze Zeile geprueft). **Die Ausnahme darf nur Verweise wegnehmen, die INS
  LEERE zeigen** — dafuer ist sie da, denn fremde Zaehlungen treffen keinen
  Abschnitt. Nimmt sie einen mit, der TRIFFT, ist das Muster zu weit: Exit 1 mit
  der Zahl. Und die Erfolgsmeldung nennt Muster, uebersprungene Zeilen und
  entfernte Verweise; die Zahlen gehoeren in das Abgleich-Issue.
  Wer Gesetzestexte fuehrt, setzt das Muster im
  Gate-Kommando und nennt es dort. Ein Waechter, der falsch alarmiert, wird
  abgeschaltet — und dann schuetzt er nichts mehr.
  Dazu gehoert dieses Skript selbst: Seine Selbstprobe traegt Beispiel-Verweise
  im Quelltext. Wer die .py-Dateien mitprueft, nimmt es mit --ausser heraus;
  das Gate-Kommando oben prueft die Textdateien. Das Muster gehoert ENG gesetzt:
  Die Meldung nennt die Zahl der uebersprungenen Zeilen UND der dabei entfernten
  Verweise, und beide gehoeren ins Abgleich-Issue.
- **Code-Bloecke und Beispiele werden mitgelesen.** Ein § in einem Beispiel ist
  ein Verweis wie jeder andere; das ist Absicht, weil ein Beispiel mit falscher
  Nummer genauso in die Irre fuehrt. Umgekehrt gilt das auch fuer die
  ABSCHNITTS-Seite: Eine Zeile "## 9. Beispiel" in einem Code-Block zaehlt als
  Abschnitt und macht §9 gruen. Dort ist die Fehlrichtung still, nicht laut —
  ein Grund mehr, Verweise beim Uebernehmen nachzuschlagen.
- **Vorlagen-Verweise gegen die Zaehlung der Vorlage.** Das Skript kennt deren
  Abschnitte nicht; "Vorlage §99" laeuft als Vorlagen-Verweis durch, auch wenn
  es dort keinen §99 gibt.
- **Ein eigener Verweis dicht hinter dem Wort "Vorlage" im selben Satzteil**
  ("die Vorlage gilt fuer §3") wird als Vorlagen-Verweis gelesen und NICHT
  geprueft — die stille Richtung. Sie braucht das Wort am Wortanfang, hoechstens
  20 Zeichen davor und keinen Trenner; in zwei gemessenen Kind-Repos kam das nur
  bei echten Vorlagen-Verweisen vor. Wer so schreibt, setzt ein Komma oder
  formuliert um.
- **Andere Formen eines Vorlagen-Verweises** werden als eigene gelesen und
  schlagen falsch an — die laute Richtung: nachgestellt ("§22 der Vorlage"),
  aufgezaehlt ("Vorlage §20 und §21": §21 gilt als eigener), mit einem Umbruch
  zwischen Wort und Verweis, oder nur mit Versionsstempel ("v1.10.0 §19" ohne das
  Wort). Abhilfe: das Wort vor jeden Verweis ("Vorlage §20 und Vorlage §21").
- **Ob die Lehre selbst richtig ist.** Das ist das Panel.
"""

import io
import os
import re
import sys
import tempfile

# Eine Abschnitts-Zeile darf auch am Dateiende ohne folgendes Zeichen stehen.
ABSCHNITT = re.compile(r"^##+\s*(\d+)(?:[.\s]|$)")
# Eine Spanne tragen nur ZWEI Paragrafenzeichen (§§28-38); ein einzelnes § mit
# Bindestrich ist ein Verweis plus eine andere Zahl, keine Spanne (Fremdstimme).
# Striche: Bindestrich, Halbgeviert UND Geviert — letzteres ist die Hausschrift
# dieser Vorlage und fehlte (Blindpruefer).
# Ein Buchstabe direkt hinter der Zahl macht sie zu einer fremden Zaehlung
# (§32b ASVG) — dann ist es kein Verweis auf eine Lehre (Gegenpruefer).
VERWEIS = re.compile(r"(§§?)\s*(\d+)(?![0-9]*[A-Za-zÄÖÜäöü])"
                     r"(?:\s*[-–—]\s*(\d+)(?![0-9]*[A-Za-zÄÖÜäöü]))?")


def lies(pfad: str) -> str:
    try:
        with io.open(pfad, encoding="utf-8-sig") as datei:
            return datei.read()
    except (OSError, UnicodeDecodeError) as fehler:
        sys.stderr.write("Aufruffehler: %s nicht lesbar (%s).\n"
                         % (pfad, type(fehler).__name__))
        raise SystemExit(2)


def abschnitte(text: str) -> set:
    return {int(t.group(1)) for t in (ABSCHNITT.match(z) for z in text.splitlines()) if t}


# Das Wort, an dem ein Verweis in die Zaehlung der VORLAGE erkannt wird
# (abgleich.md 2d: Vorlagen-Lehren werden als "Vorlage §N" zitiert). Nur am
# WORTANFANG — "Brief-Vorlage" oder "Prompt-Vorlage" sind keine Marke, "Vorlagen"
# und "Vorlagen-Lehre" schon. Gross geschrieben, wie das Substantiv.
VORLAGE_MARKE = re.compile(r"(?<![A-Za-zÄÖÜäöüß-])Vorlage")
# Hoechstens so viele Zeichen zwischen dem Wort und dem Verweis. Gemessen an zwei
# Kind-Repos: alle 26 echten Vorlagen-Verweise haben hoechstens 11 dazwischen
# ("Vorlage** (v1.9.0 §18)"); die zwei Beinahe-Treffer, bei denen ein EIGENER
# Verweis durchrutschte, hatten 55 und 75. Beide Pruefer haben es gefunden.
VORLAGE_FENSTER = 20
# Ein Satzteil-Trenner zwischen Wort und Verweis loest die Bindung: Komma,
# Semikolon, Gedanken- und Halbgeviertstrich, Satzzeichen mit folgendem Leerraum
# (der Punkt in "v1.11.0" trennt nicht).
SATZTEIL_TRENNER = re.compile(r"[,;—–]|[.:!?](?=\s)")


def aufteilen(zeile: str) -> tuple:
    """(lokal, vorlage) — die Nummern dieser Zeile als Text, nach Zaehlung getrennt.

    Ein Verweis gehoert der VORLAGE, wenn das Wort "Vorlage" (am Wortanfang)
    hoechstens VORLAGE_FENSTER Zeichen vor ihm steht, ohne Satzteil-Trenner und
    ohne einen anderen Verweis dazwischen. Das deckt "Vorlage §25", "aus der
    Vorlage (v1.11.0 §20)" und "in der Vorlage als §30"; in "Vorlage §8, bei uns
    §3" bleibt die §3 lokal, ebenso in "Die Vorlage regelt das anders; bei uns
    gilt §23". Ohne diese Trennung meldete das Werkzeug in einem
    Kind-Repo, das 2d befolgt, elf korrekte Vorlagen-Verweise als Verweise ins
    Leere — und keine Ausnahme machte es gruen.
    """
    lokal, vorlage, vorher = [], [], 0
    for t in VERWEIS.finditer(zeile):
        nummern = [t.group(2)]
        if t.group(3) is not None and t.group(1) == "§§":
            nummern.append(t.group(3))
        abschnitt = zeile[vorher:t.start()]
        marken = list(VORLAGE_MARKE.finditer(abschnitt))
        der_vorlage = False
        if marken:
            zwischen = abschnitt[marken[-1].end():]
            der_vorlage = (len(zwischen) <= VORLAGE_FENSTER
                           and not SATZTEIL_TRENNER.search(zwischen))
        (vorlage if der_vorlage else lokal).extend(nummern)
        vorher = t.end()
    return lokal, vorlage


def rohnummern(zeile: str) -> list:
    """Die LOKALEN Nummern dieser Zeile als Text (ohne Vorlagen-Verweise).

    Eine Stelle fuer beide Wege: die gepruefte Zeile und die von `--ausser`
    uebersprungene. Ohne sie zaehlt der eine Weg anders als der andere.
    """
    return aufteilen(zeile)[0]


def verweise(text: str, ausser=None, uebersprungen=None, entfernt=None,
             vorlage=None) -> list:
    """[(Zeilennummer, Nummer)] — bei §§N-M beide Enden; `ausser` ueberspringt Zeilen.

    `uebersprungen` und `entfernt` sind Listen, die die Aufrufer nur ZAEHLEN: die
    ausgenommenen Zeilen und die Verweise, die dabei WEGGEFALLEN sind. Auf ihren
    Inhalt verlaesst sich nichts. Die zweite Zahl ist die
    aussagekraeftige: Uebersprungene Zeilen ohne Verweis kosten nichts, und eine
    Ausnahme, die Verweise wegnimmt, muss sich zeigen (Blindpruefer v1.17.1).
    `vorlage` nimmt die Verweise in die Zaehlung der Vorlage auf; sie werden
    nicht gegen die eigene Zaehlung geprueft, aber gezaehlt und gemeldet.
    """
    gefunden = []
    for nr, zeile in enumerate(text.splitlines(), 1):
        if ausser is not None and ausser.search(zeile):
            if uebersprungen is not None:
                uebersprungen.append(nr)
            if vorlage is not None:
                # Ein Vorlagen-Verweis bleibt einer, auch auf einer ausgenommenen
                # Zeile; sonst haengt die gemeldete Zahl am Muster (Pruefer v1.17.2).
                vorlage.extend(aufteilen(zeile)[1])
            if entfernt is not None:
                # Nicht umwandeln: eine uebersprungene Zeile wird nicht geprueft,
                # also darf eine absurde Zahl darin auch nicht abbrechen.
                entfernt.extend(rohnummern(zeile))
            continue
        lokal, fremd = aufteilen(zeile)
        if vorlage is not None:
            vorlage.extend(fremd)
        for rohzahl in lokal:
            try:
                gefunden.append((nr, int(rohzahl)))
            except ValueError:
                # CPython begrenzt die Ziffernzahl von int(); ohne den Faenger
                # endet ein absurder Verweis im Traceback mit Exit 1, also im
                # Code fuer "Verweis ins Leere" (Blindpruefer).
                sys.stderr.write("Aufruffehler: Zeile %d traegt eine Zahl, die "
                                 "Python nicht umwandelt.\n" % nr)
                raise SystemExit(2)
    return gefunden


def pruefen(lehren: str, dateien: list, ausser=None) -> tuple:
    """(geprueft, Funde, ausgenommene Zeilen, entfernte, davon treffende, Vorlagen-Verweise).

    Die letzte Zahl ist die entscheidende: Ein von der Ausnahme entfernter
    Verweis, der einen Abschnitt TRIFFT, ist ein echter Lehren-Verweis — dann ist
    das Muster zu weit. Fremde Zaehlungen treffen keinen Abschnitt.
    """
    vorhanden = abschnitte(lies(lehren))
    if not vorhanden:
        sys.stderr.write("Aufruffehler: %s hat keine Abschnitte der Form '## N.'.\n" % lehren)
        raise SystemExit(2)
    hoechste = max(vorhanden)
    funde, gesamt, ausgenommen, weg, weg_treffend, der_vorlage = [], 0, 0, 0, 0, 0
    for pfad in dateien:
        text = lies(pfad)
        raus, verloren, fremd = [], [], []
        for zeilennr, nummer in verweise(text, ausser, raus, verloren, fremd):
            gesamt += 1
            if nummer not in vorhanden:
                grund = ("ueber der hoechsten Nummer %d" % hoechste
                         if nummer > hoechste else "es gibt keinen Abschnitt %d" % nummer)
                funde.append("%s:%d: Verweis §%d — %s" % (pfad, zeilennr, nummer, grund))
        ausgenommen += len(raus)
        weg += len(verloren)
        der_vorlage += len(fremd)
        for rohzahl in verloren:
            try:
                # Eine Zahl, die Python nicht umwandelt, trifft auch keinen
                # Abschnitt — hier darf sie nicht abbrechen.
                if int(rohzahl) in vorhanden:
                    weg_treffend += 1
            except ValueError:
                pass
    return gesamt, funde, ausgenommen, weg, weg_treffend, der_vorlage


def selbstprobe() -> int:
    """Faelle mit bekanntem Ergebnis; ohne sie ist dieses Skript Disziplin."""
    geprueft = [0]
    fehler = []

    def erwarte(name, ist, soll):
        geprueft[0] += 1
        if ist != soll:
            fehler.append("%s: %r, erwartet %r" % (name, ist, soll))

    erwarte("Abschnitte: '## 3. Titel'", abschnitte("## 3. Titel\n"), {3})
    erwarte("Abschnitte: '### 12 Titel'", abschnitte("### 12 Titel\n"), {12})
    erwarte("Abschnitte: Fliesstext zaehlt nicht", abschnitte("Der 3. Versuch\n"), set())
    erwarte("Abschnitte: '## Vor jedem Slice' zaehlt nicht",
            abschnitte("## Vor jedem Slice: fuenf Fragen\n"), set())
    erwarte("Verweise: einfach", [n for _, n in verweise("siehe §7 dort")], [7])
    erwarte("Verweise: mit Leerraum", [n for _, n in verweise("siehe § 7")], [7])
    erwarte("Verweise: Spanne mit Halbgeviert",
            [n for _, n in verweise("unsere §§28–38 hangen an")], [28, 38])
    erwarte("Verweise: Spanne mit Bindestrich",
            [n for _, n in verweise("§§4-6")], [4, 6])
    erwarte("Verweise: zwei in einer Zeile",
            [n for _, n in verweise("§17, §21")], [17, 21])
    erwarte("Verweise: Zeilennummer stimmt",
            verweise("nichts\nhier §5\n"), [(2, 5)])
    erwarte("Verweise: ohne Zahl kein Verweis", verweise("§ und weiter"), [])

    # Die Form "Vorlage §N" (abgleich.md 2d). Die ersten fuenf Faelle stehen so in
    # einem Kind-Repo, das 2d befolgt; dort meldete das Werkzeug elf korrekte
    # Vorlagen-Verweise als Verweise ins Leere (gemessen).
    erwarte("Vorlage: 'Vorlage §25'", aufteilen("Vorlage §25: Ein Befehl"), ([], ["25"]))
    erwarte("Vorlage: 'aus der Vorlage (v1.11.0 §20)'",
            aufteilen("Übernommen aus der Vorlage (v1.11.0 §20), mit Beleg"), ([], ["20"]))
    erwarte("Vorlage: 'in der Vorlage als §30'",
            aufteilen("Unser Fall, in der Vorlage als §30 verallgemeinert."), ([], ["30"]))
    erwarte("Vorlage: 'aus der Vorlage (dort §22'",
            aufteilen("Übernommen aus der Vorlage (dort §22, drei Belege"), ([], ["22"]))
    erwarte("Vorlage: 'Vorlage (v1.9.0 §18)' — Nummer, die es auch lokal gibt",
            aufteilen("Vorlage** (v1.9.0 §18). Zwei Projekte"), ([], ["18"]))
    erwarte("Vorlage: danach ein eigener Verweis bleibt lokal",
            aufteilen("Vorlage §8, bei uns §3"), (["3"], ["8"]))
    erwarte("Vorlage: ein Verweis VOR dem Wort bleibt lokal",
            aufteilen("Unser §4 kommt aus der Vorlage §21"), (["4"], ["21"]))
    erwarte("Vorlage: Spanne gehoert ganz der Vorlage",
            aufteilen("aus der Vorlage §§28–38"), ([], ["28", "38"]))
    erwarte("Vorlage: auch 'Vorlagen-Lehre'",
            aufteilen("Die Vorlagen-Lehre §21 sagt"), ([], ["21"]))
    erwarte("Vorlage: ohne das Wort alles lokal",
            aufteilen("Nach §1 und §2"), (["1", "2"], []))
    erwarte("Vorlage: verweise() liefert nur die lokalen",
            [n for _, n in verweise("Vorlage §20, dazu §1")], [1])
    _fremd = []
    verweise("Vorlage §20, dazu §1", vorlage=_fremd)
    erwarte("Vorlage: verweise() sammelt die Vorlagen-Verweise getrennt", _fremd, ["20"])

    # Die drei Bedingungen, jede einzeln. Die stille Richtung — ein EIGENER
    # Verweis rutscht als Vorlagen-Verweis durch — haben beide Pruefer an
    # echtem Text gezeigt, sobald der Absatz anders umbrochen war; die beiden
    # Zeilen hier sind diese Stellen, zusammengezogen.
    erwarte("Vorlage: Trenner — Gedankenstrich und Komma loesen die Bindung",
            aufteilen("an die Vorlage gemeldet — und bei uns behoben statt abgewartet, "
                      "weil §15 gilt"), (["15"], []))
    erwarte("Vorlage: Trenner — Komma und Semikolon",
            aufteilen("(Vorlage, Fund eines anderen Projekts — nicht dieses Repos; "
                      "eigene Funde stehen in §12)"), (["12"], []))
    erwarte("Vorlage: Trenner — Semikolon allein",
            aufteilen("Die Vorlage; §23"), (["23"], []))
    erwarte("Vorlage: Punkt in einer Versionsnummer trennt nicht",
            aufteilen("aus der Vorlage (v1.11.0 §20)"), ([], ["20"]))
    erwarte("Vorlage: Satzende mit Leerraum trennt",
            aufteilen("Das steht in der Vorlage. §7"), (["7"], []))
    erwarte("Vorlage: Wortanfang — ein Kompositum ist keine Marke",
            aufteilen("Die Brief-Vorlage §12"), (["12"], []))
    erwarte("Vorlage: klein geschrieben ist keine Marke",
            aufteilen("siehe vorlage §20"), (["20"], []))
    _genau = "Vorlage" + "x" * 19 + " §5"
    erwarte("Vorlage: Fenster — 20 Zeichen dazwischen binden noch",
            aufteilen(_genau), ([], ["5"]))
    erwarte("Vorlage: Fenster — 21 Zeichen dazwischen binden nicht",
            aufteilen("Vorlage" + "x" * 20 + " §5"), (["5"], []))
    erwarte("Vorlage: Fenster — 'Vorlagen-Version ... unser §4' bleibt lokal",
            aufteilen("Seit der Vorlagen-Version v1.16.0 gilt unser §4"), (["4"], []))
    erwarte("Vorlage: Aufzaehlung — nur der erste gehoert der Vorlage (benannte Grenze)",
            aufteilen("Vorlage §20 und §21"), (["21"], ["20"]))
    erwarte("Verweise: fremde Zaehlung mit Buchstabe (§32b) zaehlt nicht",
            verweise("Pflicht nach §32b ASVG"), [])
    erwarte("Verweise: §43 mit Gesetzesnamen zaehlt (nur --ausser hilft)",
            [n for _, n in verweise("Frist nach § 43 B-KUVG")], [43])
    erwarte("Verweise: --ausser nimmt die Zeile heraus",
            verweise("Frist nach § 43 B-KUVG", re.compile("B-KUVG")), [])
    erwarte("Verweise: Spanne mit Geviertstrich",
            [n for _, n in verweise("unsere §§28—38")], [28, 38])
    erwarte("Verweise: einzelnes § mit Strich ist KEINE Spanne",
            [n for _, n in verweise("siehe §28-38")], [28])
    erwarte("Abschnitte: '## 9' am Dateiende ohne Zeilenumbruch",
            abschnitte("## 9"), {9})

    with tempfile.TemporaryDirectory() as d:
        lehren = os.path.join(d, "lehren.md")
        text = os.path.join(d, "text.md")

        def schreib(pfad, inhalt):
            with io.open(pfad, "w", encoding="utf-8", newline="\n") as datei:
                datei.write(inhalt)

        schreib(lehren, "## 1. Eins\n## 2. Zwei\nsiehe §1\n")
        schreib(text, "Verweis auf §2 — gut.\n")
        gesamt, funde, _raus, _weg, _tr, _vl = pruefen(lehren, [lehren, text])
        erwarte("gruen: alle Verweise treffen", funde, [])
        erwarte("gruen: beide Dateien gelesen", gesamt, 2)

        schreib(text, "Verweis auf §9 — es gibt nur zwei.\n")
        gesamt, funde, _raus, _weg, _tr, _vl = pruefen(lehren, [lehren, text])
        erwarte("rot: Verweis ueber der hoechsten Nummer", len(funde), 1)
        erwarte("rot: Meldung nennt die hoechste Nummer",
                "ueber der hoechsten Nummer 2" in funde[0], True)
        erwarte("rot: Meldung nennt Datei und Zeile", ":1: Verweis §9" in funde[0], True)

        schreib(lehren, "## 1. Eins\n## 3. Drei\n")
        schreib(text, "Verweis auf §2 — die Nummer fehlt in der Mitte.\n")
        gesamt, funde, _raus, _weg, _tr, _vl = pruefen(lehren, [lehren, text])
        erwarte("rot: Luecke in der Nummerierung", len(funde), 1)
        erwarte("rot: Meldung nennt den fehlenden Abschnitt",
                "es gibt keinen Abschnitt 2" in funde[0], True)

        # Der Fall, den dieses Skript NICHT faengt — als Erwartung festgehalten,
        # damit niemand ihm mehr zutraut, als es kann.
        schreib(lehren, "## 1. Eins\n## 2. Zwei\n")
        schreib(text, "Verweis auf §1, gemeint war die Lehre, die hier §2 ist.\n")
        gesamt, funde, _raus, _weg, _tr, _vl = pruefen(lehren, [lehren, text])
        erwarte("Grenze: falscher, aber existierender Verweis bleibt unentdeckt", funde, [])

        schreib(text, "kein Verweis\n")
        gesamt, funde, _raus, _weg, _tr, _vl = pruefen(lehren, [text])
        erwarte("gruen: Datei ohne Verweise", (gesamt, funde), (0, []))

        # Die Ausnahme muss sich ZEIGEN — sonst legt ein zu weites Muster den
        # Waechter still (Blindpruefer der letzten Runde von v1.17.0).
        schreib(lehren, "## 1. Eins\n## 2. Zwei\n")
        schreib(text, "Verweis auf §1.\nFrist nach § 43 B-KUVG.\nNoch ein §2.\n")
        gesamt, funde, raus, weg, treffend, _vl = pruefen(lehren, [text], re.compile("B-KUVG"))
        erwarte("Ausnahme: zaehlt die uebersprungenen Zeilen", raus, 1)
        erwarte("Ausnahme: zaehlt die dabei entfernten Verweise", weg, 1)
        erwarte("Ausnahme: die uebrigen Verweise werden geprueft", (gesamt, funde), (2, []))
        gesamt, funde, raus, weg, treffend, _vl = pruefen(lehren, [text], re.compile("."))
        erwarte("Ausnahme: ein zu weites Muster nimmt alle Zeilen heraus", raus, 3)
        erwarte("Ausnahme: und dabei alle Verweise", weg, 3)
        erwarte("Ausnahme: dann bleibt kein Verweis uebrig", gesamt, 0)
        # Die entscheidende Zahl: wie viele der entfernten TREFFEN einen Abschnitt.
        # Fremde Zaehlungen treffen keinen, echte Lehren-Verweise schon.
        erwarte("Ausnahme: zaehlt die entfernten, die einen Abschnitt treffen",
                treffend, 2)
        gesamt, funde, raus, weg, treffend, _vl = pruefen(
            lehren, [text], re.compile("trifft-nichts"))
        erwarte("Ausnahme: ein Muster ohne Treffer nimmt nichts heraus", (raus, weg), (0, 0))
        erwarte("Ausnahme: ohne Muster wird nichts uebersprungen",
                pruefen(lehren, [text])[2:5], (0, 0, 0))
        # Eine Zeile OHNE Verweis kostet nichts: uebersprungen ja, entfernt nein.
        # Ohne diese Trennung machte der rote Fall einen legitimen Baum rot.
        schreib(text, "Nur Text, kein Verweis.\nNoch eine Zeile.\n")
        erwarte("Ausnahme: uebersprungene Zeile ohne Verweis entfernt keinen",
                pruefen(lehren, [text], re.compile("Nur Text"))[2:5], (1, 0, 0))
        # Zwei Dateien und ein Wert > 1: ohne diesen Fall blieben fuenf Mutationen
        # an der gedruckten Zahl gruen (Blindpruefer v1.17.1, gemessen).
        zweit = os.path.join(d, "zweit.md")
        schreib(text, "Frist nach § 43 B-KUVG.\nVerweis auf §1.\nNoch § 44 B-KUVG.\n")
        schreib(zweit, "Auch hier § 45 B-KUVG.\nUnd §2.\n")
        erwarte("Ausnahme: summiert ueber zwei Dateien",
                pruefen(lehren, [text, zweit], re.compile("B-KUVG"))[2:5], (3, 3, 0))

        # main() selbst: der Exit-Code-Vertrag des Kopfes. Ohne diese drei
        # Erwartungen liesse sich der Zweck des Werkzeugs still entfernen —
        # "if funde:" auf "if False:" gedreht blieb die Selbstprobe gruen und ein
        # Gate mit "... || exit 1" dauerhaft still (Blindpruefer, gemessen).
        # main() druckt dabei; stumm gestellt, weil eine gruene Selbstprobe im
        # Gate-Protokoll nicht nach einem Befund aussehen darf. Die abgefangene
        # Meldung wird gleich mitgepinnt.
        def stumm(argv):
            """(Exit-Code, gedruckte Ausgabe) — beide Stroeme abgefangen.

            SystemExit wird wie auf der Befehlszeile in einen Code uebersetzt:
            Einige Fehlerwege brechen ab, statt zurueckzugeben, und ohne diesen
            Faenger endete die ganze Selbstprobe still mit deren Code.
            """
            alt_out, alt_err = sys.stdout, sys.stderr
            sys.stdout = sys.stderr = fang = io.StringIO()
            try:
                return main(argv), fang.getvalue()
            except SystemExit as ende:
                return (ende.code if isinstance(ende.code, int) else 1), fang.getvalue()
            finally:
                sys.stdout, sys.stderr = alt_out, alt_err

        schreib(lehren, "## 1. Eins\n## 2. Zwei\n")
        schreib(text, "Verweis auf §2.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, text])
        erwarte("main: alle Verweise treffen -> Exit 0", rc, 0)
        erwarte("main: gruene Meldung nennt die Zahl der Verweise",
                "1 Verweise in 1 Datei" in ausgabe, True)
        schreib(text, "Verweis auf §9.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, text])
        erwarte("main: Verweis ins Leere -> Exit 1", rc, 1)
        erwarte("main: rote Meldung nennt Datei, Zeile und Nummer",
                "text.md:1: Verweis §9" in ausgabe, True)
        erwarte("main: rote Meldung nennt die Regel 2d", "abgleich.md, 2d" in ausgabe, True)
        rc, ausgabe = stumm(["prog", "--lehren"])
        erwarte("main: fehlendes Argument -> Exit 2", rc, 2)
        # Die uebrigen Regeln des Vertrags, jede als eigene Mutation gepinnt
        # (Gegenpruefer: acht Regeln waren es nicht).
        schreib(text, "Verweis auf §1.\nFrist nach § 43 B-KUVG.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, text])
        erwarte("main: Gesetzeszitat ohne --ausser -> Exit 1", rc, 1)
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "B-KUVG", text])
        erwarte("main: --ausser macht dieselbe Datei gruen", rc, 0)
        erwarte("main: die gruene Meldung nennt das Muster",
                "Ausnahme 'B-KUVG'" in ausgabe, True)
        erwarte("main: die gruene Meldung nennt die Zahl der uebersprungenen Zeilen",
                "1 Zeile(n) uebersprungen" in ausgabe, True)
        erwarte("main: die gruene Meldung nennt die entfernten Verweise",
                "1 Verweis(e) entfernt" in ausgabe, True)
        erwarte("main: die gruene Meldung verlangt beide Zahlen im Abgleich-Issue",
                "beide Zahlen gehoeren" in ausgabe and "Abgleich-Issue" in ausgabe,
                True)
        erwarte("main: ohne Ausnahme steht kein Ausnahme-Satz in der Meldung",
                "uebersprungen" in stumm(["prog", "--lehren", lehren, text])[1], False)
        # Die gedruckten Ziffern bei zwei Dateien und Werten > 1.
        schreib(text, "Frist nach § 43 B-KUVG.\nVerweis auf §1.\nNoch § 44 B-KUVG.\n")
        schreib(zweit, "Auch hier § 45 B-KUVG.\nUnd §2.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "B-KUVG",
                             text, zweit])
        erwarte("main: zwei Dateien -> Exit 0", rc, 0)
        erwarte("main: gedruckte Zahlen stimmen bei mehreren Dateien",
                "3 Zeile(n) uebersprungen und dabei 3 Verweis(e) entfernt" in ausgabe,
                True)
        # Der BLOCKER: ein Baum, dessen Dateien nur fremde Zaehlungen tragen,
        # bleibt gruen — auch wenn die Ausnahme dort Verweise wegnimmt und keiner
        # uebrig bleibt. Die erste Fassung dieser Regel machte ihn rot, ohne
        # gruenen Ausweg (Blindpruefer v1.17.1, gemessen).
        schreib(text, "Frist nach § 43 B-KUVG.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "B-KUVG", text])
        erwarte("main: nur fremde Zaehlungen, keine eigene -> gruen", rc, 0)
        erwarte("main: und meldet, dass ein Verweis entfernt wurde",
                "1 Verweis(e) entfernt" in ausgabe, True)
        # Ein Muster ohne Treffer aendert nichts.
        schreib(text, "Nur Text, kein Verweis.\n")
        erwarte("main: Muster ohne Treffer bleibt gruen",
                stumm(["prog", "--lehren", lehren, "--ausser", "trifft-nichts", text])[0], 0)
        # Und der rote Fall: die Ausnahme nimmt einen TREFFENDEN Verweis mit.
        schreib(text, "Verweis auf §1.\nFrist nach § 43 B-KUVG.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", ".", text])
        erwarte("main: Ausnahme nimmt einen treffenden Verweis mit -> Exit 1", rc, 1)
        erwarte("main: und sagt, dass das Muster zu weit ist",
                "Muster ist zu weit" in ausgabe, True)
        erwarte("main: der rote Fall nennt Muster und die drei Zahlen",
                "'.'" in ausgabe and "1 Verweis(e) mit, die einen Abschnitt TREFFEN"
                in ausgabe and "2 entfernten in 2 Zeile(n)" in ausgabe, True)
        # Ein enges Muster, das nur die fremde Zaehlung trifft, bleibt gruen —
        # OBWOHL ein eigener Verweis im Satz steht.
        erwarte("main: enges Muster neben einem echten Verweis bleibt gruen",
                stumm(["prog", "--lehren", lehren, "--ausser", "B-KUVG", text])[0], 0)
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "[", text])
        erwarte("main: kaputtes --ausser-Muster -> Exit 2", rc, 2)
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "x"])
        erwarte("main: --ausser ohne Datei -> Exit 2", rc, 2)
        schreib(lehren, "kein Abschnitt hier\n")
        schreib(text, "Verweis auf §1.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, text])
        erwarte("main: Lehren-Datei ohne '## N.' -> Exit 2", rc, 2)
        erwarte("main: Selbstprobe-Schalter wird exakt geprueft",
                stumm(["prog", "--selbstprobe", "zusatz"])[0], 2)
        # BOM: utf-8-sig, sonst ist die erste Ueberschrift unsichtbar
        with io.open(lehren, "w", encoding="utf-8-sig", newline="\n") as datei:
            datei.write("## 1. Eins\n")
        erwarte("Abschnitte: Datei mit BOM wird gelesen", abschnitte(lies(lehren)), {1})
        erwarte("Abschnitte: eine Raute genuegt NICHT", abschnitte("# 9. Titel\n"), set())
        # Eigener Lauf statt einer Variablen von weiter oben: ein spaeter
        # eingeschobener Fall hat "ausgabe" neu belegt, und die Erwartung pruefte
        # seither den falschen Text (beim Bauen dieser Runde passiert).
        _, hilfe = stumm(["prog"])
        # Der Fall aus dem Kind-Repo, Ende zu Ende: zwei eigene Abschnitte,
        # Vorlagen-Verweise mit Nummern darueber UND darunter. Vorher rot ohne
        # gruenen Ausweg; jetzt gruen, und die Meldung zaehlt sie.
        schreib(lehren, "## 1. Eins\n## 2. Zwei\n")
        schreib(text, "Übernommen aus der Vorlage (v1.11.0 §20).\n"
                      "Vorlage §2 — die Nummer gibt es auch hier.\n"
                      "Unser eigener Verweis §1.\n")
        erwarte("Vorlage: pruefen() zaehlt die Vorlagen-Verweise getrennt",
                pruefen(lehren, [text])[0:2] + pruefen(lehren, [text])[5:], (1, [], 2))
        rc, ausgabe = stumm(["prog", "--lehren", lehren, text])
        erwarte("main: Vorlagen-Verweise machen nicht rot", rc, 0)
        erwarte("main: die Meldung nennt die Zahl der Vorlagen-Verweise",
                "Dazu 2 Verweis(e) in der Form 'Vorlage §N'" in ausgabe, True)
        # Und die Ausnahme zaehlt sie nicht als "entfernt": Sie werden ohnehin
        # nicht geprueft, also nimmt ihr Ueberspringen nichts weg.
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "Vorlage", text])
        erwarte("main: --ausser ueber Vorlagen-Zeilen bleibt gruen", rc, 0)
        erwarte("main: und entfernt dabei keinen eigenen Verweis",
                "dabei 0 Verweis(e) entfernt" in ausgabe, True)
        # Die Zahl der Vorlagen-Verweise ueber ZWEI Dateien: ohne diesen Fall
        # blieb "=" statt "+=" gruen, und auf echten Bestaenden verschwand der
        # Satz, weil die letzte Datei keinen traegt (beide Pruefer, gemessen).
        schreib(zweit, "Vorlage §31 und dazu Vorlage §32.\n")
        erwarte("Vorlage: pruefen() summiert die Vorlagen-Verweise ueber Dateien",
                pruefen(lehren, [text, zweit])[5], 4)
        schreib(zweit, "Nur §1.\n")
        erwarte("main: ohne Vorlagen-Verweise steht kein Vorlagen-Satz",
                "Form 'Vorlage" in stumm(["prog", "--lehren", lehren, zweit])[1], False)
        # Ausgenommene Zeilen: die Vorlagen-Verweise darauf werden trotzdem gezaehlt.
        rc, ausgabe = stumm(["prog", "--lehren", lehren, "--ausser", "Vorlage", text])
        erwarte("main: Vorlagen-Verweise auf ausgenommenen Zeilen zaehlen mit",
                "Dazu 2 Verweis(e) in der Form 'Vorlage §N'" in ausgabe, True)
        # Der rote Pfad mit Vorlagen-Verweisen: Hinweis und Zahl stehen dort auch.
        schreib(zweit, "Vorlage §20 und ein eigener §9.\n")
        rc, ausgabe = stumm(["prog", "--lehren", lehren, zweit])
        erwarte("main: roter Pfad mit Vorlagen-Verweis -> Exit 1", rc, 1)
        erwarte("main: roter Pfad nennt die Form 'Vorlage §N' als Abhilfe",
                "steht als 'Vorlage §N'" in ausgabe, True)
        erwarte("main: roter Pfad nennt die Zahl der Vorlagen-Verweise",
                "Dazu 1 Verweis(e) in der Form 'Vorlage §N'" in ausgabe, True)
        erwarte("main: Aufruffehler nennt alle drei Aufrufformen",
                "--selbstprobe" in hilfe and "--lehren" in hilfe
                and "--ausser" in hilfe, True)

    erwarte("mindestens 100 Erwartungen", geprueft[0] >= 100, True)
    if fehler:
        sys.stderr.write("Selbstprobe ROT: %d Abweichung(en)\n  " % len(fehler)
                         + "\n  ".join(fehler) + "\n")
        return 1
    print("Selbstprobe gruen: %d Erwartungen (Abschnitts- und Verweiserkennung, "
          "Spannen mit drei Strichen, Luecke, Meldungstext, die drei Exit-Codes von "
          "main). Nicht geprueft: ob ein Verweis auf die GEMEINTE Lehre zeigt — das "
          "kann dieses Skript nicht." % geprueft[0])
    return 0


def main(argv: list) -> int:
    # Ohne das scheitert die Ausgabe auf einer Konsole mit Codepage 850/437 an
    # einem Gedankenstrich, mit Exit 1 — eine gruene Probe risse so die
    # Gate-Zeile (`... || exit 1`) mit. Dieselbe Zeile steht in ast-gleich.py.
    for strom in (sys.stdout, sys.stderr):
        try:
            strom.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if argv[1:] == ["--selbstprobe"]:
        return selbstprobe()

    if len(argv) < 4 or argv[1] != "--lehren":
        sys.stderr.write(
            "Aufruffehler: --lehren <lehren.md> und mindestens eine zu pruefende Datei.\n"
            "    python lehren-verweise-pruefen.py --lehren docs/agents/lehren.md "
            "docs/agents/*.md CLAUDE.md\n"
            "    python lehren-verweise-pruefen.py --lehren <lehren.md> "
            "--ausser \"B-KUVG|ASVG\" <datei> …\n"
            "    python lehren-verweise-pruefen.py --selbstprobe\n")
        return 2

    lehren, rest = argv[2], argv[3:]
    ausser = None
    if rest[:1] == ["--ausser"]:
        if len(rest) < 3:
            sys.stderr.write("Aufruffehler: --ausser braucht ein Muster und mindestens "
                             "eine Datei.\n")
            return 2
        try:
            ausser = re.compile(rest[1])
        except re.error as fehler:
            sys.stderr.write("Aufruffehler: --ausser ist kein gueltiges Muster (%s).\n"
                             % fehler)
            return 2
        rest = rest[2:]
    dateien = rest
    if not dateien:
        sys.stderr.write("Aufruffehler: keine zu pruefende Datei genannt.\n")
        return 2
    gesamt, funde, ausgenommen, entfernt, entfernt_treffend, der_vorlage = pruefen(
        lehren, dateien, ausser)
    # Vorlagen-Verweise werden nicht geprueft, aber sichtbar gezaehlt: Wer sie
    # nicht sieht, haelt eine wachsende Zahl davon fuer "alles gut".
    vorlage_satz = (" Dazu %d Verweis(e) in der Form 'Vorlage §N' — nicht gegen die "
                    "eigene Zaehlung geprueft." % der_vorlage) if der_vorlage else ""
    # Die Ausnahme ist fuer FREMDE Zaehlungen da, und die treffen keinen Abschnitt.
    # Nimmt sie einen Verweis mit, der TRIFFT, hat sie einen echten Lehren-Verweis
    # verschluckt — dann ist das Muster zu weit, gleich wie viele uebrig bleiben.
    # Warum nicht "keiner uebrig": Das ist nicht entscheidbar. Genau so sieht ein
    # junges Repo aus, dessen Dateien nur fremde Zaehlungen tragen — die erste
    # Fassung dieser Regel machte es rot, ohne gruenen Ausweg (Blindpruefer
    # v1.17.1, gemessen). Die Zahl der treffenden ist dagegen eindeutig.
    if entfernt_treffend:
        sys.stderr.write(
            "Die Ausnahme %r nimmt %d Verweis(e) mit, die einen Abschnitt TREFFEN "
            "(von %d entfernten in %d Zeile(n)) — das Muster ist zu weit und legt "
            "die Pruefung teilweise still.\n"
            "Die Ausnahme ist fuer fremde Zaehlungen gedacht; die treffen keinen "
            "Abschnitt. Muster engen, bis diese Zahl 0 ist.\n"
            % (ausser.pattern, entfernt_treffend, entfernt, ausgenommen))
        return 1
    if funde:
        sys.stderr.write("Verweise ins Leere (%d von %d):\n  " % (len(funde), gesamt)
                         + "\n  ".join(funde) + "\n"
                         "Beim Uebernehmen einer Lehre werden auch die Verweise IN ihrem "
                         "Text auf die eigene Zaehlung umgeschrieben (abgleich.md, 2d); "
                         "ein Verweis in die Zaehlung der Vorlage steht als 'Vorlage §N'.\n"
                         + (vorlage_satz.strip() + "\n" if vorlage_satz else ""))
        # Auch der rote Pfad nennt die Ausnahme: Sonst sieht niemand, dass neben
        # den Funden noch Verweise weggefallen sind (Blindpruefer v1.17.1).
        if ausser is not None:
            sys.stderr.write("Ausnahme %r: %d Zeile(n) uebersprungen, dabei %d "
                             "Verweis(e) entfernt, davon %d treffende.\n"
                             % (ausser.pattern, ausgenommen, entfernt,
                                entfernt_treffend))
        return 1
    # Muster und Zahlen gehoeren in die MELDUNG: Ein Gate, das nur den Exit-Code
    # liest, saehe sonst nicht, was die Ausnahme weggenommen hat. Ein zu weites
    # Muster faellt seit v1.17.1 nicht mehr nur auf, es wird rot (oben); die
    # Zahlen hier tragen den Fall, der GRUEN bleiben darf: fremde Zaehlungen, die
    # keinen Abschnitt treffen. Auch dann gehoeren sie ins Abgleich-Issue, damit
    # eine wachsende Ausnahme auffaellt.
    print("Verweise gruen: %d Verweise in %d Datei(en), alle treffen einen Abschnitt "
          "von %s.%s%s Nicht geprueft: ob ein Verweis die GEMEINTE Lehre trifft."
          % (gesamt, len(dateien), lehren, vorlage_satz,
             (" Ausnahme %r hat %d Zeile(n) uebersprungen und dabei %d Verweis(e) "
              "entfernt, keinen treffenden — beide Zahlen gehoeren in das "
              "Abgleich-Issue."
              % (ausser.pattern, ausgenommen, entfernt)) if ausser is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
