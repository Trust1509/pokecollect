from sqlalchemy import Column, Integer, Text

from app.database import Base


class PokemonSet(Base):
    __tablename__ = "pokemon_sets"

    code = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    max_card_nr = Column(Integer, nullable=True)
