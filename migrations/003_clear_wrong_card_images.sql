-- Migration 003: Falsche pokemon.com URLs entfernen
-- SWSH/XY-era deutsche Sets haben andere Kartennummern als die englischen Vorlagen
-- → falsche Karten wurden angezeigt → URLs löschen, Pokédex-Artwork als Fallback

UPDATE pokemon_cards
SET bild_karte_url = NULL
WHERE bild_karte_url IS NOT NULL
  AND (
    set_edition ILIKE '%(ASC)%'   -- Erhabene Helden (SWSH10 DE ≠ EN-Nummerierung)
    OR set_edition ILIKE '%(PFL)%' -- Fatale Flammen (SWSH11 DE ≠ EN-Nummerierung)
    OR set_edition ILIKE '%(BLK)%' -- Schwarze Blitze (SWSH7 DE ≠ EN-Nummerierung)
    OR set_edition ILIKE '%(BRS)%' -- Strahlende Gestirne (SWSH9 DE ≠ EN-Nummerierung)
    OR set_edition ILIKE '%(WHT)%' -- Weiße Flammen (SWSH9 DE ≠ EN-Nummerierung)
    OR set_edition ILIKE '%(MEG)%' -- Mega-Entwicklung (kein direktes EN-Äquivalent)
    OR set_edition ILIKE '%(LOR)%' -- Lost Origin (SWSH11)
    OR set_edition ILIKE '%(ASR)%' -- Astral Radiance (SWSH10)
    OR set_edition ILIKE '%(FST)%' -- Fusion Strike (SWSH8)
    OR set_edition ILIKE '%(EVS)%' -- Evolving Skies (SWSH7)
    OR set_edition ILIKE '%(BKT)%' -- BREAKthrough
    OR set_edition ILIKE '%(BKP)%' -- BREAKpoint
  );

SELECT COUNT(*) as bereinigt FROM pokemon_cards WHERE bild_karte_url IS NULL AND besessen = true;
