"""V-12: README and INSTALL cover REQ-DOC-1; LICENSE satisfies REQ-DOC-2."""

import unittest

import support

LAZY_LINE = (
    '{ dir = "~/.local/share/ukiyo_e", lazy = false, priority = 1000, '
    'config = function() require("ukiyo_e").setup({ transparent = true '
    '}); vim.cmd.colorscheme("ukiyo_e") end }'
)
TMUX_LINE = "run-shell ~/.local/share/ukiyo_e/ukiyo_e.tmux"
README_ITEMS = (
    LAZY_LINE,
    TMUX_LINE,
    "python3 configure.py",
    "python3 configure.py [all|gnome|ptyxis|tmux|nvim|dircolors|bash] "
    "[--dry-run] [--uninstall] [--set-default] [-h|--help]",
    "--dry-run",
    "| `0` |", "| `2` |", "| `3` |", "| `4` |",
    "XDG_DATA_HOME",
    "--set-default",
    "python3 configure.py all --uninstall",
    "@ukiyo_e_show_status_content",
    "@ukiyo_e_date_format",
    "%Y-%m-%d",
    "nord-dark-tmux",
    "transparent",
    "overrides",
    "linux-gnome_terminal_configuration#Transparency",
    "git clone",
    "palette.toml",
    "rebelot/kanagawa.nvim",
    "bb85e4b",
    "| `ptyxis` |",
    "skipped (not installed)",
    "org.gnome.Ptyxis/palettes/Ukiyo-e.palette",
    "`default-profile-uuid`",
    "effective default",
    "open Ptyxis tabs keep",
    "`opacity`",
    "  ptyxis.py           #",
    "  test_ptyxis.py      #",
    # REQ-DOC-1, 16-colour revision.
    "`base00`", "`base07`", "`base0F`",
    "lavaBlack", "cinderBlack", "basaltGray", "ashGray", "mistGray",
    "hazeGray", "cloudGray", "snowWhite",
    "fujiRed", "persimmonOrange", "strawYellow", "pineGreen",
    "lakeAqua", "ridgeBlue", "twilightViolet", "blossomPink",
    "OKLCH", "C 0.051", "documentation only", "Mount Fuji",
    "reserved",
    "darkRed", "darkOrange", "darkYellow", "darkGreen",
    "darkAqua", "darkBlue", "darkViolet", "darkPink",
    "50 %", "required entries",
    "5.0:1", "5.3:1", "3.8:1", "2026-09-28",
    "python3 tests/regen_nvim_reference.py",
    "python3 -m unittest discover -s tests",
)
README_ABSENT = ("@plugin", '"louis01010100/theme"', "scripts/generate.py",
                 "gnome-terminal/install.sh",
                 "UKIYO_E_KANAGAWA" + "_SEED")
LICENSE_ITEMS = (
    "MIT License",
    "Permission is hereby granted, free of charge",
    'THE SOFTWARE IS PROVIDED "AS IS"',
    "louis01010100",
    "Copyright (c) 2021 Tommaso Laurenzi",
    "derived from rebelot/kanagawa.nvim",
)


def docs_text():
    """README.md (theme definition) and INSTALL.md (installation)."""
    return "".join((support.REPO / name).read_text()
                   for name in ("README.md", "INSTALL.md"))


class DocsTest(unittest.TestCase):
    def test_readme_items(self):
        text = docs_text()
        for item in README_ITEMS:
            self.assertIn(item, text)

    def test_readme_absent_items(self):
        text = docs_text()
        for item in README_ABSENT:
            self.assertNotIn(item, text)

    def test_license_items(self):
        text = (support.REPO / "LICENSE").read_text()
        for item in LICENSE_ITEMS:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
