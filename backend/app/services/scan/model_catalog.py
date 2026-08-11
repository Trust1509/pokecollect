"""
Vorschlagslisten für die Lese-Modell-Auswahl (Scan-Stufe B, Issue #57).

Damit man sich den Modellnamen nicht vertippt, bietet das UI eine Combobox
(tippen ODER auswählen). Die Vorschläge kommen von hier:

- **OpenRouter** hat einen ÖFFENTLICHEN `/models`-Endpunkt (kein Key nötig), der
  pro Modell die Eingabe-Modalitäten ausweist → wir filtern auf bild-fähige
  Modelle und liefern sie live (kurz gecacht). Fällt der Abruf aus, greift eine
  kuratierte Kurzliste.
- **OpenAI/Gemini** haben keine gleichwertige öffentliche, bild-gefilterte Liste
  (OpenAIs `/models` braucht den Key und führt keine Vision-Metadaten) → wir
  liefern kuratierte, bild-fähige Kurzlisten. Das Feld bleibt frei tippbar.
"""

from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger(__name__)

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_CACHE_TTL = 3600.0  # 1 h – die Liste ändert sich selten

# Prozess-lokaler Cache: {provider: (monotonic_ts, models)}. Flüchtig, Reset bei
# Neustart – bewusst kein DB-Wert.
_cache: dict[str, tuple[float, list[dict]]] = {}

# Kuratierte, bild-fähige Vorschläge (frei überschreibbar im Eingabefeld).
_CURATED: dict[str, list[dict]] = {
    "openai": [
        {"id": "gpt-4o-mini", "name": "GPT-4o mini (günstig, schnell)"},
        {"id": "gpt-4o", "name": "GPT-4o"},
        {"id": "gpt-4.1-mini", "name": "GPT-4.1 mini"},
        {"id": "gpt-4.1", "name": "GPT-4.1"},
    ],
    "gemini": [
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash (Standard)"},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
    ],
    "openrouter": [
        {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
        {"id": "openai/gpt-4o-mini", "name": "GPT-4o mini"},
        {"id": "qwen/qwen-2.5-vl-72b-instruct", "name": "Qwen2.5-VL 72B"},
    ],
}


def _is_vision(model: dict) -> bool:
    """Bild-fähig, wenn die Eingabe-Modalitäten „image" enthalten."""
    arch = model.get("architecture") or {}
    mods = arch.get("input_modalities") or []
    return "image" in mods or "image" in (arch.get("modality") or "")


async def list_models(provider: str, *, transport=None) -> dict:
    """{"models": [{"id","name"}], "source": "live"|"curated"} für einen Provider.

    `transport` ist ein optionaler httpx-Transport für Tests.
    """
    provider = (provider or "").lower()
    if provider == "openrouter":
        return await _openrouter_models(transport=transport)
    return {"models": _CURATED.get(provider, []), "source": "curated"}


async def _openrouter_models(*, transport=None) -> dict:
    now = time.monotonic()
    cached = _cache.get("openrouter")
    if cached and (now - cached[0]) < _CACHE_TTL:
        return {"models": cached[1], "source": "live"}
    try:
        async with httpx.AsyncClient(timeout=15.0, transport=transport) as client:
            resp = await client.get(
                _OPENROUTER_MODELS_URL, headers={"User-Agent": "PokeCollect/1.0"})
        resp.raise_for_status()
        data = resp.json().get("data", [])
        models = sorted(
            ({"id": m["id"], "name": m.get("name") or m["id"]}
             for m in data if m.get("id") and _is_vision(m)),
            key=lambda m: m["id"],
        )
        if models:
            _cache["openrouter"] = (now, models)
            return {"models": models, "source": "live"}
        log.warning("OpenRouter lieferte keine bild-fähigen Modelle – kuratierte Liste.")
    except Exception as exc:
        log.warning("OpenRouter-Modellliste nicht abrufbar (%s) – kuratierte Liste.",
                    type(exc).__name__)
    return {"models": _CURATED["openrouter"], "source": "curated"}
