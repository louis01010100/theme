"""V-9: the installed ukiyo_e.tmux on a dedicated tmux server."""

import os
import time
import unittest

import support
from configurator import tmux

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
THEME_OPTIONS = (tmux.STYLE_OPTIONS + tmux.STATUS_OPTIONS
                 + tmux.PRIVATE_OPTIONS)


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
        self.env = support.scratch_env(self)
        self.server = support.TmuxServer.start(self, self.env)
        self.attached = self.server.attach(self.env)

    def configure(self, *args):
        return support.configure_ok(self.attached, "tmux", *args)

    def run_script(self):
        script = self.env.install / "ukiyo_e.tmux"
        result = self.server.run_script(self.env, script)
        self.assertEqual(result.code, 0, result.stderr)

    def status_values(self):
        return {n: self.server.value(n) for n in tmux.STATUS_OPTIONS}

    def theme_values(self):
        return {n: self.server.value(n) for n in THEME_OPTIONS}


class ConstantsTest(unittest.TestCase):
    def test_allowlist(self):
        self.assertEqual(len(tmux.STYLE_OPTIONS), 13)
        self.assertEqual(len(tmux.STATUS_OPTIONS), 5)
        self.assertEqual(set(THEME_OPTIONS), support.TMUX_ALLOWLIST)


class AllowlistTest(TmuxTestCase):
    def test_install_reloads_allowlisted_options_only(self):
        before = self.server.snapshot()
        result = self.configure()
        self.assertEqual(result.stdout.splitlines()[-1],
                         "  reload tmux server")
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
        self.configure()
        after = [self.server.tmux(*argv).stdout for argv in scopes]
        self.assertEqual(after, before)

    def test_styles_match_roles(self):
        self.configure()
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

    def test_script_idempotent(self):
        self.configure()
        first = self.server.snapshot()
        self.run_script()
        self.run_script()
        self.assertEqual(self.server.snapshot(), first)


class GlyphTest(TmuxTestCase):
    def test_patched_default_has_powerline_glyphs(self):
        self.configure()
        values = self.status_values()
        glyphs = set("".join(values.values())) & POWERLINE
        self.assertTrue(glyphs, values)
        self.assertIn("#{T:@ukiyo_e_status_date}", values["status-right"])

    def test_no_patched_font_has_no_private_use(self):
        self.configure()
        for flag in ("on", "YES", "1", "True"):
            with self.subTest(flag=flag):
                self.server.tmux("set", "-g", "@ukiyo_e_no_patched_font",
                                 flag)
                self.run_script()
                text = "".join(self.status_values().values())
                self.assertIn("#S", text)
                self.assertFalse([c for c in text if is_private_use(c)])


class StatusContentTest(TmuxTestCase):
    def test_status_content_off_keeps_formats(self):
        self.server.tmux("set", "-g", "@ukiyo_e_show_status_content", "OFF")
        before = self.status_values()
        self.configure()
        self.assertEqual(self.status_values(), before)
        roles = support.resolved_tmux()
        expected = {"fg": roles["status_fg"], "bg": roles["status_bg"]}
        self.assertEqual(attribute_map(self.server.value("status-style")),
                         expected)

    def test_date_format_and_twelve_hour_clock(self):
        self.server.tmux("set", "-g", "@ukiyo_e_date_format", "%d/%m")
        self.server.tmux("set", "-gw", "clock-mode-style", "12")
        self.configure()
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
        self.configure()
        self.assertEqual(self.server.value("@ukiyo_e_status_date"),
                         "%Y-%m-%d")
        self.assertEqual(self.server.value("@ukiyo_e_status_time"), "%H:%M")
        self.assertEqual(self.server.value("@ukiyo_e_date_format"), "")


class ResetTest(TmuxTestCase):
    def test_uninstall_restores_defaults(self):
        defaults = self.theme_values()
        self.configure()
        self.assertNotEqual(self.theme_values(), defaults)
        result = self.configure("--uninstall")
        self.assertIn("tmux: removed", result.stdout)
        self.assertIn("  reset tmux options", result.stdout)
        self.assertEqual(self.theme_values(), defaults)

    def test_status_content_off_keeps_user_status(self):
        self.server.tmux("set", "-g", "@ukiyo_e_show_status_content", "off")
        self.server.tmux("set", "-g", "status-left", "mine")
        style = self.server.value("status-style")
        self.configure()
        self.configure("--uninstall")
        self.assertEqual(self.server.value("status-left"), "mine")
        self.assertEqual(self.server.value("status-style"), style)


class NoServerTest(unittest.TestCase):
    def test_no_server_running(self):
        env = support.scratch_env(self)
        result = support.configure_ok(env, "tmux")
        self.assertEqual(result.stdout.splitlines()[-1],
                         "  skip tmux reload (no server running)")
        self.assertTrue(env.install.is_symlink())

    def test_tmux_not_found(self):
        env = support.scratch_env(self)
        empty = env.root / "bin"
        empty.mkdir()
        env = env.with_vars(PATH=empty)
        result = support.configure_ok(env, "tmux")
        self.assertEqual(result.stdout.splitlines()[-1],
                         "  skip tmux reload (tmux not found)")


class LocationTest(unittest.TestCase):
    def test_script_reads_its_physical_directory(self):
        env = support.scratch_env(self)
        support.configure_ok(env, "tmux")
        wrapper = env.root / "bin"
        wrapper.mkdir()
        log = env.root / "tmux.log"
        (wrapper / "tmux").write_text(
            f'#!/bin/sh\necho "$*" >> {log}\n')
        (wrapper / "tmux").chmod(0o755)
        path = f"{wrapper}:{os.environ['PATH']}"
        result = support.run([str(env.install / "ukiyo_e.tmux")],
                             env=dict(env.vars, PATH=path), stdin="")
        self.assertEqual(result.code, 0, result.stderr)
        version = env.install.resolve()
        sourced = [line.split(" ", 1)[1] for line in
                   log.read_text().splitlines()
                   if line.startswith("source-file")]
        self.assertEqual(sourced, [f"{version}/tmux/colors.conf",
                                   f"{version}/tmux/status.conf"])


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
