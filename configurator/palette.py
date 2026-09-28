"""Load and validate palette.toml; shared validation helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

SOURCE = "palette.toml"
TABLE = "palette"
SLOTS = tuple(f"base0{digit}" for digit in "0123456789ABCDEF")
# REQ-PAL-7: documentation names of the slots, reserved-name data only.
NEUTRAL_NAMES = ("lavaBlack", "cinderBlack", "basaltGray", "ashGray",
                 "mistGray", "hazeGray", "cloudGray", "snowWhite")
ACCENT_NAMES = ("fujiRed", "persimmonOrange", "strawYellow",
                "pineGreen", "lakeAqua", "ridgeBlue", "twilightViolet",
                "blossomPink")
COLOUR_NAMES = NEUTRAL_NAMES + ACCENT_NAMES
NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
TOML_TYPES = {
    "dict": "table", "int": "integer", "float": "float",
    "bool": "boolean", "list": "array",
}


# REQ-SHADE-1: the eight dark shades, required [palette] entries.
SHADES = ("darkRed", "darkOrange", "darkYellow", "darkGreen",
          "darkAqua", "darkBlue", "darkViolet", "darkPink")


@dataclass(frozen=True)
class ReservedName:
    """A name an extra [palette] entry may not take, in any case."""

    canonical: str
    kind: str


def reserved_table() -> dict:
    """Lowercased name -> ReservedName (REQ-PAL-4)."""
    groups = (("slot", SLOTS), ("shade", SHADES),
              ("neutral name", NEUTRAL_NAMES),
              ("accent name", ACCENT_NAMES))
    return {name.lower(): ReservedName(name, kind)
            for kind, names in groups for name in names}


RESERVED = MappingProxyType(reserved_table())


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
    """[palette] names and the dark shades -> lowercase `#rrggbb`."""

    colors: Mapping[str, str]
    shades: Mapping[str, str]


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


def reserved_reason(name: str) -> str | None:
    """REQ-PAL-4: why an entry name is reserved, or None."""
    reserved = RESERVED.get(name.lower())
    if name in SLOTS or name in SHADES or reserved is None:
        return None
    return f"reserved name ({reserved.kind} {reserved.canonical})"


def validate_entries(table: dict) -> list:
    """REQ-PAL-2, REQ-PAL-3 and REQ-PAL-4 over the [palette] table."""
    errors = []
    for name, value in table.items():
        for reason in (entry_reason(name, value), reserved_reason(name)):
            if reason:
                errors.append(ValidationError(pal_addr(name), reason))
    for name in SLOTS:
        if name not in table:
            errors.append(ValidationError(pal_addr(name),
                                          "missing required slot"))
    for name in SHADES:
        if name not in table:
            errors.append(ValidationError(pal_addr(name),
                                          "missing required shade"))
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


def colour_names(raw: dict) -> frozenset:
    """Names a mapping may use: [palette] names and the shades."""
    return palette_names(raw) | frozenset(SHADES)


def make_palette(raw: dict) -> Palette:
    """The validated [palette] table (lowercase), shades split out."""
    table = {k: v.lower() for k, v in raw[TABLE].items()}
    colors = {k: v for k, v in table.items() if k not in SHADES}
    shades = {name: table[name] for name in SHADES}
    return Palette(MappingProxyType(colors), MappingProxyType(shades))


def resolve(palette: Palette, name: str) -> str:
    """REQ-SHADE-3: a [palette] entry or a dark shade."""
    if name in palette.colors:
        return palette.colors[name]
    return palette.shades[name]


def check_name(address: str, value, names) -> list:
    """A mapping value must be a [palette] name or a shade name."""
    if not isinstance(value, str):
        return [ValidationError(address, "expected a [palette] name")]
    if value not in names:
        reason = f'"{value}" is not a [palette] name or derived shade'
        return [ValidationError(address, reason)]
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
