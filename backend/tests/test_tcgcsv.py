"""
TCGCSV-Matching-Helfer (Epic #41, Slice 1) — pure, netzfrei.
Set-Code aus Gruppenname, Kartennummer aus extendedData, CDN-Bild-URL hochskalieren.
"""

import pytest

from app.services import tcgcsv


@pytest.mark.parametrize("name, code", [
    ("M3: Nihil Zero", "M3"),
    ("m1S: Mega Symphonia", "M1S"),
    ("M2a: High Class Pack: MEGA Dream ex", "M2A"),
    ("SV1a: Triplet Beat", "SV1A"),
    ("No Colon Here", None),
    ("", None),
    (None, None),
    (123, None),          # nicht-String (defektes API-Feld) → None statt TypeError
    (": leer", None),     # leerer Code vor dem Doppelpunkt
])
def test_set_code_from_group(name, code):
    assert tcgcsv.set_code_from_group(name) == code


@pytest.mark.parametrize("ext, num", [
    ([{"name": "Number", "value": "009/080"}], "9"),
    ([{"name": "Number", "value": "016/080"}], "16"),
    ([{"name": "Number", "value": "100"}], "100"),
    ([{"name": "Number", "value": "TG01/TG30"}], None),   # nicht rein numerisch
    ([{"name": "Rarity", "value": "Rare"}], None),        # keine Nummer → Sealed
    ([], None),
])
def test_product_number(ext, num):
    assert tcgcsv.product_number({"extendedData": ext}) == num


def test_hires_image_url():
    p = {"imageUrl": "https://tcgplayer-cdn.tcgplayer.com/product/674320_200w.jpg"}
    assert tcgcsv.hires_image_url(p) == \
        "https://tcgplayer-cdn.tcgplayer.com/product/674320_in_1000x1000.jpg"
    # Fremd-Host → None (Sicherheit)
    assert tcgcsv.hires_image_url({"imageUrl": "https://evil.example/x_200w.jpg"}) is None
    assert tcgcsv.hires_image_url({}) is None


@pytest.mark.parametrize("url", [
    # Look-alike-Host: die EXAKTE Host-Prüfung muss greifen, eine reine
    # Substring-Prüfung („IMAGE_HOST in url") würde das durchlassen.
    "https://tcgplayer-cdn.tcgplayer.com.evil.example/product/1_200w.jpg",
    "https://evil.example/tcgplayer-cdn.tcgplayer.com/1_200w.jpg",
    "http://tcgplayer-cdn.tcgplayer.com/product/1_200w.jpg",  # kein https
    "not-a-url",
    123,   # nicht-String
])
def test_hires_image_url_rejects_foreign_host(url):
    assert tcgcsv.hires_image_url({"imageUrl": url}) is None


@pytest.mark.parametrize("data, expected", [
    ({"results": [{"a": 1}, {"b": 2}]}, [{"a": 1}, {"b": 2}]),
    ({"results": [{"a": 1}, "kaputt", 5]}, [{"a": 1}]),  # nicht-dict-Einträge raus
    ({"results": None}, []),
    ({"success": True}, []),          # kein results-Feld
    ([{"a": 1}, "x"], [{"a": 1}]),    # nackte Liste
    (None, []),                        # _get_json-Fehler
    ("kaputt", []),
])
def test_results_robust(data, expected):
    assert tcgcsv._results(data) == expected


def test_is_card_product():
    assert tcgcsv.is_card_product({"extendedData": [{"name": "Number", "value": "9/80"}]}) is True
    # Sealed-Produkt (keine Nummer) → kein Kartenprodukt
    assert tcgcsv.is_card_product({"extendedData": [{"name": "Rarity", "value": "Rare"}]}) is False
