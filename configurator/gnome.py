"""GNOME Terminal: the "Ukiyo-e" profile."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from configurator import settings
from configurator.palette import Palette, resolve
from configurator.settings import (DesiredKey, KeyChange, format_as,
                                   quote)
from configurator.terminal_ansi import TERMINAL_ROLES, resolve_ansi

PREFIX = "gnome"
UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE_SCHEMA = "org.gnome.Terminal.Legacy.Profile"
LIST_SCHEMA = "org.gnome.Terminal.ProfilesList"
PROFILES_ROOT = "/org/gnome/terminal/legacy/profiles:/"
PROFILE_PATH = f"{PROFILES_ROOT}:{UUID}/"
PROFILE = f"{PROFILE_SCHEMA}:{PROFILE_PATH}"
# Read only: an unused profile path reports the schema defaults.
DEFAULTS = (f"{PROFILE_SCHEMA}:{PROFILES_ROOT}:"
            "00000000-0000-0000-0000-000000000000/")
PROFILE_KEYS = (
    "visible-name", "use-theme-colors", "background-color",
    "foreground-color", "palette", "cursor-colors-set",
    "cursor-background-color", "cursor-foreground-color",
    "highlight-colors-set", "highlight-background-color",
    "highlight-foreground-color", "bold-color-same-as-fg",
)
LIST_KEYS = ("list", "default")
COLOUR_KEYS = frozenset(k for k in PROFILE_KEYS
                        if k.endswith("-color") or k == "palette")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}"
                     r"-[0-9a-fA-F]{12}")


@dataclass(frozen=True)
class GnomeState:
    """Read-only probe of the profile, its defaults, list, default."""

    values: Mapping
    defaults: Mapping
    uuids: tuple
    default: str


@dataclass(frozen=True)
class GnomePlan:
    """The ordered writes of the gnome step."""

    changes: tuple
    installed: bool = True

    @property
    def details(self) -> tuple:
        return tuple(change.detail for change in self.changes)


def parse_uuids(text: str) -> tuple:
    """UUID-shaped tokens of a printed `as` value (`@as []` too)."""
    return tuple(UUID_RE.findall(text))


def desired_keys(palette: Palette) -> tuple:
    """REQ-GT-3: the 12 profile keys, in write order."""
    role = {r: quote(resolve(palette, n))
            for r, n in TERMINAL_ROLES.items()}
    values = (
        "'Ukiyo-e'", "false", role["background"], role["foreground"],
        format_as(resolve_ansi(palette)), "true", role["cursor_bg"],
        role["cursor_fg"], "true", role["selection_bg"],
        role["selection_fg"], "true",
    )
    return tuple(DesiredKey(k, v) for k, v in zip(PROFILE_KEYS, values))


def missing() -> str | None:
    return settings.missing(LIST_SCHEMA, PROFILE_SCHEMA)


def read(*args) -> str:
    return settings.read(PREFIX, *args)


def read_profile(schema_path: str) -> dict:
    return settings.read_profile(PREFIX, schema_path)


def probe() -> GnomeState:
    """Current keys, their schema defaults, `list` and `default`."""
    uuids = parse_uuids(read("get", LIST_SCHEMA, "list"))
    default = read("get", LIST_SCHEMA, "default").strip().strip("'")
    return GnomeState(read_profile(PROFILE), read_profile(DEFAULTS),
                      uuids, default)


def same(key: str, current: str | None, wanted: str) -> bool:
    """Colours compare case-insensitively (REQ-GT-3)."""
    if key in COLOUR_KEYS and current is not None:
        return current.lower() == wanted.lower()
    return current == wanted


def profile_change(desired: DesiredKey, state: GnomeState) -> KeyChange:
    current = state.values.get(desired.key)
    unset = current == state.defaults.get(desired.key)
    return KeyChange(PROFILE, desired.key, None if unset else current,
                     desired.value, f"set {desired.key}")


def plan_install(desired, state: GnomeState, set_default) -> GnomePlan:
    """REQ-GT-3/5: differing keys, then registration, then default."""
    changes = [profile_change(d, state) for d in desired
               if not same(d.key, state.values.get(d.key), d.value)]
    if UUID not in state.uuids:
        changes.append(KeyChange(LIST_SCHEMA, "list",
                                 format_as(state.uuids),
                                 format_as(state.uuids + (UUID,)),
                                 "list add"))
    if set_default and state.default != UUID:
        changes.append(KeyChange(LIST_SCHEMA, "default",
                                 quote(state.default), quote(UUID),
                                 f"default {UUID}"))
    return GnomePlan(tuple(changes))


def list_changes(state: GnomeState) -> list:
    """REQ-GT-7 steps 1-3: the new `default` (if any), then `list`."""
    remaining = tuple(u for u in state.uuids if u != UUID)
    old_list, old_default = format_as(state.uuids), quote(state.default)
    if state.default == UUID and not remaining:
        return [KeyChange(LIST_SCHEMA, "default", old_default, None,
                          "default reset"),
                KeyChange(LIST_SCHEMA, "list", old_list, None,
                          "list remove")]
    changes = []
    if state.default == UUID:
        changes.append(KeyChange(LIST_SCHEMA, "default", old_default,
                                 quote(remaining[0]),
                                 f"default {remaining[0]}"))
    changes.append(KeyChange(LIST_SCHEMA, "list", old_list,
                             format_as(remaining), "list remove"))
    return changes


def plan_uninstall(state: GnomeState) -> GnomePlan:
    """REQ-GT-7; `unchanged (not installed)` when not listed."""
    if UUID not in state.uuids:
        return GnomePlan((), installed=False)
    reset = KeyChange(PROFILE, None, None, None, "reset profile")
    return GnomePlan(tuple(list_changes(state)) + (reset,))


def allowed(change: KeyChange) -> bool:
    """REQ-GT-8: only the profile path keys and list/default."""
    if change.schema == PROFILE:
        return change.key is None or change.key in PROFILE_KEYS
    return change.schema == LIST_SCHEMA and change.key in LIST_KEYS


def write(change: KeyChange, value: str | None) -> str | None:
    """One gsettings write guarded by REQ-GT-8."""
    return settings.write(change, value, allowed)


def undo(change: KeyChange) -> None:
    """REQ-GT-9: restore one recorded value (reset: not undone)."""
    if change.key is not None:
        write(change, change.old)


def apply(plan: GnomePlan) -> str | None:
    """Apply the writes in order; on failure roll back, return why."""
    return settings.apply(plan.changes, lambda c: write(c, c.new), undo)
