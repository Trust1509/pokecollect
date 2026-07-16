from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Table, Text
from sqlalchemy.orm import relationship

from app.database import Base

# n:m Verknüpfung Sammlung ↔ Karte
# position = Slot-Index im Binder (0-basiert, darf Lücken haben → leere Slots)
collection_cards = Table(
    "collection_cards",
    Base.metadata,
    Column("collection_id", Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
    Column("card_id", Integer, ForeignKey("pokemon_cards.id", ondelete="CASCADE"), primary_key=True),
    Column("position", Integer, nullable=True),
)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    beschreibung = Column(Text, nullable=True)
    binder_layout = Column(Text, nullable=True, default="3x3")  # cols x rows, z.B. "3x3"
    binder_slots = Column(Integer, nullable=True)  # persistierte Binder-Größe (Slot-Kapazität inkl. leerer Seiten)
    erstellt_am = Column(DateTime, default=datetime.utcnow)
    # ── Set-Sammlung / Sammelziel (Issue #16, additiv) ───────────────────────
    # typ = "frei" (klassischer Binder) | "set_ziel" (Set-Sammlung mit Soll-Liste)
    typ = Column(Text, nullable=True, default="frei")
    ziel_set_id = Column(Text, nullable=True)        # TCGdex-Set-Id, z.B. "sv03"
    ziel_folierung = Column(Text, nullable=True)     # Regel-Folierung (NULL = egal)
    ziel_sprache = Column(Text, nullable=True)       # Regel-Sprache (NULL = egal)
    ziel_master_set = Column(Boolean, nullable=True, default=False)  # inkl. Secret Rares

    # backref "collections" wird auf PokemonCard gesetzt → card.collections
    cards = relationship(
        "PokemonCard",
        secondary=collection_cards,
        backref="collections",
        lazy="selectin",
    )


class CollectionSoll(Base):
    """
    Kuratierbare Soll-Liste einer Set-Sammlung (Issue #16): welche Katalog-Karte
    (mit welcher Folierung) zum Sammelziel gehört. Beim Anlegen automatisch aus
    tcgdex_catalog vorbefüllt, danach frei kuratierbar.
    Kein SQLAlchemy-Relationship nötig — das Löschen der Sammlung räumt die
    Slots per DB-CASCADE ab (ondelete).
    """
    __tablename__ = "collection_soll"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(
        Integer, ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    tcgdex_card_id = Column(Text, nullable=False, index=True)  # "sv03-125"
    soll_folierung = Column(Text, nullable=True)  # Slot-Override; NULL = Regel (ziel_folierung) gilt
    position = Column(Integer, nullable=True)     # Reihenfolge in der Soll-Ansicht
