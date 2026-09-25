"""Load and validate palette.toml; shared validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

SOURCE = "palette.toml"
TABLE = "palette"
REQUIRED_NAMES = (
    "autumnGreen", "autumnRed", "autumnYellow", "carpYellow",
    "dragonAqua", "dragonAsh", "dragonBlack0", "dragonBlack1",
    "dragonBlack2", "dragonBlack3", "dragonBlack4", "dragonBlack5",
    "dragonBlack6", "dragonBlue", "dragonBlue2", "dragonGray",
    "dragonGray2", "dragonGray3", "dragonGreen", "dragonGreen2",
    "dragonOrange", "dragonOrange2", "dragonPink", "dragonRed",
    "dragonTeal", "dragonViolet", "dragonWhite", "dragonYellow",
    "fujiWhite", "katanaGray", "oldWhite", "roninYellow", "samuraiRed",
    "springBlue", "springGreen", "springViolet1", "sumiInk6",
    "waveAqua1", "waveAqua2", "waveBlue1", "waveBlue2", "waveRed",
    "winterBlue", "winterGreen", "winterRed", "winterYellow",
)
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
TOML_TYPES = {
    "dict": "table", "int": "integer", "float": "float",
    "bool": "boolean", "list": "array",
}


class InputError(Exception):
    """Unreadable or unusable input; the message is printed as is."""


@dataclass(frozen=True)
class ValidationError:
    """One violated rule, printed as `<address>: <reason>`."""

    address: str
    reason: str

    def __str__(self) -> str:
        return f"{self.address}: {self.reason}"


@dataclass(frozen=True)
class Palette:
    """Palette names mapped to lowercase `#rrggbb`."""

    colors: Mapping[str, str]


def pal_addr(name: str) -> str:
    return f"{SOURCE}: [{TABLE}].{name}"


def map_addr(module: str, const: str, role: str) -> str:
    return f"{module}: {const}.{role}"


def tmpl_addr(file: str, line: int) -> str:
    return f"tmux/{file}:{line}"


def read_toml(path: Path) -> dict:
    """Read and parse palette.toml."""
    import tomllib

    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except OSError as exc:
        raise InputError(f"{SOURCE}: cannot read: {exc.strerror}")
    except tomllib.TOMLDecodeError as exc:
        raise InputError(f"{SOURCE}: TOML syntax error: {exc}")


def type_name(value) -> str:
    name = type(value).__name__
    return TOML_TYPES.get(name, name)


def validate_top_level(raw: dict) -> list:
    """REQ-PAL-1: exactly one table, [palette]."""
    errors = []
    for key, value in raw.items():
        if key == TABLE:
            continue
        if isinstance(value, dict):
            errors.append(ValidationError(f"{SOURCE}: [{key}]",
                                          "unexpected table"))
        else:
            errors.append(ValidationError(f"{SOURCE}: {key}",
                                          "unexpected key"))
    if TABLE not in raw:
        errors.append(ValidationError(f"{SOURCE}: [{TABLE}]",
                                      "missing table"))
    elif not isinstance(raw[TABLE], dict):
        errors.append(ValidationError(f"{SOURCE}: [{TABLE}]",
                                      "expected a table"))
    return errors


def entry_reason(name: str, value) -> str | None:
    """REQ-PAL-2: why one [palette] entry is invalid, or None."""
    if not NAME_RE.match(name):
        return "invalid name"
    if not isinstance(value, str):
        return f"expected a string, found {type_name(value)}"
    if not HEX_RE.match(value):
        return f'"{value}" is not #RRGGBB'
    return None


def validate_entries(table: dict) -> list:
    """REQ-PAL-2 and REQ-PAL-3 over the [palette] table."""
    errors = []
    for name, value in table.items():
        reason = entry_reason(name, value)
        if reason:
            errors.append(ValidationError(pal_addr(name), reason))
    for name in REQUIRED_NAMES:
        if name not in table:
            errors.append(ValidationError(pal_addr(name),
                                          "missing required name"))
    return errors


def validate_palette(raw: dict) -> list:
    """Every palette rule violation of a parsed palette.toml."""
    errors = validate_top_level(raw)
    if isinstance(raw.get(TABLE), dict):
        errors += validate_entries(raw[TABLE])
    return errors


def palette_names(raw: dict) -> frozenset:
    """Names of the [palette] table (empty when it is missing)."""
    table = raw.get(TABLE)
    return frozenset(table) if isinstance(table, dict) else frozenset()


def make_palette(raw: dict) -> Palette:
    """The validated [palette] table with lowercase values."""
    colors = {k: v.lower() for k, v in raw[TABLE].items()}
    return Palette(MappingProxyType(colors))


def resolve(palette: Palette, name: str) -> str:
    return palette.colors[name]


def check_name(address: str, value, names) -> list:
    """A mapping value must be the name of a [palette] entry."""
    if not isinstance(value, str):
        return [ValidationError(address, "expected a [palette] name")]
    if value not in names:
        return [ValidationError(address,
                                f'"{value}" is not a [palette] name')]
    return []


def check_role_map(module, const, roles, keys, names) -> list:
    """REQ-MAP-3 for a name -> name role mapping with a fixed key set."""
    errors = []
    for role in keys:
        if role not in roles:
            errors.append(ValidationError(map_addr(module, const, role),
                                          "missing role"))
    for role, value in roles.items():
        address = map_addr(module, const, role)
        if role not in keys:
            errors.append(ValidationError(address, "unknown role"))
        else:
            errors += check_name(address, value, names)
    return errors
