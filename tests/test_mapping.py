"""REQ-MAP: role mappings, templates, and the nvim source tree."""

import os
import unittest

import support
from configurator import gnome, nvim, palette, terminal_ansi, tmux

NAMES = frozenset(palette.REQUIRED_NAMES)
SPEC_ANSI = (
    "dragonBlack0", "dragonRed", "dragonGreen2", "dragonYellow",
    "dragonBlue2", "dragonPink", "dragonAqua", "oldWhite", "dragonGray",
    "waveRed", "dragonGreen", "carpYellow", "springBlue", "springViolet1",
    "waveAqua2", "dragonWhite",
)
SPEC_TERMINAL = {
    "background": "dragonBlack3", "foreground": "dragonWhite",
    "cursor_bg": "oldWhite", "cursor_fg": "dragonBlack3",
    "selection_bg": "waveBlue2", "selection_fg": "oldWhite",
}
SPEC_TMUX = {
    "status_fg": "oldWhite", "status_bg": "dragonBlack0",
    "accent_fg": "dragonBlack0", "accent_bg": "dragonBlue2",
    "status_segment_fg": "oldWhite", "status_segment_bg": "dragonBlack4",
    "window_fg": "dragonGray3", "window_bg": "dragonBlack0",
    "window_current_fg": "dragonWhite", "window_current_bg": "dragonBlack5",
    "window_activity_fg": "roninYellow",
    "window_activity_bg": "dragonBlack0",
    "window_bell_fg": "samuraiRed", "window_bell_bg": "dragonBlack0",
    "window_separator_fg": "dragonBlack6", "pane_border_fg": "dragonBlack5",
    "pane_active_border_fg": "dragonBlue2", "message_fg": "oldWhite",
    "message_bg": "dragonBlack0", "command_fg": "dragonWhite",
    "command_bg": "dragonBlack0", "copy_selection_fg": "oldWhite",
    "copy_selection_bg": "waveBlue2", "clock_fg": "dragonBlue2",
    "display_panes_fg": "dragonBlack6",
    "display_panes_active_fg": "roninYellow",
}
ANSI_MODULE = "configurator/terminal_ansi.py"


def texts(errors):
    return [str(e) for e in errors]


class ConstantsTest(unittest.TestCase):
    def test_v1_values(self):
        self.assertEqual(tuple(terminal_ansi.ANSI), SPEC_ANSI)
        self.assertEqual(dict(gnome.TERMINAL_ROLES), SPEC_TERMINAL)
        self.assertEqual(dict(tmux.TMUX_ROLES), SPEC_TMUX)

    def test_repository_mappings_are_valid(self):
        errors = (terminal_ansi.validate_ansi(NAMES)
                  + gnome.validate_roles(NAMES)
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
            [f'{ANSI_MODULE}: ANSI[3]: "noSuchColour" is not a '
             f'[palette] name'])

    def test_tmux_role_unknown_name(self):
        roles = dict(SPEC_TMUX, clock_fg="dragonBlu2")
        self.assertEqual(
            texts(tmux.validate_roles(NAMES, roles)),
            ['configurator/tmux.py: TMUX_ROLES.clock_fg: "dragonBlu2" '
             'is not a [palette] name'])

    def test_tmux_role_keys(self):
        roles = dict(SPEC_TMUX, extra_fg="oldWhite")
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
            sorted(texts(gnome.validate_roles(NAMES, roles))),
            ['configurator/gnome.py: TERMINAL_ROLES.background: "nope" '
             'is not a [palette] name',
             "configurator/gnome.py: TERMINAL_ROLES.cursor_fg: "
             "missing role"])


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
                         ["colors.conf.tmpl", "status.conf.tmpl",
                          "status-plain.conf.tmpl"])
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


if __name__ == "__main__":
    unittest.main()
