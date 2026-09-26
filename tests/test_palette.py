"""REQ-PAL: palette.toml loading and validation rules."""

import unittest

import support
from configurator import palette as pal

V1 = ("#181616", "#282727", "#393836", "#625e5a", "#7a8382",
      "#9e9b93", "#a6a69c", "#c5c9c5", "#ae4e47", "#9d7257",
      "#ae955e", "#6e7e60", "#6d8885", "#668696", "#68738b",
      "#857186")
GOOD = dict(zip(pal.SLOTS, V1))
SLOTS = ("base00", "base01", "base02", "base03", "base04", "base05",
         "base06", "base07", "base08", "base09", "base0A", "base0B",
         "base0C", "base0D", "base0E", "base0F")
SHADES = {
    "shadowRed": "#63322e", "shadowOrange": "#5a4436",
    "shadowYellow": "#63563a", "shadowGreen": "#434a3b",
    "shadowAqua": "#424f4e", "shadowBlue": "#3f4e56",
    "shadowViolet": "#404450", "shadowPink": "#4e444e",
}


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
            ("shadowRed", "derived shade shadowRed"),
            ("shadowred", "derived shade shadowRed"),
            ("SHADOWRED", "derived shade shadowRed"),
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
        for name in ("rust", "shadowGray", "shadowBrown", "base08_dark"):
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
        self.assertEqual(colours.shades["shadowRed"], "#627282")

    def test_resolve_shade(self):
        colours = pal.make_palette({"palette": dict(GOOD)})
        self.assertEqual(pal.resolve(colours, "shadowAqua"), "#424f4e")


class DeriveShadesTest(unittest.TestCase):
    def test_v1(self):
        shades = pal.derive_shades(GOOD)
        self.assertEqual(list(shades.items()), list(SHADES.items()))

    def test_ties_round_to_even(self):
        colours = dict(GOOD, base00="#181616",
                       base08="#8b7b95", base09="#010101")
        self.assertEqual(pal.derive_shades(colours)["shadowRed"],
                         "#524856")

    def test_case_insensitive(self):
        upper = {k: v.upper() for k, v in GOOD.items()}
        self.assertEqual(dict(pal.derive_shades(upper)), SHADES)

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
