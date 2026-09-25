"""REQ-CLI-5: report lines (stdout) and error lines (stderr)."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum

PREFIX = "configure.py: "


class Status(Enum):
    UPDATED = "updated"
    UNCHANGED = "unchanged"
    WOULD_UPDATE = "would update"
    WOULD_REMOVE = "would remove"
    REMOVED = "removed"
    FAILED = "failed"
    NOT_RUN = "not run"


@dataclass(frozen=True)
class TargetResult:
    """One report entry: `<target>: <status> (<note>)` plus details."""

    target: str
    status: Status
    note: str | None = None
    details: tuple = ()


def format_result(result: TargetResult) -> str:
    line = f"{result.target}: {result.status.value}"
    if result.note:
        line += f" ({result.note})"
    return "\n".join([line] + [f"  {d}" for d in result.details])


def emit(result: TargetResult) -> None:
    print(format_result(result), flush=True)


def err(message: str) -> None:
    print(PREFIX + message, file=sys.stderr, flush=True)


def warn(message: str) -> None:
    err(f"warning: {message}")
