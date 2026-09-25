"""V-DOC: README covers REQ-DOC-1; LICENSE satisfies REQ-DOC-2."""

import unittest

import support

README_ITEMS = (
    '"louis01010100/theme"',
    'colorscheme("ukiyo_e")',
    "set -g @plugin 'louis01010100/theme'",
    "prefix + I",
    "@ukiyo_e_no_patched_font",
    "@ukiyo_e_show_status_content",
    "@ukiyo_e_date_format",
    "%Y-%m-%d",
    "Nerd Font",
    "nord-dark-tmux",
    "gnome-terminal/install.sh",
    "--set-default",
    "--uninstall",
    "transparent",
    "overrides",
    "python3 scripts/generate.py",
    "python3 scripts/generate.py --check",
    "palette.toml",
    "rebelot/kanagawa.nvim",
    "bb85e4b",
    "linux-gnome_terminal_configuration#Transparency",
)
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

    def test_license_items(self):
        text = (support.REPO / "LICENSE").read_text()
        for item in LICENSE_ITEMS:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
