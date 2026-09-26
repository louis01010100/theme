"""V-9: the installed ukiyo_e.tmux on a dedicated tmux server."""

import os
import re
import subprocess
import time
import unittest

import support
from configurator import tmux
from test_render import GOLDEN_STATUS

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
THEME_OPTIONS = (tmux.STYLE_OPTIONS + tmux.STATUS_OPTIONS
                 + tmux.PRIVATE_OPTIONS)
# REQ-TMUX-8: the committed status template, byte for byte.
STATUS_TEMPLATE = (
    "set -g status-style 'fg={{status_fg}},bg={{status_bg}}'\n"
    'set -g status-left "#[fg={{status_text_fg}},bg={{status_block_bg}}]'
    ' #S #[fg={{status_separator_fg}},bg={{status_segment_bg}}]|"\n'
    'set -g status-right "#[fg={{status_separator_fg}},'
    'bg={{status_segment_bg}}]|#[fg={{status_text_fg}},'
    'bg={{status_segment_bg}}] #{T:@ukiyo_e_status_date} '
    "#[fg={{status_text_fg}},bg={{status_segment_bg}}]"
    '#{T:@ukiyo_e_status_time} "\n'
    'set -g window-status-format "#[fg={{status_text_fg}},'
    'bg={{status_segment_bg}}] #I.#W "\n'
    'set -g window-status-current-format "#[fg={{status_current_fg}},'
    'bg={{status_current_bg}}] #I.#W "\n'
    'set -g window-status-separator "#[fg={{status_separator_fg}},'
    'bg={{status_segment_bg}}]|"\n'
)
# PRD R6 minimum code, the fixture of V-15 (b).
PRD_MINIMUM = """\
set -g status-style 'fg=#b2b4b2,bg=#2e2d2c'
set -g status-left "#[fg=#70706f,bg=#444343] #S #[fg=#444343,bg=#2e2d2c]|"
set -g status-right "#[fg=#444343,bg=#2e2d2c]|#[fg=#70706f,bg=#2e2d2c] \
%Y-%m-%d #[fg=#70706f,bg=#2e2d2c]%H:%M "
set -g window-status-format "#[fg=#70706f,bg=#2e2d2c] #I.#W "
set -g window-status-current-format "#[fg=#9c9d9c,bg=#63322e] #I.#W "
set -g window-status-separator "#[fg=#444343,bg=#2e2d2c]|"
"""
STATUS_RENDERED = tmux.HEADER + "\n" + GOLDEN_STATUS
COLOURS_SINCE = "68eaef3"
DIRECTIVE = re.compile(r"#\[[^\]]*\]")


def attribute_map(style):
    """Parse a tmux style string into {attribute: value}."""
    attributes = {}
    for part in style.split(","):
        key, _, value = part.strip().partition("=")
        attributes[key] = value.lower()
    return attributes


def rendered_formats():
    """Option -> value of the 5 format lines of STATUS_RENDERED."""
    found = {}
    for line in STATUS_RENDERED.splitlines()[1:]:
        match = re.fullmatch(r"""set -g (\S+) (['"])(.*)\2""", line)
        found[match.group(1)] = match.group(3)
    return {k: v for k, v in found.items() if k in tmux.STATUS_OPTIONS}


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

    def assert_bar(self, date_format, time_format):
        """status-right reads `| <date> <time> `."""
        stamps = [(time.strftime(date_format), time.strftime(time_format))]
        shown = self.server.tmux("display", "-p", "#{T:status-right}")
        stamps.append((time.strftime(date_format),
                       time.strftime(time_format)))
        text = DIRECTIVE.sub("", shown.stdout.rstrip("\n"))
        self.assertIn(text, [f"| {d} {t} " for d, t in stamps])


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


class StatusLayoutStaticTest(unittest.TestCase):
    """V-15 (a), (b): the one status template and its minimum code."""

    def test_status_template(self):
        path = support.REPO / "tmux/status.conf.tmpl"
        self.assertEqual(path.read_bytes(), STATUS_TEMPLATE.encode())

    def test_no_flat_template(self):
        path = support.REPO / "tmux/status-plain.conf.tmpl"
        self.assertFalse(os.path.lexists(path))

    def test_colours_template_unchanged(self):
        rel = "tmux/colors.conf.tmpl"
        old = subprocess.run(
            ["git", "-C", str(support.REPO), "show",
             f"{COLOURS_SINCE}:{rel}"],
            capture_output=True, check=True).stdout
        self.assertEqual((support.REPO / rel).read_bytes(), old)

    def test_golden_is_prd_minimum(self):
        body = (GOLDEN_STATUS
                .replace("#{T:@ukiyo_e_status_date}", "%Y-%m-%d")
                .replace("#{T:@ukiyo_e_status_time}", "%H:%M"))
        self.assertEqual(body, PRD_MINIMUM)


class StatusLayoutLiveTest(TmuxTestCase):
    """V-15 (b)-(g) on a test server after a default install."""

    def setUp(self):
        super().setUp()
        self.defaults = self.theme_values()
        self.before = self.server.snapshot()
        self.configure()
        self.installed = self.theme_values()

    def test_rendered(self):
        path = self.env.install / "tmux/status.conf"
        self.assertEqual(path.read_text(), STATUS_RENDERED)
        plain = self.env.install / "tmux/status-plain.conf"
        self.assertFalse(os.path.lexists(plain))

    def test_default_options(self):
        self.assertEqual(self.server.value("@ukiyo_e_status_date"),
                         "%Y-%m-%d")
        self.assertEqual(self.server.value("@ukiyo_e_status_time"),
                         "%H:%M")
        self.assertEqual(self.status_values(), rendered_formats())
        self.assertEqual(attribute_map(self.server.value("status-style")),
                         {"fg": "#b2b4b2", "bg": "#2e2d2c"})
        text = "".join(self.status_values().values())
        self.assertFalse([c for c in text if is_private_use(c)])
        for option in ("window-status-format",
                       "window-status-current-format"):
            self.assertIn("#I.#W", self.server.value(option))
            self.assertNotIn("#F", self.server.value(option))
        self.assert_bar("%Y-%m-%d", "%H:%M")
        changed = support.changed_options(self.before,
                                          self.server.snapshot())
        self.assertLessEqual(changed, support.TMUX_ALLOWLIST)

    def test_no_patched_font_has_no_effect(self):
        self.server.tmux("set", "-g", "@ukiyo_e_no_patched_font", "on")
        self.run_script()
        self.assertEqual(self.theme_values(), self.installed)
        self.assertEqual(self.server.value("@ukiyo_e_no_patched_font"),
                         "on")

    def test_status_content_off(self):
        self.server.tmux("set", "-g", "@ukiyo_e_show_status_content", "off")
        self.server.tmux("set", "-g", "status-left", "mine")
        formats = self.status_values()
        self.run_script()
        self.assertEqual(self.status_values(), formats)
        self.assertEqual(self.server.value("status-left"), "mine")
        styles = {o: self.server.value(o) for o in tmux.STYLE_OPTIONS}
        self.assertEqual(styles, {o: self.installed[o]
                                  for o in tmux.STYLE_OPTIONS})

    def test_script_twice(self):
        self.run_script()
        first = self.server.snapshot()
        self.run_script()
        self.assertEqual(self.server.snapshot(), first)

    def test_uninstall(self):
        self.configure("--uninstall")
        self.assertEqual(self.theme_values(), self.defaults)


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
        self.assert_bar("%d/%m", "%I:%M %p")
        self.assertEqual(self.server.value("@ukiyo_e_date_format"), "%d/%m")
        self.assertEqual(self.server.value("@ukiyo_e_status_date"), "%d/%m")
        self.assertEqual(self.server.value("@ukiyo_e_status_time"),
                         "%I:%M %p")
        rendered = self.env.install / "tmux/status.conf"
        self.assertEqual(rendered.read_text(), STATUS_RENDERED)

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
