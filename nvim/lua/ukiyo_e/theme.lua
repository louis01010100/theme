-- Theme layer: semantic colour roles built from palette names.
-- Transcribed from the kanagawa.nvim "dragon" theme at bb85e4b.

local function pmenu_float(palette)
    return {
        pmenu = {
            fg = palette.fujiWhite,
            fg_sel = "none",
            bg = palette.waveBlue1,
            bg_sel = palette.waveBlue2,
            bg_thumb = palette.waveBlue2,
            bg_sbar = palette.waveBlue1,
        },
        float = {
            fg = palette.oldWhite,
            bg = palette.dragonBlack0,
            fg_border = palette.sumiInk6,
            bg_border = palette.dragonBlack0,
        },
    }
end

local function ui(palette)
    local roles = {
        fg = palette.dragonWhite,
        fg_dim = palette.oldWhite,
        fg_reverse = palette.waveBlue1,
        bg_dim = palette.dragonBlack1,
        bg_gutter = palette.dragonBlack4,
        bg_m3 = palette.dragonBlack0,
        bg_m2 = palette.dragonBlack1,
        bg_m1 = palette.dragonBlack2,
        bg = palette.dragonBlack3,
        bg_p1 = palette.dragonBlack4,
        bg_p2 = palette.dragonBlack5,
        special = palette.dragonGray3,
        whitespace = palette.dragonBlack6,
        nontext = palette.dragonBlack6,
        bg_visual = palette.waveBlue1,
        bg_search = palette.waveBlue2,
    }
    for key, value in pairs(pmenu_float(palette)) do
        roles[key] = value
    end
    return roles
end

local function syn(palette)
    return {
        string = palette.dragonGreen2,
        variable = "none",
        number = palette.dragonPink,
        constant = palette.dragonOrange,
        identifier = palette.dragonYellow,
        parameter = palette.dragonGray,
        fun = palette.dragonBlue2,
        statement = palette.dragonViolet,
        keyword = palette.dragonViolet,
        operator = palette.dragonRed,
        preproc = palette.dragonRed,
        type = palette.dragonAqua,
        regex = palette.dragonRed,
        deprecated = palette.katanaGray,
        punct = palette.dragonGray2,
        comment = palette.dragonAsh,
        special1 = palette.dragonTeal,
        special2 = palette.dragonRed,
        special3 = palette.dragonRed,
    }
end

local function diag_diff_vcs(palette)
    return {
        diag = {
            error = palette.samuraiRed,
            ok = palette.springGreen,
            warning = palette.roninYellow,
            info = palette.dragonBlue,
            hint = palette.waveAqua1,
        },
        diff = {
            add = palette.winterGreen,
            delete = palette.winterRed,
            change = palette.winterBlue,
            text = palette.winterYellow,
        },
        vcs = {
            added = palette.autumnGreen,
            removed = palette.autumnRed,
            changed = palette.autumnYellow,
        },
    }
end

---@param palette table<string, string> palette name -> "#rrggbb"
---@return table theme layer: ui, syn, diag, diff, vcs
return function(palette)
    local theme = diag_diff_vcs(palette)
    theme.ui = ui(palette)
    theme.syn = syn(palette)
    return theme
end
