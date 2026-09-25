"""REQ-PAL: palette.toml loading and validation rules."""

import unittest

import support
from configurator import palette as pal

GOOD = {name: "#ABCDEF" for name in pal.REQUIRED_NAMES}


def messages(raw):
    return [str(e) for e in pal.validate_palette(raw)]


def with_entry(name, value):
    table = dict(GOOD)
    table[name] = value
    return {"palette": table}


class PaletteRulesTest(unittest.TestCase):
    def test_valid_palette_has_no_errors(self):
        self.assertEqual(messages({"palette": dict(GOOD)}), [])

    def test_required_names_are_46(self):
        self.assertEqual(len(set(pal.REQUIRED_NAMES)), 46)

    def test_extra_table(self):
        raw = {"palette": dict(GOOD), "terminal": {"x": "y"}}
        self.assertEqual(messages(raw),
                         ["palette.toml: [terminal]: unexpected table"])

    def test_extra_key(self):
        raw = {"palette": dict(GOOD), "colour": "#123456"}
        self.assertEqual(messages(raw),
                         ["palette.toml: colour: unexpected key"])

    def test_missing_palette_table(self):
        self.assertEqual(messages({}),
                         ["palette.toml: [palette]: missing table"])

    def test_palette_not_a_table(self):
        self.assertEqual(messages({"palette": "x"}),
                         ["palette.toml: [palette]: expected a table"])

    def test_bad_name(self):
        self.assertEqual(messages(with_entry("1bad", "#123456")),
                         ["palette.toml: [palette].1bad: invalid name"])

    def test_name_reference(self):
        self.assertEqual(
            messages(with_entry("dragonBlue2", "dragonBlue")),
            ['palette.toml: [palette].dragonBlue2: '
             '"dragonBlue" is not #RRGGBB'])

    def test_short_and_long_hex(self):
        for value in ("#12345", "#1234567", "123456", "#12345g"):
            with self.subTest(value=value):
                self.assertEqual(
                    messages(with_entry("dragonRed", value)),
                    [f'palette.toml: [palette].dragonRed: '
                     f'"{value}" is not #RRGGBB'])

    def test_non_string(self):
        self.assertEqual(
            messages(with_entry("dragonRed", 12)),
            ["palette.toml: [palette].dragonRed: "
             "expected a string, found integer"])

    def test_inline_table(self):
        self.assertEqual(
            messages(with_entry("dragonRed", {"a": "#123456"})),
            ["palette.toml: [palette].dragonRed: "
             "expected a string, found table"])

    def test_missing_required_name(self):
        table = dict(GOOD)
        del table["waveRed"]
        self.assertEqual(
            messages({"palette": table}),
            ["palette.toml: [palette].waveRed: missing required name"])

    def test_all_errors_collected(self):
        table = dict(GOOD, dragonRed="#12345", extra="nope")
        del table["waveRed"]
        found = messages({"palette": table, "tmux": {}})
        self.assertEqual(len(found), 4, found)

    def test_extra_names_allowed(self):
        self.assertEqual(messages(with_entry("myColour", "#010203")), [])

    def test_lowercase_normalisation(self):
        colours = pal.make_palette(with_entry("dragonRed", "#ABCDEF"))
        self.assertEqual(colours.colors["dragonRed"], "#abcdef")
        self.assertEqual(pal.resolve(colours, "dragonRed"), "#abcdef")

    def test_toml_syntax_error(self):
        folder = support.scratch_dir()
        self.addCleanup(support.remove_dir, folder)
        path = folder / "palette.toml"
        path.write_text("[palette\n")
        with self.assertRaises(pal.InputError) as caught:
            pal.read_toml(path)
        self.assertTrue(str(caught.exception).startswith(
            "palette.toml: TOML syntax error: "), str(caught.exception))

    def test_unreadable(self):
        folder = support.scratch_dir()
        self.addCleanup(support.remove_dir, folder)
        with self.assertRaises(pal.InputError) as caught:
            pal.read_toml(folder / "palette.toml")
        self.assertIn("palette.toml: cannot read", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
