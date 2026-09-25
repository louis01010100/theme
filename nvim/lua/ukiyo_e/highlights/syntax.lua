-- Syntax highlight groups, transcribed from
-- kanagawa.nvim at bb85e4b (dragon theme, default config).

local M = {}

local function part_1(theme)
    return {
        -- *Comment	any comment
        Comment = { fg = theme.syn.comment, italic = true },
        -- *Constant	any constant
        Constant = { fg = theme.syn.constant },
        String = { fg = theme.syn.string },
        Character = { link = "String" },
        Number = { fg = theme.syn.number },
        Boolean = { fg = theme.syn.constant, bold = true },
        Float = { link = "Number" },
        -- *Identifier	any variable name
        Identifier = { fg = theme.syn.identifier },
        Function = { fg = theme.syn.fun },
        -- *Statement	any statement
        Statement = { fg = theme.syn.statement, bold = true },
        -- Label		case, default, etc.
        Operator = { fg = theme.syn.operator },
        -- Keyword	any other keyword
        Keyword = { fg = theme.syn.keyword, italic = true },
        -- Exception	try, catch, throw
        Exception = { fg = theme.syn.special2 },
        -- *PreProc	generic Preprocessor
        PreProc = { fg = theme.syn.preproc },
        -- *Type		int, long, char, etc.
        Type = { fg = theme.syn.type },
        -- *Special	any special symbol
        Special = { fg = theme.syn.special1 },
        -- Delimiter	character that needs attention
        Delimiter = { fg = theme.syn.punct },
        -- Debug		debugging statements
        Underlined = { fg = theme.syn.special1, underline = true },
        Bold = { bold = true },
        Italic = { italic = true },
        -- *Ignore		left blank, hidden  |hl-Ignore|
        Ignore = { link = "NonText" },
    }
end

local function part_2(theme)
    local ui = theme.ui
    return {
        -- *Error		any erroneous construct
        Error = { fg = theme.diag.error },
        Todo = { fg = ui.fg_reverse, bg = theme.diag.info, bold = true },
        qfLineNr = { link = "lineNr" },
        qfFileName = { link = "Directory" },
        markdownCode = { fg = theme.syn.string },
        markdownCodeBlock = { fg = theme.syn.string },
        markdownEscape = { fg = "NONE" },
    }
end

---@param colors table colours; only colors.theme is used
---@param config table { transparent }
---@return table<string, table> group name -> highlight spec
function M.setup(colors, config)
    local groups = {}
    for _, part in ipairs({ part_1, part_2 }) do
        for name, spec in pairs(part(colors.theme, config)) do
            groups[name] = spec
        end
    end
    return groups
end

return M
