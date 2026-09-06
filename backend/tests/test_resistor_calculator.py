import pytest

from app.services.resistor_calculator import ResistorDecodeError, decode_four_band_resistor


def test_decodes_standard_four_band_resistor():
    result = decode_four_band_resistor(["brown", "black", "red", "gold"])

    assert result.resistance_ohms == 1000
    assert result.formatted_resistance == "1 kΩ"
    assert result.tolerance == "±5%"
    assert result.bands == ["brown", "black", "red", "gold"]


def test_decodes_decimal_multiplier():
    result = decode_four_band_resistor(["green", "blue", "gold", "silver"])

    assert result.resistance_ohms == 5.6
    assert result.formatted_resistance == "5.6 Ω"
    assert result.tolerance == "±10%"


def test_decodes_large_values_with_compact_units():
    result = decode_four_band_resistor(["yellow", "violet", "orange", "gold"])

    assert result.resistance_ohms == 47000
    assert result.formatted_resistance == "47 kΩ"


def test_rejects_unsupported_band_count():
    with pytest.raises(ResistorDecodeError, match="Exactly four"):
        decode_four_band_resistor(["brown", "black", "red"])


def test_rejects_invalid_multiplier():
    with pytest.raises(ResistorDecodeError, match="Multiplier"):
        decode_four_band_resistor(["brown", "black", "pink", "gold"])
