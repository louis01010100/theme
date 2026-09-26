"""V-8: `configure.py gnome` in an isolated D-Bus session."""

import os
import unittest

import gnome_harness as harness
import support
from configurator import terminal_ansi

UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE_A, PROFILE_B = harness.PROFILE_A, harness.PROFILE_B
ROOT_SECTION = "legacy/profiles:"
OWN_SECTION = f"legacy/profiles:/:{UUID}"
PROFILE = f"{harness.PROFILE_SCHEMA}:{harness.PROFILE_ROOT}:{UUID}/"


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


def expected_profile(root=support.REPO):
    """The 12 profile keys of REQ-GT-3, as gsettings values."""
    term = support.resolved_roles(terminal_ansi.TERMINAL_ROLES,
                                  root)
    ansi = ", ".join(f"'{c}'" for c in support.resolved_ansi(root))
    return {
        "visible-name": "'Ukiyo-e'",
        "use-theme-colors": "false",
        "background-color": f"'{term['background']}'",
        "foreground-color": f"'{term['foreground']}'",
        "palette": f"[{ansi}]",
        "cursor-colors-set": "true",
        "cursor-background-color": f"'{term['cursor_bg']}'",
        "cursor-foreground-color": f"'{term['cursor_fg']}'",
        "highlight-colors-set": "true",
        "highlight-background-color": f"'{term['selection_bg']}'",
        "highlight-foreground-color": f"'{term['selection_fg']}'",
        "bold-color-same-as-fg": "true",
    }


def effective_profile(session):
    """LD-8: the 12 keys as gsettings reports them (defaults too)."""
    return {key: harness.gsettings(session.vars, "get", PROFILE, key)
            for key in expected_profile()}


def lowered(section):
    return {k: v.lower() for k, v in section.items()}


def section(step, name):
    return support.parse_dump(step.dump).get(name, {})


class IsolationGuardTest(unittest.TestCase):
    def test_guard_rejects_outer_bus(self):
        env = support.scratch_env(self).with_vars(
            DBUS_SESSION_BUS_ADDRESS=os.environ.get(
                "DBUS_SESSION_BUS_ADDRESS", ""))
        with self.assertRaises(harness.IsolationError):
            harness.check_isolation(env.vars)

    def test_guard_rejects_real_home(self):
        env = support.scratch_env(self).with_vars(HOME=os.environ["HOME"])
        with self.assertRaises(AssertionError):
            support.run_configure(env, "nvim")


class LifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        env = support.scratch_env(cls)
        cls.session = harness.start_session(cls, env)
        harness.seed_two_profiles(cls.session.vars)
        cls.seeded = harness.dump(cls.session.vars)
        cls.steps = {}
        for name, args in (("install", ()), ("reinstall", ()),
                           ("set_default", ("--set-default",)),
                           ("uninstall", ("--uninstall",)),
                           ("uninstall_again", ("--uninstall",))):
            if name == "install":
                cls.fresh_dump = harness.dump(cls.session.vars)
            step = harness.run_installer(cls.session, name, "gnome", *args)
            if name == "install":
                cls.effective = effective_profile(cls.session)
            cls.steps[name] = step

    def test_install(self):
        step = self.steps["install"]
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.stdout.splitlines()[0], "gnome: updated")
        self.assertIn("  list add", step.stdout)
        self.assertEqual(lowered(self.effective),
                         lowered(expected_profile()))
        own = section(step, OWN_SECTION)
        self.assertEqual(len(own), 11, own)
        root = section(step, ROOT_SECTION)
        self.assertEqual(root["list"],
                         f"['{PROFILE_A}', '{PROFILE_B}', '{UUID}']")
        self.assertEqual(root["default"], f"'{PROFILE_A}'")
        seeded = support.parse_dump(self.seeded)
        for uuid in (PROFILE_A, PROFILE_B):
            name = f"legacy/profiles:/:{uuid}"
            self.assertEqual(section(step, name), seeded[name])

    def test_reinstall_changes_nothing(self):
        step = self.steps["reinstall"]
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.stdout, "gnome: unchanged\n")
        self.assertEqual(step.dump, self.steps["install"].dump)

    def test_set_default(self):
        step = self.steps["set_default"]
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.stdout, f"gnome: updated\n  default {UUID}\n")
        dump = support.parse_dump(step.dump)
        before = support.parse_dump(self.steps["reinstall"].dump)
        before[ROOT_SECTION]["default"] = f"'{UUID}'"
        self.assertEqual(dump, before)

    def test_uninstall_restores_seeded_state(self):
        step = self.steps["uninstall"]
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.stdout.splitlines(), [
            "gnome: removed", f"  default {PROFILE_A}", "  list remove",
            "  reset profile"])
        self.assertEqual(step.dump, self.seeded)

    def test_uninstall_again_is_noop(self):
        step = self.steps["uninstall_again"]
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.stdout, "gnome: unchanged (not installed)\n")
        self.assertEqual(step.dump, self.seeded)


class SingleProfileTest(unittest.TestCase):
    def test_uninstall_resets_list_and_default(self):
        session = harness.start_session(self, support.scratch_env(self))
        harness.seed_empty_list(session.vars)
        step = harness.run_installer(session, "i", "gnome", "--set-default")
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(section(step, ROOT_SECTION),
                         {"default": f"'{UUID}'", "list": f"['{UUID}']"})
        step = harness.run_installer(session, "u", "gnome", "--uninstall")
        self.assertEqual(step.code, 0, step.stderr)
        self.assertEqual(step.dump, "")


class PrerequisiteTest(unittest.TestCase):
    def setUp(self):
        env = support.scratch_env(self)
        self.session = harness.start_session(self, env)
        harness.seed_two_profiles(self.session.vars)
        self.seeded = harness.dump(self.session.vars)
        self.server = support.TmuxServer.start(self, env)
        self.session = self.server.attach(self.session)

    def assert_refused(self, session, message):
        """Named gnome only; `all` skips it (test_ptyxis.NoTerminal)."""
        before = self.server.snapshot()
        for target in ("gnome",):
            with self.subTest(target=target):
                step = harness.run_installer(session, target, target)
                self.assertEqual(step.code, 3, step.stderr)
                self.assertIn(f"configure.py: gnome: {message}",
                              step.stderr)
                self.assertEqual(step.stdout, "")
                self.assertEqual(step.dump, self.seeded)
                self.assertFalse(os.path.lexists(session.install))
                self.assertEqual(self.server.snapshot(), before)

    def test_missing_gsettings(self):
        empty = self.session.root / "empty-bin"
        empty.mkdir()
        self.assert_refused(self.session.with_vars(PATH=empty),
                            "gsettings not found on PATH")

    def test_missing_schema(self):
        empty = self.session.root / "empty-share"
        empty.mkdir()
        session = self.session.with_vars(
            XDG_DATA_DIRS=empty, XDG_DATA_HOME=empty,
            GSETTINGS_SCHEMA_DIR=None)
        self.assert_refused(session, "GSettings schema "
                            "org.gnome.Terminal.ProfilesList is not "
                            "installed")

    def test_usage_errors_change_nothing(self):
        for args in (("gnome", "--set-default", "--uninstall"),
                     ("tmux", "--set-default"), ("nvim", "--set-default"),
                     ("--frobnicate",), ("gnome", "tmux")):
            with self.subTest(args=args):
                step = harness.run_installer(self.session, "x", *args)
                self.assertEqual(step.code, 2, step.stderr)
                self.assertEqual(step.dump, self.seeded)


class RollbackTest(unittest.TestCase):
    """LD-1: a failing write rolls back the keys already written."""

    def setUp(self):
        self.session = harness.start_session(self,
                                             support.scratch_env(self))
        folder = self.session.root / "wrap"
        folder.mkdir()
        (folder / "gsettings").write_text(
            '#!/bin/sh\nif [ "$1" = set ] && [ "$3" = palette ]; then\n'
            '  echo "wrapper: palette refused" >&2; exit 1\nfi\n'
            'exec /usr/bin/gsettings "$@"\n')
        (folder / "gsettings").chmod(0o755)
        self.failing = self.session.with_vars(
            PATH=f"{folder}:{self.session.vars['PATH']}")

    def assert_rolled_back(self, root):
        before = harness.dump(self.session.vars)
        step = harness.run_installer(self.failing, "x", "all", root=root)
        self.assertEqual(step.code, 4, step.stderr)
        self.assertEqual(step.stdout.splitlines(), [
            "gnome: failed (set palette: wrapper: palette refused)",
            "ptyxis: not run (earlier target failed)",
            "tmux: not run (earlier target failed)",
            "nvim: not run (earlier target failed)"])
        self.assertEqual(step.dump, before)
        self.assertFalse(os.path.lexists(self.session.install))

    def test_unset_keys_are_reset(self):
        self.assert_rolled_back(support.REPO)

    def test_set_keys_are_rewritten(self):
        harness.run_installer(self.session, "i", "gnome")
        root = support.copy_repo()
        self.addCleanup(support.remove_tree, root)
        support.replace_line(root / "palette.toml", "base00 ",
                             'base00 = "#010101"')
        support.replace_line(root / "palette.toml", "base08 ",
                             'base08 = "#020202"')
        self.assert_rolled_back(root)


if __name__ == "__main__":
    unittest.main()
