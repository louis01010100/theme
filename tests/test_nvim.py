"""V-NVIM: load, equivalence with kanagawa-dragon, setup contract."""

import json
import os
import re
import unittest
from dataclasses import dataclass

import support

DUMP_SCRIPT = support.REPO / "tests" / "nvim_dump.lua"


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


def nvim_dump(spec: NeovimRun) -> dict:
    """Run nvim_dump.lua in a clean headless Neovim; parse its JSON."""
    out = support.scratch_dir() / "dump.json"
    env = dict(os.environ, UKIYO_E_SIDE=spec.side, UKIYO_E_ROOT=spec.root,
               UKIYO_E_OPTS=spec.opts, UKIYO_E_PRELUDE=spec.prelude,
               UKIYO_E_POSTLUDE=spec.postlude,
               UKIYO_E_DUMP_OUT=str(out))
    argv = ["nvim", "--clean", "--headless",
            "-c", f"luafile {DUMP_SCRIPT}", "-c", "qa!"]
    result = support.run(argv, env=env, stdin="")
    try:
        return json.loads(out.read_text())
    except FileNotFoundError:
        raise AssertionError(f"no dump: {result.stderr}")
    finally:
        support.remove_dir(out.parent)


def ukiyo(opts="nil", prelude="", postlude=""):
    spec = NeovimRun("ukiyo_e", str(support.REPO), opts, prelude, postlude)
    return nvim_dump(spec)


def without_default_flag(groups: dict) -> dict:
    """Groups with the `default` flag removed.

    Neovim clears the flag of a `default = true` link when Normal is set
    after it, so kanagawa's own dump varies with Lua table iteration
    order; the flag is therefore compared separately.
    """
    return {name: {k: v for k, v in spec.items() if k != "default"}
            if isinstance(spec, dict) else spec
            for name, spec in groups.items()}


def declared_defaults() -> set:
    """Groups the highlight modules declare with `default = true`."""
    folder = support.REPO / "lua/ukiyo_e/highlights"
    text = "".join(p.read_text() for p in folder.glob("*.lua"))
    return set(re.findall(r"(\w+) = \{[^}]*default = true", text))


def group_diff(left: dict, right: dict, limit=20) -> list:
    """First differing group names with both specs (default flag aside)."""
    left, right = without_default_flag(left), without_default_flag(right)
    names = sorted(set(left) | set(right))
    diff = [(n, left.get(n), right.get(n)) for n in names
            if left.get(n) != right.get(n)]
    return diff[:limit]


class LoadTest(unittest.TestCase):
    def test_load(self):
        dump = ukiyo()
        self.assertNotIn("error", dump)
        self.assertEqual(dump["colors_name"], "ukiyo_e")
        self.assertFalse(dump["kanagawa_loaded"])
        self.assertEqual(dump["kanagawa_files"], 0)


class EquivalenceTest(unittest.TestCase):
    def assert_equivalent(self, opts):
        seed = nvim_dump(NeovimRun("seed", seed_root(), opts))
        mine = ukiyo(opts)
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
        for opts in ("{ transparent = false }", "{ transparent = true }"):
            terminal = [c.lower() for c in ukiyo(opts)["terminal"]]
            self.assertEqual(terminal, support.resolved_ansi())


class SetupContractTest(unittest.TestCase):
    def test_transparent_type_error(self):
        dump = ukiyo('{ transparent = "yes" }')
        self.assertIn("ukiyo_e.setup: opts.transparent must be a boolean",
                      dump.get("error", ""))

    def test_overrides_type_error(self):
        dump = ukiyo("{ overrides = 3 }")
        self.assertIn("opts.overrides", dump.get("error", ""))

    def test_opts_type_error(self):
        dump = ukiyo('"transparent"')
        self.assertIn("ukiyo_e.setup", dump.get("error", ""))

    def test_unknown_fields_ignored(self):
        self.assertEqual(ukiyo("{ foo = 1 }")["groups"], ukiyo()["groups"])

    def test_override_changes_only_normal_fg(self):
        opts = ('{ overrides = function(colors) return '
                '{ Normal = { fg = "#ffffff" } } end }')
        groups = ukiyo(opts)["groups"]
        self.assertEqual(groups["Normal"]["fg"], 0xFFFFFF)
        # Expected: the default load, then only Normal's fg changed
        # (Neovim re-derives built-ins that use Normal's colours).
        postlude = ('local n = vim.api.nvim_get_hl(0, { name = "Normal" })'
                    ' n.fg = 0xffffff vim.api.nvim_set_hl(0, "Normal", n)')
        expected = ukiyo(postlude=postlude)["groups"]
        self.assertEqual(group_diff(expected, groups), [])

    def test_override_drops_link(self):
        opts = ('{ overrides = function(colors) return { NormalNC = '
                '{ fg = colors.palette.dragonRed } } end }')
        spec = ukiyo(opts)["groups"]["NormalNC"]
        self.assertNotIn("link", spec)
        self.assertEqual(spec["fg"], 0xC4746E)

    def test_override_nil_is_noop(self):
        opts = "{ overrides = function() return nil end }"
        self.assertEqual(ukiyo(opts)["groups"], ukiyo()["groups"])

    def test_override_non_table_errors(self):
        dump = ukiyo('{ overrides = function() return "x" end }')
        self.assertIn("overrides", dump.get("error", ""))

    def test_setup_replaces_config(self):
        prelude = 'require("ukiyo_e").setup({ transparent = true })'
        dump = ukiyo("{}", prelude)
        self.assertEqual(dump["groups"], ukiyo()["groups"])

    def test_palette_is_a_copy(self):
        prelude = ('require("ukiyo_e").palette().dragonBlue2 = '
                   '"#000000"')
        dump = ukiyo("nil", prelude)
        self.assertEqual(dump["groups"], ukiyo()["groups"])
        doc = support.load_palette_toml()
        expected = {k: v.lower() for k, v in doc["palette"].items()}
        self.assertEqual(dump["palette"], expected)


if __name__ == "__main__":
    unittest.main()
