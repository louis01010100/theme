# Ukiyo-e

One palette for GNOME Terminal, tmux, and Neovim.

`palette.toml` is the only hand-edited colour file. `configure.py`
validates it, then applies the theme to this machine: it installs the
Neovim colorscheme (`ukiyo_e`) and the tmux theme into a local install
directory, updates the "Ukiyo-e" GNOME Terminal profile, and reloads
the theme on your running tmux server. Version 1 of the palette
reproduces Kanagawa Dragon exactly. The repository holds source only;
nothing is committed, pushed, or fetched to apply a colour change.

## Layout

```text
palette.toml          # named colours: the only hand-edited colour file
configure.py          # entry point: python3 configure.py [target] [flags]
configurator/         # validation, role mappings, install, per-tool apply
  cli.py              #   argument parsing, run order, exit codes
  palette.py          #   palette.toml loading and validation
  terminal_ansi.py    #   ANSI: 16 terminal colours (GNOME and Neovim)
  gnome.py            #   TERMINAL_ROLES, "Ukiyo-e" profile via gsettings
  tmux.py             #   TMUX_ROLES, template rendering, server reload
  nvim.py             #   rendered Neovim palette module
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
```

## Workflow

1. Edit `palette.toml` (`[palette]`: `name = "#RRGGBB"`). Optionally
   edit the role mappings in `configurator/` (`ANSI` in
   `terminal_ansi.py`, `TERMINAL_ROLES` in `gnome.py`, `TMUX_ROLES` in
   `tmux.py`), the Lua under `nvim/`, or the templates under `tmux/`.
2. Run `python3 configure.py` (Python 3.11 or later, standard library
   only; no root).
3. Check the report: one line per target (`updated`, `unchanged`, ...)
   with the files and settings that changed.

Every palette entry, mapping, and template is validated before anything
changes; any error is printed (file, table or constant, and key) and
nothing is touched.

## Getting the source

On another machine, clone the repository and run the configurator:

```sh
git clone https://github.com/louis01010100/theme.git
cd theme
python3 configure.py
```

## Command line

```text
python3 configure.py [all|gnome|tmux|nvim] [--dry-run] [--uninstall] [--set-default] [-h|--help]
```

| Target | Effect |
|---|---|
| `all` (default) | `gnome`, then `tmux`, then `nvim` |
| `gnome` | the "Ukiyo-e" GNOME Terminal profile |
| `tmux` | the tmux theme files, then a reload of the running server |
| `nvim` | the Neovim colorscheme files |

| Flag | Effect |
|---|---|
| `--dry-run` | Report what would change (`would update`, `would remove`) with the same detail lines; change nothing. |
| `--uninstall` | Remove the target instead (does not read `palette.toml`). |
| `--set-default` | With `gnome` or `all`: also make "Ukiyo-e" the default profile. Not with `--uninstall`. |

| Exit code | Meaning |
|---|---|
| `0` | Success, including a dry run and an all-`unchanged` run. |
| `2` | Usage error. |
| `3` | Validation error, unreadable input, unsupported Python, unresolvable install directory, or missing prerequisite; nothing changed. |
| `4` | An apply step failed or was interrupted; the report says what remains. |

## Install directory

Files are installed under `$XDG_DATA_HOME/ukiyo_e` when `XDG_DATA_HOME`
is set and absolute, otherwise `~/.local/share/ukiyo_e`. That path is a
symlink to a complete version under `ukiyo_e.versions/`; each run that
changes files builds a new version and switches the symlink atomically,
so a failed or interrupted run never leaves a half-written theme. Do not
edit files there by hand; they are overwritten.

## One-time configuration

Add these two lines by hand once (the configurator never edits your
dotfiles). If `XDG_DATA_HOME` is set, adjust `~/.local/share` in both.

Neovim, as a lazy.nvim spec:

```lua
{ dir = "~/.local/share/ukiyo_e", lazy = false, priority = 1000, config = function() require("ukiyo_e").setup({ transparent = true }); vim.cmd.colorscheme("ukiyo_e") end }
```

tmux, in `~/.tmux.conf` (after any `@ukiyo_e_*` options):

```tmux
run-shell ~/.local/share/ukiyo_e/ukiyo_e.tmux
```

## Live effect

- GNOME Terminal: open windows change immediately.
- tmux: when the tmux files change, `configure.py` re-runs the installed
  `ukiyo_e.tmux` on the server your `tmux` command would reach; no
  restart. Without a running server (or without `tmux`) the reload is
  skipped and reported.
- Neovim: running instances keep their colours until the next
  `:colorscheme ukiyo_e` (or a restart), which loads the new version.

## Neovim

Requires Neovim 0.10 or later and a true-colour terminal.
`:colorscheme ukiyo_e` works without calling `setup`.

| `setup` option | Default | Effect |
|---|---|---|
| `transparent` | `false` | `true` leaves the `Normal` background unset (`NONE`), so the terminal background shows through. |
| `overrides` | `nil` | `function(colors) -> table` returning highlight group → spec. `colors` is `{ palette = …, theme = … }`. A returned spec is merged over the built-in one (a non-empty spec drops a built-in `link`). |

`require("ukiyo_e").palette()` returns a copy of the palette
(name → `#rrggbb`); `vim.g.terminal_color_0` … `15` come from the same
16-colour mapping as the GNOME Terminal palette.

## tmux

Requires tmux 3.5 or later. Set any options **before** the `run-shell`
line:

| Option | Default | Effect |
|---|---|---|
| `@ukiyo_e_no_patched_font` | `off` | `on` uses plain separators instead of powerline glyphs. |
| `@ukiyo_e_show_status_content` | `on` | `off` applies colours only; your `status-left`, `status-right`, and window formats are left alone. |
| `@ukiyo_e_date_format` | `%Y-%m-%d` | strftime format of the date in `status-right`. |

The time is shown as `%H:%M`, or `%I:%M %p` when `clock-mode-style` is
`12`. The default status content uses powerline glyphs, which need a
Nerd Font (or another powerline-patched font); without one, set
`@ukiyo_e_no_patched_font on`. The theme sets only global style and
format options; it never changes key bindings, the prefix, hooks, or
the environment.

**Switching from nord-dark-tmux:** only one theme may own the status
bar. Remove the `nord-dark-tmux` plugin line from your tmux
configuration.

## GNOME Terminal

`python3 configure.py gnome` creates or updates the "Ukiyo-e" profile
(fixed UUID, so never a duplicate) and writes only the settings whose
values differ: its name, its colours (background, foreground, the
16-colour palette, cursor, and selection colours), and the switches
that make GNOME Terminal use them, plus the profile list. The default
profile changes only with `--set-default`. If a write fails, the
settings already written are restored.

Not changed: font, size, transparency, scrolling, keybindings, any
other setting of the profile, and every other profile. Needs
`gsettings` and the GNOME Terminal schemas.

## Transparency

Transparency is configured outside the configurator: in Neovim with
`setup({ transparent = true })`, and in GNOME Terminal with the
profile's own transparency setting (Preferences → the profile →
Colors → "Use transparent background"; author's notes:
`linux-gnome_terminal_configuration#Transparency`).

## Uninstall

```sh
python3 configure.py all --uninstall
```

This removes the GNOME profile (making the first remaining profile the
default if it was the default), the install directory, and resets the
theme's tmux options on the running server to tmux defaults. Then remove
the two one-time lines above by hand.

## Tests

```sh
UKIYO_E_KANAGAWA_SEED=~/.local/share/nvim/lazy/kanagawa.nvim \
    python3 -m unittest discover -s tests
```

The suite uses scratch home and data directories, headless Neovim, a
dedicated tmux server, and an isolated D-Bus session with a scratch
dconf database; it never touches your running tmux server, your real
install directory, or your real GNOME Terminal settings.

## Credits

The Neovim theme layer, the highlight groups, and the v1 palette are
derived from [Kanagawa](https://github.com/rebelot/kanagawa.nvim)
(rebelot/kanagawa.nvim) by Tommaso Laurenzi, seeded from commit
`bb85e4b` (`bb85e4bfc8d89b0e62c8fa53ccdd13d12e2f77b3`), Dragon variant.
The tmux theme follows the structure of
[nord-dark-tmux](https://github.com/louis01010100/nord-dark-tmux).

MIT licensed; see `LICENSE`.
