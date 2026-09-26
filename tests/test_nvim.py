"""V-6: the installed colorscheme against kanagawa-dragon; setup."""

import json
import os
import re
import unittest
from dataclasses import dataclass

import support
from configurator import terminal_ansi

DUMP_SCRIPT = support.REPO / "tests" / "nvim_dump.lua"
HIGHLIGHTS = support.REPO / "nvim" / "lua" / "ukiyo_e" / "highlights"


@dataclass(frozen=True)
class NeovimRun:
    """How one headless Neovim loads a colorscheme."""

    side: str
    root: str
    opts: str = "nil"
    prelude: str = ""
    postlude: str = ""


def seed_root():
    """The kanagawa.nvim seed checkout (UKIYO_E_KANAGAWA_SEED)."""
    root = os.environ.get("UKIYO_E_KANAGAWA_SEED", "")
    if not root:
        raise AssertionError("UKIYO_E_KANAGAWA_SEED is not set")
    head = support.run(["git", "-C", root, "rev-parse", "HEAD"])
    if head.stdout.strip() != support.SEED_HASH:
        raise AssertionError(f"seed HEAD is {head.stdout.strip()!r}")
    return root


def nvim_env(spec: NeovimRun, out) -> dict:
    """Outer PATH/locale plus the dump parameters; scratch HOME."""
    home = out.parent / "home"
    home.mkdir()
    return dict(support.base_vars(), HOME=str(home),
                XDG_CONFIG_HOME=str(home / "config"),
                XDG_DATA_HOME=str(home / "data"),
                XDG_STATE_HOME=str(home / "state"),
                XDG_CACHE_HOME=str(home / "cache"),
                UKIYO_E_SIDE=spec.side, UKIYO_E_ROOT=spec.root,
                UKIYO_E_OPTS=spec.opts, UKIYO_E_PRELUDE=spec.prelude,
                UKIYO_E_POSTLUDE=spec.postlude, UKIYO_E_DUMP_OUT=str(out))


def nvim_dump(spec: NeovimRun) -> dict:
    """Run nvim_dump.lua in a clean headless Neovim; parse its JSON."""
    out = support.scratch_dir() / "dump.json"
    argv = ["nvim", "--clean", "--headless",
            "-c", f"luafile {DUMP_SCRIPT}", "-c", "qa!"]
    try:
        result = support.run(argv, env=nvim_env(spec, out), stdin="")
        return json.loads(out.read_text())
    except FileNotFoundError:
        raise AssertionError(f"no dump: {result.stderr}")
    finally:
        support.remove_dir(out.parent)


def install_nvim(owner, root=support.REPO):
    """`configure.py nvim` into a scratch data dir; returns the env."""
    env = support.scratch_env(owner)
    support.configure_ok(env, "nvim", root=root)
    return env


def without_default_flag(groups: dict) -> dict:
    """Groups with the `default` flag removed (compared separately)."""
    return {name: {k: v for k, v in spec.items() if k != "default"}
            if isinstance(spec, dict) else spec
            for name, spec in groups.items()}


def declared_defaults() -> set:
    """Groups the highlight modules declare with `default = true`."""
    text = "".join(p.read_text() for p in HIGHLIGHTS.glob("*.lua"))
    return set(re.findall(r"(\w+) = \{[^}]*default = true", text))


def group_diff(left: dict, right: dict, limit=20) -> list:
    """First differing group names with both specs (default aside)."""
    left, right = without_default_flag(left), without_default_flag(right)
    names = sorted(set(left) | set(right))
    diff = [(n, left.get(n), right.get(n)) for n in names
            if left.get(n) != right.get(n)]
    return diff[:limit]


class InstalledTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = install_nvim(cls)

    def ukiyo(self, opts="nil", prelude="", postlude=""):
        spec = NeovimRun("ukiyo_e", str(self.env.install), opts, prelude,
                         postlude)
        return nvim_dump(spec)


class LoadTest(InstalledTestCase):
    def test_load(self):
        dump = self.ukiyo()
        self.assertNotIn("error", dump)
        self.assertEqual(dump["colors_name"], "ukiyo_e")
        self.assertFalse(dump["kanagawa_loaded"])
        self.assertEqual(dump["kanagawa_files"], 0)

    def test_palette_cache_is_dropped(self):
        postlude = (
            'local p = vim.api.nvim_get_runtime_file('
            '"lua/ukiyo_e/palette.lua", false)[1] '
            'local t = io.open(p):read("a"):gsub("#8ba4b0", "#123456") '
            'os.remove(p) local f = io.open(p, "w") f:write(t) f:close() '
            'vim.cmd.colorscheme("ukiyo_e")')
        env = install_nvim(self)
        spec = NeovimRun("ukiyo_e", str(env.install), postlude=postlude)
        dump = nvim_dump(spec)
        self.assertNotIn("error", dump)
        self.assertEqual(dump["terminal"][4].lower(), "#123456")
        self.assertEqual(dump["palette"]["dragonBlue2"], "#123456")
        fgs = {s.get("fg") for s in dump["groups"].values()}
        self.assertIn(0x123456, fgs)
        self.assertNotIn(0x8BA4B0, fgs)


class EquivalenceTest(InstalledTestCase):
    def assert_equivalent(self, opts):
        seed = nvim_dump(NeovimRun("seed", seed_root(), opts))
        mine = self.ukiyo(opts)
        self.assertNotIn("error", seed)
        self.assertNotIn("error", mine)
        diff = group_diff(seed["groups"], mine["groups"])
        self.assertEqual(diff, [], f"{len(diff)} shown")
        self.assertGreater(len(mine["groups"]), 700)
        for name in declared_defaults():
            self.assertIs(mine["groups"][name].get("default"), True, name)

    def test_equivalence_opaque(self):
        self.assert_equivalent("{ transparent = false }")

    def test_equivalence_transparent(self):
        self.assert_equivalent("{ transparent = true }")

    def test_terminal_colors(self):
        expected = list(terminal_ansi.resolve_ansi(support.repo_palette()))
        for opts in ("{ transparent = false }", "{ transparent = true }"):
            terminal = [c.lower() for c in self.ukiyo(opts)["terminal"]]
            self.assertEqual(terminal, expected)


class SetupContractTest(InstalledTestCase):
    def test_transparent_type_error(self):
        dump = self.ukiyo('{ transparent = "yes" }')
        self.assertIn("ukiyo_e.setup: opts.transparent must be a boolean",
                      dump.get("error", ""))

    def test_overrides_type_error(self):
        dump = self.ukiyo("{ overrides = 3 }")
        self.assertIn("opts.overrides", dump.get("error", ""))

    def test_opts_type_error(self):
        dump = self.ukiyo('"transparent"')
        self.assertIn("ukiyo_e.setup", dump.get("error", ""))

    def test_unknown_fields_ignored(self):
        self.assertEqual(self.ukiyo("{ foo = 1 }")["groups"],
                         self.ukiyo()["groups"])

    def test_override_changes_only_normal_fg(self):
        opts = ('{ overrides = function(colors) return '
                '{ Normal = { fg = "#ffffff" } } end }')
        groups = self.ukiyo(opts)["groups"]
        self.assertEqual(groups["Normal"]["fg"], 0xFFFFFF)
        postlude = ('local n = vim.api.nvim_get_hl(0, { name = "Normal" })'
                    ' n.fg = 0xffffff vim.api.nvim_set_hl(0, "Normal", n)')
        expected = self.ukiyo(postlude=postlude)["groups"]
        self.assertEqual(group_diff(expected, groups), [])

    def test_override_drops_link(self):
        opts = ('{ overrides = function(colors) return { NormalNC = '
                '{ fg = colors.palette.dragonRed } } end }')
        spec = self.ukiyo(opts)["groups"]["NormalNC"]
        self.assertNotIn("link", spec)
        self.assertEqual(spec["fg"], 0xC4746E)

    def test_override_nil_is_noop(self):
        opts = "{ overrides = function() return nil end }"
        self.assertEqual(self.ukiyo(opts)["groups"],
                         self.ukiyo()["groups"])

    def test_override_non_table_errors(self):
        dump = self.ukiyo('{ overrides = function() return "x" end }')
        self.assertIn("overrides", dump.get("error", ""))

    def test_setup_replaces_config(self):
        prelude = 'require("ukiyo_e").setup({ transparent = true })'
        dump = self.ukiyo("{}", prelude)
        self.assertEqual(dump["groups"], self.ukiyo()["groups"])

    def test_palette_is_a_copy(self):
        prelude = ('require("ukiyo_e").palette().dragonBlue2 = '
                   '"#000000"')
        dump = self.ukiyo("nil", prelude)
        self.assertEqual(dump["groups"], self.ukiyo()["groups"])
        expected = dict(support.repo_palette().colors)
        self.assertEqual(dump["palette"], expected)


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
