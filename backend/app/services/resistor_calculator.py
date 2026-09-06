from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


DIGIT_VALUES = {
    "black": 0,
    "brown": 1,
    "red": 2,
    "orange": 3,
    "yellow": 4,
    "green": 5,
    "blue": 6,
    "violet": 7,
    "gray": 8,
    "white": 9,
}

MULTIPLIERS = {
    "black": Decimal("1"),
    "brown": Decimal("10"),
    "red": Decimal("100"),
    "orange": Decimal("1000"),
    "yellow": Decimal("10000"),
    "green": Decimal("100000"),
    "blue": Decimal("1000000"),
    "violet": Decimal("10000000"),
    "gray": Decimal("100000000"),
    "white": Decimal("1000000000"),
    "gold": Decimal("0.1"),
    "silver": Decimal("0.01"),
}

TOLERANCES = {
    "brown": "±1%",
    "red": "±2%",
    "green": "±0.5%",
    "blue": "±0.25%",
    "violet": "±0.1%",
    "gray": "±0.05%",
    "gold": "±5%",
    "silver": "±10%",
}


@dataclass(frozen=True)
class ResistorValue:
    bands: list[str]
    resistance_ohms: float
    formatted_resistance: str
    tolerance: str


class ResistorDecodeError(ValueError):
    """Raised when color bands cannot be decoded as a supported resistor."""


def decode_four_band_resistor(bands: list[str]) -> ResistorValue:
    normalized = [band.strip().lower() for band in bands]
    if len(normalized) != 4:
        raise ResistorDecodeError("Exactly four color bands are required.")

    first, second, multiplier, tolerance = normalized
    if first not in DIGIT_VALUES:
        raise ResistorDecodeError(f"First digit band '{first}' is not supported.")
    if second not in DIGIT_VALUES:
        raise ResistorDecodeError(f"Second digit band '{second}' is not supported.")
    if multiplier not in MULTIPLIERS:
        raise ResistorDecodeError(f"Multiplier band '{multiplier}' is not supported.")
    if tolerance not in TOLERANCES:
        raise ResistorDecodeError(f"Tolerance band '{tolerance}' is not supported.")

    significant_digits = DIGIT_VALUES[first] * 10 + DIGIT_VALUES[second]
    resistance = Decimal(significant_digits) * MULTIPLIERS[multiplier]

    return ResistorValue(
        bands=normalized,
        resistance_ohms=float(resistance),
        formatted_resistance=format_resistance(resistance),
        tolerance=TOLERANCES[tolerance],
    )


def format_resistance(ohms: Decimal) -> str:
    units = [
        (Decimal("1000000000"), "GΩ"),
        (Decimal("1000000"), "MΩ"),
        (Decimal("1000"), "kΩ"),
        (Decimal("1"), "Ω"),
    ]

    for factor, suffix in units:
        if ohms >= factor:
            value = ohms / factor
            return f"{_compact_decimal(value)} {suffix}"

    return f"{_compact_decimal(ohms)} Ω"


def _compact_decimal(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.01")).normalize()
    return format(rounded, "f")
