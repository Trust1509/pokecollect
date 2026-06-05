from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, Text
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

    # backref "collections" wird auf PokemonCard gesetzt → card.collections
    cards = relationship(
        "PokemonCard",
        secondary=collection_cards,
        backref="collections",
        lazy="selectin",
    )
