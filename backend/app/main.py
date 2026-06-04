import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.api.v1 import router as v1_router
from app.services.cron import start_scheduler

logging.basicConfig(level=logging.INFO)

# SV-Ära Set-Stammdaten (code, name, max_card_nr)
_SET_SEED = [
    ("SVI",  "Scharlachrot & Violett",      198),
    ("PAL",  "Entwicklungen in Paldea",     193),
    ("OBF",  "Obsidian Flammen",            197),
    ("MEW",  "Pokémon 151",                 165),
    ("151",  "Pokémon 151",                 165),
    ("PAR",  "Paradox Rift",                182),
    ("PAF",  "Paldeas Schicksale",           91),
    ("TEF",  "Temporale Kräfte",            162),
    ("TWM",  "Masken der Wandlung",         167),
    ("SFA",  "Schicksalsfunken",             65),
    ("SCR",  "Sternenglanz",                175),
    ("SSP",  "Surging Sparks",              191),
    ("PRE",  "Prismatische Entwicklungen",  131),
    ("JTG",  "Reisegefährten",             131),
    ("DRI",  "Ewige Rivalen",              None),
    ("SVE",  "SV Energie-Karten",           30),
]


def _seed_sets():
    from app.models.pokemon_set import PokemonSet
    db = SessionLocal()
    try:
        for code, name, max_nr in _SET_SEED:
            if not db.get(PokemonSet, code):
                db.add(PokemonSet(code=code, name=name, max_card_nr=max_nr))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _seed_sets()
    start_scheduler()
    yield


app = FastAPI(
    title="PokéCollect API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)

# Serve uploaded card images
app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")


@app.get("/health")
def health():
    return {"status": "ok"}
