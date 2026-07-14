"""
Domain-Service: besessene Karte anlegen — EINE Routine für alle Anlege-Pfade
(POST /cards, POST /scan/commit, Katalog-Übernahme), Kredo „eine Routine je
Sache" (Issue #4).

Kapselt die Pokédex-Invarianten:
- **Platzhalter-Adoption:** existiert eine nicht-besessene Karte derselben
  Pokédex-Nr., wird sie übernommen statt ein Duplikat anzulegen.
- **Auto-im_pokedex (exklusiv):** die Karte wird Pokédex-Vertreter genau dann,
  wenn noch keine andere Karte dieser Pokédex-Nr. das Flag trägt.
- **Bild-Fetch-Trigger:** TCGdex-Bild + Metadaten werden nach der Response im
  Hintergrund nachgeladen (sofern der Aufrufer BackgroundTasks mitgibt).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import BackgroundTasks
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.card import PokemonCard
from app.services.card_image_service import (
    apply_card_to_model,
    apply_species_image,
    fetch_tcgdex_card,
    fetch_tcgdex_card_by_name,
    resolve_set_id,
)

log = logging.getLogger(__name__)


async def _trigger_image_fetch(card_id: int):
    """
    Holt TCGdex-Daten (Bild high.webp, dexId, Varianten, tcgdex_card_id) im
    Hintergrund und speichert sie. Eigenes Foto / manuelle URL behalten Vorrang
    fürs Anzeigen – die Metadaten (Varianten/dexId) werden trotzdem gesetzt.
    Läuft als BackgroundTask nach der Response → eigene Session.
    """
    db = SessionLocal()
    try:
        card = db.get(PokemonCard, card_id)
        if not card or not card.besessen:
            return
        set_id = card.set_id or resolve_set_id(db, card.set_edition)
        # Exakte Auflösung über Set + aufgedruckte Nummer (sofern Nummer da).
        tc = await fetch_tcgdex_card(set_id, card.karten_nr, card.sprache) if set_id else None
        matched_exact = tc is not None
        # Issue 2: keine Nummer/kein Treffer → Fallback über Namenssuche
        # (wahrscheinliches Bild der gleichen Spezies).
        if tc is None:
            tc = await fetch_tcgdex_card_by_name(card.kartenname, card.sprache, set_id=set_id)
        if tc is None:
            return
        overwrite = not (card.bild_karte_pfad or card.bild_pokedex_url)
        # Treffer im bekannten Set gilt als exakt → volle Metadaten; sonst nur
        # Bild + Pokédex-Nr., um keine falsche konkrete Karte zu erzwingen.
        exact = matched_exact or bool(set_id and tc.set and tc.set.id == set_id)
        if exact:
            apply_card_to_model(card, tc, overwrite_image=overwrite)
        else:
            apply_species_image(card, tc, overwrite_image=overwrite)
        db.commit()
    finally:
        db.close()


def create_owned_card(
    db: Session,
    fields: dict,
    *,
    background_tasks: Optional[BackgroundTasks] = None,
    commit: bool = True,
) -> PokemonCard:
    """
    Legt eine besessene Karte an (oder adoptiert den Platzhalter) und wendet
    die Pokédex-Invarianten an.

    fields: Spaltenwerte für PokemonCard. `besessen` wird auf True erzwungen,
    `im_pokedex` wird ignoriert und exklusiv berechnet (Vertreter nur, wenn
    noch keiner existiert). background_tasks: wenn gesetzt, wird der
    TCGdex-Bild-Fetch nach der Response angestoßen. commit=False lässt die
    Transaktion offen (Batch-Aufrufer committen selbst); geflusht wird immer.
    """
    fields = dict(fields)
    fields["besessen"] = True
    fields.pop("im_pokedex", None)  # wird unten exklusiv berechnet
    fields.setdefault("wunschliste", False)
    pokedex_nr = fields.get("pokedex_nr")

    card: Optional[PokemonCard] = None
    if pokedex_nr:
        # Platzhalter-Adoption: vorhandene nicht-besessene Zeile übernehmen
        card = db.scalars(
            select(PokemonCard)
            .where(PokemonCard.pokedex_nr == pokedex_nr)
            .where(PokemonCard.besessen == False)  # noqa: E712
        ).first()
    if card is not None:
        for field, value in fields.items():
            setattr(card, field, value)
        if "bild_karte_url" not in fields:
            card.bild_karte_url = None  # wird neu abgerufen
    else:
        card = PokemonCard(**fields)
        db.add(card)
    db.flush()  # ID vergeben, Flag-Abfrage sieht den aktuellen Stand

    # Auto-Pokédex-Flag, exklusiv: nur wenn kein anderer Vertreter existiert
    if card.pokedex_nr and not card.im_pokedex:
        existing_flag = db.scalar(
            select(func.count(PokemonCard.id))
            .where(PokemonCard.pokedex_nr == card.pokedex_nr)
            .where(PokemonCard.im_pokedex == True)  # noqa: E712
            .where(PokemonCard.id != card.id)
        )
        if existing_flag == 0:
            card.im_pokedex = True

    if commit:
        db.commit()
        db.refresh(card)
    else:
        db.flush()

    if background_tasks is not None:
        background_tasks.add_task(_trigger_image_fetch, card.id)
    return card
