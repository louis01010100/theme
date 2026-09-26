"""Headless Neovim dumps and the REQ-NVIM-10 reference snapshot."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import support

DUMP_SCRIPT = support.REPO / "tests" / "nvim_dump.lua"
REFERENCE = support.REPO / "tests" / "reference" / "nvim-highlights.json"
REFERENCE_REL = "tests/reference/nvim-highlights.json"
COLOUR_ATTRIBUTES = ("fg", "bg", "sp")
OPTS = {False: "{ transparent = false }", True: "{ transparent = true }"}


@dataclass(frozen=True)
class NeovimRun:
    """How one headless Neovim loads the colorscheme."""

    root: str
    opts: str = "nil"
    prelude: str = ""
    postlude: str = ""


@dataclass(frozen=True)
class Baseline:
    """The committed reference snapshot (REQ-NVIM-10 (b))."""

    palette_sha256: str
    neovim: str
    opaque: dict
    transparent: dict

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, indent=2,
                          ensure_ascii=False) + "\n"


def nvim_env(spec: NeovimRun, out) -> dict:
    """Outer PATH/locale plus the dump parameters; scratch HOME."""
    home = out.parent / "home"
    home.mkdir()
    return dict(support.base_vars(), HOME=str(home),
                XDG_CONFIG_HOME=str(home / "config"),
                XDG_DATA_HOME=str(home / "data"),
                XDG_STATE_HOME=str(home / "state"),
                XDG_CACHE_HOME=str(home / "cache"),
                UKIYO_E_ROOT=spec.root,
                UKIYO_E_OPTS=spec.opts, UKIYO_E_PRELUDE=spec.prelude,
                UKIYO_E_POSTLUDE=spec.postlude, UKIYO_E_DUMP_OUT=str(out))


def nvim_dump(spec: NeovimRun) -> dict:
    """Run nvim_dump.lua in a clean headless Neovim; parse its JSON."""
    out = support.scratch_dir() / "dump.json"
    argv = ["nvim", "--clean", "--headless",
            "-c", f"luafile {DUMP_SCRIPT}", "-c", "qa!"]
    try:
        result = support.run(argv, env=nvim_env(spec, out), stdin="")
        if not out.exists():
            raise AssertionError(f"no dump: {result.stderr}")
        return json.loads(out.read_text())
    finally:
        support.remove_dir(out.parent)


def baseline_dumps(install) -> dict:
    """The dumps for transparent false and true of an install."""
    return {t: nvim_dump(NeovimRun(str(install), opts))
            for t, opts in OPTS.items()}


def hex_attrs(attrs: dict) -> dict:
    """An attribute map without `default`, colours as `#rrggbb`."""
    if not isinstance(attrs, dict):
        return {}
    return {k: f"#{v:06x}" if k in COLOUR_ATTRIBUTES else v
            for k, v in attrs.items() if k != "default"}


def theme_set_part(dump: dict) -> dict:
    """The theme-set groups of a dump, in snapshot form."""
    groups = dump["groups"]
    return {name: hex_attrs(groups.get(name, {}))
            for name in dump["theme_set"]}


def allowed_colours(root=support.REPO) -> set:
    """The 16 slot and 8 shade values of a tree's palette."""
    from configurator import palette

    colours = support.repo_palette(root)
    return ({colours.colors[s] for s in palette.SLOTS}
            | set(colours.shades.values()))


def link_end(groups: dict, name: str):
    """Follow `link` from a group; the last group name reached."""
    lower = {k.lower(): k for k in groups}
    seen = set()
    while name not in seen:
        seen.add(name)
        target = groups.get(name, {}).get("link")
        if target is None:
            return name
        name = lower.get(target.lower(), target)
    return name


def closure_errors(dump: dict, allowed: set) -> list:
    """REQ-NVIM-10 (a) violations of one dump."""
    groups = {k: hex_attrs(v) for k, v in dump["groups"].items()}
    theme_set = set(dump["theme_set"])
    errors = []
    for name in sorted(theme_set):
        end = link_end(groups, name)
        checked = [name] if end in theme_set else [name, end]
        for group in checked:
            for key in COLOUR_ATTRIBUTES:
                value = groups.get(group, {}).get(key)
                if value is not None and value not in allowed:
                    errors.append(f"{name}: {group}.{key} = {value}")
    return errors


def palette_sha256(root=support.REPO) -> str:
    data = (Path(root) / "palette.toml").read_bytes()
    return hashlib.sha256(data).hexdigest()


def neovim_version() -> str:
    return support.run(["nvim", "--version"]).stdout.splitlines()[0]


def make_baseline(dumps: dict, root=support.REPO) -> Baseline:
    return Baseline(palette_sha256(root), neovim_version(),
                    theme_set_part(dumps[False]),
                    theme_set_part(dumps[True]))


def snapshot_problem(path=REFERENCE, root=support.REPO):
    """Why the snapshot does not belong to root's palette, or None."""
    if not Path(path).is_file():
        return f"{REFERENCE_REL}: missing"
    data = json.loads(Path(path).read_text())
    if data.get("palette_sha256") != palette_sha256(root):
        return (f"{REFERENCE_REL}: generated from a different "
                "palette.toml; review and regenerate")
    return None
