-- Treesitter highlight groups, transcribed from
-- kanagawa.nvim at bb85e4b (dragon theme, default config).

local M = {}

local function part_1(theme)
    local ui = theme.ui
    return {
        ["@variable"] = { fg = ui.fg },
        ["@variable.builtin"] = { fg = theme.syn.special2, italic = true },
        ["@variable.parameter"] = { fg = theme.syn.parameter },
        ["@variable.member"] = { fg = theme.syn.identifier },
        -- @string                 string literals
        ["@string.regexp"] = { fg = theme.syn.regex },
        -- @string.escape          escape sequences
        ["@string.escape"] = { fg = theme.syn.regex, bold = true },
        -- @string.special.symbol  symbols or atoms
        ["@string.special.symbol"] = { fg = theme.syn.identifier },
        -- @string.special.path    filenames
        ["@string.special.url"] = {
            fg = theme.syn.special1,
            undercurl = true,
        },
        --
        ["@attribute"] = { link = "Constant" },
        -- @function.call          function calls
        ["@function.macro"] = { link = "Macro" },
        --
        ["@constructor"] = { fg = theme.syn.special1 },
        ["@constructor.lua"] = { fg = theme.syn.keyword },
        ["@operator"] = { link = "Operator" },
        --
        ["@keyword.operator"] = { fg = theme.syn.operator, bold = true },
        ["@keyword.import"] = { link = "PreProc" },
        ["@keyword.return"] = { fg = theme.syn.special3, italic = true },
        ["@keyword.exception"] = { fg = theme.syn.special3, bold = true },
        ["@keyword.luap"] = { link = "@string.regex" },
        --
        ["@punctuation.delimiter"] = { fg = theme.syn.punct },
        ["@punctuation.bracket"] = { fg = theme.syn.punct },
        ["@punctuation.special"] = { fg = theme.syn.special1 },
    }
end

local function part_2(theme)
    return {
        --
        ["@comment.error"] = {
            fg = theme.ui.fg,
            bg = theme.diag.error,
            bold = true,
        },
        ["@comment.warning"] = {
            fg = theme.ui.fg_reverse,
            bg = theme.diag.warning,
            bold = true,
        },
        ["@comment.note"] = {
            fg = theme.ui.fg_reverse,
            bg = theme.diag.hint,
            bold = true,
        },
        -- @markup.strong          bold text
        ["@markup.strong"] = { bold = true },
        -- @markup.italic          italic text
        ["@markup.italic"] = { italic = true },
        ["@markup.strikethrough"] = { strikethrough = true },
        ["@markup.underline"] = { underline = true },
        --
        ["@markup.heading"] = { link = "Function" },
        -- @markup.quote           block quotes
        ["@markup.quote"] = { link = "@variable.parameter" },
        ["@markup.math"] = { link = "Constant" },
        ["@markup.environment"] = { link = "Keyword" },
        -- @markup.link.url        URL-style links
        ["@markup.link.url"] = { link = "@string.special.url" },
        ["@markup.raw"] = { link = "String" },
        --
        ["@diff.plus"] = { fg = theme.vcs.added },
        ["@diff.minus"] = { fg = theme.vcs.removed },
    }
end

local function part_3(theme)
    return {
        ["@diff.delta"] = { fg = theme.vcs.changed },
        --
        ["@tag.attribute"] = { fg = theme.syn.identifier },
        ["@tag.delimiter"] = { fg = theme.syn.punct },
    }
end

---@param colors table colours; only colors.theme is used
---@param config table { transparent }
---@return table<string, table> group name -> highlight spec
function M.setup(colors, config)
    local groups = {}
    for _, part in ipairs({ part_1, part_2, part_3 }) do
        for name, spec in pairs(part(colors.theme, config)) do
            groups[name] = spec
        end
    end
    return groups
end

return M
