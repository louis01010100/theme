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
INSTALL_ONLY = ("org.gnome.Ptyxis",)
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
        # ptyxis is updated by this run; the file step's paths are not
        data = support.tree_snapshot(self.env.data, INSTALL_ONLY)
        result = support.run_configure(self.env, "all", root=root)
        self.assertEqual(result.code, 4, result.stderr)
        lines = status_lines(result)
        self.assertEqual(lines[:2], ["gnome: updated", "ptyxis: updated"])
        self.assertTrue(lines[2].startswith("tmux: failed ("), lines)
        self.assertTrue(lines[3].startswith("nvim: failed ("), lines)
        self.assertEqual(os.readlink(self.env.install), target)
        self.assertEqual(through_install(self.env), tree)
        self.assertEqual(support.tree_snapshot(self.env.data,
                                               INSTALL_ONLY), data)
        self.assertEqual(self.server.snapshot(), options)
        os.chmod(self.env.versions, 0o755)
        again = support.configure_ok(self.env, "all", root=root)
        self.assertEqual(status_lines(again), [
            "gnome: unchanged", "ptyxis: unchanged", "tmux: updated",
            "nvim: updated"])
        last = support.configure_ok(self.env, "all", root=root)
        self.assertEqual(status_lines(last), [
            "gnome: unchanged", "ptyxis: unchanged", "tmux: unchanged",
            "nvim: unchanged"])


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
            "gnome: unchanged", "ptyxis: unchanged", "tmux: unchanged",
            "nvim: unchanged"])
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
            "ptyxis: unchanged (not installed)",
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
        self.assertEqual(lines[:2], ["gnome: updated", "ptyxis: updated"])
        self.assertTrue(lines[2].startswith(
            "tmux: failed (reload: wrapper: tmux source-file refused"),
            lines)
        self.assertEqual(lines[3], "nvim: updated")
        palette = self.env.install / "lua/ukiyo_e/palette.lua"
        self.assertIn('dragonBlue2 = "#123456"', palette.read_text())
        reset = support.run_configure(failing, "tmux", "--uninstall")
        self.assertEqual(reset.code, 4, reset.stderr)
        self.assertEqual(reset.stdout,
                         "tmux: failed (reset: wrapper: tmux set-option "
                         "refused)\n")
        self.assertFalse(os.path.lexists(self.env.install / "tmux"))
        self.assertTrue(palette.exists())


GSETTINGS_WRAPPER = """#!/bin/sh
if [ "$1" = set ] && [ "$2" = org.gnome.Ptyxis ] \\
        && [ "$3" = profile-uuids ]; then
  echo "wrapper: profile-uuids refused" >&2; exit 1
fi
exec /usr/bin/gsettings "$@"
"""


class PtyxisFailTest(FailTestCase):
    """(d) Ptyxis step failures and (e) Ptyxis leftovers."""

    def ptx_state(self):
        return (support.tree_snapshot(support.ptx(self.env), skip=()),
                harness.dump_ptyxis(self.env.vars))

    def test_read_only_palette_directory(self):
        support.configure_ok(self.env, "all")
        root = blue_copy(self)
        folder = support.ptx(self.env)
        before = self.ptx_state()
        os.chmod(folder, 0o555)
        self.addCleanup(os.chmod, folder, 0o755)
        result = support.run_configure(self.env, "all", root=root)
        self.assertEqual(result.code, 4, result.stderr)
        lines = status_lines(result)
        self.assertEqual(lines[0], "gnome: updated")
        self.assertTrue(lines[1].startswith("ptyxis: failed ("), lines)
        self.assertEqual(lines[2:], [
            "tmux: not run (earlier target failed)",
            "nvim: not run (earlier target failed)"])
        self.assertEqual(self.ptx_state(), before)
        self.assertEqual(list(folder.glob(".Ukiyo-e.palette.new-*")), [])

    def test_key_write_rolled_back(self):
        folder = self.env.root / "wrap"
        folder.mkdir()
        (folder / "gsettings").write_text(GSETTINGS_WRAPPER)
        (folder / "gsettings").chmod(0o755)
        failing = self.env.with_vars(
            PATH=f"{folder}:{self.env.vars['PATH']}")
        before = harness.dump_ptyxis(self.env.vars)
        result = support.run_configure(failing, "ptyxis")
        self.assertEqual(result.code, 4, result.stderr)
        self.assertEqual(result.stdout, "ptyxis: failed (set profile-uuids"
                         ": wrapper: profile-uuids refused)\n")
        self.assertEqual(harness.dump_ptyxis(self.env.vars), before)
        palette = support.ptx(self.env) / "Ukiyo-e.palette"
        self.assertFalse(os.path.lexists(palette))
        again = support.configure_ok(self.env, "ptyxis")
        self.assertEqual(status_lines(again), ["ptyxis: updated"])

    def test_leftover_temporary_file(self):
        support.configure_ok(self.env, "ptyxis")
        leftover = support.ptx(self.env) / ".Ukiyo-e.palette.new-1"
        leftover.write_text("partial")
        dry = support.configure_ok(self.env, "ptyxis", "--dry-run")
        self.assertEqual(dry.stdout, "ptyxis: unchanged\n")
        self.assertTrue(leftover.exists())
        real = support.configure_ok(self.env, "ptyxis")
        self.assertEqual(real.stdout, "ptyxis: unchanged\n")
        self.assertFalse(os.path.lexists(leftover))


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


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
