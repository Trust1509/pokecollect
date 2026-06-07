from sqlalchemy import Boolean, Column, Integer, Text

from app.database import Base


class TcgdexCatalog(Base):
    """
    Lokaler Spiegel aller TCGdex-Karten (Nachschlagewerk).
    Zählt NICHT zu besessenen/Pokédex-Karten und in keine Statistik.
    Read-only; per Stern auf die Wunschliste / in Sammlungen übernehmbar.
    """
    __tablename__ = "tcgdex_catalog"

    card_id = Column(Text, primary_key=True)            # "swsh3-136"
    set_id = Column(Text, index=True)                   # "swsh3"
    set_code = Column(Text, index=True, nullable=True)  # PTCGO-Kürzel (aus pokemon_sets)
    set_name = Column(Text, nullable=True)              # deutscher Set-Name
    local_id = Column(Text, nullable=True)              # aufgedruckte Nr. (String)
    local_id_num = Column(Integer, index=True, nullable=True)  # numerisch (Sortierung)
    name = Column(Text, index=True, nullable=True)      # DE (Fallback EN)
    name_en = Column(Text, index=True, nullable=True)
    dex_id = Column(Integer, index=True, nullable=True)
    rarity = Column(Text, nullable=True)
    illustrator = Column(Text, index=True, nullable=True)
    category = Column(Text, nullable=True)
    image = Column(Text, nullable=True)                 # Basis-URL
    image_url = Column(Text, nullable=True)             # high.webp
    variants_normal = Column(Boolean, nullable=True)
    variants_reverse = Column(Boolean, nullable=True)
    variants_holo = Column(Boolean, nullable=True)
    variants_firstedition = Column(Boolean, nullable=True)
    enriched = Column(Boolean, default=False, index=True)  # Volldetails (Illustrator etc.) geladen?
    updated = Column(Text, nullable=True)               # TCGdex-Zeitstempel
