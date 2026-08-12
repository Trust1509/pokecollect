"""
Katalogzeile zu einer Karten-Referenz finden — case-tolerant (v1.7.3).

Der Scan-Resolver liefert TCGdex-IDs klein („me03-029"), der JP-Katalog führt
sie groß („ME03-029", aus den ja-Set-Details); West-IDs sind klein. Ein nackter
Primärschlüssel-Lookup verfehlt deshalb scan-committete JP-Karten — und damit
den $→€-Preis-Fallback, die $-Anzeige im Detail und den EN-Namen. Erst exakt
(Index), dann case-insensitiv (nur im Fehlfall, eine Zusatzabfrage).

Bewusst ein Leaf-Modul (nur Model-Import) — wird von pricing, cards-API und
card_creation geteilt, ohne Importzyklen zu riskieren.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.tcgdex_catalog import TcgdexCatalog


def catalog_row_for(db: Session, card_id: Optional[str]) -> Optional[TcgdexCatalog]:
    """
    Katalogzeile zur TCGdex-Karten-ID; None ohne Referenz/Zeile.

    Der upper()-Fallback nutzt den Funktionsindex ix_tcgdex_catalog_card_id_upper
    (Light-Migration) und ordnet deterministisch — sollten je zwei case-
    verschiedene Zeilen existieren (heute nur theoretisch: West klein, JP groß,
    unterschiedliche Set-Schemata), gewinnt stabil die alphabetisch erste statt
    Planer-Zufall (Panel-Fund).
    """
    if not card_id:
        return None
    row = db.get(TcgdexCatalog, card_id)
    if row is not None:
        return row
    return db.scalars(
        select(TcgdexCatalog)
        .where(func.upper(TcgdexCatalog.card_id) == card_id.upper())
        .order_by(TcgdexCatalog.card_id)
    ).first()
