from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class PokemonCard(Base):
    __tablename__ = "pokemon_cards"

    id = Column(Integer, primary_key=True, index=True)
    kartenname = Column(Text, nullable=False)
    pokedex_nr = Column(Integer, nullable=True, index=True)
    englischer_name = Column(Text, nullable=True)
    set_edition = Column(Text, nullable=True, index=True)
    karten_nr = Column(Text, nullable=True)
    seltenheit = Column(Text, nullable=True, index=True)
    kartenversion = Column(Text, nullable=True)
    folierung = Column(Text, nullable=True)
    sprache = Column(Text, nullable=True, default="DE", index=True)
    besessen = Column(Boolean, default=False, index=True)
    wunschliste = Column(Boolean, default=False, index=True)
    im_pokedex = Column(Boolean, default=False, index=True)  # Pokédex-Repräsentant für diese Pokédex-Nr.
    prioritaet = Column(Text, nullable=True)  # Chase, Hoch, Mittel, Niedrig
    wert_eur = Column(Numeric(8, 2), nullable=True)
    wert_aktualisiert = Column(DateTime, nullable=True)
    notizen = Column(Text, nullable=True)
    zustand = Column(Text, nullable=True)
    bild_pokedex_url = Column(Text, nullable=True)
    bild_karte_url = Column(Text, nullable=True)   # auto: TCGdex high.webp (vorher pokemon.com)
    bild_karte_pfad = Column(Text, nullable=True)
    bild_thumbnail_pfad = Column(Text, nullable=True)
    bild_original_pfad = Column(Text, nullable=True)   # ungeschnittenes Originalfoto
    # ── TCGdex-Referenz + Varianten (v0.7.0, additiv) ────────────────────────
    tcgdex_card_id = Column(Text, nullable=True, index=True)   # "swsh3-136"
    set_id = Column(Text, nullable=True)                       # "swsh3"
    dex_id = Column(Integer, nullable=True)                    # aus dexId[0]
    illustrator = Column(Text, nullable=True, index=True)      # aus TCGdex
    variants_normal = Column(Boolean, nullable=True)
    variants_reverse = Column(Boolean, nullable=True)
    variants_holo = Column(Boolean, nullable=True)
    variants_firstedition = Column(Boolean, nullable=True)
    hinzugefuegt_am = Column(DateTime, default=datetime.utcnow)
    aktualisiert_am = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    preis_historie = relationship("PreisHistorie", back_populates="karte", cascade="all, delete-orphan")


class PreisHistorie(Base):
    __tablename__ = "preis_historie"

    id = Column(Integer, primary_key=True, index=True)
    karte_id = Column(Integer, ForeignKey("pokemon_cards.id", ondelete="CASCADE"), index=True)
    wert_eur = Column(Numeric(8, 2))
    quelle = Column(Text, nullable=True)
    erfasst_am = Column(DateTime, default=datetime.utcnow, index=True)

    karte = relationship("PokemonCard", back_populates="preis_historie")
