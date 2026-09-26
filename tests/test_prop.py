"""V-5: one palette change reaches GNOME, tmux, and Neovim."""

import os
import unittest

import gnome_harness as harness
import support
from nvim_live import NvimServer
from test_cli import blue_copy
from nvim_baseline import NeovimRun, nvim_dump
from configurator import tmux

OLD_BLUE = 0x6f838d
NEW_BLUE = 0x123456
# base0D -> #123456 moves its shade darkBlue #444c52 -> #152536.
BLUE_CHANGE = {OLD_BLUE: NEW_BLUE, 0x444C52: 0x152536}
# base0C -> #123456 moves its shade darkAqua #454c4c -> #152536.
AQUA_CHANGE = {0x728381: 0x123456, 0x454C4C: 0x152536}
COLOUR_ATTRIBUTES = ("fg", "bg", "sp")
UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE = f"{harness.PROFILE_SCHEMA}:{harness.PROFILE_ROOT}:{UUID}/"
RENDERED = ["lua/ukiyo_e/palette.lua", "tmux/colors.conf"]


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


def recoloured(groups: dict, change: dict) -> dict:
    """Baseline groups with every changed colour attribute replaced."""
    result = {}
    for name, spec in groups.items():
        if isinstance(spec, dict):
            spec = {k: change.get(v, v) if k in COLOUR_ATTRIBUTES else v
                    for k, v in spec.items()}
        result[name] = spec
    return result


def uses(spec, change: dict) -> bool:
    return isinstance(spec, dict) and any(
        spec.get(k) in change for k in COLOUR_ATTRIBUTES)


def fresh_dump(install):
    return nvim_dump(NeovimRun(str(install), "{ transparent = false }"))


def gnome_palette(env):
    text = harness.gsettings(env.vars, "get", PROFILE, "palette")
    return [c.strip(" '") for c in text.strip("[]").split(",")]


def status_formats(server) -> dict:
    return {o: server.value(o) for o in tmux.STATUS_OPTIONS}


def changed_lines(old: bytes, new: bytes) -> list:
    old, new = old.split(b"\n"), new.split(b"\n")
    if len(old) != len(new):
        raise AssertionError("line count changed")
    return [(a, b) for a, b in zip(old, new) if a != b]


class PropagationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = support.scratch_env(cls)
        session = harness.start_session(cls, env)
        cls.server = support.TmuxServer.start(cls, env)
        cls.env = cls.server.attach(session)
        support.configure_ok(cls.env, "all")
        cls.pid = cls.server.pid()
        cls.old_status = status_formats(cls.server)
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
        cls.old_gnome = gnome_palette(cls.env)
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
        """V-5: only Color4/Color12 change; no Ptyxis key is written."""
        self.assertEqual(
            changed_lines(self.old_palette, self.palette_file.read_bytes()),
            [(b"Color4=#6f838d", b"Color4=#123456"),
             (b"Color12=#6f838d", b"Color12=#123456")])
        self.assertEqual(harness.dump_ptyxis(self.env.vars),
                         self.ptyxis_dump)

    def test_gnome(self):
        palette = gnome_palette(self.env)
        self.assertEqual(palette[4], "#123456")
        self.assertEqual(palette[12], "#123456")
        changed = [i for i, (a, b) in
                   enumerate(zip(self.old_gnome, palette)) if a != b]
        self.assertEqual(changed, [4, 12])

    def test_tmux_live(self):
        self.assertEqual(self.server.pid(), self.pid)
        self.assertEqual(self.server.value("clock-mode-colour"), "#123456")
        self.assertEqual(self.server.value("pane-active-border-style"),
                         "fg=#123456")
        self.assertEqual(status_formats(self.server), self.old_status)

    def test_fresh_neovim(self):
        new = fresh_dump(self.env.install)
        self.assertEqual(new["terminal"][4].lower(), "#123456")
        self.assertEqual(new["terminal"][12].lower(), "#123456")
        changed = [n for n, s in self.base["groups"].items()
                   if uses(s, BLUE_CHANGE)]
        self.assertGreater(len(changed), 10)
        self.assertEqual(new["groups"],
                         recoloured(self.base["groups"], BLUE_CHANGE))

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


def aqua_copy(owner):
    """A scratch repository copy with base0C changed to #123456."""
    root = support.copy_repo()
    support.later(owner, support.remove_tree, root)
    support.replace_line(root / "palette.toml", "base0C ",
                         'base0C = "#123456"')
    return root


def dconf_changes(before: str, after: str) -> dict:
    """section -> changed keys between two dconf dumps."""
    old, new = support.parse_dump(before), support.parse_dump(after)
    found = {}
    for section in set(old) | set(new):
        a, b = old.get(section, {}), new.get(section, {})
        keys = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        if keys:
            found[section] = keys
    return found


class ShadePropagationTest(unittest.TestCase):
    """V-5 (b): a slot change reaches its derived shade everywhere."""

    @classmethod
    def setUpClass(cls):
        env = support.scratch_env(cls)
        session = harness.start_session(cls, env)
        cls.server = support.TmuxServer.start(cls, env)
        cls.env = cls.server.attach(session)
        support.configure_ok(cls.env, "all")
        cls.base = fresh_dump(cls.env.install)
        cls.gnome = harness.dump(cls.env.vars)
        cls.palette_file = support.ptx(cls.env) / "Ukiyo-e.palette"
        cls.old_palette = cls.palette_file.read_bytes()
        cls.tmux = cls.server.snapshot()
        support.configure_ok(cls.env, "all", root=aqua_copy(cls))

    def test_gnome(self):
        palette = gnome_palette(self.env)
        self.assertEqual((palette[6], palette[14]),
                         ("#123456", "#123456"))
        changes = dconf_changes(self.gnome, harness.dump(self.env.vars))
        self.assertEqual(list(changes.values()), [["palette"]])

    def test_ptyxis_file(self):
        self.assertEqual(
            changed_lines(self.old_palette, self.palette_file.read_bytes()),
            [(b"Color6=#728381", b"Color6=#123456"),
             (b"Color14=#728381", b"Color14=#123456")])

    def test_tmux(self):
        after = self.server.snapshot()
        self.assertEqual(support.changed_options(self.tmux, after),
                         {"mode-style"})
        self.assertEqual(self.server.value("mode-style"),
                         "fg=#b2b4b2,bg=#152536")

    def test_fresh_neovim(self):
        new = fresh_dump(self.env.install)
        changed = [n for n, s in self.base["groups"].items()
                   if uses(s, AQUA_CHANGE)]
        self.assertTrue(changed)
        self.assertEqual(new["groups"],
                         recoloured(self.base["groups"], AQUA_CHANGE))
        self.assertEqual(new["groups"]["Search"]["bg"], 0x152536)


def segment_copy(owner):
    """A scratch repository copy with base01 changed to #123456."""
    root = support.copy_repo()
    support.later(owner, support.remove_tree, root)
    support.replace_line(root / "palette.toml", "base01 ",
                         'base01 = "#123456"')
    return root


class StatusBarPropagationTest(unittest.TestCase):
    """V-5 (c): a status-layout colour reaches the running bar."""

    @classmethod
    def setUpClass(cls):
        env = support.scratch_env(cls)
        cls.server = support.TmuxServer.start(cls, env)
        cls.env = cls.server.attach(env)
        support.configure_ok(cls.env, "tmux")
        cls.pid = cls.server.pid()
        cls.old_status = status_formats(cls.server)
        cls.tmux = cls.server.snapshot()
        cls.old_tree = support.tree_snapshot(cls.env.install.resolve())
        support.configure_ok(cls.env, "tmux", root=segment_copy(cls))

    def test_formats(self):
        self.assertEqual(self.server.pid(), self.pid)
        expected = {o: v.replace("bg=#2e2d2c", "bg=#123456")
                    for o, v in self.old_status.items()}
        self.assertNotEqual(expected, self.old_status)
        self.assertEqual(status_formats(self.server), expected)

    def test_only_bar_style_changed(self):
        changed = support.changed_options(self.tmux,
                                          self.server.snapshot())
        self.assertEqual(changed & set(tmux.STYLE_OPTIONS),
                         {"status-style"})
        self.assertEqual(self.server.value("status-style"),
                         "fg=#b2b4b2,bg=#123456")

    def test_only_tmux_conf_files_differ(self):
        new_tree = support.tree_snapshot(self.env.install.resolve())
        self.assertEqual(sorted(new_tree), sorted(self.old_tree))
        differ = sorted(k for k in new_tree
                        if new_tree[k][3] != self.old_tree[k][3])
        self.assertEqual(differ, ["tmux/colors.conf",
                                  "tmux/status.conf"])


if __name__ == "__main__":
    unittest.main()
