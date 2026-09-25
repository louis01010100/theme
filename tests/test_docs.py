"""V-12: README covers REQ-DOC-1; LICENSE satisfies REQ-DOC-2."""

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
    "python3 configure.py [all|gnome|tmux|nvim] [--dry-run] "
    "[--uninstall] [--set-default] [-h|--help]",
    "--dry-run",
    "| `0` |", "| `2` |", "| `3` |", "| `4` |",
    "XDG_DATA_HOME",
    "--set-default",
    "python3 configure.py all --uninstall",
    "@ukiyo_e_no_patched_font",
    "@ukiyo_e_show_status_content",
    "@ukiyo_e_date_format",
    "%Y-%m-%d",
    "Nerd Font",
    "nord-dark-tmux",
    "transparent",
    "overrides",
    "linux-gnome_terminal_configuration#Transparency",
    "git clone",
    "palette.toml",
    "rebelot/kanagawa.nvim",
    "bb85e4b",
)
README_ABSENT = ("@plugin", '"louis01010100/theme"', "scripts/generate.py",
                 "gnome-terminal/install.sh")
LICENSE_ITEMS = (
    "MIT License",
    "Permission is hereby granted, free of charge",
    'THE SOFTWARE IS PROVIDED "AS IS"',
    "louis01010100",
    "Copyright (c) 2021 Tommaso Laurenzi",
    "derived from rebelot/kanagawa.nvim",
)


class DocsTest(unittest.TestCase):
    def test_readme_items(self):
        text = (support.REPO / "README.md").read_text()
        for item in README_ITEMS:
            self.assertIn(item, text)

    def test_readme_absent_items(self):
        text = (support.REPO / "README.md").read_text()
        for item in README_ABSENT:
            self.assertNotIn(item, text)

    def test_license_items(self):
        text = (support.REPO / "LICENSE").read_text()
        for item in LICENSE_ITEMS:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
