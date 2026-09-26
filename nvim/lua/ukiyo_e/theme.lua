-- Theme layer: semantic colour roles built from the palette slots
-- (palette.base00 ... palette.base0F) and the derived shades
-- (shades.darkRed ...). Role set of the kanagawa.nvim "dragon"
-- theme at bb85e4b, without `term`.

local function pmenu_float(palette, shades)
    return {
        pmenu = {
            fg = palette.base07,
            fg_sel = "none",
            bg = shades.darkBlue,
            bg_sel = shades.darkAqua,
            bg_thumb = shades.darkAqua,
            bg_sbar = shades.darkBlue,
        },
        float = {
            fg = palette.base07,
            bg = palette.base00,
            fg_border = palette.base03,
            bg_border = palette.base00,
        },
    }
end

local function ui(palette, shades)
    local roles = {
        fg = palette.base07,
        fg_dim = palette.base07,
        fg_reverse = shades.darkBlue,
        bg_dim = palette.base00,
        bg_gutter = palette.base01,
        bg_m3 = palette.base00,
        bg_m2 = palette.base00,
        bg_m1 = palette.base00,
        bg = palette.base00,
        bg_p1 = palette.base01,
        bg_p2 = palette.base02,
        special = palette.base04,
        whitespace = palette.base03,
        nontext = palette.base03,
        bg_visual = shades.darkBlue,
        bg_search = shades.darkAqua,
    }
    for key, value in pairs(pmenu_float(palette, shades)) do
        roles[key] = value
    end
    return roles
end

local function syn(palette)
    return {
        string = palette.base0B,
        variable = "none",
        number = palette.base0F,
        constant = palette.base09,
        identifier = palette.base0A,
        parameter = palette.base06,
        fun = palette.base0D,
        statement = palette.base0E,
        keyword = palette.base0E,
        operator = palette.base08,
        preproc = palette.base08,
        type = palette.base0C,
        regex = palette.base08,
        deprecated = palette.base04,
        punct = palette.base05,
        comment = palette.base04,
        special1 = palette.base0E,
        special2 = palette.base08,
        special3 = palette.base08,
    }
end

local function diag_diff_vcs(palette, shades)
    return {
        diag = {
            error = palette.base08,
            ok = palette.base0B,
            warning = palette.base09,
            info = palette.base0D,
            hint = palette.base0C,
        },
        diff = {
            add = shades.darkGreen,
            delete = shades.darkRed,
            change = shades.darkBlue,
            text = shades.darkYellow,
        },
        vcs = {
            added = palette.base0B,
            removed = palette.base08,
            changed = palette.base0A,
        },
    }
end

---@param palette table<string, string> palette name -> "#rrggbb"
---@param shades table<string, string> shade name -> "#rrggbb"
---@return table theme layer: ui, syn, diag, diff, vcs
return function(palette, shades)
    local theme = diag_diff_vcs(palette, shades)
    theme.ui = ui(palette, shades)
    theme.syn = syn(palette)
    return theme
end
