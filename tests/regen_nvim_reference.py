"""Regenerate the Neovim reference snapshot (REQ-NVIM-10 (c)).

Usage: python3 tests/regen_nvim_reference.py [--output PATH]

Installs this tree's `nvim` target into a scratch XDG_DATA_HOME, dumps
the colorscheme in a clean headless Neovim for transparent false and
true, checks closure, and only then writes the snapshot atomically.
Run it after a deliberate change to palette.toml, the theme layer, or
the highlight modules; review the diff and commit it with the change.
"""

import argparse
import os
import sys
from pathlib import Path

import support
from nvim_baseline import (REFERENCE, allowed_colours, baseline_dumps,
                           closure_errors, make_baseline)


def scratch_vars(folder: Path) -> dict:
    """Scratch HOME and XDG directories; no TMUX, no D-Bus."""
    for name in ("home", "data", "config", "runtime"):
        (folder / name).mkdir(mode=0o700)
    return dict(support.base_vars(), HOME=str(folder / "home"),
                XDG_DATA_HOME=str(folder / "data"),
                XDG_CONFIG_HOME=str(folder / "config"),
                XDG_RUNTIME_DIR=str(folder / "runtime"))


def take_dumps(folder: Path) -> dict:
    """`configure.py nvim` into folder, then the two dumps."""
    env = scratch_vars(folder)
    argv = [sys.executable, str(support.REPO / "configure.py"), "nvim"]
    result = support.run(argv, cwd=str(folder), env=env, stdin="")
    if result.code != 0:
        raise SystemExit(f"configure.py nvim failed ({result.code}):\n"
                         f"{result.stdout}{result.stderr}")
    return baseline_dumps(Path(env["XDG_DATA_HOME"]) / "ukiyo_e")


def problems(dumps: dict) -> list:
    """Load errors and closure violations of both dumps."""
    allowed = allowed_colours()
    found = []
    for transparent, dump in dumps.items():
        if "error" in dump:
            found.append(f"transparent={transparent}: {dump['error']}")
        else:
            found += [f"transparent={transparent}: {line}"
                      for line in closure_errors(dump, allowed)]
    return found


def write_atomic(path: Path, text: str) -> None:
    temp = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temp, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=REFERENCE)
    args = parser.parse_args(argv)
    folder = support.scratch_dir()
    try:
        dumps = take_dumps(folder)
    finally:
        support.remove_dir(folder)
    found = problems(dumps)
    if found:
        for line in found:
            print(f"closure: {line}", file=sys.stderr)
        print("refusing to write the snapshot", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(args.output, make_baseline(dumps).to_json())
    return 0


if __name__ == "__main__":
    sys.exit(main())
