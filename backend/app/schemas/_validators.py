"""
Geteilte Eingabe-Validatoren für die Schreib-Schemas (#55).

Hintergrund: Der wöchentliche Schemathesis-Lauf fand 500er statt 4xx — beide
Ursachen sind Klassen, keine Einzelfälle:

1. **Steuerzeichen im Text.** PostgreSQL-`text` kann kein NUL-Byte (0x00)
   speichern; der Treiber wirft, die Anfrage endet als 500. Andere C0-Zeichen
   sind in Kartennamen ebenso wenig sinnvoll. Zeilenumbruch/Tab bleiben erlaubt
   (Notizen).
2. **Explizites `null` auf Pflichtfeldern.** Optional-Felder mit Default None
   können „weggelassen" und „ausdrücklich null" nicht am Typ unterscheiden;
   ein `null` landete per setattr auf einer NOT-NULL-Spalte → IntegrityError.
   Pydantic validiert Defaults NICHT (`validate_default=False`), darum feuert
   `reject_explicit_null` nur bei tatsächlich mitgeschicktem `null` —
   „weglassen = unverändert" bleibt also unangetastet.

Anwendung in den Schemas:
    _v_ctrl = field_validator("*", mode="before")(reject_control_chars)
    _v_null = field_validator("name", "besessen")(reject_explicit_null)
"""

from __future__ import annotations

import re
from typing import Any

# C0-Steuerzeichen ohne \t (09), \n (0A), \r (0D) + DEL.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


# Grenzen der Rekursion (Panel-Funde): ohne Tiefenlimit sprengte ein tief
# verschachteltes Array den Stack (RecursionError → 500 — genau die Klasse, die
# dieses Modul beseitigen soll); ohne Längenlimit liefe die Prüfung erst durch
# eine Millionen-Liste, bevor die max_length-Kappe greift.
_MAX_TIEFE = 12
_MAX_ELEMENTE = 10_000


def reject_control_chars(v: Any, _tiefe: int = 0) -> Any:
    """
    Strings mit Steuerzeichen ablehnen (422 statt 500 aus der DB). Rekursiv
    über Listen UND Dicts (Schlüssel wie Werte) — ein künftiges Freiform-Feld
    soll nicht still an der Prüfung vorbeilaufen.

    NUR an EINGABE-Schemas hängen: an einer gemeinsamen Basisklasse würde die
    Sperre auch Antworten prüfen und Bestandsdaten unlesbar machen (Panel-Fund).
    Serverseitig erzeugte Werte (OCR-/LLM-Text) NICHT hierdurch schicken —
    dort gehört `strip_control_chars` hin, sonst stürzt der Scan ab.
    """
    if _tiefe > _MAX_TIEFE:
        raise ValueError("Struktur zu tief verschachtelt")
    if isinstance(v, str) and _CONTROL_CHARS.search(v):
        raise ValueError("Text enthält unerlaubte Steuerzeichen")
    if isinstance(v, (list, tuple, set)):
        if len(v) > _MAX_ELEMENTE:
            raise ValueError("Liste zu lang")
        for item in v:
            reject_control_chars(item, _tiefe + 1)
    elif isinstance(v, dict):
        if len(v) > _MAX_ELEMENTE:
            raise ValueError("Objekt zu groß")
        for key, item in v.items():
            reject_control_chars(key, _tiefe + 1)
            reject_control_chars(item, _tiefe + 1)
    return v


def strip_control_chars(v: Any) -> Any:
    """
    Steuerzeichen ENTFERNEN statt abzulehnen — für serverseitig erzeugte Texte
    (Tesseract-OCR liefert z. B. regelmäßig Seitenvorschübe, LLM-JSON kann
    `\\u0007` enthalten). Ablehnen wäre dort falsch: es gibt keinen Client, den
    man korrigieren könnte — der Scan würde nur abstürzen (Panel-Fund).
    """
    if isinstance(v, str):
        return _CONTROL_CHARS.sub("", v)
    return v


def reject_explicit_null(v: Any) -> Any:
    """
    Ausdrückliches `null` auf einem Pflichtfeld ablehnen. Feuert NICHT, wenn
    das Feld weggelassen wurde (Pydantic validiert Defaults nicht) — die
    „weglassen = unverändert"-Semantik der Update-Schemas bleibt erhalten.
    """
    if v is None:
        raise ValueError("Feld darf nicht null sein (weglassen = unverändert)")
    return v
