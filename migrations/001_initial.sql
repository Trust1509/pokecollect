-- PokéCollect – initiales Datenbankschema
-- Ausführen: psql -U pokecollect -d pokecollect -f 001_initial.sql

CREATE TABLE IF NOT EXISTS pokemon_cards (
    id                  SERIAL PRIMARY KEY,
    kartenname          TEXT NOT NULL,
    -- Deutscher offizieller Name (z.B. "Glumanda")
    -- Sonderkarten: z.B. "Team Rockets Arbok", "Erikas Knofensa"

    pokedex_nr          INTEGER,
    -- 1-1025, NULL für Trainer/Energie-Karten

    englischer_name     TEXT,

    set_edition         TEXT,
    -- z.B. "Erhabene Helden (ASC)"

    karten_nr           TEXT,
    -- z.B. "022/217"

    seltenheit          TEXT,
    -- Common | Uncommon | Rare | Holo Rare | Double Rare |
    -- Ultra Rare | Secret Rare | Full Art | Illustration Rare |
    -- Special Illustration Rare | Rainbow Rare | Hyper Rare | Promo
    CONSTRAINT seltenheit_check CHECK (seltenheit IN (
        'Common', 'Uncommon', 'Rare', 'Holo Rare', 'Double Rare',
        'Ultra Rare', 'Secret Rare', 'Full Art', 'Illustration Rare',
        'Special Illustration Rare', 'Rainbow Rare', 'Hyper Rare', 'Promo'
    )),

    kartenversion       TEXT,
    -- Normal | Full Art | Special Art | Rainbow | Gold |
    -- Shiny | Illustration Rare | Special Illustration Rare
    CONSTRAINT kartenversion_check CHECK (kartenversion IN (
        'Normal', 'Full Art', 'Special Art', 'Rainbow', 'Gold',
        'Shiny', 'Illustration Rare', 'Special Illustration Rare'
    )),

    folierung           TEXT,
    -- Normal | Holo | Cosmos Holo | Reverse Holo | ...
    CONSTRAINT folierung_check CHECK (folierung IN (
        'Normal', 'Holo', 'Cosmos Holo', 'Reverse Holo',
        'Reverse Holo – Sterne', 'Reverse Holo – Energie',
        'Reverse Holo – Pokéball', 'Reverse Holo – Masterball',
        'Reverse Holo – Team Rocket R', 'Reverse Holo – Muster',
        'Etched Holo', 'Bubble Holo'
    )),

    sprache             TEXT DEFAULT 'DE',
    CONSTRAINT sprache_check CHECK (sprache IN ('DE', 'EN', 'CN', 'JP', 'FR', 'ES', 'IT')),

    besessen            BOOLEAN DEFAULT FALSE,

    wert_eur            DECIMAL(8,2),
    wert_aktualisiert   TIMESTAMP,

    notizen             TEXT,

    zustand             TEXT,
    CONSTRAINT zustand_check CHECK (zustand IN (
        'Mint', 'Near Mint', 'Excellent', 'Good', 'Played'
    )),

    bild_pokedex_url    TEXT,
    bild_karte_pfad     TEXT,
    bild_thumbnail_pfad TEXT,

    hinzugefuegt_am     TIMESTAMP DEFAULT NOW(),
    aktualisiert_am     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pokedex_nr   ON pokemon_cards(pokedex_nr);
CREATE INDEX IF NOT EXISTS idx_besessen     ON pokemon_cards(besessen);
CREATE INDEX IF NOT EXISTS idx_set_edition  ON pokemon_cards(set_edition);
CREATE INDEX IF NOT EXISTS idx_sprache      ON pokemon_cards(sprache);
CREATE INDEX IF NOT EXISTS idx_seltenheit   ON pokemon_cards(seltenheit);

CREATE TABLE IF NOT EXISTS preis_historie (
    id          SERIAL PRIMARY KEY,
    karte_id    INTEGER REFERENCES pokemon_cards(id) ON DELETE CASCADE,
    wert_eur    DECIMAL(8,2),
    quelle      TEXT,
    erfasst_am  TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_preis_karte_id ON preis_historie(karte_id);
CREATE INDEX IF NOT EXISTS idx_preis_erfasst  ON preis_historie(erfasst_am);

-- Trigger: aktualisiert_am automatisch setzen
CREATE OR REPLACE FUNCTION update_aktualisiert_am()
RETURNS TRIGGER AS $$
BEGIN
    NEW.aktualisiert_am = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_pokemon_cards_aktualisiert
    BEFORE UPDATE ON pokemon_cards
    FOR EACH ROW EXECUTE FUNCTION update_aktualisiert_am();
