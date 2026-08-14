from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Table,
    Text,
    func,
)

from app.database import Base

# n:m Verknüpfung Sealed-Produkt ↔ Set (Issue #35, Spec-Änderung 2026-07-26):
# ein Bundle/eine Kollektion spannt oft mehrere Sets → 0..N set_codes je Produkt.
# set_code ist bewusst freier Text (aufgedrucktes Kürzel wie "OBF"), KEIN FK auf
# pokemon_sets — so bleibt die Zuordnung robust, auch wenn ein Set (noch) nicht
# als Stammdatensatz existiert. Manuelle Pflege im Router (wie collection_cards).
sealed_product_sets = Table(
    "sealed_product_sets",
    Base.metadata,
    Column(
        "sealed_product_id",
        Integer,
        ForeignKey("sealed_products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("set_code", Text, primary_key=True),
)

# Ausdrucks-Index für den Set-Filter (Härtung #38): der zusammengesetzte PK
# beginnt mit sealed_product_id, taugt also nicht als Set-Lookup. Der Filter
# vergleicht case-insensitiv über upper(set_code) (Altbestand kann gemischt
# geschrieben sein) — ein Plain-Index auf set_code würde dafür NICHT greifen,
# darum ein Ausdrucks-Index auf upper(set_code).
Index(
    "ix_sealed_product_sets_set_code_upper",
    func.upper(sealed_product_sets.c.set_code),
)


class SealedProduct(Base):
    """
    Ein versiegeltes (oder geöffnetes) Sammelprodukt — Booster, Display, ETB,
    Tin, Blister, Bundle … (Issue #35). Eigene Entität, NICHT in pokemon_cards.
    Jedes physische Stück ist ein eigener Datensatz (KEIN Mengenfeld) — so hat
    jedes Stück seinen eigenen Kaufpreis/Zustand. wert_eur wird MANUELL gepflegt
    (keine TCGdex-Preisquelle für Sealed).
    """

    __tablename__ = "sealed_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    # Fester Katalog (schemas/sealed.py::SEALED_TYP_VALUES): Booster, Display,
    # ETB, Tin, Blister, Bundle, Sonstiges. Als Text gehalten (Label-Map im UI).
    typ = Column(Text, nullable=True, index=True)
    # Versiegelt / Geöffnet / Beschädigt (SEALED_ZUSTAND_VALUES).
    zustand = Column(Text, nullable=True, index=True)
    # Persönlicher Einstand (analog Karten #26): beide optional.
    kaufpreis_eur = Column(Numeric(8, 2), nullable=True)
    kaufdatum = Column(Date, nullable=True)
    # Aktueller Wert. Mit Katalog-Verknüpfung (#46) täglich automatisch aus dem
    # TCGplayer-$ × EZB-Kurs gesetzt (Owner-Entscheid 2026-08-13); ohne
    # Verknüpfung manuell gepflegt wie bisher.
    wert_eur = Column(Numeric(8, 2), nullable=True)
    wert_aktualisiert = Column(DateTime, nullable=True)   # Stand des Auto-Werts
    # Verknüpfung in den Sealed-Katalog (#46): TCGplayer-productId. NULL =
    # Freitext-Produkt (bleibt manuell bewertet).
    tcgplayer_product_id = Column(Integer, nullable=True, index=True)
    bild_pfad = Column(Text, nullable=True)
    bild_thumbnail_pfad = Column(Text, nullable=True)
    # Produktbild vom TCGplayer-CDN (aus dem Katalog, #46) — eigenes Foto
    # (bild_pfad) hat in der Anzeige Vorrang.
    bild_url = Column(Text, nullable=True)
    notizen = Column(Text, nullable=True)
    hinzugefuegt_am = Column(DateTime, default=datetime.utcnow)


class SealedCatalog(Base):
    """
    TCGplayer-Sealed-Katalog (#46): Nachschlagewerk für den Produkt-Picker —
    echte Produkte statt Freitext, mit CDN-Bild und $-Marktpreis. Wird im
    täglichen Katalog-Sync mitbefüllt (dieselben Produkt-Abrufe wie die
    Karten-Preise, Kat. 3 West + Kat. 85 JP — null Zusatz-Requests).
    Read-only fürs UI; kein FK von sealed_products (lose Kopplung wie
    tcgdex_catalog ↔ pokemon_cards).
    """

    __tablename__ = "sealed_catalog"

    product_id = Column(Integer, primary_key=True)          # TCGplayer productId
    region = Column(Text, nullable=False, default="west", index=True)  # west|ja
    set_code = Column(Text, index=True, nullable=True)      # Set der Gruppe (z. B. WHT)
    set_id = Column(Text, nullable=True)
    name = Column(Text, nullable=False, index=True)
    image_url = Column(Text, nullable=True)                 # TCGplayer-CDN (hires)
    price_usd = Column(Numeric(10, 2), nullable=True)       # Marktpreis, täglich
    price_usd_updated = Column(Text, nullable=True)         # ISO-Datenstand
