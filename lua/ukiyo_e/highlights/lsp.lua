-- Lsp highlight groups, transcribed from
-- kanagawa.nvim at bb85e4b (dragon theme, default config).

local M = {}

local function part_1(theme)
    return {
        ["@lsp.type.macro"] = { link = "Macro" },
        ["@lsp.type.method"] = { link = "@function.method" },
        ["@lsp.type.namespace"] = { link = "@module" },
        ["@lsp.type.parameter"] = { link = "@variable.parameter" },
        ["@lsp.type.variable"] = { fg = "none" },
        ["@lsp.type.comment"] = { link = "Comment" },
        ["@lsp.type.const"] = { link = "Constant" },
        ["@lsp.type.comparison"] = { link = "Operator" },
        ["@lsp.type.bitwise"] = { link = "Operator" },
        ["@lsp.type.punctuation"] = { link = "Delimiter" },
        ["@lsp.type.selfParameter"] = { link = "@variable.builtin" },
        ["@lsp.type.builtinConstant"] = { link = "@constant.builtin" },
        ["@lsp.type.magicFunction"] = { link = "@function.builtin" },
        ["@lsp.mod.readonly"] = { link = "Constant" },
        ["@lsp.mod.typeHint"] = { link = "Type" },
        ["@lsp.typemod.operator.controlFlow"] = {
            link = "@keyword.exception",
        },
        ["@lsp.type.lifetime"] = { link = "Operator" },
        ["@lsp.typemod.keyword.documentation"] = { link = "Special" },
        ["@lsp.type.decorator.rust"] = { link = "PreProc" },
        ["@lsp.typemod.variable.global"] = { link = "Constant" },
        ["@lsp.typemod.variable.static"] = { link = "Constant" },
        ["@lsp.typemod.variable.defaultLibrary"] = { link = "Special" },
        ["@lsp.typemod.function.builtin"] = { link = "@function.builtin" },
        ["@lsp.typemod.function.defaultLibrary"] = {
            link = "@function.builtin",
        },
        ["@lsp.typemod.method.defaultLibrary"] = {
            link = "@function.builtin",
        },
        ["@lsp.typemod.variable.injected"] = { link = "@variable" },
        ["@lsp.typemod.function.readonly"] = {
            fg = theme.syn.fun,
            bold = true,
        },
    }
end

---@param colors table colours; only colors.theme is used
---@param config table { transparent }
---@return table<string, table> group name -> highlight spec
function M.setup(colors, config)
    local groups = {}
    for _, part in ipairs({ part_1 }) do
        for name, spec in pairs(part(colors.theme, config)) do
            groups[name] = spec
        end
    end
    return groups
end

return M
