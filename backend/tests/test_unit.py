"""
Unit-Tests für pure Parser/Mapper (Issue #9) — laufen ohne Postgres/Netz:
- resolver._map_rarity + Confidence-Formel
- tcgdex.local_id_from_card_nr
- pricing.pick_cardmarket_price
- gemini._bbox / _quad
"""

from decimal import Decimal

import pytest

from app.services.pricing import pick_cardmarket_price
from app.services.scan.gemini import _bbox, _quad
from app.services.scan.resolver import _confidence, _map_rarity
from app.services.tcgdex import CardMarketPricing, local_id_from_card_nr


# ── resolver._map_rarity ─────────────────────────────────────────────────────

@pytest.mark.parametrize("raw, expected", [
    (None, None),
    ("", None),
    ("Common", "Common"),
    ("common", "Common"),
    ("  Rare Holo ", "Rare"),
    ("Special Illustration Rare", "Special Illustration Rare"),
    ("ACE SPEC RARE", "ACE SPEC Rare"),
    ("Völlig Unbekannt", "Völlig Unbekannt"),  # unbekannt → Durchreichen
])
def test_map_rarity(raw, expected):
    assert _map_rarity(raw) == expected


# ── resolver._confidence ─────────────────────────────────────────────────────

def test_confidence_exact_match_lifts_to_085():
    assert _confidence(None, matched=True, via_search=False, via_number=False,
                       uncertain_count=0) == 0.85


def test_confidence_keeps_higher_raw_value():
    assert _confidence(0.95, matched=True, via_search=False, via_number=False,
                       uncertain_count=0) == 0.95


def test_confidence_via_search_capped_at_075():
    assert _confidence(0.95, matched=True, via_search=True, via_number=False,
                       uncertain_count=0) == 0.75


def test_confidence_via_search_and_number():
    assert _confidence(None, matched=True, via_search=True, via_number=True,
                       uncertain_count=0) == 0.8


def test_confidence_no_match_capped_at_035():
    assert _confidence(0.9, matched=False, via_search=False, via_number=False,
                       uncertain_count=0) == 0.35


def test_confidence_dampened_by_uncertain_fields():
    # 0.85 * (1 - 0.1*2) = 0.68
    assert _confidence(None, matched=True, via_search=False, via_number=False,
                       uncertain_count=2) == 0.68


def test_confidence_clamped_to_zero():
    assert _confidence(None, matched=False, via_search=False, via_number=False,
                       uncertain_count=10) == 0.0


# ── tcgdex.local_id_from_card_nr ─────────────────────────────────────────────

@pytest.mark.parametrize("karten_nr, expected", [
    (None, None),
    ("", None),
    ("  ", None),
    ("007/091", "7"),
    ("195/091", "195"),
    ("000/091", "0"),
    ("TG01/TG30", "TG01"),
    ("42", "42"),
])
def test_local_id_from_card_nr(karten_nr, expected):
    assert local_id_from_card_nr(karten_nr) == expected


# ── pricing.pick_cardmarket_price ────────────────────────────────────────────

def test_price_none_pricing():
    assert pick_cardmarket_price(None, "Holo") is None


def test_price_holo_prefers_avg30_holo():
    cm = CardMarketPricing(avg30_holo=5.5, avg30=3.0)
    assert pick_cardmarket_price(cm, "Holo") == Decimal("5.5")


def test_price_holo_falls_back_to_avg30():
    cm = CardMarketPricing(avg30=3.0)
    assert pick_cardmarket_price(cm, "Holo") == Decimal("3.0")


def test_price_reverse_holo_counts_as_normal():
    cm = CardMarketPricing(avg30_holo=5.5, avg30=3.0)
    assert pick_cardmarket_price(cm, "Reverse Holo") == Decimal("3.0")


def test_price_normal_fallback_chain():
    assert pick_cardmarket_price(CardMarketPricing(avg7=2.5), None) == Decimal("2.5")
    assert pick_cardmarket_price(CardMarketPricing(trend=1.2), None) == Decimal("1.2")


def test_price_no_values():
    assert pick_cardmarket_price(CardMarketPricing(), "Normal") is None


# ── gemini._bbox / _quad ─────────────────────────────────────────────────────

def test_bbox_box2d_normalized_from_1000():
    # box_2d = [ymin, xmin, ymax, xmax] in 0..1000 → [x, y, w, h] in 0..1
    box = _bbox({"box_2d": [100, 200, 500, 600]})
    assert box == pytest.approx([0.2, 0.1, 0.4, 0.4])


def test_bbox_box2d_already_fractional():
    box = _bbox({"box_2d": [0.1, 0.2, 0.5, 0.6]})
    assert box == pytest.approx([0.2, 0.1, 0.4, 0.4])


def test_bbox_degenerate_box_rejected():
    assert _bbox({"box_2d": [500, 600, 500, 600]}) is None


def test_bbox_fallback_xywh_percent():
    assert _bbox({"bbox": [10, 20, 30, 40]}) == pytest.approx([0.1, 0.2, 0.3, 0.4])


def test_bbox_invalid():
    assert _bbox({}) is None
    assert _bbox({"box_2d": ["a", 1, 2, 3]}) is None
    assert _bbox({"bbox": [1, 2, 3]}) is None


def test_quad_normalized_from_1000():
    quad = _quad({"corners": [[0, 0], [1000, 0], [1000, 1000], [0, 1000]]})
    assert quad == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


def test_quad_already_fractional():
    pts = [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.1, 0.9]]
    assert _quad({"quad": pts}) == pts


def test_quad_invalid():
    assert _quad({}) is None
    assert _quad({"corners": [[0, 0], [1, 1]]}) is None
    assert _quad({"corners": [[0, 0], [1, 1], [2, 2], ["x", 3]]}) is None


# ── domain.pokedex.generation + extract_set_code (#7) ────────────────────────

from app.domain.pokedex import GEN_RANGES, generation
from app.services.card_image_service import extract_set_code


def test_generation_boundaries():
    assert generation(1) == 1
    assert generation(151) == 1
    assert generation(152) == 2
    assert generation(905) == 8
    assert generation(906) == 9
    assert generation(1025) == 9


def test_generation_unknown():
    assert generation(None) is None
    assert generation(0) is None
    assert generation(1026) is None


def test_gen_ranges_cover_pokedex_without_gaps():
    borders = sorted(GEN_RANGES.values())
    assert borders[0][0] == 1
    assert borders[-1][1] == 1025
    for (lo1, hi1), (lo2, _hi2) in zip(borders, borders[1:]):
        assert lo2 == hi1 + 1


def test_extract_set_code_variants():
    # Regex-Vertrag mit web/src/lib/utils.ts::setCodeFromEdition
    assert extract_set_code("Paldeas Schicksale (PAF)") == "PAF"
    assert extract_set_code("Pokémon 151 (SV03.5)") == "SV03.5"
    assert extract_set_code("ohne Kürzel") is None
    assert extract_set_code(None) is None
    assert extract_set_code("(zulang123456)") is None
