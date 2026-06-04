-- Migration 002: Automatische Kartenbilder (pokemon.com)
-- Ausführen mit:
--   docker exec -i $(docker ps -qf name=pokecollect-db) psql -U pokecollect -d pokecollect < migrations/002_add_bild_karte_url.sql

ALTER TABLE pokemon_cards
    ADD COLUMN IF NOT EXISTS bild_karte_url TEXT;

COMMENT ON COLUMN pokemon_cards.bild_karte_url IS
    'Automatisch generierte pokemon.com Karten-URL (HEAD-verifiziert). Wird vom Backend befüllt.';
