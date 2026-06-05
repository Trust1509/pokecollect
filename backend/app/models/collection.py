from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, Text
from sqlalchemy.orm import relationship

from app.database import Base

# n:m Verknüpfung Sammlung ↔ Karte
collection_cards = Table(
    "collection_cards",
    Base.metadata,
    Column("collection_id", Integer, ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
    Column("card_id", Integer, ForeignKey("pokemon_cards.id", ondelete="CASCADE"), primary_key=True),
)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    beschreibung = Column(Text, nullable=True)
    erstellt_am = Column(DateTime, default=datetime.utcnow)

    # backref "collections" wird auf PokemonCard gesetzt → card.collections
    cards = relationship(
        "PokemonCard",
        secondary=collection_cards,
        backref="collections",
        lazy="selectin",
    )
