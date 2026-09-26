"""REQ-MAP: role mappings, templates, and the nvim source tree."""

import ast
import os
import unittest

import support
from configurator import nvim, palette, terminal_ansi, tmux

NAMES = palette.colour_names(
    {"palette": dict.fromkeys(palette.SLOTS, "#000000")})
SPEC_ANSI = (
    "base00", "base08", "base0B", "base0A", "base0D", "base0E",
    "base0C", "base05", "base03", "base08", "base0B", "base0A",
    "base0D", "base0E", "base0C", "base07",
)
SPEC_TERMINAL = {
    "background": "base00", "foreground": "base06",
    "cursor_bg": "base07", "cursor_fg": "base00",
    "selection_bg": "base01", "selection_fg": "base06",
}
SPEC_TMUX = {
    "status_fg": "base07", "status_bg": "base01",
    "window_fg": "base04", "window_bg": "base00",
    "window_current_fg": "base07", "window_current_bg": "base02",
    "window_activity_fg": "base09", "window_activity_bg": "base00",
    "window_bell_fg": "base08", "window_bell_bg": "base00",
    "pane_border_fg": "base02", "pane_active_border_fg": "base0D",
    "message_fg": "base07", "message_bg": "base00",
    "command_fg": "base07", "command_bg": "base00",
    "copy_selection_fg": "base07", "copy_selection_bg": "darkAqua",
    "clock_fg": "base0D", "display_panes_fg": "base03",
    "display_panes_active_fg": "base09",
    "status_text_fg": "base05", "status_segment_bg": "base01",
    "status_block_bg": "base02", "status_separator_fg": "base02",
    "status_current_fg": "base06", "status_current_bg": "darkRed",
}
NOT_A_NAME = "is not a [palette] name or derived shade"
ANSI_MODULE = "configurator/terminal_ansi.py"
PTYXIS_MODULE = "configurator/ptyxis.py"
SPEC_PTYXIS = {"Background": "background", "Foreground": "foreground",
               "Cursor": "cursor_bg"}


def texts(errors):
    return [str(e) for e in errors]


class ConstantsTest(unittest.TestCase):
    def test_v1_values(self):
        self.assertEqual(tuple(terminal_ansi.ANSI), SPEC_ANSI)
        self.assertEqual(dict(terminal_ansi.TERMINAL_ROLES),
                         SPEC_TERMINAL)
        self.assertEqual(dict(tmux.TMUX_ROLES), SPEC_TMUX)

    def test_repository_mappings_are_valid(self):
        errors = (terminal_ansi.validate_ansi(NAMES)
                  + terminal_ansi.validate_roles(NAMES)
                  + tmux.validate_roles(NAMES)
                  + nvim.validate_sources(support.REPO))
        self.assertEqual(texts(errors), [])


class MappingRulesTest(unittest.TestCase):
    def test_ansi_length(self):
        for count in (15, 17):
            with self.subTest(count=count):
                ansi = (SPEC_ANSI * 2)[:count]
                self.assertEqual(
                    texts(terminal_ansi.validate_ansi(NAMES, ansi)),
                    [f"{ANSI_MODULE}: ANSI: expected 16 entries, "
                     f"found {count}"])

    def test_ansi_unknown_name(self):
        ansi = list(SPEC_ANSI)
        ansi[3] = "noSuchColour"
        self.assertEqual(
            texts(terminal_ansi.validate_ansi(NAMES, tuple(ansi))),
            [f'{ANSI_MODULE}: ANSI[3]: "noSuchColour" {NOT_A_NAME}'])

    def test_tmux_role_unknown_name(self):
        cases = (("clock_fg", "base0G"), ("status_current_bg", "fujiRed"),
                 ("status_current_bg", "lavaBlack"),
                 ("status_current_bg", "base08_dark"))
        for role, value in cases:
            with self.subTest(role=role, value=value):
                roles = dict(SPEC_TMUX, **{role: value})
                self.assertEqual(
                    texts(tmux.validate_roles(NAMES, roles)),
                    [f'configurator/tmux.py: TMUX_ROLES.{role}: '
                     f'"{value}" {NOT_A_NAME}'])

    def test_terminal_role_unknown_shade(self):
        for value in ("darkGray", "darkred"):
            with self.subTest(value=value):
                roles = dict(SPEC_TERMINAL, selection_bg=value)
                self.assertEqual(
                    texts(terminal_ansi.validate_roles(NAMES, roles)),
                    [f'{ANSI_MODULE}: TERMINAL_ROLES.selection_bg: '
                     f'"{value}" {NOT_A_NAME}'])

    def test_shade_is_valid_target(self):
        roles = dict(SPEC_TERMINAL, selection_bg="darkAqua")
        self.assertEqual(
            texts(terminal_ansi.validate_roles(NAMES, roles)), [])
        self.assertEqual(NAMES, frozenset(palette.SLOTS)
                         | frozenset(palette.SHADES))

    def test_tmux_role_keys(self):
        roles = dict(SPEC_TMUX, extra_fg="base07")
        del roles["clock_fg"]
        self.assertEqual(
            sorted(texts(tmux.validate_roles(NAMES, roles))),
            ["configurator/tmux.py: TMUX_ROLES.clock_fg: missing role",
             "configurator/tmux.py: TMUX_ROLES.extra_fg: unknown role"])

    def test_terminal_role_keys(self):
        roles = dict(SPEC_TERMINAL)
        del roles["cursor_fg"]
        roles["background"] = "nope"
        self.assertEqual(
            sorted(texts(terminal_ansi.validate_roles(NAMES, roles))),
            [f'{ANSI_MODULE}: TERMINAL_ROLES.background: "nope" '
             f'{NOT_A_NAME}',
             f"{ANSI_MODULE}: TERMINAL_ROLES.cursor_fg: "
             "missing role"])


def assigned_names(rel):
    """Module-level names assigned in a repository source file."""
    tree = ast.parse((support.REPO / rel).read_text())
    return {target.id for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)}


def mutated_run(owner, rel, old, new, *args):
    """configure.py <args> of a scratch copy with one snippet changed."""
    root = support.copy_repo()
    owner.addCleanup(support.remove_tree, root)
    target = root / rel
    source = target.read_text()
    if old not in source:
        raise AssertionError(f"{rel}: {old!r} not found")
    target.write_text(source.replace(old, new, 1))
    env = support.scratch_env(owner)
    return support.run_configure(env, *args, root=root), env


class RolesMovedTest(unittest.TestCase):
    """REQ-REPO-5: TERMINAL_ROLES lives in terminal_ansi.py."""

    def test_defined_once(self):
        from configurator.terminal_ansi import TERMINAL_ROLES

        self.assertEqual(dict(TERMINAL_ROLES), SPEC_TERMINAL)
        self.assertIn("TERMINAL_ROLES",
                      assigned_names("configurator/terminal_ansi.py"))
        self.assertNotIn("TERMINAL_ROLES",
                         assigned_names("configurator/gnome.py"))

    def test_broken_role_names_terminal_ansi(self):
        result, env = mutated_run(
            self, "configurator/terminal_ansi.py",
            '"cursor_bg": "base07"', '"cursor_bg": "base7"', "nvim")
        self.assertEqual(result.code, 3, result.stderr)
        self.assertIn(f'{ANSI_MODULE}: TERMINAL_ROLES.cursor_bg: '
                      f'"base7" {NOT_A_NAME}',
                      result.stderr.splitlines())
        self.assertEqual(list(env.data.iterdir()), [])


class PtyxisKeysTest(unittest.TestCase):
    """REQ-MAP-1/3/5 for PTYXIS_KEYS."""

    def test_values(self):
        from configurator import ptyxis

        self.assertEqual(dict(ptyxis.PTYXIS_KEYS), SPEC_PTYXIS)
        self.assertEqual(texts(ptyxis.validate_keys()), [])

    def test_unknown_role(self):
        result, env = mutated_run(
            self, PTYXIS_MODULE, '"Cursor": "cursor_bg"',
            '"Cursor": "cursor"', "nvim")
        self.assertEqual(result.code, 3, result.stderr)
        self.assertIn(f'{PTYXIS_MODULE}: PTYXIS_KEYS.Cursor: "cursor" '
                      f'is not a TERMINAL_ROLES role',
                      result.stderr.splitlines())
        self.assertEqual(list(env.data.iterdir()), [])

    def test_missing_key(self):
        result, _env = mutated_run(
            self, PTYXIS_MODULE, '"Foreground": "foreground",', "",
            "nvim")
        self.assertEqual(result.code, 3, result.stderr)
        self.assertIn(f"{PTYXIS_MODULE}: PTYXIS_KEYS.Foreground: "
                      f"missing role", result.stderr.splitlines())

    def test_uninstall_ignores_mappings(self):
        """REQ-CLI-7: a broken mapping never blocks removal."""
        result, _env = mutated_run(
            self, PTYXIS_MODULE, '"Cursor": "cursor_bg"',
            '"Cursor": "cursor"', "nvim", "--uninstall")
        self.assertEqual(result.code, 0, result.stderr)
        self.assertEqual(result.stdout,
                         "nvim: unchanged (not installed)\n")


class TemplateRulesTest(unittest.TestCase):
    def test_unknown_role(self):
        text = "set -g a 'x'\nset -g b '{{status_fg}} {{no_such_role}}'\n"
        template = tmux.Template("colors.conf.tmpl", text)
        self.assertEqual(
            texts(tmux.validate_templates((template,))),
            ['tmux/colors.conf.tmpl:2: unknown role "{{no_such_role}}"'])

    def test_hex_in_template(self):
        template = tmux.Template("status.conf.tmpl", "set -g a '#aBc123'\n")
        self.assertEqual(
            texts(tmux.validate_templates((template,))),
            ["tmux/status.conf.tmpl:1: hex literal (use a {{role}})"])


    def test_repository_templates(self):
        templates = tmux.load_templates(support.REPO)
        self.assertEqual([t.name for t in templates],
                         ["colors.conf.tmpl", "status.conf.tmpl"])
        self.assertEqual(texts(tmux.validate_templates(templates)), [])


class SourceTreeTest(unittest.TestCase):
    def setUp(self):
        self.root = support.copy_repo()
        self.addCleanup(support.remove_tree, self.root)
        self.lua = self.root / "nvim/lua/ukiyo_e"

    def test_reserved_palette_path(self):
        (self.lua / "palette.lua").write_text("return {}\n")
        self.assertEqual(
            texts(nvim.validate_sources(self.root)),
            ["nvim/lua/ukiyo_e/palette.lua: reserved path (rendered by "
             "configure.py); remove it from the source tree"])

    def test_symlink(self):
        os.symlink("theme.lua", self.lua / "alias.lua")
        self.assertEqual(
            texts(nvim.validate_sources(self.root)),
            ["nvim/lua/ukiyo_e/alias.lua: symlink in the source tree "
             "(only regular files are installed)"])


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
