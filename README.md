# Ukiyo-e

One palette for GNOME Terminal, tmux, and Neovim.

`palette.toml` is the only hand-edited colour file. A small generator,
`scripts/generate.py`, renders it into committed files for a Neovim
colorscheme (`ukiyo_e`), a tmux theme, and a GNOME Terminal profile
installer. Version 1 reproduces Kanagawa Dragon exactly, so the three
tools start from a verified baseline and every later colour change is
made once and propagates everywhere.

Installing never runs Python; only regenerating does.

## Neovim

Requires Neovim 0.10 or later and a true-colour terminal. With
[lazy.nvim](https://github.com/folke/lazy.nvim):

```lua
{
  "louis01010100/theme",
  lazy = false,
  priority = 1000,
  config = function()
    require("ukiyo_e").setup({ transparent = true })
    vim.cmd.colorscheme("ukiyo_e")
  end,
}
```

`:colorscheme ukiyo_e` also works without calling `setup`.

### `setup` options

| Option | Default | Effect |
|---|---|---|
| `transparent` | `false` | `true` leaves the `Normal` background unset (`NONE`), so the terminal background shows through. |
| `overrides` | `nil` | `function(colors) -> table` returning highlight group → spec. `colors` is `{ palette = …, theme = … }`. A returned spec is merged over the built-in one (a non-empty spec drops a built-in `link`). |

Other functions: `require("ukiyo_e").load()` applies the colorscheme;
`require("ukiyo_e").palette()` returns a copy of the palette
(name → `#rrggbb`). `vim.g.terminal_color_0` … `15` are set from
`[terminal].ansi`.

## tmux

Requires tmux 3.5 or later and [TPM](https://github.com/tmux-plugins/tpm).
Add to your tmux configuration, then press `prefix + I`:

```tmux
set -g @plugin 'louis01010100/theme'
```

Set any options **before** TPM runs:

| Option | Default | Effect |
|---|---|---|
| `@ukiyo_e_no_patched_font` | `off` | `on` uses plain separators instead of powerline glyphs. |
| `@ukiyo_e_show_status_content` | `on` | `off` applies colours only; your `status-left`, `status-right`, and window formats are left alone. |
| `@ukiyo_e_date_format` | `%Y-%m-%d` | strftime format of the date in `status-right`. |

The time is shown as `%H:%M`, or `%I:%M %p` when `clock-mode-style` is
`12`. The default status content uses powerline glyphs, which need a
Nerd Font (or another powerline-patched font); without one, set
`@ukiyo_e_no_patched_font on`.

The theme sets only global style and format options; it never changes
key bindings, the prefix, hooks, or the environment.

**Switching from nord-dark-tmux:** only one theme may own the status
bar. Remove the `nord-dark-tmux` plugin line from your tmux
configuration before adding this one.

## GNOME Terminal

```sh
gnome-terminal/install.sh                 # install or update "Ukiyo-e"
gnome-terminal/install.sh --set-default   # ... and make it the default
gnome-terminal/install.sh --uninstall     # remove it
```

Needs bash, `gsettings`, and the GNOME Terminal schemas; no root, no
Python. The profile uses a fixed UUID, so re-running updates it in place
and never creates a duplicate.

What is changed: the profile's name, its colours (background,
foreground, the 16-colour palette, cursor, and selection colours) and
the switches that make GNOME Terminal use them, plus the profile list.
The default profile changes only with `--set-default`. `--uninstall`
removes the profile from the list, clears its settings, and, if it was
the default, makes the first remaining profile the default.

What is not changed: font, size, transparency, scrolling, keybindings,
any other setting of the profile, and every other profile.

## Transparency

Transparency is configured outside this project: in Neovim with
`setup({ transparent = true })`, and in GNOME Terminal with the
profile's own transparency setting (Preferences → the profile →
Colors → "Use transparent background"; author's notes:
`linux-gnome_terminal_configuration#Transparency`).

## Changing colours

1. Edit `palette.toml`. `[palette]` holds named `#RRGGBB` colours;
   `[terminal]` and `[tmux]` values are `#RRGGBB` or a `[palette]` name.
2. Regenerate: `python3 scripts/generate.py` (Python 3.11 or later,
   standard library only).
3. Verify: `python3 scripts/generate.py --check` exits 0 when every
   generated file is up to date (1 and a `stale:` list otherwise).
4. Commit `palette.toml` and the generated files together.

Generated files (never edit them by hand): `lua/ukiyo_e/palette.lua`,
`tmux/colors.conf`, `tmux/status.conf`, `tmux/status-plain.conf`, and
`gnome-terminal/palette.sh`. The Neovim highlight groups are
hand-written Lua in `lua/ukiyo_e/` that refers to colours by palette
name only.

## Tests

```sh
UKIYO_E_KANAGAWA_SEED=~/.local/share/nvim/lazy/kanagawa.nvim \
    python3 -m unittest discover -s tests
```

The suite uses headless Neovim, a dedicated tmux socket, and an isolated
D-Bus session with a scratch dconf database; it never touches your
running tmux server or your real GNOME Terminal settings.

## Credits

The Neovim theme layer, the highlight groups, and the v1 palette are
derived from [Kanagawa](https://github.com/rebelot/kanagawa.nvim)
(rebelot/kanagawa.nvim) by Tommaso Laurenzi, at commit `bb85e4b`
(`bb85e4bfc8d89b0e62c8fa53ccdd13d12e2f77b3`), Dragon variant. The tmux
theme follows the structure of
[nord-dark-tmux](https://github.com/louis01010100/nord-dark-tmux).

MIT licensed; see `LICENSE`.
