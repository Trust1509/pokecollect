"""
Binder-Slots einer Sammlung: `collection_cards.position` ist ein Slot-Index
(0-basiert, Lücken erlaubt → leere Slots). Neue Karten füllen den nächsten
WIRKLICH freien Slot, ohne bestehende Positionen zu verschieben — der Binder
ist positionsbasiert, nicht kompaktiert (Issue #30).

Eine Routine je Sache (Kredo DRY): genutzt vom Sammlungs-Router, vom
Scan-Commit und von der Katalog-Übernahme — kein doppelter Positions-Code.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.collection import collection_cards


def next_free_position(db: Session, collection_id: int) -> int:
    """Kleinster nicht belegter Slot-Index (0-basiert) einer Sammlung.

    Füllt Lücken von vorne auf und lässt bestehende Karten unangetastet. Nie
    ``None`` zurück — so kann kein positionsloser Eintrag entstehen, der die
    Binder-Anzeige zum Kompaktieren zwingen würde (Issue #30).
    """
    used = {
        p
        for p in db.scalars(
            select(collection_cards.c.position)
            .where(collection_cards.c.collection_id == collection_id)
            .where(collection_cards.c.position.isnot(None))
        ).all()
    }
    pos = 0
    while pos in used:
        pos += 1
    return pos
