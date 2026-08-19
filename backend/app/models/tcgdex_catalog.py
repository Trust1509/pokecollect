from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, Text

from app.database import Base


class TcgdexCatalog(Base):
    """
    Lokaler Spiegel aller TCGdex-Karten (Nachschlagewerk).
    Zählt NICHT zu besessenen/Pokédex-Karten und in keine Statistik.
    Read-only; per Stern auf die Wunschliste / in Sammlungen übernehmbar.
    """
    __tablename__ = "tcgdex_catalog"

    card_id = Column(Text, primary_key=True)            # "swsh3-136"
    # Region der Karte: "west" (EN+DE, dieselbe Karte) oder eine asiatische
    # Region wie "ja" (eigene Sets/Karten). Treibt den Katalog-Regionsfilter
    # (#33-Folge, erweiterbar für "ko"/"zh"). Default „west" für Altbestand.
    region = Column(Text, index=True, nullable=False, default="west", server_default="west")
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
    # Woher das Bild stammt: "tcgdex" (Standard) oder "tcgplayer" (JP-Fallback,
    # Epic #41). Für die Quellen-Kennzeichnung in der Detailansicht (Slice 6).
    image_source = Column(Text, nullable=True)
    # Lokal gecachte Preise (Epic #41 #45), im täglichen Sync gefüllt: € aus
    # Cardmarket (TCGdex), $ aus TCGdex (West) bzw. TCGCSV/TCGplayer (JP). Der
    # *_updated-Zeitstempel (ISO-String) zeigt den Datenstand je Währung.
    price_eur = Column(Numeric(10, 2), nullable=True)
    price_usd = Column(Numeric(10, 2), nullable=True)
    price_eur_updated = Column(Text, nullable=True)
    price_usd_updated = Column(Text, nullable=True)
    # #66: EIGENER Stempel für den rollierenden €-Repass — wann WIR zuletzt bei
    # TCGdex nachgesehen haben. NICHT dasselbe wie price_eur_updated: das ist
    # der Stand DER QUELLE (TCGdex liefert ihn als cm.updated mit) und würde,
    # nach ihm rotiert, bei einer seit Monaten unveränderten Quelle täglich
    # wieder ganz vorne stehen (Hunger-Effekt für andere Zeilen). NULL heißt
    # „noch nie im Repass geprüft" — sortiert per NULLS FIRST vor jedem Datum.
    price_eur_checked = Column(DateTime, nullable=True)
    # Varianten-$-Preise (#63): Subtypen des Basisprodukts (Holofoil/Reverse
    # Holofoil) + Muster-PRODUKTE („(Poke Ball Pattern)"/„(Master Ball Pattern)",
    # eigene TCGplayer-Produkte je Karte). Datenstand teilt price_usd_updated.
    price_usd_holo = Column(Numeric(10, 2), nullable=True)
    price_usd_reverse = Column(Numeric(10, 2), nullable=True)
    price_usd_pokeball = Column(Numeric(10, 2), nullable=True)
    price_usd_masterball = Column(Numeric(10, 2), nullable=True)
    variants_normal = Column(Boolean, nullable=True)
    variants_reverse = Column(Boolean, nullable=True)
    variants_holo = Column(Boolean, nullable=True)
    variants_firstedition = Column(Boolean, nullable=True)
    enriched = Column(Boolean, default=False, index=True)  # Volldetails (Illustrator etc.) geladen?
    updated = Column(Text, nullable=True)               # TCGdex-Zeitstempel
