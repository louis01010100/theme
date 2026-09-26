"""Shared terminal mappings: ANSI and TERMINAL_ROLES."""

from __future__ import annotations

from types import MappingProxyType

from configurator.palette import (Palette, ValidationError, check_name,
                                  check_role_map, resolve)

MODULE = "configurator/terminal_ansi.py"
COUNT = 16
ANSI = (
    "dragonBlack0", "dragonRed", "dragonGreen2", "dragonYellow",
    "dragonBlue2", "dragonPink", "dragonAqua", "oldWhite",
    "dragonGray", "waveRed", "dragonGreen", "carpYellow",
    "springBlue", "springViolet1", "waveAqua2", "dragonWhite",
)
TERMINAL_ROLES = MappingProxyType({
    "background": "dragonBlack3",
    "foreground": "dragonWhite",
    "cursor_bg": "oldWhite",
    "cursor_fg": "dragonBlack3",
    "selection_bg": "waveBlue2",
    "selection_fg": "oldWhite",
})
ROLE_KEYS = (
    "background", "foreground", "cursor_bg", "cursor_fg",
    "selection_bg", "selection_fg",
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


def validate_roles(names, roles=TERMINAL_ROLES) -> list:
    """REQ-MAP-3 for TERMINAL_ROLES."""
    return check_role_map(MODULE, "TERMINAL_ROLES", roles, ROLE_KEYS,
                          names)
