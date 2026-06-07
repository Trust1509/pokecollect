from sqlalchemy import Column, Integer, Text

from app.database import Base


class PokemonSet(Base):
    __tablename__ = "pokemon_sets"

    # `code` = aufgedrucktes PTCGO-Kürzel (PAF, OBF, …) – Primärschlüssel,
    # treibt den Set-Picker und steckt im `set_edition`-Feld der Karten.
    code = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)            # deutscher Anzeigename
    max_card_nr = Column(Integer, nullable=True)   # reguläre Obergrenze (ohne Secret Rares)

    # ── TCGdex-Anreicherung (additiv, befüllt durch Set-Sync) ────────────────
    set_id = Column(Text, nullable=True, index=True)   # stabile TCGdex-ID, z.B. "sv04.5"
    name_en = Column(Text, nullable=True)              # englischer Name
    series_id = Column(Text, nullable=True)            # "sv", "swsh", …
    card_count_official = Column(Integer, nullable=True)
    card_count_total = Column(Integer, nullable=True)
    logo_url = Column(Text, nullable=True)
    symbol_url = Column(Text, nullable=True)
