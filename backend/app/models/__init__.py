# Alle Models hier importieren, damit Base.metadata.create_all() beim Start
# garantiert jede Tabelle kennt (unabhängig von Import-Seiteneffekten der Router).
from app.models.card import PokemonCard, PreisHistorie
from app.models.setting import AppSetting  # noqa: F401
from app.models.pokemon_set import PokemonSet  # noqa: F401
from app.models.collection import Collection, CollectionSoll, collection_cards  # noqa: F401
from app.models.gemini_usage import GeminiUsage  # noqa: F401
from app.models.tcgdex_catalog import TcgdexCatalog  # noqa: F401
