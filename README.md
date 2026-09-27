# Ukiyo-e

One palette for GNOME Terminal, Ptyxis, tmux, Neovim, and `ls`
(`dircolors`). This document defines the theme: the palette, the derived
shades, and how each tool uses them. To install or apply it, see
[INSTALL.md](INSTALL.md).

`palette.toml` is the only hand-edited colour file. The palette is 16
base16 slots derived from Kanagawa Dragon (see Palette); `configure.py`
validates it and renders every tool's colours from it.

## Layout

palette.toml          # the 16 slots: the only hand-edited colour file
configure.py          # entry point: python3 configure.py [target] [flags]
README.md             # the theme definition (this file)
INSTALL.md            # installation, command line, one-time configuration
configurator/         # validation, role mappings, install, per-tool apply
  cli.py              #   argument parsing, run order, exit codes
  palette.py          #   palette.toml validation, derived shades
  terminal_ansi.py    #   ANSI (16 colours), TERMINAL_ROLES (shared)
  settings.py         #   gsettings access shared by gnome and ptyxis
  gnome.py            #   "Ukiyo-e" GNOME Terminal profile via gsettings
  ptyxis.py           #   PTYXIS_KEYS, Ptyxis palette file and profile
  tmux.py             #   TMUX_ROLES, template rendering, server reload
  nvim.py             #   rendered Neovim palette module
  dircolors.py        #   DIRCOLORS_ROLES, rendered ls colour database
  install_dir.py      #   $XDG_DATA_HOME/ukiyo_e resolution
  files.py            #   version build, atomic symlink switch, cleanup
  report.py           #   per-target report lines
nvim/                 # Neovim colorscheme source (installed as-is)
  colors/ukiyo_e.lua
  lua/ukiyo_e/        #   init.lua, theme.lua, highlights/*.lua
tmux/                 # tmux theme source
  ukiyo_e.tmux        #   entry script run by `run-shell`
  *.conf.tmpl         #   templates rendered with {{role}} colours
tests/                # unittest suite (isolated; see Tests below)
  test_ptyxis.py      #   Ptyxis lifecycle, edges, single-schema runs
  regen_nvim_reference.py  # rewrites the Neovim reference snapshot
  reference/          #   nvim-highlights.json (verification fixture)
```

## Palette

`palette.toml` has one table, `[palette]`, holding the 16 base16 slots
`base00`–`base0F` (spelled exactly so). `base00`–`base07` are neutrals
from dark to light (`base00` the background, `base07` normal text):
`base07` is its Kanagawa origin 10 % darker with HSL saturation
2 points lower (`base00` likewise loses 2 points, which rounds to the
same value), and `base01`–`base06`
are spaced linearly between `base00` and `base07` (per RGB channel,
step 1/7, rounded half to even);
`base08`–`base0F` are the eight accents, each 20 % darker (HSL
lightness × 0.8) and 36 % less saturated (HSL saturation × 0.8,
applied twice) than its Kanagawa origin.

| Slot | Name | Role | Value | Kanagawa origin |
|---|---|---|---|---|
| `base00` | lavaBlack | background (darkest neutral) | `#181616` | dragonBlack3 |
| `base01` | cinderBlack | neutral | `#2e2d2c` | dragonBlack4, linear 1/7 |
| `base02` | basaltGray | neutral | `#444343` | dragonBlack5, linear 2/7 |
| `base03` | ashGray | neutral | `#5a5a59` | dragonBlack6, linear 3/7 |
| `base04` | mistGray | neutral | `#70706f` | dragonGray3, linear 4/7 |
| `base05` | hazeGray | neutral | `#868785` | dragonGray2, linear 5/7 |
| `base06` | cloudGray | neutral | `#9c9d9c` | dragonGray, linear 6/7 |
| `base07` | snowWhite | normal text (lightest neutral) | `#b2b4b2` | dragonWhite, 10 % darker, saturation −2 points |
| `base08` | fujiRed | red | `#9c5e59` | dragonRed, 20 % darker, 36 % less saturated |
| `base09` | persimmonOrange | orange | `#907564` | dragonOrange, 20 % darker, 36 % less saturated |
| `base0A` | strawYellow | yellow | `#a0906c` | dragonYellow, 20 % darker, 36 % less saturated |
| `base0B` | pineGreen | green | `#6e7965` | dragonGreen2, 20 % darker, 36 % less saturated |
| `base0C` | lakeAqua | cyan | `#728381` | dragonAqua, 20 % darker, 36 % less saturated |
| `base0D` | ridgeBlue | blue | `#6f838d` | dragonBlue2, 20 % darker, 36 % less saturated |
| `base0E` | twilightViolet | violet | `#6f7584` | dragonViolet, 20 % darker, 36 % less saturated |
| `base0F` | blossomPink | pink | `#827582` | dragonPink, 20 % darker, 36 % less saturated |

Each slot line carries a comment with its name, its Kanagawa origin,
and the removed Kanagawa colours merged into it. The names
(`lavaBlack` … `snowWhite`, `fujiRed` … `blossomPink`) are
documentation only: mappings, templates, and Lua refer to slots by
slot name.

Extra names are allowed (for example a colour added later for tmux).
By convention they follow the Mount Fuji naming style: a landscape
image plus a plain English colour word, in camelCase. Some names are
reserved and rejected in any letter case: a slot name in another case
(e.g. `base0a`), the eight `dark*` shade names, and the neutral and
accent names above.

**Derived shades.** Eight dark shades are computed from the slots on
every run: `darkRed`, `darkOrange`, `darkYellow`, `darkGreen`,
`darkAqua`, `darkBlue`, `darkViolet`, `darkPink`, each 50 % of
its accent (`base08` … `base0F`) blended with 50 % `base00` (per
channel, rounded half to even). They are never stored in
`palette.toml`; mappings use them by name like a slot. Uses: diff
backgrounds (`darkGreen` added, `darkRed` removed, `darkBlue`
changed, `darkYellow` changed text); `darkBlue` for the completion
menu and Neovim's reverse text; `darkAqua` for search and the
completion-menu selection; `darkRed` for the
current window of the tmux status bar; in `ls`, `darkBlue` behind
sticky and other-writable directories and `darkRed` behind setuid
files. `darkOrange`, `darkViolet`,
and `darkPink` are not used yet.

**Contrast (accepted 2026-09-26).** Normal text `base07` on the shades
is 3.6:1 to 4.8:1, below 4.5:1 on the yellow, aqua, blue, orange,
and pink shades (lowest 3.6:1 on `darkYellow`); on `base00` it is
8.6:1. As code text on `base00`, the darkened red, violet,
pink, green, and orange accents are below 4.5:1 (lowest about 3.6:1,
red). Both are accepted in favour of the darker look and readable
dark shades; no check enforces a contrast ratio.

**Neovim reference snapshot.** `tests/reference/nvim-highlights.json`
records the highlight groups the colorscheme sets for the committed
palette. After a deliberate change to `palette.toml`, the theme layer,
or the highlight modules, regenerate it with
`python3 tests/regen_nvim_reference.py`, review its diff, and commit
it together with the change.

## Role mappings

Each tool maps its own roles to slot or shade names, never to hex
values: `ANSI` and `TERMINAL_ROLES` in `configurator/terminal_ansi.py`
(the 16-colour terminal palette and the background, foreground, cursor,
and selection colours shared by GNOME Terminal and Ptyxis),
`PTYXIS_KEYS` in `configurator/ptyxis.py`, `TMUX_ROLES` in
`configurator/tmux.py`, `DIRCOLORS_ROLES` in
`configurator/dircolors.py`, and the theme layer in
`nvim/lua/ukiyo_e/theme.lua`. `vim.g.terminal_color_0` … `15` come
from the same 16-colour mapping as the terminal palette.

## Credits

The Neovim theme layer, the highlight groups, and the v1 palette are
derived from [Kanagawa](https://github.com/rebelot/kanagawa.nvim)
(rebelot/kanagawa.nvim) by Tommaso Laurenzi, seeded from commit
`bb85e4b` (`bb85e4bfc8d89b0e62c8fa53ccdd13d12e2f77b3`), Dragon variant.
The tmux theme follows the structure of
[nord-dark-tmux](https://github.com/louis01010100/nord-dark-tmux).

MIT licensed; see `LICENSE`.
