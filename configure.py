#!/usr/bin/env python3
"""Apply the Ukiyo-e palette to GNOME Terminal, tmux, and Neovim."""

import os
import sys

if sys.version_info < (3, 11):
    sys.stderr.write("configure.py: Python 3.11 or later is required\n")
    sys.exit(3)

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

import configurator.cli  # noqa: E402

raise SystemExit(configurator.cli.main(sys.argv[1:]))
