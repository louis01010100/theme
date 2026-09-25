-- Editor highlight groups, transcribed from
-- kanagawa.nvim at bb85e4b (dragon theme, default config).

local M = {}

local function part_1(theme)
    local ui = theme.ui
    return {
        ColorColumn = { bg = ui.bg_p1 },
        Conceal = { fg = ui.special, bold = true },
        CurSearch = { fg = ui.fg, bg = ui.bg_search, bold = true },
        -- Cursor		Character under the cursor.
        Cursor = { fg = ui.bg, bg = ui.fg },
        lCursor = { link = "Cursor" },
        CursorIM = { link = "Cursor" },
        CursorColumn = { link = "CursorLine" },
        CursorLine = { bg = ui.bg_p2 },
        Directory = { fg = theme.syn.fun },
        DiffAdd = { bg = theme.diff.add },
        DiffChange = { bg = theme.diff.change },
        DiffDelete = { fg = theme.vcs.removed, bg = theme.diff.delete },
        DiffText = { bg = theme.diff.text },
        EndOfBuffer = { fg = ui.bg },
        -- TermCursor	Cursor in a focused terminal.
        ErrorMsg = { fg = theme.diag.error },
        WinSeparator = { fg = ui.bg_m3, bg = "NONE" },
        VertSplit = { link = "WinSeparator" },
        -- Folded		Line used for closed folds.
        Folded = { fg = ui.special, bg = ui.bg_p1 },
        -- FoldColumn	'foldcolumn'
        FoldColumn = { fg = ui.nontext, bg = ui.bg_gutter },
        SignColumn = { fg = ui.special, bg = ui.bg_gutter },
        IncSearch = { fg = ui.fg_reverse, bg = theme.diag.warning },
        Substitute = { fg = ui.fg, bg = theme.vcs.removed },
        LineNr = { fg = ui.nontext, bg = ui.bg_gutter },
        CursorLineNr = {
            fg = theme.diag.warning,
            bg = ui.bg_gutter,
            bold = true,
        },
        MatchParen = { fg = theme.diag.warning, bold = true },
        ModeMsg = { fg = theme.diag.warning, bold = true },
    }
end

local function part_2(theme, config)
    local ui = theme.ui
    return {
        -- MsgArea		Area for messages and cmdline.
        MsgArea = vim.o.cmdheight == 0 and { link = "StatusLine" }
            or { fg = ui.fg_dim },
        MsgSeparator = {
            bg = vim.o.cmdheight == 0 and ui.bg or ui.bg_m3,
            fg = ui.bg_m3,
        },
        -- MoreMsg		|more-prompt|
        MoreMsg = { fg = theme.diag.info },
        NonText = { fg = ui.nontext },
        -- Normal		Normal text.
        Normal = {
            fg = ui.fg,
            bg = config.transparent and "NONE" or ui.bg,
        },
        NormalFloat = { fg = ui.float.fg, bg = ui.float.bg },
        -- FloatBorder	Border of floating windows.
        FloatBorder = {
            fg = ui.float.fg_border,
            bg = ui.float.bg_border,
        },
        -- FloatTitle	Title of floating windows.
        FloatTitle = {
            fg = ui.special,
            bg = ui.float.bg_border,
            bold = true,
        },
        -- FloatFooter	Footer of floating windows.
        FloatFooter = { fg = ui.nontext, bg = ui.float.bg_border },
        NormalNC = { link = "Normal" },
        Pmenu = { fg = ui.pmenu.fg, bg = ui.pmenu.bg },
        PmenuSel = { fg = ui.pmenu.fg_sel, bg = ui.pmenu.bg_sel },
        PmenuKind = { fg = ui.fg_dim, bg = ui.pmenu.bg },
        PmenuKindSel = { fg = ui.fg_dim, bg = ui.pmenu.bg_sel },
    }
end

local function part_3(theme)
    local ui = theme.ui
    return {
        PmenuExtra = { fg = ui.special, bg = ui.pmenu.bg },
        PmenuExtraSel = { fg = ui.special, bg = ui.pmenu.bg_sel },
        PmenuSbar = { bg = ui.pmenu.bg_sbar },
        PmenuThumb = { bg = ui.pmenu.bg_thumb },
        PmenuBorder = { link = "FloatBorder" },
        Question = { link = "MoreMsg" },
        QuickFixLine = { bg = ui.bg_p1 },
        Search = { fg = ui.fg, bg = ui.bg_search },
        SpecialKey = { fg = ui.special },
        SpellBad = {
            undercurl = true,
            underline = false,
            sp = theme.diag.error,
        },
        SpellCap = {
            undercurl = true,
            underline = false,
            sp = theme.diag.warning,
        },
        SpellLocal = {
            undercurl = true,
            underline = false,
            sp = theme.diag.warning,
        },
        SpellRare = {
            undercurl = true,
            underline = false,
            sp = theme.diag.warning,
        },
        StatusLine = { fg = ui.fg_dim, bg = ui.bg_m3 },
        StatusLineNC = { fg = ui.nontext, bg = ui.bg_m3 },
        TabLine = { bg = ui.bg_m3, fg = ui.special },
        TabLineFill = { bg = ui.bg },
        TabLineSel = { fg = ui.fg_dim, bg = ui.bg_p1 },
        Title = { fg = theme.syn.fun, bold = true },
        -- Visual		Visual mode selection.
        Visual = { bg = ui.bg_visual },
        VisualNOS = { link = "Visual" },
    }
end

local function part_4(theme)
    local ui = theme.ui
    return {
        -- WarningMsg	Warning messages.
        WarningMsg = { fg = theme.diag.warning },
        Whitespace = { fg = ui.whitespace },
        WildMenu = { link = "Pmenu" },
        -- WinBar		Window bar of current window.
        WinBar = { fg = ui.fg_dim, bg = "NONE" },
        WinBarNC = { fg = ui.fg_dim, bg = "NONE" },
        debugPC = { bg = theme.diff.delete },
        debugBreakpoint = { fg = theme.syn.special1, bg = ui.bg_gutter },
        LspReferenceText = { bg = theme.diff.text },
        LspReferenceRead = { link = "LspReferenceText" },
        LspReferenceWrite = { bg = theme.diff.text, underline = true },
        DiagnosticError = { fg = theme.diag.error },
        DiagnosticWarn = { fg = theme.diag.warning },
        DiagnosticInfo = { fg = theme.diag.info },
        DiagnosticHint = { fg = theme.diag.hint },
        DiagnosticOk = { fg = theme.diag.ok },
        DiagnosticFloatingError = { fg = theme.diag.error },
        DiagnosticFloatingWarn = { fg = theme.diag.warning },
        DiagnosticFloatingInfo = { fg = theme.diag.info },
        DiagnosticFloatingHint = { fg = theme.diag.hint },
        DiagnosticFloatingOk = { fg = theme.diag.ok },
        DiagnosticSignError = { fg = theme.diag.error, bg = ui.bg_gutter },
        DiagnosticSignWarn = { fg = theme.diag.warning, bg = ui.bg_gutter },
        DiagnosticSignInfo = { fg = theme.diag.info, bg = ui.bg_gutter },
        DiagnosticSignHint = { fg = theme.diag.hint, bg = ui.bg_gutter },
        DiagnosticVirtualTextError = { link = "DiagnosticError" },
        DiagnosticVirtualTextWarn = { link = "DiagnosticWarn" },
        DiagnosticVirtualTextInfo = { link = "DiagnosticInfo" },
        DiagnosticVirtualTextHint = { link = "DiagnosticHint" },
    }
end

local function part_5(theme)
    return {
        DiagnosticUnderlineError = {
            undercurl = true,
            underline = false,
            sp = theme.diag.error,
        },
        DiagnosticUnderlineWarn = {
            undercurl = true,
            underline = false,
            sp = theme.diag.warning,
        },
        DiagnosticUnderlineInfo = {
            undercurl = true,
            underline = false,
            sp = theme.diag.info,
        },
        DiagnosticUnderlineHint = {
            undercurl = true,
            underline = false,
            sp = theme.diag.hint,
        },
        LspSignatureActiveParameter = { fg = theme.diag.warning },
        LspCodeLens = { fg = theme.syn.comment },
        -- vcs
        diffAdded = { fg = theme.vcs.added },
        diffRemoved = { fg = theme.vcs.removed },
        diffDeleted = { fg = theme.vcs.removed },
        diffChanged = { fg = theme.vcs.changed },
        diffOldFile = { fg = theme.vcs.removed },
        diffNewFile = { fg = theme.vcs.added },
    }
end

---@param colors table colours; only colors.theme is used
---@param config table { transparent }
---@return table<string, table> group name -> highlight spec
function M.setup(colors, config)
    local groups = {}
    for _, part in ipairs({ part_1, part_2, part_3, part_4, part_5 }) do
        for name, spec in pairs(part(colors.theme, config)) do
            groups[name] = spec
        end
    end
    return groups
end

return M
