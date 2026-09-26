"""V-5: one palette change reaches GNOME, tmux, and Neovim."""

import os
import unittest

import gnome_harness as harness
import support
from nvim_live import NvimServer
from test_cli import blue_copy
from test_nvim import NeovimRun, nvim_dump

OLD_BLUE = 0x8BA4B0
NEW_BLUE = 0x123456
COLOUR_ATTRIBUTES = ("fg", "bg", "sp")
UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE = f"{harness.PROFILE_SCHEMA}:{harness.PROFILE_ROOT}:{UUID}/"
RENDERED = ["lua/ukiyo_e/palette.lua", "tmux/colors.conf",
            "tmux/status-plain.conf", "tmux/status.conf"]


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


def recoloured(groups: dict) -> dict:
    """Baseline groups with every old-blue attribute set to new blue."""
    result = {}
    for name, spec in groups.items():
        if isinstance(spec, dict):
            spec = {k: NEW_BLUE if k in COLOUR_ATTRIBUTES and v == OLD_BLUE
                    else v for k, v in spec.items()}
        result[name] = spec
    return result


def uses_old_blue(spec) -> bool:
    return isinstance(spec, dict) and any(
        spec.get(k) == OLD_BLUE for k in COLOUR_ATTRIBUTES)


def fresh_dump(install):
    return nvim_dump(NeovimRun("ukiyo_e", str(install),
                               "{ transparent = false }"))


class PropagationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = support.scratch_env(cls)
        session = harness.start_session(cls, env)
        cls.server = support.TmuxServer.start(cls, env)
        cls.env = cls.server.attach(session)
        support.configure_ok(cls.env, "all")
        cls.pid = cls.server.pid()
        cls.old_dir = cls.env.install.resolve()
        cls.old_tree = support.tree_snapshot(cls.old_dir)
        cls.base = fresh_dump(cls.env.install)
        cls.nvim = cls.start_nvim()
        cls.group = next(n for n, s in sorted(cls.base["groups"].items())
                         if isinstance(s, dict) and s.get("fg") == OLD_BLUE)
        cls.before_fg = cls.nvim.group_fg(cls.group)
        cls.palette_file = support.ptx(cls.env) / "Ukiyo-e.palette"
        cls.old_palette = cls.palette_file.read_bytes()
        cls.ptyxis_dump = harness.dump_ptyxis(cls.env.vars)
        cls.result = support.configure_ok(cls.env, "all",
                                          root=blue_copy(cls))

    @classmethod
    def start_nvim(cls):
        home = cls.env.root / "nvim-home"
        home.mkdir()
        env = dict(support.base_vars(), HOME=str(home),
                   XDG_STATE_HOME=str(home / "state"))
        return NvimServer.start(cls, cls.env.install,
                                cls.env.vars["TMUX_TMPDIR"], env)

    def test_report(self):
        lines = self.result.stdout.splitlines()
        self.assertEqual([ln for ln in lines if not ln.startswith(" ")],
                         ["gnome: updated", "ptyxis: updated",
                          "tmux: updated", "nvim: updated"])
        at = lines.index("ptyxis: updated")
        self.assertEqual(lines[at + 1:at + 3], [
            "  write palette Ukiyo-e.palette", "tmux: updated"])

    def test_ptyxis_file(self):
        """V-5: only Color4 changes; no Ptyxis key is written."""
        old = self.old_palette.split(b"\n")
        new = self.palette_file.read_bytes().split(b"\n")
        self.assertEqual(len(old), len(new))
        self.assertEqual([(a, b) for a, b in zip(old, new) if a != b],
                         [(b"Color4=#8ba4b0", b"Color4=#123456")])
        self.assertEqual(harness.dump_ptyxis(self.env.vars),
                         self.ptyxis_dump)

    def test_gnome(self):
        text = harness.gsettings(self.env.vars, "get", PROFILE, "palette")
        palette = [c.strip(" '") for c in text.strip("[]").split(",")]
        self.assertEqual(palette[4], "#123456")

    def test_tmux_live(self):
        self.assertEqual(self.server.pid(), self.pid)
        self.assertEqual(self.server.value("clock-mode-colour"), "#123456")
        self.assertEqual(self.server.value("pane-active-border-style"),
                         "fg=#123456")
        for option in ("status-left", "status-right"):
            self.assertIn("bg=#123456", self.server.value(option))

    def test_fresh_neovim(self):
        new = fresh_dump(self.env.install)
        self.assertEqual(new["terminal"][4].lower(), "#123456")
        changed = [n for n, s in self.base["groups"].items()
                   if uses_old_blue(s)]
        self.assertGreater(len(changed), 10)
        self.assertEqual(new["groups"], recoloured(self.base["groups"]))

    def test_version_diff(self):
        new_dir = self.env.install.resolve()
        self.assertNotEqual(new_dir, self.old_dir)
        self.assertFalse(os.path.lexists(self.old_dir))
        new_tree = support.tree_snapshot(new_dir)
        self.assertEqual(sorted(new_tree), sorted(self.old_tree))
        differ = sorted(k for k in new_tree
                        if new_tree[k][3] != self.old_tree[k][3])
        self.assertEqual(differ, RENDERED)
        self.assertEqual(os.listdir(self.env.versions), [new_dir.name])

    def test_running_neovim(self):
        self.assertEqual(self.before_fg, OLD_BLUE)
        self.nvim.colorscheme()
        self.assertEqual(self.nvim.group_fg(self.group), NEW_BLUE)
        self.assertEqual(self.nvim.lua("vim.g.terminal_color_4"),
                         "#123456")


if __name__ == "__main__":
    unittest.main()
