"""gsettings access shared by the GNOME and Ptyxis configurators."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass

from configurator.files import Interrupted
from configurator.palette import InputError


@dataclass(frozen=True)
class DesiredKey:
    """One profile key and its gsettings value text."""

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


def quote(text: str) -> str:
    return f"'{text}'"


def format_as(items) -> str:
    """A GVariant `as` literal; `@as []` when empty."""
    if not items:
        return "@as []"
    return "[" + ", ".join(quote(item) for item in items) + "]"


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["gsettings", *args], capture_output=True,
                          text=True, stdin=subprocess.DEVNULL,
                          check=False)


def first_line(proc: subprocess.CompletedProcess) -> str:
    lines = proc.stderr.strip().splitlines()
    return lines[0] if lines else f"exit status {proc.returncode}"


def read(prefix: str, *args) -> str:
    """A read-only gsettings call; failure is an input error."""
    proc = run(*args)
    if proc.returncode != 0:
        raise InputError(f"{prefix}: gsettings {args[0]} failed: "
                         f"{first_line(proc)}")
    return proc.stdout


def has_line(text: str, line: str) -> bool:
    return line in text.splitlines()


def missing(list_schema: str, profile_schema: str) -> str | None:
    """The missing installation prerequisite, or None (REQ-GT-2)."""
    if shutil.which("gsettings") is None:
        return "gsettings not found on PATH"
    if not has_line(run("list-schemas").stdout, list_schema):
        return f"GSettings schema {list_schema} is not installed"
    relocatable = run("list-relocatable-schemas").stdout
    if not has_line(relocatable, profile_schema):
        return f"GSettings schema {profile_schema} is not installed"
    return None


def read_profile(prefix: str, schema_path: str) -> dict:
    """key -> printed value of every key at a profile path."""
    values = {}
    listing = read(prefix, "list-recursively", schema_path)
    for line in listing.splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3:
            values[parts[1]] = parts[2]
    return values


def write_args(change: KeyChange, value: str | None) -> tuple:
    if change.key is None:
        return ("reset-recursively", change.schema)
    if value is None:
        return ("reset", change.schema, change.key)
    return ("set", change.schema, change.key, value)


def write(change: KeyChange, value: str | None, allowed) -> str | None:
    """One guarded gsettings write; a failure reason or None."""
    if not allowed(change):
        return f"refusing to write {change.schema} {change.key}"
    args = write_args(change, value)
    proc = run(*args)
    if proc.returncode != 0:
        return f"{args[0]} {change.key or 'profile'}: {first_line(proc)}"
    return None


def rollback(done, undo) -> None:
    """Undo the applied changes in reverse order (best effort)."""
    for change in reversed(done):
        try:
            undo(change)
        except Interrupted:
            continue


def apply(changes, do, undo) -> str | None:
    """Apply changes in order; on failure roll back, return why."""
    done = []
    for change in changes:
        try:
            failure = do(change)
        except Interrupted:
            failure = "interrupted"
        if failure:
            rollback(done, undo)
            return failure
        done.append(change)
    return None
