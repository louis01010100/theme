"""V-TMUX: ukiyo_e.tmux on an isolated tmux server."""

import time
import unittest

import support

STATUS_OPTIONS = (
    "status-left", "status-right", "window-status-format",
    "window-status-current-format", "window-status-separator",
)
STYLE_ROLES = {
    "status-style": ("status_fg", "status_bg"),
    "window-status-style": ("window_fg", "window_bg"),
    "window-status-current-style": ("window_current_fg",
                                    "window_current_bg"),
    "window-status-activity-style": ("window_activity_fg",
                                     "window_activity_bg"),
    "window-status-bell-style": ("window_bell_fg", "window_bell_bg"),
    "pane-border-style": ("pane_border_fg", None),
    "pane-active-border-style": ("pane_active_border_fg", None),
    "message-style": ("message_fg", "message_bg"),
    "message-command-style": ("command_fg", "command_bg"),
    "mode-style": ("copy_selection_fg", "copy_selection_bg"),
}
COLOUR_ROLES = {
    "clock-mode-colour": "clock_fg",
    "display-panes-colour": "display_panes_fg",
    "display-panes-active-colour": "display_panes_active_fg",
}
POWERLINE = {chr(c) for c in range(0xE0B0, 0xE0B4)}


def attribute_map(style):
    """Parse a tmux style string into {attribute: value}."""
    attributes = {}
    for part in style.split(","):
        key, _, value = part.strip().partition("=")
        attributes[key] = value.lower()
    return attributes


def is_private_use(char):
    code = ord(char)
    return 0xE000 <= code <= 0xF8FF or code >= 0xF0000


class TmuxTestCase(unittest.TestCase):
    def setUp(self):
        self.server = support.TmuxServer.start(self)

    def run_theme(self):
        result = self.server.run_theme()
        self.assertEqual(result.code, 0, result.stderr)
        return result

    def status_values(self):
        return {name: self.server.value(name) for name in STATUS_OPTIONS}


class AllowlistTest(TmuxTestCase):
    def test_only_allowlisted_global_options_change(self):
        before = self.server.snapshot()
        self.run_theme()
        after = self.server.snapshot()
        changed = support.changed_options(before, after)
        self.assertTrue(changed)
        self.assertLessEqual(changed, support.TMUX_ALLOWLIST)
        for key in ("keys", "hooks", "environment"):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(before["options"]["prefix"],
                         after["options"]["prefix"])

    def test_nothing_set_outside_global_scope(self):
        scopes = (("show-options",), ("show-options", "-w"),
                  ("show-options", "-p"))
        before = [self.server.tmux(*argv).stdout for argv in scopes]
        self.run_theme()
        after = [self.server.tmux(*argv).stdout for argv in scopes]
        self.assertEqual(after, before)

    def test_styles_match_roles(self):
        self.run_theme()
        roles = support.resolved_tmux()
        for option, (fg, bg) in STYLE_ROLES.items():
            expected = {"fg": roles[fg]}
            if bg:
                expected["bg"] = roles[bg]
            actual = attribute_map(self.server.value(option))
            self.assertEqual(actual, expected, option)
        for option, role in COLOUR_ROLES.items():
            self.assertEqual(self.server.value(option).lower(),
                             roles[role], option)

    def test_idempotent(self):
        self.run_theme()
        first = self.server.snapshot()
        self.run_theme()
        self.assertEqual(self.server.snapshot(), first)


class GlyphTest(TmuxTestCase):
    def test_patched_default_has_powerline_glyphs(self):
        self.run_theme()
        values = self.status_values()
        glyphs = set("".join(values.values())) & POWERLINE
        self.assertTrue(glyphs, values)
        self.assertIn("#{T:@ukiyo_e_status_date}", values["status-right"])

    def test_no_patched_font_has_no_private_use(self):
        for flag in ("on", "YES", "1", "True"):
            with self.subTest(flag=flag):
                server = support.TmuxServer.start(self)
                server.tmux("set", "-g", "@ukiyo_e_no_patched_font", flag)
                self.assertEqual(server.run_theme().code, 0)
                text = "".join(server.value(n) for n in STATUS_OPTIONS)
                self.assertIn("#S", text)
                self.assertFalse([c for c in text if is_private_use(c)])


class StatusContentTest(TmuxTestCase):
    def test_status_content_off_keeps_formats(self):
        self.server.tmux("set", "-g", "@ukiyo_e_show_status_content", "OFF")
        before = self.status_values()
        self.run_theme()
        self.assertEqual(self.status_values(), before)
        roles = support.resolved_tmux()
        expected = {"fg": roles["status_fg"], "bg": roles["status_bg"]}
        self.assertEqual(attribute_map(self.server.value("status-style")),
                         expected)

    def test_date_format_and_twelve_hour_clock(self):
        self.server.tmux("set", "-g", "@ukiyo_e_date_format", "%d/%m")
        self.server.tmux("set", "-gw", "clock-mode-style", "12")
        self.run_theme()
        first = time.strftime("%I:%M %p")
        shown = self.server.tmux("display", "-p", "#{T:status-right}")
        last = time.strftime("%I:%M %p")
        self.assertIn(time.strftime("%d/%m"), shown.stdout)
        self.assertTrue(first in shown.stdout or last in shown.stdout,
                        shown.stdout)
        self.assertEqual(self.server.value("@ukiyo_e_date_format"), "%d/%m")
        self.assertEqual(self.server.value("@ukiyo_e_status_time"),
                         "%I:%M %p")

    def test_default_date_and_24_hour_clock(self):
        self.run_theme()
        self.assertEqual(self.server.value("@ukiyo_e_status_date"),
                         "%Y-%m-%d")
        self.assertEqual(self.server.value("@ukiyo_e_status_time"), "%H:%M")
        self.assertEqual(self.server.value("@ukiyo_e_date_format"), "")


if __name__ == "__main__":
    unittest.main()
