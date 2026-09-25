"""REQ-INST: install directory, version build and switch, gc."""

import os
import re
import stat
import unittest
from pathlib import Path
from unittest import mock

import support
from configurator import files, install_dir
from configurator.files import CurrentState, FileSpec
from configurator.palette import InputError

ID_RE = re.compile(r"^\d{8}T\d{6}Z-\d+(-\d+)?$")
NVIM = {"colors/ukiyo_e.lua": FileSpec(b"c\n"),
        "lua/ukiyo_e/init.lua": FileSpec(b"i\n"),
        "lua/ukiyo_e/palette.lua": FileSpec(b"p1\n")}
TMUX = {"ukiyo_e.tmux": FileSpec(b"#!/bin/sh\n", 0o755),
        "tmux/colors.conf": FileSpec(b"t1\n")}


class DataDirTestCase(unittest.TestCase):
    def setUp(self):
        self.data = support.scratch_dir()
        self.addCleanup(support.remove_dir, self.data)
        self.layout = install_dir.resolve(
            {"XDG_DATA_HOME": str(self.data), "HOME": "/nonexistent"})

    def install(self, tree):
        current = files.read_current(self.layout)
        outcome = files.apply_tree(self.layout, current, tree)
        self.assertIsNone(outcome.error)
        return outcome

    def entries(self):
        return sorted(p.name for p in self.data.iterdir())

    def versions(self):
        return sorted(p.name for p in self.layout.versions.iterdir())


class LayoutTest(DataDirTestCase):
    def test_xdg_absolute(self):
        self.assertEqual(self.layout.data, self.data)
        self.assertEqual(self.layout.install, self.data / "ukiyo_e")
        self.assertEqual(self.layout.versions,
                         self.data / "ukiyo_e.versions")

    def test_home_fallback(self):
        for xdg in (None, "", "relative/share"):
            env = {"HOME": "/h"}
            if xdg is not None:
                env["XDG_DATA_HOME"] = xdg
            with self.subTest(xdg=xdg):
                layout = install_dir.resolve(env)
                self.assertEqual(layout.data, Path("/h/.local/share"))

    def test_unresolvable(self):
        for env in ({}, {"HOME": ""}, {"XDG_DATA_HOME": "rel"}):
            with self.subTest(env=env):
                with self.assertRaises(InputError):
                    install_dir.resolve(env)

    def test_absent_is_managed(self):
        files.check_managed(self.layout)
        self.assertIsNone(files.managed_id(self.layout))
        self.assertEqual(files.read_current(self.layout).tree, {})

    def test_managed_symlink(self):
        os.symlink("ukiyo_e.versions/abc", self.layout.install)
        files.check_managed(self.layout)
        self.assertEqual(files.managed_id(self.layout), "abc")
        self.assertEqual(files.read_current(self.layout).tree, {})

    def assert_unmanaged(self, path):
        with self.assertRaises(InputError) as caught:
            files.check_managed(self.layout)
        self.assertEqual(str(caught.exception),
                         f"{path} exists and is not managed by "
                         f"configure.py; move it away and rerun")

    def test_real_directory(self):
        self.layout.install.mkdir()
        self.assert_unmanaged(self.layout.install)

    def test_other_symlinks(self):
        for target in ("/tmp", "ukiyo_e.versions/a/b",
                       "./ukiyo_e.versions/a", "ukiyo_e.versions/.."):
            with self.subTest(target=target):
                os.symlink(target, self.layout.install)
                self.assert_unmanaged(self.layout.install)
                os.unlink(self.layout.install)

    def test_versions_is_a_file(self):
        self.layout.versions.write_text("x")
        self.assert_unmanaged(self.layout.versions)


class VersionTest(DataDirTestCase):
    def test_desired_tree(self):
        current = dict(NVIM, **TMUX)
        new = {"tmux/colors.conf": FileSpec(b"t2\n")}
        want = files.desired_tree(current, ("tmux",), {"tmux": new},
                                  False)
        self.assertEqual(want, dict(NVIM, **new))
        gone = files.desired_tree(current, ("nvim",), {}, True)
        self.assertEqual(gone, TMUX)
        self.assertEqual(
            files.desired_tree(current, ("tmux", "nvim"), {}, True), {})

    def test_diff(self):
        want = dict(TMUX, **{"tmux/colors.conf": FileSpec(b"t2\n"),
                             "tmux/status.conf": FileSpec(b"s\n")})
        want["ukiyo_e.tmux"] = FileSpec(b"#!/bin/sh\n", 0o644)
        change = files.diff(dict(NVIM, **TMUX), want, "tmux")
        self.assertEqual(change.writes, ("tmux/colors.conf",
                                         "tmux/status.conf",
                                         "ukiyo_e.tmux"))
        self.assertEqual(change.removes, ())
        gone = files.diff(dict(NVIM, **TMUX), TMUX, "nvim")
        self.assertEqual(gone.removes, tuple(sorted(NVIM)))

    def test_build_switch_modes(self):
        old = os.umask(0o077)
        self.addCleanup(os.umask, old)
        outcome = self.install(dict(NVIM, **TMUX))
        self.assertTrue(ID_RE.match(outcome.version_id))
        self.assertEqual(os.readlink(self.layout.install),
                         f"ukiyo_e.versions/{outcome.version_id}")
        tree = files.read_current(self.layout).tree
        self.assertEqual(tree, dict(NVIM, **TMUX))
        for path in self.layout.install.resolve().rglob("*"):
            mode = stat.S_IMODE(path.stat().st_mode)
            expected = 0o755 if path.is_dir() or path.name.endswith(
                ".tmux") else 0o644
            self.assertEqual(mode, expected, path)
        self.assertEqual(self.versions(), [outcome.version_id])

    def test_links_identical_writes_changed(self):
        self.install(dict(NVIM, **TMUX))
        old = self.layout.install.resolve()
        before = {rel: (old / rel).stat() for rel in ("colors/ukiyo_e.lua",
                                                      "lua/ukiyo_e/"
                                                      "palette.lua")}
        want = dict(NVIM, **TMUX)
        want["lua/ukiyo_e/palette.lua"] = FileSpec(b"p2\n")
        outcome = self.install(want)
        new = self.layout.install.resolve()
        same = (new / "colors/ukiyo_e.lua").stat()
        self.assertEqual(same.st_ino, before["colors/ukiyo_e.lua"].st_ino)
        changed = (new / "lua/ukiyo_e/palette.lua").stat()
        self.assertNotEqual(changed.st_ino,
                            before["lua/ukiyo_e/palette.lua"].st_ino)
        self.assertEqual(self.versions(), [outcome.version_id])
        self.assertFalse(old.exists())

    def test_unchanged_tree_is_a_no_op(self):
        first = self.install(dict(NVIM, **TMUX))
        current = files.read_current(self.layout)
        outcome = files.apply_tree(self.layout, current, dict(current.tree))
        self.assertFalse(outcome.switched)
        self.assertEqual(self.versions(), [first.version_id])

    def test_empty_result_removes_everything(self):
        self.install(dict(NVIM, **TMUX))
        outcome = self.install({})
        self.assertTrue(outcome.switched)
        self.assertEqual(self.entries(), [])

    def test_id_suffix(self):
        first = files.new_id(self.layout)
        self.assertTrue(ID_RE.match(first), first)
        (self.layout.versions / first).mkdir(parents=True)
        second = files.new_id(self.layout)
        self.assertTrue(ID_RE.match(second), second)
        self.assertNotEqual(second, first)
        self.assertTrue(second.startswith(first + "-"))


class GcTest(DataDirTestCase):
    def leftovers(self):
        partial = self.layout.versions / "19700101T000000Z-1"
        (partial / "lua").mkdir(parents=True)
        (partial / "lua/x.lua").write_text("x")
        os.symlink("ukiyo_e.versions/19700101T000000Z-1",
                   self.data / ".ukiyo_e.new-19700101T000000Z-1")
        (self.layout.versions / "stray.txt").write_text("x")

    def test_removes_unreferenced(self):
        outcome = self.install(NVIM)
        self.leftovers()
        self.assertEqual(files.gc(self.layout), ())
        self.assertEqual(self.versions(), [outcome.version_id])
        self.assertEqual(self.entries(), ["ukiyo_e", "ukiyo_e.versions"])

    def test_versions_without_install(self):
        self.install(NVIM)
        os.unlink(self.layout.install)
        self.leftovers()
        self.assertEqual(files.gc(self.layout), ())
        self.assertEqual(self.entries(), [])

    def test_failure_is_a_warning(self):
        if os.geteuid() == 0:
            self.skipTest("root ignores directory modes")
        self.install(NVIM)
        self.leftovers()
        os.chmod(self.layout.versions, 0o555)
        self.addCleanup(os.chmod, self.layout.versions, 0o755)
        warnings = files.gc(self.layout)
        self.assertEqual(len(warnings), 2, warnings)
        self.assertTrue(all(w.startswith("could not remove ")
                            for w in warnings), warnings)


class InterruptTest(DataDirTestCase):
    def test_interrupt_during_build(self):
        first = self.install(NVIM)
        calls = []

        def flaky(path, spec):
            calls.append(path)
            if len(calls) == 2:
                raise files.Interrupted()
            return real(path, spec)

        real = files.write_one
        want = dict(NVIM, **TMUX)
        current = files.read_current(self.layout)
        with mock.patch("configurator.files.write_one", flaky):
            outcome = files.apply_tree(self.layout, current, want)
        self.assertEqual(outcome.error, "interrupted")
        self.assertFalse(outcome.switched)
        self.assertEqual(self.versions(), [first.version_id])
        self.assertEqual(self.entries(), ["ukiyo_e", "ukiyo_e.versions"])
        self.assertEqual(files.read_current(self.layout).tree, NVIM)

    def test_failure_before_switch(self):
        first = self.install(NVIM)
        current = files.read_current(self.layout)
        broken = OSError(13, "Permission denied")
        with mock.patch("configurator.files.os.replace",
                        side_effect=broken):
            outcome = files.apply_tree(self.layout, current,
                                       dict(NVIM, **TMUX))
        self.assertFalse(outcome.switched)
        self.assertIn("Permission denied", outcome.error)
        self.assertEqual(self.versions(), [first.version_id])
        self.assertEqual(self.entries(), ["ukiyo_e", "ukiyo_e.versions"])

    def test_interrupt_after_switch(self):
        first = self.install(NVIM)
        current = files.read_current(self.layout)
        with mock.patch("configurator.files.clean",
                        side_effect=files.Interrupted()):
            outcome = files.apply_tree(self.layout, current,
                                       dict(NVIM, **TMUX))
        self.assertTrue(outcome.switched)
        self.assertEqual(outcome.error, "interrupted")
        self.assertEqual(files.read_current(self.layout).tree,
                         dict(NVIM, **TMUX))
        self.assertIn(first.version_id, self.versions())


if __name__ == "__main__":
    unittest.main()
