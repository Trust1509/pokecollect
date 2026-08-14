"""
#53: Property-based Tests (Hypothesis) auf die rechnerischen Kerne.

Beispieltests prüfen die Fälle, an die wir gedacht haben. Hypothesis erzeugt
die Eingaben selbst und schrumpft Gegenbeispiele — gesucht sind hier die
Eigenschaften, die IMMER gelten müssen, weil an ihnen Geldwerte hängen:

- Ein Preis kommt immer aus den gelieferten Quelldaten (nie „erfunden").
- Umrechnung ist monoton, nicht-negativ und auf Cent gerundet.
- Die Varianten-Wahl liefert immer einen bekannten Schlüssel und genau die
  Spalte, die dieser Schlüssel benennt.
- Parser stürzen an keiner Eingabe ab.

Kein DB-Zugriff, keine Netzaufrufe — reine Funktionen.
"""

from decimal import Decimal

from hypothesis import assume, given, settings as hyp_settings, strategies as st

from app.schemas._validators import reject_control_chars, strip_control_chars
from app.services.fx import _parse_rate
from app.services.pricing import (
    _is_holo, _wert_plausibel, convert_usd_eur, normalize_price_source,
    pick_cardmarket_price, variant_usd,
)
from app.services.scan.resolver import _confidence, _denominator, strip_card_suffix
from app.services.tcgdex import CardMarketPricing, local_id_from_card_nr
from app.services.tcgcsv import clean_card_name, product_denominator, product_number

# Preise: nicht-negativ, endlich, in realistischer Größenordnung.
preise = st.floats(min_value=0, max_value=1_000_000, allow_nan=False, allow_infinity=False)
opt_preise = st.one_of(st.none(), preise)
kurse = st.decimals(min_value=Decimal("0.3"), max_value=Decimal("3"), places=4)
folierungen = st.sampled_from([None, "", "Normal", "Holo", "Reverse Holo"])
muster = st.sampled_from([None, "", "Pokéball", "Masterball", "Cosmos", "Sterne"])
quellen = st.sampled_from(["30d_avg", "daily", "current", "", None, "unbekannt"])
texte = st.text(max_size=60)


# ── convert_usd_eur ─────────────────────────────────────────────────────────

@given(usd=preise, rate=kurse)
def test_umrechnung_ist_auf_cent_gerundet_und_nicht_negativ(usd, rate):
    eur = convert_usd_eur(Decimal(str(usd)), rate)
    assert eur >= 0
    assert eur.as_tuple().exponent == -2            # genau zwei Nachkommastellen
    assert abs(eur - Decimal(str(usd)) * rate) <= Decimal("0.005")


@given(a=preise, b=preise, rate=kurse)
def test_umrechnung_ist_monoton(a, b, rate):
    """Mehr Dollar darf nie weniger Euro ergeben."""
    assume(a <= b)
    assert convert_usd_eur(Decimal(str(a)), rate) <= convert_usd_eur(Decimal(str(b)), rate)


# ── pick_cardmarket_price ───────────────────────────────────────────────────

@given(
    avg=opt_preise, low=opt_preise, trend=opt_preise,
    avg1=opt_preise, avg7=opt_preise, avg30=opt_preise,
    avg_holo=opt_preise, trend_holo=opt_preise,
    avg1_holo=opt_preise, avg7_holo=opt_preise, avg30_holo=opt_preise,
    folierung=folierungen, quelle=quellen, echtes_holo=st.booleans(),
)
def test_preis_stammt_immer_aus_den_quelldaten(
    avg, low, trend, avg1, avg7, avg30,
    avg_holo, trend_holo, avg1_holo, avg7_holo, avg30_holo,
    folierung, quelle, echtes_holo,
):
    """Der gewählte Preis ist IMMER einer der gelieferten Werte — nie ein
    gerechneter oder geratener."""
    werte = dict(avg=avg, low=low, trend=trend, avg1=avg1, avg7=avg7, avg30=avg30)
    cm = CardMarketPricing(**{
        **werte,
        "avg-holo": avg_holo, "trend-holo": trend_holo,
        "avg1-holo": avg1_holo, "avg7-holo": avg7_holo, "avg30-holo": avg30_holo,
    })
    preis = pick_cardmarket_price(cm, folierung, quelle, hat_echtes_holo=echtes_holo)
    if preis is None:
        return
    vorhanden = {v for v in (avg, low, trend, avg1, avg7, avg30, avg_holo,
                             trend_holo, avg1_holo, avg7_holo, avg30_holo)
                 if v is not None}
    assert float(preis) in vorhanden
    assert preis >= 0


@given(folierung=folierungen, quelle=quellen, echtes_holo=st.booleans())
def test_ohne_daten_kein_preis(folierung, quelle, echtes_holo):
    assert pick_cardmarket_price(CardMarketPricing(), folierung, quelle,
                                 hat_echtes_holo=echtes_holo) is None
    assert pick_cardmarket_price(None, folierung, quelle) is None


@given(quelle=quellen)
def test_preisquelle_normalisiert_auf_zwei_werte(quelle):
    assert normalize_price_source(quelle) in ("30d_avg", "daily")


# ── variant_usd ─────────────────────────────────────────────────────────────

class _Row:
    def __init__(self, **kw):
        for k in ("price_usd", "price_usd_holo", "price_usd_reverse",
                  "price_usd_pokeball", "price_usd_masterball"):
            v = kw.get(k)
            setattr(self, k, Decimal(str(v)) if v is not None else None)


@given(
    basis=opt_preise, holo=opt_preise, reverse=opt_preise,
    pokeball=opt_preise, masterball=opt_preise,
    folierung=folierungen, m=muster,
)
def test_variantenwahl_liefert_bekannten_schluessel_und_passende_spalte(
    basis, holo, reverse, pokeball, masterball, folierung, m,
):
    row = _Row(price_usd=basis, price_usd_holo=holo, price_usd_reverse=reverse,
               price_usd_pokeball=pokeball, price_usd_masterball=masterball)
    preis, key = variant_usd(row, folierung, m)
    assert key in ("pokeball", "masterball", "holo", "reverse", "normal")
    spalte = {"pokeball": row.price_usd_pokeball, "masterball": row.price_usd_masterball,
              "holo": row.price_usd_holo, "reverse": row.price_usd_reverse,
              "normal": row.price_usd}[key]
    assert preis == spalte      # der Schlüssel benennt exakt die genutzte Spalte


@given(basis=opt_preise, pokeball=preise, masterball=preise, m=muster)
def test_muster_zaehlt_nur_bei_folierter_grundform(basis, pokeball, masterball, m):
    """Ein am Formular zurückgelassenes Muster darf eine Normal-Karte nie auf
    den Muster-Preis heben (v1.8.0-Riegel)."""
    row = _Row(price_usd=basis, price_usd_pokeball=pokeball,
               price_usd_masterball=masterball)
    preis, key = variant_usd(row, "Normal", m)
    assert key == "normal"
    assert preis == row.price_usd


@given(preis=st.decimals(min_value=Decimal("-1000"), max_value=Decimal("2000000"),
                         places=2))
def test_wertebereich_haelt_die_datenbankgrenze(preis):
    """_wert_plausibel muss genau das durchlassen, was Numeric(8,2) fasst."""
    assert _wert_plausibel(preis) == (Decimal("0.01") <= preis <= Decimal("999999.99"))


# ── Parser: dürfen an keiner Eingabe abstürzen ──────────────────────────────

@given(text=texte)
def test_kartennummer_parser_stuerzt_nie_ab(text):
    lid = local_id_from_card_nr(text)
    assert lid is None or isinstance(lid, str)
    denom = _denominator(text)
    assert denom is None or isinstance(denom, int)


@given(text=texte)
def test_suffix_stripper_ist_stabil(text):
    out = strip_card_suffix(text)
    assert out is None or isinstance(out, str)
    # Idempotent: zweimal anwenden ändert nichts mehr
    assert strip_card_suffix(out) == out


@given(nummer=texte, name=texte)
def test_tcgcsv_parser_stuerzen_nie_ab(nummer, name):
    produkt = {"name": name, "extendedData": [{"name": "Number", "value": nummer}]}
    num = product_number(produkt)
    assert num is None or (num.isdigit() and not num.startswith("0") or num == "0")
    denom = product_denominator(produkt)
    assert denom is None or isinstance(denom, int)
    sauber = clean_card_name(name)
    assert sauber is None or isinstance(sauber, str)


@given(raw_confidence=st.one_of(st.none(), st.floats(min_value=-5, max_value=5,
                                                     allow_nan=False)),
       matched=st.booleans(), via_search=st.booleans(), via_number=st.booleans(),
       via_suffix=st.booleans(), uncertain=st.integers(min_value=0, max_value=20))
def test_confidence_bleibt_im_intervall(raw_confidence, matched, via_search,
                                        via_number, via_suffix, uncertain):
    c = _confidence(raw_confidence, matched=matched, via_search=via_search,
                    via_number=via_number, via_suffix=via_suffix,
                    uncertain_count=uncertain)
    assert 0.0 <= c <= 1.0


# ── Eingabe-Härtung (#55) als Eigenschaft ───────────────────────────────────

@given(text=st.text(max_size=200))
def test_gesaeuberter_text_passiert_die_sperre_immer(text):
    """strip und reject sind zwei Seiten derselben Regel: was gesäubert wurde,
    muss die Sperre widerspruchslos passieren."""
    sauber = strip_control_chars(text)
    assert reject_control_chars(sauber) == sauber      # wirft nicht
    assert strip_control_chars(sauber) == sauber       # idempotent


@given(wert=st.one_of(st.none(), st.floats(allow_nan=True, allow_infinity=True),
                      st.text(max_size=20), st.integers()))
@hyp_settings(max_examples=200)
def test_fx_kurs_nimmt_nur_plausible_werte(wert):
    """Ein Kurs außerhalb 0,3–3 ist ein Datenfehler und darf nie durchkommen."""
    rate = _parse_rate({"rates": {"EUR": wert}})
    assert rate is None or Decimal("0.3") < rate < Decimal("3")


@given(folierung=folierungen)
def test_is_holo_ignoriert_reverse(folierung):
    assert _is_holo(folierung) == bool(
        folierung and "holo" in folierung.lower() and "reverse" not in folierung.lower())
