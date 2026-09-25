"""Version tree planning, build, switch, gc, and file modes."""

from __future__ import annotations

import os
import shutil
import stat
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from configurator.palette import InputError

FILE_MODE = 0o644
EXEC_MODE = 0o755
DIR_MODE = 0o755
LINK_PREFIX = "ukiyo_e.versions/"
TEMP_PREFIX = ".ukiyo_e.new-"
OWNERS = {"nvim": ("colors/", "lua/"), "tmux": ("ukiyo_e.tmux", "tmux/")}


class Interrupted(Exception):
    """SIGINT or SIGTERM arrived while applying."""


@dataclass(frozen=True)
class FileSpec:
    """The bytes and permission bits of one installed file."""

    data: bytes
    mode: int = FILE_MODE


Tree = Mapping[str, FileSpec]


@dataclass(frozen=True)
class Layout:
    """$DATA, $INSTALL (managed symlink) and $VERSIONS."""

    data: Path
    install: Path
    versions: Path


@dataclass(frozen=True)
class CurrentState:
    """The version $INSTALL references (None: none) and its tree."""

    version_id: str | None
    tree: Tree


@dataclass(frozen=True)
class TreeDiff:
    """Relpaths one target writes or removes."""

    writes: tuple
    removes: tuple

    @property
    def changed(self) -> bool:
        return bool(self.writes or self.removes)


@dataclass(frozen=True)
class StepOutcome:
    """Result of the file step: switched or not, and why it failed."""

    switched: bool
    error: str | None
    warnings: tuple
    version_id: str | None


def owner_of(rel: str) -> str | None:
    for target, prefixes in OWNERS.items():
        if rel.startswith(prefixes):
            return target
    return None


def managed_id(layout: Layout) -> str | None:
    """The <id> of a managed $INSTALL symlink, else None."""
    if not layout.install.is_symlink():
        return None
    target = os.readlink(layout.install)
    if not target.startswith(LINK_PREFIX):
        return None
    version_id = target[len(LINK_PREFIX):]
    if "/" in version_id or version_id in ("", ".", ".."):
        return None
    return version_id


def unmanaged(path: Path) -> InputError:
    return InputError(f"{path} exists and is not managed by "
                      f"configure.py; move it away and rerun")


def check_managed(layout: Layout) -> None:
    """REQ-INST-2 prerequisite for the tmux and nvim targets."""
    if os.path.lexists(layout.install) and managed_id(layout) is None:
        raise unmanaged(layout.install)
    versions = layout.versions
    if os.path.lexists(versions) and (versions.is_symlink()
                                      or not versions.is_dir()):
        raise unmanaged(versions)


def read_tree(folder: Path) -> dict:
    """Every regular file under folder: relpath -> FileSpec."""
    tree = {}
    for top, _dirs, names in os.walk(folder):
        for name in names:
            path = Path(top) / name
            info = path.lstat()
            if stat.S_ISREG(info.st_mode):
                rel = path.relative_to(folder).as_posix()
                tree[rel] = FileSpec(path.read_bytes(),
                                     stat.S_IMODE(info.st_mode))
    return tree


def read_current(layout: Layout) -> CurrentState:
    version_id = managed_id(layout)
    folder = layout.versions / (version_id or "")
    if version_id is None or not folder.is_dir():
        return CurrentState(None, {})
    return CurrentState(version_id, read_tree(folder))


def desired_tree(current: Tree, selected, rendered, uninstall) -> dict:
    """REQ-INST-4: selected targets replaced (or dropped), others kept."""
    want = {rel: spec for rel, spec in current.items()
            if owner_of(rel) not in selected}
    if not uninstall:
        for target in selected:
            want.update(rendered[target])
    return want


def diff(current: Tree, want: Tree, owner: str) -> TreeDiff:
    writes = sorted(rel for rel, spec in want.items()
                    if owner_of(rel) == owner and current.get(rel) != spec)
    removes = sorted(rel for rel in current
                     if owner_of(rel) == owner and rel not in want)
    return TreeDiff(tuple(writes), tuple(removes))


def warning(path, exc: OSError) -> str:
    return f"could not remove {path}: {exc.strerror}"


def rmtree(path: Path, record) -> None:
    """shutil.rmtree reporting each failure to record (3.11 and 3.12+)."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=record)
    else:
        shutil.rmtree(path, onerror=record)


def remove_path(path: Path) -> tuple:
    """Delete a file, symlink or tree; a failure becomes a warning."""
    failures = []

    def record(_function, name, info):
        failures.append(warning(name, info[1] if isinstance(
            info, tuple) else info))

    try:
        if path.is_dir() and not path.is_symlink():
            rmtree(path, record)
        else:
            path.unlink(missing_ok=True)
    except OSError as exc:
        failures.append(warning(path, exc))
    return tuple(failures)


def gc(layout: Layout) -> tuple:
    """REQ-INST-5 step 6: delete unreferenced versions and temp links."""
    warnings = ()
    for link in sorted(layout.data.glob(TEMP_PREFIX + "*")):
        warnings += remove_path(link)
    if not layout.versions.is_dir():
        return warnings
    if not os.path.lexists(layout.install):
        return warnings + remove_path(layout.versions)
    keep = managed_id(layout)
    for entry in sorted(layout.versions.iterdir()):
        if entry.name != keep:
            warnings += remove_path(entry)
    return warnings


def new_id(layout: Layout) -> str:
    """<UTC yyyymmddTHHMMSSZ>-<pid>, with -<n> appended if taken."""
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"{stamp}-{os.getpid()}"
    candidate, number = base, 0
    while os.path.lexists(layout.versions / candidate):
        number += 1
        candidate = f"{base}-{number}"
    return candidate


def make_dir(path: Path) -> None:
    """Create a directory with mode 0755 regardless of umask."""
    path.mkdir()
    os.chmod(path, DIR_MODE)


def write_one(path: Path, spec: FileSpec) -> None:
    """Write a fresh file (new inode, new mtime) and flush it."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(spec.data)
        while view:
            view = view[os.write(fd, view):]
        os.fchmod(fd, spec.mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def link_one(source: Path, path: Path, spec: FileSpec) -> None:
    """Hard-link an identical file; copy where links are unsupported."""
    try:
        os.link(source, path)
    except OSError:
        write_one(path, spec)


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def fsync_tree(root: Path) -> None:
    for top, _dirs, _names in os.walk(root, topdown=False):
        fsync_dir(Path(top))


def place(root: Path, rel: str, spec: FileSpec, current) -> None:
    """Create one desired file inside the new version directory."""
    path = root / rel
    for parent in reversed(path.relative_to(root).parents[:-1]):
        if not (root / parent).is_dir():
            make_dir(root / parent)
    if current.version_id and current.tree.get(rel) == spec:
        source = root.parent / current.version_id / rel
        link_one(source, path, spec)
    else:
        write_one(path, spec)


def build(layout: Layout, current, want: Tree, version_id: str) -> None:
    """REQ-INST-5 step 1: a complete, flushed $VERSIONS/<id>/."""
    layout.data.mkdir(parents=True, exist_ok=True)
    if not layout.versions.is_dir():
        make_dir(layout.versions)
    root = layout.versions / version_id
    make_dir(root)
    for rel in sorted(want):
        place(root, rel, want[rel], current)
    fsync_tree(root)
    fsync_dir(layout.versions)


def temp_link(layout: Layout, version_id: str) -> Path:
    return layout.data / f"{TEMP_PREFIX}{version_id}"


def switch(layout: Layout, version_id: str) -> None:
    """REQ-INST-5 step 2: atomically point $INSTALL at the version."""
    link = temp_link(layout, version_id)
    os.symlink(LINK_PREFIX + version_id, link)
    os.replace(link, layout.install)
    fsync_dir(layout.data)


def clean(layout: Layout, previous: str | None) -> tuple:
    """REQ-INST-5 step 3: delete the previous version directory."""
    if previous is None:
        return ()
    return remove_path(layout.versions / previous)


def remove_all(layout: Layout) -> tuple:
    """REQ-INST-5 step 4: unlink $INSTALL, then delete $VERSIONS."""
    if os.path.lexists(layout.install):
        os.unlink(layout.install)
        fsync_dir(layout.data)
    return remove_path(layout.versions)


def reason(exc: BaseException) -> str:
    if isinstance(exc, Interrupted):
        return "interrupted"
    if isinstance(exc, OSError) and exc.filename:
        return f"{exc.strerror}: {exc.filename}"
    if isinstance(exc, OSError):
        return str(exc.strerror)
    return str(exc)


def discard(layout: Layout, version_id: str) -> None:
    """REQ-INST-5 step 5: best-effort removal of an unused build."""
    remove_path(temp_link(layout, version_id))
    remove_path(layout.versions / version_id)


def failed_step(layout, version_id, exc) -> StepOutcome:
    """Classify a failure as before or after the switch."""
    if managed_id(layout) == version_id:
        return StepOutcome(True, reason(exc), (), version_id)
    discard(layout, version_id)
    return StepOutcome(False, reason(exc), (), None)


def switch_step(layout, current, want) -> StepOutcome:
    """Build, switch and clean one new version."""
    version_id = new_id(layout)
    try:
        build(layout, current, want, version_id)
        switch(layout, version_id)
        warnings = clean(layout, current.version_id)
    except (OSError, Interrupted) as exc:
        return failed_step(layout, version_id, exc)
    return StepOutcome(True, None, warnings, version_id)


def remove_step(layout) -> StepOutcome:
    """The empty result: remove $INSTALL and $VERSIONS."""
    try:
        warnings = remove_all(layout)
    except (OSError, Interrupted) as exc:
        gone = not os.path.lexists(layout.install)
        return StepOutcome(gone, reason(exc), (), None)
    return StepOutcome(True, None, warnings, None)


def apply_tree(layout: Layout, current, want: Tree) -> StepOutcome:
    """The file step: no-op, removal, or build and switch."""
    if dict(want) == dict(current.tree):
        return StepOutcome(False, None, (), current.version_id)
    if not want:
        return remove_step(layout)
    return switch_step(layout, current, want)
