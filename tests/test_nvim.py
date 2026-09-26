"""V-6: the installed colorscheme, its baseline, and setup()."""

import json
import sys
import unittest

import support
from configurator import palette, terminal_ansi
from nvim_baseline import (REFERENCE, NeovimRun, allowed_colours,
                           baseline_dumps, closure_errors, nvim_dump,
                           palette_sha256, snapshot_problem,
                           theme_set_part)

REGEN = "tests/regen_nvim_reference.py"
MISMATCH = ("tests/reference/nvim-highlights.json: generated from a "
            "different palette.toml; review and regenerate")
# Data Model Theme-layer table (REQ-NVIM-3).
THEME_LAYER = {
    "ui": {
        "fg": "base07", "fg_dim": "base07", "fg_reverse": "shadowBlue",
        "bg_dim": "base00", "bg_gutter": "base01", "bg_m3": "base00",
        "bg_m2": "base00", "bg_m1": "base00", "bg": "base00",
        "bg_p1": "base01", "bg_p2": "base02", "special": "base04",
        "whitespace": "base03", "nontext": "base03",
        "bg_visual": "shadowBlue", "bg_search": "shadowAqua",
        "pmenu": {
            "fg": "base07", "fg_sel": "none", "bg": "shadowBlue",
            "bg_sel": "shadowAqua", "bg_thumb": "shadowAqua",
            "bg_sbar": "shadowBlue",
        },
        "float": {
            "fg": "base07", "bg": "base00", "fg_border": "base03",
            "bg_border": "base00",
        },
    },
    "syn": {
        "string": "base0B", "variable": "none", "number": "base0F",
        "constant": "base09", "identifier": "base0A",
        "parameter": "base06", "fun": "base0D", "statement": "base0E",
        "keyword": "base0E", "operator": "base08", "preproc": "base08",
        "type": "base0C", "regex": "base08", "deprecated": "base04",
        "punct": "base05", "comment": "base04", "special1": "base0E",
        "special2": "base08", "special3": "base08",
    },
    "diag": {
        "error": "base08", "ok": "base0B", "warning": "base09",
        "info": "base0D", "hint": "base0C",
    },
    "diff": {
        "add": "shadowGreen", "delete": "shadowRed",
        "change": "shadowBlue", "text": "shadowYellow",
    },
    "vcs": {"added": "base0B", "removed": "base08", "changed": "base0A"},
}


def resolved_layer(layer: dict, colours) -> dict:
    """THEME_LAYER with every colour name resolved to hex."""
    return {key: resolved_layer(value, colours)
            if isinstance(value, dict)
            else value if value == "none"
            else palette.resolve(colours, value)
            for key, value in layer.items()}


def install_nvim(owner, root=support.REPO):
    """`configure.py nvim` into a scratch data dir; returns the env."""
    env = support.scratch_env(owner)
    support.configure_ok(env, "nvim", root=root)
    return env


def as_int(colour: str) -> int:
    return int(colour[1:], 16)


def without_default_flag(groups: dict) -> dict:
    """Groups with the `default` flag removed (compared separately)."""
    return {name: {k: v for k, v in spec.items() if k != "default"}
            if isinstance(spec, dict) else spec
            for name, spec in groups.items()}


def group_diff(left: dict, right: dict, limit=20) -> list:
    """First differing group names with both specs (default aside)."""
    left, right = without_default_flag(left), without_default_flag(right)
    names = sorted(set(left) | set(right))
    diff = [(n, left.get(n), right.get(n)) for n in names
            if left.get(n) != right.get(n)]
    return diff[:limit]


def distinct_slots() -> dict:
    """16 slot values whose 24 slot and shade values all differ."""
    return {slot: f"#{0x10 + i * i:02x}{0x20 + 5 * i:02x}"
                  f"{0x30 + 3 * i:02x}"
            for i, slot in enumerate(palette.SLOTS)}


class InstalledTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.env = install_nvim(cls)

    def ukiyo(self, opts="nil", prelude="", postlude=""):
        spec = NeovimRun(str(self.env.install), opts, prelude, postlude)
        return nvim_dump(spec)


class BaselineTest(InstalledTestCase):
    """V-6 (a)-(e) on one install of the committed palette."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dumps = baseline_dumps(cls.env.install)
        cls.colours = support.repo_palette()

    def test_loaded(self):
        for t, dump in self.dumps.items():
            self.assertNotIn("error", dump, t)
            self.assertEqual(len(dump["theme_set"]), 572, t)

    def test_closure(self):
        allowed = allowed_colours()
        self.assertEqual(len(allowed), 24)
        for t, dump in self.dumps.items():
            with self.subTest(transparent=t):
                self.assertEqual(closure_errors(dump, allowed), [])

    def test_snapshot(self):
        self.assertIsNone(snapshot_problem())
        data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        self.assertEqual(sorted(data), ["neovim", "opaque",
                                        "palette_sha256", "transparent"])
        self.assertEqual(data["palette_sha256"], palette_sha256())
        self.assertEqual(data["opaque"], theme_set_part(self.dumps[False]))
        self.assertEqual(data["transparent"],
                         theme_set_part(self.dumps[True]))

    def test_snapshot_format(self):
        text = REFERENCE.read_bytes().decode("utf-8")
        canonical = json.dumps(json.loads(text), sort_keys=True, indent=2,
                               ensure_ascii=False) + "\n"
        self.assertEqual(text, canonical)

    def test_normal(self):
        for t, dump in self.dumps.items():
            normal = dump["groups"]["Normal"]
            self.assertEqual(normal["fg"],
                             as_int(self.colours.colors["base07"]), t)
        self.assertEqual(self.dumps[False]["groups"]["Normal"]["bg"],
                         as_int(self.colours.colors["base00"]))

    def test_terminal_colors(self):
        expected = list(terminal_ansi.resolve_ansi(self.colours))
        for t, dump in self.dumps.items():
            terminal = [c.lower() for c in dump["terminal"]]
            self.assertEqual(terminal, expected, t)

    def test_theme_layer(self):
        expected = resolved_layer(THEME_LAYER, self.colours)
        for t, dump in self.dumps.items():
            self.assertEqual(dump["theme"], expected, t)


class SnapshotProblemTest(unittest.TestCase):
    def test_sha_mismatch_message(self):
        folder = support.scratch_dir()
        self.addCleanup(support.remove_dir, folder)
        path = folder / "nvim-highlights.json"
        data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        data["palette_sha256"] = "0" * 64
        path.write_text(json.dumps(data))
        self.assertEqual(snapshot_problem(path), MISMATCH)


class DistinctClosureTest(unittest.TestCase):
    """V-6 (a), second case: closure not by coincidence of v1."""

    def test_closure(self):
        root = support.copy_repo()
        self.addCleanup(support.remove_tree, root)
        for slot, value in distinct_slots().items():
            support.replace_line(root / "palette.toml", f"{slot} ",
                                 f'{slot} = "{value}"')
        allowed = allowed_colours(root)
        self.assertEqual(len(allowed), 24)
        env = install_nvim(self, root)
        for t, dump in baseline_dumps(env.install).items():
            with self.subTest(transparent=t):
                self.assertNotIn("error", dump)
                self.assertEqual(closure_errors(dump, allowed), [])


class LoadTest(InstalledTestCase):
    def test_load(self):
        dump = self.ukiyo()
        self.assertNotIn("error", dump)
        self.assertEqual(dump["colors_name"], "ukiyo_e")
        self.assertFalse(dump["kanagawa_loaded"])
        self.assertEqual(dump["kanagawa_files"], 0)
        self.assertEqual(dump["palette"],
                         dict(support.repo_palette().colors))
        self.assertEqual(sorted(dump["palette"]), sorted(palette.SLOTS))

    def test_palette_cache_is_dropped(self):
        postlude = (
            'local p = vim.api.nvim_get_runtime_file('
            '"lua/ukiyo_e/palette.lua", false)[1] '
            'local t = io.open(p):read("a"):gsub("#668696", "#123456") '
            'os.remove(p) local f = io.open(p, "w") f:write(t) f:close() '
            'vim.cmd.colorscheme("ukiyo_e")')
        env = install_nvim(self)
        spec = NeovimRun(str(env.install), postlude=postlude)
        dump = nvim_dump(spec)
        self.assertNotIn("error", dump)
        self.assertEqual(dump["terminal"][4].lower(), "#123456")
        self.assertEqual(dump["palette"]["base0D"], "#123456")
        fgs = {s.get("fg") for s in dump["groups"].values()
               if isinstance(s, dict)}
        self.assertIn(0x123456, fgs)
        self.assertNotIn(0x668696, fgs)


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
                '{ fg = colors.palette.base08 } } end }')
        spec = self.ukiyo(opts)["groups"]["NormalNC"]
        self.assertNotIn("link", spec)
        self.assertEqual(spec["fg"], 0xAE4E47)

    def test_overrides_receive_shades(self):
        opts = ('{ overrides = function(colors) return { NormalNC = '
                '{ fg = colors.shades.shadowBlue, '
                'bg = colors.theme.ui.bg_p2 } } end }')
        spec = self.ukiyo(opts)["groups"]["NormalNC"]
        self.assertEqual((spec["fg"], spec["bg"]), (0x3F4E56, 0x393836))

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
        prelude = 'require("ukiyo_e").palette().base0D = "#000000"'
        dump = self.ukiyo("nil", prelude)
        self.assertEqual(dump["groups"], self.ukiyo()["groups"])
        expected = dict(support.repo_palette().colors)
        self.assertEqual(dump["palette"], expected)


class RegenTest(unittest.TestCase):
    """V-6 (g): tests/regen_nvim_reference.py."""

    def regen(self, root, out):
        argv = [sys.executable, str(root / REGEN), "--output", str(out)]
        return support.run(argv, env=support.base_vars(), stdin="")

    def test_byte_identical(self):
        folder = support.scratch_dir()
        self.addCleanup(support.remove_dir, folder)
        out = folder / "out.json"
        result = self.regen(support.REPO, out)
        self.assertEqual(result.code, 0, result.stderr)
        self.assertEqual(out.read_bytes(), REFERENCE.read_bytes())
        self.assertEqual([p.name for p in folder.iterdir()], ["out.json"])

    def test_refuses_closure_failure(self):
        root = support.copy_repo()
        self.addCleanup(support.remove_tree, root)
        toml = root / "palette.toml"
        toml.write_text(toml.read_text() + 'rust = "#b7410e"\n')
        theme = root / "nvim/lua/ukiyo_e/theme.lua"
        source = theme.read_text()
        self.assertIn("fg = palette.base07,", source)
        theme.write_text(source.replace("fg = palette.base07,",
                                        "fg = palette.rust,", 1))
        folder = support.scratch_dir()
        self.addCleanup(support.remove_dir, folder)
        out = folder / "out.json"
        out.write_bytes(b"previous\n")
        result = self.regen(root, out)
        self.assertNotEqual(result.code, 0)
        self.assertIn("#b7410e", result.stderr)
        self.assertEqual(out.read_bytes(), b"previous\n")
        self.assertEqual([p.name for p in folder.iterdir()], ["out.json"])


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
