"""V-FAIL: failures before the switch, crash leftovers, live action."""

import os
import signal
import subprocess
import sys
import time
import unittest

import gnome_harness as harness
import support
from test_cli import blue_copy

LEFTOVER = "19700101T000000Z-1"
TMUX_WRAPPER = """#!/bin/sh
case "$1" in
  list-sessions) echo "0: 1 windows"; exit 0 ;;
  show-options) exit 0 ;;
esac
echo "wrapper: tmux $1 refused" >&2
exit 1
"""
SLOW_WRAPPER = """#!/bin/sh
case "$1" in
  list-sessions) echo "0: 1 windows"; exit 0 ;;
  show-options) exit 0 ;;
esac
touch "{marker}"
sleep 5
"""


def status_lines(result):
    return [ln for ln in result.stdout.splitlines()
            if not ln.startswith(" ")]


def through_install(env):
    """The tree reached through $INSTALL (not following links)."""
    return support.tree_snapshot(env.install.resolve())


def wrapper_env(case, env, text):
    folder = env.root / "wrap"
    folder.mkdir(exist_ok=True)
    (folder / "tmux").write_text(text)
    (folder / "tmux").chmod(0o755)
    return env.with_vars(PATH=f"{folder}:{env.vars['PATH']}", TMUX=None)


class FailTestCase(unittest.TestCase):
    def setUp(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores directory modes")
        env = support.scratch_env(self)
        self.env = harness.start_session(self, env)

    def attach_server(self):
        self.server = support.TmuxServer.start(self, self.env)
        self.env = self.server.attach(self.env)


class BeforeSwitchTest(FailTestCase):
    """(a) the file step fails before the switch."""

    def test_read_only_versions(self):
        self.attach_server()
        support.configure_ok(self.env, "all")
        root = blue_copy(self)
        target = os.readlink(self.env.install)
        tree = through_install(self.env)
        options = self.server.snapshot()
        os.chmod(self.env.versions, 0o555)
        self.addCleanup(os.chmod, self.env.versions, 0o755)
        data = support.tree_snapshot(self.env.data)
        result = support.run_configure(self.env, "all", root=root)
        self.assertEqual(result.code, 4, result.stderr)
        lines = status_lines(result)
        self.assertEqual(lines[0], "gnome: updated")
        self.assertTrue(lines[1].startswith("tmux: failed ("), lines)
        self.assertTrue(lines[2].startswith("nvim: failed ("), lines)
        self.assertEqual(os.readlink(self.env.install), target)
        self.assertEqual(through_install(self.env), tree)
        self.assertEqual(support.tree_snapshot(self.env.data), data)
        self.assertEqual(self.server.snapshot(), options)
        os.chmod(self.env.versions, 0o755)
        again = support.configure_ok(self.env, "all", root=root)
        self.assertEqual(status_lines(again), [
            "gnome: unchanged", "tmux: updated", "nvim: updated"])
        last = support.configure_ok(self.env, "all", root=root)
        self.assertEqual(status_lines(last), [
            "gnome: unchanged", "tmux: unchanged", "nvim: unchanged"])


class LeftoverTest(FailTestCase):
    """(b) what a SIGKILL during a build leaves behind."""

    def plant(self):
        partial = self.env.versions / LEFTOVER
        (partial / "lua/ukiyo_e").mkdir(parents=True)
        (partial / "lua/ukiyo_e/init.lua").write_text("-- partial\n")
        link = self.env.data / f".ukiyo_e.new-{LEFTOVER}"
        os.symlink(f"ukiyo_e.versions/{LEFTOVER}", link)
        return partial, link

    def test_dry_run_keeps_then_run_removes(self):
        support.configure_ok(self.env, "all")
        partial, link = self.plant()
        target = os.readlink(self.env.install)
        tree = through_install(self.env)
        before = support.tree_snapshot(self.env.root)
        dry = support.configure_ok(self.env, "all", "--dry-run")
        self.assertEqual(status_lines(dry), [
            "gnome: unchanged", "tmux: unchanged", "nvim: unchanged"])
        self.assertEqual(support.tree_snapshot(self.env.root), before)
        real = support.configure_ok(self.env, "all")
        self.assertEqual(status_lines(real), status_lines(dry))
        self.assertFalse(os.path.lexists(partial))
        self.assertFalse(os.path.lexists(link))
        self.assertEqual(os.readlink(self.env.install), target)
        self.assertEqual(through_install(self.env), tree)

    def test_versions_without_install(self):
        support.configure_ok(self.env, "tmux")
        os.unlink(self.env.install)
        result = support.configure_ok(self.env, "all", "--uninstall")
        self.assertEqual(status_lines(result), [
            "gnome: unchanged (not installed)",
            "tmux: unchanged (not installed)",
            "nvim: unchanged (not installed)"])
        self.assertFalse(os.path.lexists(self.env.versions))


class LiveActionTest(FailTestCase):
    """(c) the tmux live action fails; the new version stays."""

    def test_reload_and_reset_failures(self):
        support.configure_ok(self.env, "all")
        failing = wrapper_env(self, self.env, TMUX_WRAPPER)
        result = support.run_configure(failing, "all", root=blue_copy(self))
        self.assertEqual(result.code, 4, result.stderr)
        lines = status_lines(result)
        self.assertEqual(lines[0], "gnome: updated")
        self.assertTrue(lines[1].startswith(
            "tmux: failed (reload: wrapper: tmux source-file refused"),
            lines)
        self.assertEqual(lines[2], "nvim: updated")
        palette = self.env.install / "lua/ukiyo_e/palette.lua"
        self.assertIn('dragonBlue2 = "#123456"', palette.read_text())
        reset = support.run_configure(failing, "tmux", "--uninstall")
        self.assertEqual(reset.code, 4, reset.stderr)
        self.assertEqual(reset.stdout,
                         "tmux: failed (reset: wrapper: tmux set-option "
                         "refused)\n")
        self.assertFalse(os.path.lexists(self.env.install / "tmux"))
        self.assertTrue(palette.exists())


class SignalTest(FailTestCase):
    """REQ-INST-5 step 5: SIGTERM after the switch, during reload."""

    def test_sigterm_during_reload(self):
        support.configure_ok(self.env, "tmux")
        marker = self.env.root / "reloading"
        slow = wrapper_env(self, self.env,
                           SLOW_WRAPPER.format(marker=marker))
        support.assert_isolated(slow.vars)
        argv = [sys.executable, str(blue_copy(self) / "configure.py"),
                "tmux"]
        proc = subprocess.Popen(argv, env=slow.vars, text=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                stdin=subprocess.DEVNULL)
        deadline = time.monotonic() + 20
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        proc.send_signal(signal.SIGTERM)
        out, err = proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, 4, err)
        self.assertEqual(out, "tmux: failed (interrupted)\n")
        colors = self.env.install / "tmux/colors.conf"
        self.assertIn("#123456", colors.read_text())


if __name__ == "__main__":
    unittest.main()
