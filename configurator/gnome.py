"""GNOME Terminal: TERMINAL_ROLES and the "Ukiyo-e" profile."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from configurator.files import Interrupted
from configurator.palette import (InputError, Palette, check_role_map,
                                  resolve)
from configurator.terminal_ansi import resolve_ansi

MODULE = "configurator/gnome.py"
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
class DesiredKey:
    """One REQ-GT-3 profile key and its gsettings value text."""

    key: str
    value: str


@dataclass(frozen=True)
class KeyChange:
    """One planned gsettings write (LD-1 rollback data included).

    key None: the whole profile path (reset-recursively).
    old None: the key held its default; rollback resets it.
    new None: reset the key to its schema default.
    """

    schema: str
    key: str | None
    old: str | None
    new: str | None
    detail: str


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


def validate_roles(names, roles=TERMINAL_ROLES) -> list:
    """REQ-MAP-3 for TERMINAL_ROLES."""
    return check_role_map(MODULE, "TERMINAL_ROLES", roles, ROLE_KEYS,
                          names)


def quote(text: str) -> str:
    return f"'{text}'"


def format_as(items) -> str:
    """A GVariant `as` literal; `@as []` when empty."""
    if not items:
        return "@as []"
    return "[" + ", ".join(quote(item) for item in items) + "]"


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


def gsettings(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["gsettings", *args], capture_output=True,
                          text=True, stdin=subprocess.DEVNULL,
                          check=False)


def first_line(proc: subprocess.CompletedProcess) -> str:
    lines = proc.stderr.strip().splitlines()
    return lines[0] if lines else f"exit status {proc.returncode}"


def read(*args) -> str:
    """A read-only gsettings call; failure is an input error."""
    proc = gsettings(*args)
    if proc.returncode != 0:
        raise InputError(f"gnome: gsettings {args[0]} failed: "
                         f"{first_line(proc)}")
    return proc.stdout


def has_line(text: str, line: str) -> bool:
    return line in text.splitlines()


def check_prereq() -> None:
    """REQ-GT-2: gsettings and both GNOME Terminal schemas."""
    if shutil.which("gsettings") is None:
        raise InputError("gnome: gsettings not found on PATH")
    if not has_line(gsettings("list-schemas").stdout, LIST_SCHEMA):
        raise InputError(f"gnome: GSettings schema {LIST_SCHEMA} "
                         f"is not installed")
    relocatable = gsettings("list-relocatable-schemas").stdout
    if not has_line(relocatable, PROFILE_SCHEMA):
        raise InputError(f"gnome: GSettings schema {PROFILE_SCHEMA} "
                         f"is not installed")


def read_profile(schema_path: str) -> dict:
    """key -> printed value of every key at a profile path."""
    values = {}
    for line in read("list-recursively", schema_path).splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            values[parts[1]] = parts[2]
    return values


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


def write_args(change: KeyChange, value: str | None) -> tuple:
    if change.key is None:
        return ("reset-recursively", change.schema)
    if value is None:
        return ("reset", change.schema, change.key)
    return ("set", change.schema, change.key, value)


def write(change: KeyChange, value: str | None) -> str | None:
    """One guarded gsettings write; a failure reason or None."""
    if not allowed(change):
        return f"refusing to write {change.schema} {change.key}"
    args = write_args(change, value)
    proc = gsettings(*args)
    if proc.returncode != 0:
        return f"{args[0]} {change.key or 'profile'}: {first_line(proc)}"
    return None


def rollback(done) -> None:
    """REQ-GT-9: restore recorded values in reverse (best effort)."""
    for change in reversed(done):
        if change.key is not None:
            try:
                write(change, change.old)
            except Interrupted:
                continue


def apply(plan: GnomePlan) -> str | None:
    """Apply the writes in order; on failure roll back, return why."""
    done = []
    for change in plan.changes:
        try:
            failure = write(change, change.new)
        except Interrupted:
            failure = "interrupted"
        if failure:
            rollback(done)
            return failure
        done.append(change)
    return None
