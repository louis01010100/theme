"""V-GEN: generator CLI, validation, determinism, output format."""

import re
import sys
import unittest

import support

sys.path.insert(0, str(support.REPO / "scripts"))
import generate  # noqa: E402

PALETTE_LUA = "lua/ukiyo_e/palette.lua"
PALETTE_SH = "gnome-terminal/palette.sh"
NOT_A_COLOUR = "is neither #RRGGBB nor a [palette] name"


class CopyTestCase(unittest.TestCase):
    """A test that works on a scratch copy of the repository."""

    def setUp(self):
        self.root = support.copy_repo()
        self.addCleanup(support.remove_tree, self.root)

    def toml_path(self):
        return self.root / "palette.toml"

    def set_line(self, prefix, line):
        support.replace_line(self.toml_path(), prefix, line)


class CheckModeTest(CopyTestCase):
    def test_check_clean(self):
        result = support.generate(self.root, "--check")
        self.assertEqual((result.code, result.stdout, result.stderr),
                         (0, "", ""))

    def test_check_stale_palette_colour(self):
        self.set_line("dragonBlue2 ", 'dragonBlue2 = "#123456"')
        before = support.generated_hashes(self.root)
        result = support.generate(self.root, "--check")
        expected = "".join(f"stale: {p}\n" for p in
                           support.GENERATED_PATHS)
        self.assertEqual((result.code, result.stdout), (1, expected))
        self.assertEqual(support.generated_hashes(self.root), before)

    def test_check_stale_ansi_entry(self):
        support.set_ansi_entry(self.root, 1, "#ff0000")
        result = support.generate(self.root, "--check")
        expected = f"stale: {PALETTE_LUA}\nstale: {PALETTE_SH}\n"
        self.assertEqual((result.code, result.stdout), (1, expected))

    def test_check_missing_file_is_stale(self):
        (self.root / "tmux" / "status.conf").unlink()
        result = support.generate(self.root, "--check")
        self.assertEqual((result.code, result.stdout),
                         (1, "stale: tmux/status.conf\n"))
        self.assertFalse((self.root / "tmux" / "status.conf").exists())


class InvalidInputTest(CopyTestCase):
    def assert_rejected(self, expected_lines):
        before = support.generated_hashes(self.root)
        result = support.generate(self.root)
        self.assertEqual(result.code, 3, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr.splitlines(), expected_lines)
        self.assertEqual(support.generated_hashes(self.root), before)

    def test_invalid_short_hex(self):
        support.set_ansi_entry(self.root, 3, "#12345")
        self.assert_rejected([
            f'palette.toml: [terminal].ansi[3]: "#12345" {NOT_A_COLOUR}',
        ])

    def test_invalid_unknown_name(self):
        self.set_line("clock_fg ", 'clock_fg = "dragonBlu2"')
        self.assert_rejected([
            f'palette.toml: [tmux].clock_fg: "dragonBlu2" {NOT_A_COLOUR}',
        ])

    def test_invalid_fifteen_ansi(self):
        entries = support.load_palette_toml(self.root)["terminal"]["ansi"]
        support.set_ansi(self.root, entries[:15])
        self.assert_rejected([
            "palette.toml: [terminal].ansi: expected 16 entries, found 15",
        ])

    def test_invalid_missing_required_name(self):
        self.set_line("dragonBlue2 ", "")
        dangling = f'"dragonBlue2" {NOT_A_COLOUR}'
        self.assert_rejected([
            "palette.toml: [palette].dragonBlue2: missing required key",
            f"palette.toml: [terminal].ansi[4]: {dangling}",
            f"palette.toml: [tmux].accent_bg: {dangling}",
            f"palette.toml: [tmux].clock_fg: {dangling}",
            f"palette.toml: [tmux].pane_active_border_fg: {dangling}",
        ])

    def test_invalid_unknown_tmux_key(self):
        self.set_line("clock_fg ",
                      'clock_fg = "dragonBlue2"\nclock_bg = "dragonBlue2"')
        self.assert_rejected([
            "palette.toml: [tmux].clock_bg: unknown key",
        ])

    def test_invalid_toml_syntax(self):
        self.set_line("clock_fg ", "clock_fg = ")
        before = support.generated_hashes(self.root)
        result = support.generate(self.root)
        self.assertEqual(result.code, 3)
        self.assertIn("line", result.stderr)
        self.assertEqual(support.generated_hashes(self.root), before)

    def test_missing_palette_toml(self):
        self.toml_path().unlink()
        result = support.generate(self.root)
        self.assertEqual(result.code, 3)
        self.assertIn("palette.toml", result.stderr)


class UsageTest(CopyTestCase):
    def test_unknown_argument(self):
        result = support.generate(self.root, "--frobnicate")
        self.assertEqual(result.code, 2)
        self.assertIn("usage", result.stderr.lower())

    def test_check_twice_is_usage_error(self):
        self.assertEqual(
            support.generate(self.root, "--check", "--check").code, 2)

    def test_help(self):
        for flag in ("-h", "--help"):
            result = support.generate(self.root, flag)
            self.assertEqual(result.code, 0)
            self.assertIn("usage", result.stdout.lower())

    def test_runs_from_any_directory(self):
        script = self.root / "scripts" / "generate.py"
        elsewhere = support.scratch_dir()
        self.addCleanup(support.remove_dir, elsewhere)
        result = support.run([sys.executable, str(script), "--check"],
                             cwd=elsewhere)
        self.assertEqual(result.code, 0, result.stderr)


class DeterminismTest(CopyTestCase):
    def test_second_run_writes_nothing(self):
        self.set_line("dragonBlue2 ", 'dragonBlue2 = "#123456"')
        first = support.generate(self.root)
        expected = "".join(f"wrote {p}\n" for p in
                           support.GENERATED_PATHS)
        self.assertEqual((first.code, first.stdout), (0, expected))
        hashes = support.generated_hashes(self.root)
        second = support.generate(self.root)
        self.assertEqual((second.code, second.stdout), (0, ""))
        self.assertEqual(support.generated_hashes(self.root), hashes)

    def test_palette_key_order_is_irrelevant(self):
        text = self.toml_path().read_text()
        head, rest = text.split("\n[terminal]\n", 1)
        lines = head.split("\n")
        body = [ln for ln in lines if re.match(r"^\w+\s*=", ln)]
        other = [ln for ln in lines if ln not in body]
        reordered = "\n".join(other + list(reversed(body))) + "\n"
        self.toml_path().write_text(reordered + "\n[terminal]\n" + rest)
        result = support.generate(self.root)
        self.assertEqual((result.code, result.stdout), (0, ""))

    def test_written_file_mode(self):
        (self.root / "tmux" / "colors.conf").unlink()
        support.generate(self.root)
        mode = (self.root / "tmux" / "colors.conf").stat().st_mode
        self.assertEqual(mode & 0o777, 0o644)


class OutputFormatTest(unittest.TestCase):
    def read(self, rel):
        return (support.REPO / rel).read_bytes().decode("utf-8")

    def test_headers(self):
        for rel in support.GENERATED_PATHS:
            header = (support.HEADER_LUA if rel.endswith(".lua")
                      else support.HEADER_SH)
            self.assertEqual(self.read(rel).split("\n")[0], header, rel)

    def test_line_endings_and_trailing_newline(self):
        for rel in support.GENERATED_PATHS:
            text = self.read(rel)
            self.assertNotIn("\r", text, rel)
            self.assertTrue(text.endswith("\n"), rel)
            self.assertFalse(text.endswith("\n\n"), rel)

    def test_hex_is_lowercase(self):
        for rel in support.GENERATED_PATHS:
            found = re.findall(r"#[0-9A-Fa-f]{6}\b", self.read(rel))
            self.assertTrue(found, rel)
            self.assertEqual(found, [h.lower() for h in found], rel)

    def test_palette_lua_names_sorted_and_complete(self):
        block = self.read(PALETTE_LUA).split("terminal = {", 1)[0]
        names = re.findall(r"^        (\w+) = \"#", block, re.M)
        doc = support.load_palette_toml()
        self.assertEqual(names, sorted(doc["palette"]))

    def test_ansi_consistent(self):
        lua = self.read(PALETTE_LUA)
        block = lua.split("ansi = {", 1)[1].split("}", 1)[0]
        lua_ansi = re.findall(r'"(#[0-9a-f]{6})"', block)
        sh_line = re.search(r"^UKIYO_E_PALETTE=(.*)$", self.read(PALETTE_SH),
                            re.M).group(1)
        sh_ansi = re.findall(r"'(#[0-9a-f]{6})'", sh_line)
        self.assertEqual(lua_ansi, support.resolved_ansi())
        self.assertEqual(sh_ansi, support.resolved_ansi())

    def test_palette_sh_is_assignments_only(self):
        lines = self.read(PALETTE_SH).splitlines()
        scalar = r"^UKIYO_E_[A-Z_]+='#[0-9a-f]{6}'$"
        entry = r"'#[0-9a-f]{6}'"
        array = rf"^UKIYO_E_PALETTE=\"\[{entry}(, {entry})*\]\"$"
        self.assertEqual(lines[0], support.HEADER_SH)
        for line in lines[1:]:
            self.assertTrue(re.match(scalar, line) or re.match(array, line),
                            line)
        self.assertEqual(len(lines), 8)

    def test_tmux_confs_are_set_g_lines(self):
        counts = {"tmux/colors.conf": 13, "tmux/status.conf": 5,
                  "tmux/status-plain.conf": 5}
        for rel, count in counts.items():
            lines = self.read(rel).splitlines()[1:]
            self.assertEqual(len(lines), count, rel)
            for line in lines:
                self.assertTrue(line.startswith("set -g "), line)


class ValidateUnitTest(unittest.TestCase):
    def doc(self):
        return support.load_palette_toml()

    def test_v1_is_valid(self):
        self.assertEqual(generate.validate(self.doc()), [])

    def test_non_string_colour(self):
        doc = self.doc()
        doc["tmux"]["clock_fg"] = 7
        errors = [e.format() for e in generate.validate(doc)]
        self.assertEqual(errors, [
            "palette.toml: [tmux].clock_fg: expected a string, found int",
        ])

    def test_palette_value_must_be_hex(self):
        doc = self.doc()
        doc["palette"]["extraName"] = "dragonBlue2"
        errors = [e.format() for e in generate.validate(doc)]
        self.assertEqual(errors, [
            'palette.toml: [palette].extraName: "dragonBlue2" '
            "is not #RRGGBB",
        ])

    def test_unknown_and_missing_tables(self):
        doc = self.doc()
        del doc["tmux"]
        doc["kitty"] = {}
        errors = [e.format() for e in generate.validate(doc)]
        self.assertEqual(errors, [
            "palette.toml: [tmux]: missing required table",
            "palette.toml: [kitty]: unknown table",
        ])

    def test_missing_terminal_key(self):
        doc = self.doc()
        del doc["terminal"]["cursor_fg"]
        errors = [e.format() for e in generate.validate(doc)]
        self.assertEqual(errors, [
            "palette.toml: [terminal].cursor_fg: missing required key",
        ])

    def test_resolve_lowercases(self):
        doc = self.doc()
        doc["terminal"]["background"] = "#ABCDEF"
        theme = generate.resolve(doc)
        self.assertEqual(theme.terminal.background, "#abcdef")
        self.assertEqual(theme.palette.colours["fujiWhite"], "#dcd7ba")
        self.assertEqual(len(theme.terminal.ansi), 16)
        self.assertEqual(len(theme.tmux.colours), 26)

    def test_colour_ref(self):
        palette = {"x": "#A0B0C0"}
        self.assertEqual(generate.ColorRef("x").resolve(palette), "#a0b0c0")
        self.assertEqual(generate.ColorRef("#FFEEDD").resolve(palette),
                         "#ffeedd")


if __name__ == "__main__":
    unittest.main()
