"""ANSI: the one 16-colour terminal mapping (GNOME and Neovim)."""

from __future__ import annotations

from configurator.palette import (Palette, ValidationError, check_name,
                                  resolve)

MODULE = "configurator/terminal_ansi.py"
COUNT = 16
ANSI = (
    "dragonBlack0", "dragonRed", "dragonGreen2", "dragonYellow",
    "dragonBlue2", "dragonPink", "dragonAqua", "oldWhite",
    "dragonGray", "waveRed", "dragonGreen", "carpYellow",
    "springBlue", "springViolet1", "waveAqua2", "dragonWhite",
)


def validate_ansi(names, ansi=ANSI) -> list:
    """REQ-MAP-3: exactly 16 entries, each a [palette] name."""
    errors = []
    if len(ansi) != COUNT:
        errors.append(ValidationError(
            f"{MODULE}: ANSI",
            f"expected {COUNT} entries, found {len(ansi)}"))
    for index, name in enumerate(ansi):
        errors += check_name(f"{MODULE}: ANSI[{index}]", name, names)
    return errors


def resolve_ansi(palette: Palette, ansi=ANSI) -> tuple:
    """The 16 ANSI colours as lowercase hex, in order."""
    return tuple(resolve(palette, name) for name in ansi)
