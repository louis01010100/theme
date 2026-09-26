"""REQ-CLI: parsing, report format, and whole runs of configure.py."""

import hashlib
import os
import unittest

import gnome_harness as harness
import support
from configurator import cli, report, tmux
from configurator.report import Status, TargetResult

UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PTYXIS_UUID = "9c3e7b1d5a2f4e80b6d4a1c8e7f05b93"
PTYXIS_INSTALL = ["ptyxis: updated", "  write palette Ukiyo-e.palette",
                  "  set label", "  set palette", "  list add"]
VERSION_TREE = sorted([
    "colors/ukiyo_e.lua", "lua/ukiyo_e/init.lua", "lua/ukiyo_e/theme.lua",
    "lua/ukiyo_e/palette.lua", "lua/ukiyo_e/highlights/editor.lua",
    "lua/ukiyo_e/highlights/lsp.lua", "lua/ukiyo_e/highlights/plugins.lua",
    "lua/ukiyo_e/highlights/syntax.lua",
    "lua/ukiyo_e/highlights/treesitter.lua", "ukiyo_e.tmux",
    "tmux/colors.conf", "tmux/status.conf", "tmux/status-plain.conf",
])
NOT_A_NAME = "is not a [palette] name or derived shade"
DOTFILES = {".tmux.conf": "set -g mouse on\n",
            ".config/tmux/tmux.conf": "set -g base-index 1\n",
            ".config/nvim/init.lua": "vim.o.number = true\n"}

USAGE_ERRORS = (
    ("gnome", "--set-default", "--uninstall"),
    ("ptyxis", "--set-default", "--uninstall"),
    ("ptyxis", "--uninstall", "--set-default", "--dry-run"),
    ("gnome", "ptyxis"),
    ("all", "--uninstall", "--set-default"),
    ("tmux", "--set-default"),
    ("nvim", "--set-default"),
    ("--frobnicate",),
    ("tmux", "nvim"),
    ("all", "all"),
    ("--dry-run", "--dry-run", "extra"),
)


class ParseTest(unittest.TestCase):
    def test_defaults(self):
        opts = cli.parse([])
        self.assertEqual(opts.targets, cli.ORDER)
        self.assertFalse(opts.dry_run or opts.uninstall or opts.set_default)

    def test_flags_any_order(self):
        opts = cli.parse(["--dry-run", "gnome", "--set-default"])
        self.assertEqual(opts.targets, (cli.Target.GNOME,))
        self.assertTrue(opts.dry_run and opts.set_default)
        opts = cli.parse(["--uninstall", "--dry-run", "nvim"])
        self.assertEqual(opts.targets, (cli.Target.NVIM,))
        self.assertTrue(opts.uninstall and opts.dry_run)

    def test_ptyxis_target(self):
        opts = cli.parse(["ptyxis", "--set-default", "--dry-run"])
        self.assertEqual(opts.targets, (cli.Target.PTYXIS,))
        self.assertTrue(opts.set_default and opts.dry_run)
        self.assertEqual(cli.parse(["ptyxis", "--uninstall"]).targets,
                         (cli.Target.PTYXIS,))
        self.assertEqual(cli.ORDER, (cli.Target.GNOME, cli.Target.PTYXIS,
                                     cli.Target.TMUX, cli.Target.NVIM))
        self.assertTrue(cli.parse([]).is_all and cli.parse(["all"]).is_all)
        self.assertFalse(cli.parse(["ptyxis"]).is_all)

    def test_usage_errors(self):
        for argv in USAGE_ERRORS:
            with self.subTest(argv=argv):
                with self.assertRaises(cli.UsageError):
                    cli.parse(list(argv))

    def test_help(self):
        self.assertIsInstance(cli.parse(["-h"]), cli.HelpRequest)
        self.assertIsInstance(cli.parse(["nvim", "--help"]),
                              cli.HelpRequest)


class ReportFormatTest(unittest.TestCase):
    def test_lines(self):
        cases = (
            (TargetResult("gnome", Status.UPDATED, None,
                          ("set palette", "list add")),
             "gnome: updated\n  set palette\n  list add"),
            (TargetResult("tmux", Status.FAILED, "reload: boom", ()),
             "tmux: failed (reload: boom)"),
            (TargetResult("nvim", Status.UNCHANGED, "not installed", ()),
             "nvim: unchanged (not installed)"),
            (TargetResult("nvim", Status.NOT_RUN,
                          "earlier target failed", ()),
             "nvim: not run (earlier target failed)"),
            (TargetResult("tmux", Status.WOULD_REMOVE, None, ()),
             "tmux: would remove"),
        )
        for result, text in cases:
            with self.subTest(text=text):
                self.assertEqual(report.format_result(result), text)


class ReportSkippedTest(unittest.TestCase):
    def test_skipped_line(self):
        result = TargetResult("gnome", Status.SKIPPED, "not installed",
                              ("gsettings not found on PATH",))
        self.assertEqual(report.format_result(result),
                         "gnome: skipped (not installed)\n"
                         "  gsettings not found on PATH")


class UsageTest(unittest.TestCase):
    def test_usage_errors_exit_2(self):
        env = harness.start_session(self, support.scratch_env(self))
        for argv in USAGE_ERRORS:
            with self.subTest(argv=argv):
                result = support.run_configure(env, *argv)
                self.assertEqual(result.code, 2, result.stderr)
                self.assertIn("usage: configure.py", result.stderr)
                self.assertEqual(result.stdout, "")
        self.assertEqual(list(env.data.iterdir()), [])
        self.assertEqual(harness.dump(env.vars, "/"), "")

    def test_help_exits_0_on_stdout(self):
        env = support.scratch_env(self)
        for flag in ("-h", "--help"):
            result = support.run_configure(env, flag)
            self.assertEqual(result.code, 0, result.stderr)
            self.assertTrue(result.stdout.startswith(
                "usage: configure.py [all|gnome|ptyxis|tmux|nvim] "
                "[--dry-run] "
                "[--uninstall] [--set-default] [-h|--help]"))
            self.assertEqual(result.stderr, "")

    def test_runs_as_executable(self):
        env = support.scratch_env(self)
        support.assert_isolated(env.vars)
        result = support.run([str(support.REPO / "configure.py"), "-h"],
                             cwd=env.root / "cwd", env=env.vars)
        self.assertEqual(result.code, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("usage: configure.py"))



def mutate(root, path, old, new):
    """Replace one exact snippet in a scratch copy's file."""
    target = root / path
    text = target.read_text()
    if text.count(old) < 1:
        raise AssertionError(f"{path}: {old!r} not found")
    target.write_text(text.replace(old, new, 1))


def blue_copy(owner, value="#123456"):
    """A scratch repository copy with base0D changed."""
    root = support.copy_repo()
    support.later(owner, support.remove_tree, root)
    support.replace_line(root / "palette.toml", "base0D ",
                         f'base0D = "{value}"')
    return root


class FullTestCase(unittest.TestCase):
    """A scratch env with a private D-Bus session and a tmux server."""

    def start(self, owner):
        env = support.scratch_env(owner)
        session = harness.start_session(owner, env)
        self.server = support.TmuxServer.start(owner, env)
        self.env = self.server.attach(session)

    def setUp(self):
        self.start(self)

    def run_all(self, *args, root=support.REPO):
        return support.run_configure(self.env, *args, root=root)

    def snapshots(self):
        return (support.tree_snapshot(self.env.root),
                harness.snapshot_dconf(self.env.vars),
                self.server.snapshot())

    def assert_snapshots(self, before):
        after = self.snapshots()
        self.assertEqual(support.changed_paths(before[0], after[0]), [])
        self.assertEqual(before[1], after[1])
        self.assertEqual(before[2], after[2])

    def lines(self, result):
        return result.stdout.splitlines()

    def status_lines(self, result):
        return [ln for ln in self.lines(result) if not ln.startswith(" ")]


class PaletteRejectTest(FullTestCase):
    """V-1 dynamic cases, with an earlier install present."""

    CASES = (
        ("[terminal]\nx = 1\n", None,
         "palette.toml: [terminal]: unexpected table"),
        ("base0D ", 'base0D = "base0C"',
         'palette.toml: [palette].base0D: "base0C" is not #RRGGBB'),
        ("base08 ", 'base08 = "#12345"',
         'palette.toml: [palette].base08: "#12345" is not #RRGGBB'),
        ("base0F ", "", "palette.toml: [palette].base0F: missing "
         "required slot"),
    ) + tuple(
        (f'{name} = "#000000"\n', None,
         f"palette.toml: [palette].{name}: reserved name ({why})")
        for name, why in (
            ("shadowRed", "derived shade shadowRed"),
            ("shadowred", "derived shade shadowRed"),
            ("base0a", "slot base0A"),
            ("fujiRed", "accent name fujiRed"),
            ("lavaBlack", "neutral name lavaBlack")))

    def broken_copy(self, prefix, line):
        root = support.copy_repo()
        self.addCleanup(support.remove_tree, root)
        path = root / "palette.toml"
        if line is None:
            path.write_text(path.read_text() + "\n" + prefix)
        else:
            support.replace_line(path, prefix, line)
        return root

    def assert_rejected(self):
        for prefix, line, message in self.CASES:
            with self.subTest(message=message):
                root = self.broken_copy(prefix, line)
                before = self.snapshots()
                result = self.run_all("all", root=root)
                self.assertEqual(result.code, 3, result.stderr)
                self.assertIn(message, result.stderr.splitlines())
                self.assertEqual(result.stdout, "")
                self.assert_snapshots(before)

    def test_rejected_on_fresh_home(self):
        self.assert_rejected()
        self.assertFalse(os.path.lexists(self.env.install))

    def test_rejected_after_install(self):
        support.configure_ok(self.env, "all")
        self.assert_rejected()

    def test_valid_extra_names(self):
        for line in ('rust = "#b7410e"\n', 'shadowGray = "#000000"\n'):
            name = line.split()[0]
            with self.subTest(name=name):
                root = self.broken_copy(line, None)
                support.configure_ok(self.env, "all", root=root)
                text = (self.env.install
                        / "lua/ukiyo_e/palette.lua").read_text()
                body = text.split("    palette = {\n", 1)[1]
                colours, rest = body.split("    shades = {\n", 1)
                shades = rest.split("    ansi = {\n", 1)[0]
                self.assertIn(f"        {name} = ", colours)
                self.assertNotIn(name, shades)


class MappingRejectTest(FullTestCase):
    """V-2: mapping and template errors name module and role."""

    CASES = tuple(
        (path, f'"{role}": "{old}"', f'"{role}": "{new}"',
         f'{path}: {const}.{role}: "{new}" {NOT_A_NAME}')
        for path, const, role, old, new in (
            ("configurator/tmux.py", "TMUX_ROLES", "clock_fg",
             "base0D", "base0G"),
            ("configurator/tmux.py", "TMUX_ROLES", "flat_current_bg",
             "shadowRed", "fujiRed"),
            ("configurator/tmux.py", "TMUX_ROLES", "flat_current_bg",
             "shadowRed", "lavaBlack"),
            ("configurator/tmux.py", "TMUX_ROLES", "flat_current_bg",
             "shadowRed", "base08_dark"),
            ("configurator/terminal_ansi.py", "TERMINAL_ROLES",
             "selection_bg", "shadowAqua", "shadowGray"),
            ("configurator/terminal_ansi.py", "TERMINAL_ROLES",
             "selection_bg", "shadowAqua", "shadowred"))) + (
        ("configurator/terminal_ansi.py", '"base0B", "base0A"',
         '"base0B", "noSuchName"',
         'configurator/terminal_ansi.py: ANSI[3]: "noSuchName" '
         f'{NOT_A_NAME}'),
        ("tmux/colors.conf.tmpl", "{{clock_fg}}", "{{no_such_role}}",
         'tmux/colors.conf.tmpl:11: unknown role "{{no_such_role}}"'),
    )

    def test_rejected(self):
        support.configure_ok(self.env, "all")
        for path, old, new, message in self.CASES:
            root = support.copy_repo()
            self.addCleanup(support.remove_tree, root)
            mutate(root, path, old, new)
            for target in ("all", "nvim"):
                with self.subTest(path=path, target=target):
                    before = self.snapshots()
                    result = self.run_all(target, root=root)
                    self.assertEqual(result.code, 3, result.stderr)
                    self.assertIn(message, result.stderr.splitlines())
                    self.assert_snapshots(before)


class InstallTest(FullTestCase):
    """V-3 and V-4."""

    def test_install_then_rerun(self):
        result = self.run_all()
        self.assertEqual(result.code, 0, result.stderr)
        self.assertEqual(self.status_lines(result), [
            "gnome: updated", "ptyxis: updated", "tmux: updated",
            "nvim: updated"])
        self.assert_tmux_details(self.lines(result))
        self.assert_layout()
        self.assert_live()
        self.assert_ptyxis(self.lines(result))
        before = self.snapshots()
        again = self.run_all("all")
        self.assertEqual(again.code, 0, again.stderr)
        self.assertEqual(again.stdout, "gnome: unchanged\n"
                         "ptyxis: unchanged\ntmux: unchanged\n"
                         "nvim: unchanged\n")
        self.assert_snapshots(before)

    def assert_ptyxis(self, lines):
        """V-3: the palette file, the profile, profile-uuids."""
        from test_ptyxis import expected_palette

        at = lines.index("ptyxis: updated")
        self.assertEqual(lines[at:at + 5], PTYXIS_INSTALL)
        path = support.ptx(self.env) / "Ukiyo-e.palette"
        self.assertEqual(path.read_bytes(), expected_palette())
        self.assertEqual(path.stat().st_mode & 0o7777, 0o644)
        dump = support.parse_dump(harness.dump_ptyxis(self.env.vars))
        self.assertEqual(dump[f"Profiles/{PTYXIS_UUID}"],
                         {"label": "'Ukiyo-e'", "palette": "'Ukiyo-e'"})
        self.assertEqual(dump["/"],
                         {"profile-uuids": f"['{PTYXIS_UUID}']"})

    def assert_tmux_details(self, lines):
        tmux_at = lines.index("tmux: updated")
        nvim_at = lines.index("nvim: updated")
        details = lines[tmux_at + 1:nvim_at]
        self.assertIn("  write tmux/colors.conf", details)
        self.assertIn("  write ukiyo_e.tmux", details)
        self.assertEqual(details[-2:], ["  switch install directory",
                                        "  reload tmux server"])
        self.assertIn("  write lua/ukiyo_e/palette.lua", lines[nvim_at:])
        self.assertNotIn("  switch install directory", lines[nvim_at:])

    def assert_layout(self):
        target = os.readlink(self.env.install)
        self.assertRegex(target, r"^ukiyo_e\.versions/[^/]+$")
        version = self.env.data / target
        self.assertEqual(os.listdir(self.env.versions),
                         [target.split("/")[1]])
        tree = support.tree_snapshot(version)
        files = sorted(k for k, v in tree.items() if v[0] == "file")
        self.assertEqual(files, VERSION_TREE)
        for rel, entry in tree.items():
            mode = 0o755 if entry[0] == "dir" or rel == "ukiyo_e.tmux" \
                else 0o644
            self.assertEqual(entry[2], mode, rel)

    def assert_live(self):
        listed = harness.gsettings(self.env.vars, "get",
                                   harness.PROFILES_LIST, "list")
        self.assertEqual(listed.count(UUID), 1)
        roles = support.resolved_tmux()
        self.assertEqual(self.server.value("status-style"),
                         f"fg={roles['status_fg']},bg={roles['status_bg']}")


class LayoutTest(unittest.TestCase):
    """V-3: XDG fallback and unmanaged install paths."""

    def test_home_fallback(self):
        env = support.scratch_env(self).with_vars(XDG_DATA_HOME=None)
        support.configure_ok(env, "nvim")
        install = env.root / "home/.local/share/ukiyo_e"
        self.assertTrue(install.is_symlink())
        self.assertEqual(os.listdir(env.root / "data"), [])

    def assert_unmanaged(self, env, path):
        for args in (("all",), ("nvim",), ("tmux", "--uninstall")):
            with self.subTest(args=args):
                before = support.tree_snapshot(env.root)
                result = support.run_configure(env, *args)
                self.assertEqual(result.code, 3, result.stderr)
                self.assertIn(f"configure.py: {path} exists and is not "
                              f"managed by configure.py; move it away "
                              f"and rerun", result.stderr)
                after = support.tree_snapshot(env.root)
                self.assertEqual(support.changed_paths(before, after), [])

    def test_real_directory(self):
        env = support.scratch_env(self)
        env = harness.start_session(self, env)
        env.install.mkdir()
        self.assert_unmanaged(env, env.install)

    def test_foreign_symlink(self):
        env = support.scratch_env(self)
        env = harness.start_session(self, env)
        (env.root / "elsewhere").mkdir()
        os.symlink(env.root / "elsewhere", env.install)
        self.assert_unmanaged(env, env.install)


class DryRunTest(FullTestCase):
    """V-7 cases A, B, C."""

    def dry(self, *args, root=support.REPO):
        before = self.snapshots()
        result = self.run_all("all", "--dry-run", *args, root=root)
        self.assertEqual(result.code, 0, result.stderr)
        self.assert_snapshots(before)
        return result

    def test_fresh_home(self):
        result = self.dry()
        self.assertEqual(self.status_lines(result), [
            "gnome: would update", "ptyxis: would update",
            "tmux: would update", "nvim: would update"])
        at = self.lines(result).index("ptyxis: would update")
        self.assertEqual(self.lines(result)[at + 1:at + 5],
                         PTYXIS_INSTALL[1:])
        self.assertIn("  reload tmux server", self.lines(result))
        self.assertFalse(os.path.lexists(self.env.install))
        self.assertFalse(os.path.lexists(self.env.versions))
        self.assertFalse(os.path.lexists(support.ptx(self.env)))

    def test_changed_colour(self):
        support.configure_ok(self.env, "all")
        result = self.dry(root=blue_copy(self))
        self.assertEqual(self.lines(result), [
            "gnome: would update", "  set palette",
            "ptyxis: would update", "  write palette Ukiyo-e.palette",
            "tmux: would update", "  write tmux/colors.conf",
            "  write tmux/status.conf",
            "  switch install directory", "  reload tmux server",
            "nvim: would update", "  write lua/ukiyo_e/palette.lua"])

    def test_uninstall(self):
        support.configure_ok(self.env, "all")
        result = self.dry("--uninstall")
        self.assertEqual(self.status_lines(result), [
            "gnome: would remove", "ptyxis: would remove",
            "tmux: would remove", "nvim: would remove"])
        self.assertIn("  remove palette Ukiyo-e.palette",
                      self.lines(result))
        self.assertIn("  remove install directory", self.lines(result))
        self.assertIn("  reset tmux options", self.lines(result))


def digests(home):
    return {rel: hashlib.sha256((home / rel).read_bytes()).hexdigest()
            for rel in DOTFILES}


class UninstallTest(FullTestCase):
    """V-10."""

    def write_dotfiles(self):
        home = self.env.root / "home"
        for rel, text in DOTFILES.items():
            (home / rel).parent.mkdir(parents=True, exist_ok=True)
            (home / rel).write_text(text)
        return home

    def allowed(self, rel):
        """SAF-3 (a)/(e) paths, the harness dconf db, their parents."""
        ptx = "data/org.gnome.Ptyxis/palettes"
        return rel in ("data", "config", "data/org.gnome.Ptyxis", ptx) \
            or rel.startswith(("data/ukiyo_e", "data/.ukiyo_e.new-",
                               "config/dconf", f"{ptx}/Ukiyo-e.palette",
                               f"{ptx}/.Ukiyo-e.palette.new-"))

    def test_install_then_uninstall(self):
        home = self.write_dotfiles()
        dotfiles = digests(home)
        files0 = support.tree_snapshot(self.env.root)
        tmux0 = self.server.snapshot()
        support.configure_ok(self.env, "all")
        files1 = support.tree_snapshot(self.env.root)
        result = support.configure_ok(self.env, "all", "--uninstall")
        self.assertEqual(self.status_lines(result), [
            "gnome: removed", "ptyxis: removed", "tmux: removed",
            "nvim: removed"])
        self.assert_ptyxis_removed()
        self.assertLess(self.lines(result).index("  reset tmux options"),
                        self.lines(result).index("nvim: removed"))
        self.assertFalse(os.path.lexists(self.env.install))
        self.assertFalse(os.path.lexists(self.env.versions))
        listed = harness.gsettings(self.env.vars, "get",
                                   harness.PROFILES_LIST, "list")
        self.assertNotIn(UUID, listed)
        self.assertEqual(digests(home), dotfiles)
        files2 = support.tree_snapshot(self.env.root)
        changed = (support.changed_paths(files0, files1)
                   + support.changed_paths(files1, files2))
        self.assertTrue(changed)
        self.assertEqual([p for p in changed if not self.allowed(p)], [])
        self.assertEqual(self.server.snapshot(), tmux0)

    def assert_ptyxis_removed(self):
        dump = support.parse_dump(harness.dump_ptyxis(self.env.vars))
        self.assertNotIn(PTYXIS_UUID, dump.get("/", {}).get(
            "profile-uuids", ""))
        self.assertNotIn(f"Profiles/{PTYXIS_UUID}", dump)
        self.assertFalse(os.path.lexists(support.ptx(self.env)
                                         / "Ukiyo-e.palette"))
        self.assertTrue(support.ptx(self.env).is_dir())

    def test_broken_palette_never_blocks_removal(self):
        support.configure_ok(self.env, "all")
        root = support.copy_repo()
        self.addCleanup(support.remove_tree, root)
        (root / "palette.toml").write_text("[palette\n")
        result = support.configure_ok(self.env, "all", "--uninstall",
                                      root=root)
        self.assertEqual(self.status_lines(result), [
            "gnome: removed", "ptyxis: removed", "tmux: removed",
            "nvim: removed"])

    def test_status_content_off(self):
        self.server.tmux("set", "-g", "@ukiyo_e_show_status_content", "off")
        self.server.tmux("set", "-g", "status-left", "mine")
        support.configure_ok(self.env, "all")
        support.configure_ok(self.env, "all", "--uninstall")
        self.assertEqual(self.server.value("status-left"), "mine")
        values = {o: self.server.value(o) for o in tmux.STYLE_OPTIONS}
        fresh = support.TmuxServer.start(self, self.env)
        self.assertEqual(values,
                         {o: fresh.value(o) for o in tmux.STYLE_OPTIONS})


def setUpModule():
    support.RealStateGuard.take()


def tearDownModule():
    support.RealStateGuard.verify()


if __name__ == "__main__":
    unittest.main()
