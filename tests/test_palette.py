"""REQ-PAL: palette.toml loading and validation rules."""

import unittest

import support
from configurator import palette as pal

V1 = ("#181616", "#2e2d2c", "#444343", "#5a5a59", "#70706f",
      "#868785", "#9c9d9c", "#b2b4b2", "#a67e7a", "#a1826a",
      "#938966", "#799174", "#659390", "#6d8ea5", "#8884a6",
      "#9f7d93")
SLOTS = ("base00", "base01", "base02", "base03", "base04", "base05",
         "base06", "base07", "base08", "base09", "base0A", "base0B",
         "base0C", "base0D", "base0E", "base0F")
SHADES = {
    "darkRed": "#684642", "darkOrange": "#644a34",
    "darkYellow": "#585030", "darkGreen": "#42563d",
    "darkAqua": "#2c5855", "darkBlue": "#385367",
    "darkViolet": "#504b68", "darkPink": "#624658",
}
GOOD = dict(zip(pal.SLOTS, V1), **SHADES)


def messages(raw):
    return [str(e) for e in pal.validate_palette(raw)]


def with_entry(name, value):
    table = dict(GOOD)
    table[name] = value
    return {"palette": table}


class PaletteRulesTest(unittest.TestCase):
    def test_valid_palette_has_no_errors(self):
        self.assertEqual(messages({"palette": dict(GOOD)}), [])

    def test_slots(self):
        self.assertEqual(pal.SLOTS, SLOTS)
        self.assertFalse(hasattr(pal, "REQUIRED_NAMES"))

    def test_shades_names_and_order(self):
        self.assertEqual(pal.SHADES, tuple(SHADES))

    def test_colour_names(self):
        self.assertEqual(pal.NEUTRAL_NAMES, (
            "lavaBlack", "cinderBlack", "basaltGray", "ashGray",
            "mistGray", "hazeGray", "cloudGray", "snowWhite"))
        self.assertEqual(pal.ACCENT_NAMES, (
            "fujiRed", "persimmonOrange", "strawYellow", "pineGreen",
            "lakeAqua", "ridgeBlue", "twilightViolet", "blossomPink"))
        self.assertEqual(pal.COLOUR_NAMES,
                         pal.NEUTRAL_NAMES + pal.ACCENT_NAMES)
        self.assertFalse(set(pal.COLOUR_NAMES)
                         & (set(SLOTS) | set(SHADES)))

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
            messages(with_entry("base0D", "base0C")),
            ['palette.toml: [palette].base0D: '
             '"base0C" is not #RRGGBB'])

    def test_short_and_long_hex(self):
        for value in ("#12345", "#1234567", "123456", "#12345g"):
            with self.subTest(value=value):
                self.assertEqual(
                    messages(with_entry("base08", value)),
                    [f'palette.toml: [palette].base08: '
                     f'"{value}" is not #RRGGBB'])

    def test_non_string(self):
        self.assertEqual(
            messages(with_entry("base08", 12)),
            ["palette.toml: [palette].base08: "
             "expected a string, found integer"])

    def test_inline_table(self):
        self.assertEqual(
            messages(with_entry("base08", {"a": "#123456"})),
            ["palette.toml: [palette].base08: "
             "expected a string, found table"])

    def test_missing_slot(self):
        table = dict(GOOD)
        del table["base0F"]
        self.assertEqual(
            messages({"palette": table}),
            ["palette.toml: [palette].base0F: missing required slot"])

    def test_reserved_names(self):
        cases = (
            ("darkred", "shade darkRed"),
            ("DARKRED", "shade darkRed"),
            ("base0a", "slot base0A"),
            ("fujiRed", "accent name fujiRed"),
            ("fujired", "accent name fujiRed"),
            ("lavaBlack", "neutral name lavaBlack"),
            ("lavablack", "neutral name lavaBlack"),
        )
        for name, why in cases:
            with self.subTest(name=name):
                self.assertEqual(
                    messages(with_entry(name, "#000000")),
                    [f"palette.toml: [palette].{name}: "
                     f"reserved name ({why})"])

    def test_reserved_and_missing(self):
        table = dict(GOOD)
        del table["base0A"]
        table["base0a"] = "#000000"
        self.assertEqual(sorted(messages({"palette": table})), [
            "palette.toml: [palette].base0A: missing required slot",
            "palette.toml: [palette].base0a: "
            "reserved name (slot base0A)"])

    def test_valid_extra_names(self):
        for name in ("rust", "darkGray", "darkBrown", "base08_dark"):
            with self.subTest(name=name):
                self.assertEqual(
                    messages(with_entry(name, "#b7410e")), [])

    def test_all_errors_collected(self):
        table = dict(GOOD, base08="#12345", extra="nope")
        del table["base0F"]
        found = messages({"palette": table, "tmux": {}})
        self.assertEqual(len(found), 4, found)

    def test_extra_names_allowed(self):
        self.assertEqual(messages(with_entry("myColour", "#010203")), [])

    def test_lowercase_normalisation(self):
        colours = pal.make_palette(with_entry("base08", "#ABCDEF"))
        self.assertEqual(colours.colors["base08"], "#abcdef")
        self.assertEqual(pal.resolve(colours, "base08"), "#abcdef")
        shaded = pal.make_palette(with_entry("darkRed", "#ABCDEF"))
        self.assertEqual(shaded.shades["darkRed"], "#abcdef")
        self.assertNotIn("darkRed", shaded.colors)

    def test_resolve_shade(self):
        colours = pal.make_palette({"palette": dict(GOOD)})
        self.assertEqual(pal.resolve(colours, "darkAqua"), "#2c5855")


class StoredShadesTest(unittest.TestCase):
    def test_v1(self):
        shades = pal.make_palette({"palette": GOOD}).shades
        self.assertEqual(list(shades.items()), list(SHADES.items()))

    def test_independent_of_accents(self):
        colours = pal.make_palette(with_entry("base08", "#010101"))
        self.assertEqual(colours.shades["darkRed"], SHADES["darkRed"])

    def test_missing_shade(self):
        table = dict(GOOD)
        del table["darkAqua"]
        self.assertEqual(
            messages({"palette": table}),
            ["palette.toml: [palette].darkAqua: missing required shade"])

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
