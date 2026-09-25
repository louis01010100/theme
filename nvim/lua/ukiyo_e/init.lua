-- Ukiyo-e colorscheme: setup(), load(), palette().

local M = {}

local DEFAULTS = { transparent = false }
local MODULES = { "editor", "syntax", "treesitter", "lsp", "plugins" }

local config = vim.deepcopy(DEFAULTS)

local function check(opts)
    if opts == nil then
        return {}
    end
    if type(opts) ~= "table" then
        error("ukiyo_e.setup: opts must be a table or nil", 0)
    end
    local transparent = opts.transparent
    if transparent ~= nil and type(transparent) ~= "boolean" then
        error("ukiyo_e.setup: opts.transparent must be a boolean", 0)
    end
    local overrides = opts.overrides
    if overrides ~= nil and type(overrides) ~= "function" then
        error("ukiyo_e.setup: opts.overrides must be a function", 0)
    end
    return opts
end

local function build_colors()
    local palette = M.palette()
    return { palette = palette, theme = require("ukiyo_e.theme")(palette) }
end

local function build_groups(colors)
    local groups = {}
    for _, name in ipairs(MODULES) do
        local module = require("ukiyo_e.highlights." .. name)
        for group, spec in pairs(module.setup(colors, config)) do
            groups[group] = spec
        end
    end
    return groups
end

local function apply_overrides(groups, colors)
    local result = config.overrides and config.overrides(colors)
    if result == nil then
        return groups
    end
    if type(result) ~= "table" then
        error("ukiyo_e: overrides must return a table or nil", 0)
    end
    for group, spec in pairs(result) do
        if groups[group] and next(spec) then
            groups[group].link = nil
        end
        groups[group] = vim.tbl_extend("force", groups[group] or {}, spec)
    end
    return groups
end

-- Groups declared with `default = true` are set last: setting Normal
-- after them would clear their default flag (a Neovim quirk that makes
-- kanagawa's result depend on table iteration order).
local function set_groups(groups)
    local defaults = {}
    for group, spec in pairs(groups) do
        if spec.default then
            defaults[group] = spec
        else
            vim.api.nvim_set_hl(0, group, spec)
        end
    end
    for group, spec in pairs(defaults) do
        vim.api.nvim_set_hl(0, group, spec)
    end
end

local function set_terminal()
    local ansi = require("ukiyo_e.palette").ansi
    for i, colour in ipairs(ansi) do
        vim.g["terminal_color_" .. (i - 1)] = colour
    end
end

---@param opts? { transparent?: boolean, overrides?: function }
function M.setup(opts)
    opts = check(opts)
    config = vim.tbl_extend("force", vim.deepcopy(DEFAULTS), {
        transparent = opts.transparent,
        overrides = opts.overrides,
    })
end

function M.load()
    -- Drop a cached palette so :colorscheme sees a new version.
    package.loaded["ukiyo_e.palette"] = nil
    if vim.g.colors_name then
        vim.cmd("hi clear")
    end
    vim.g.colors_name = "ukiyo_e"
    vim.o.termguicolors = true
    local colors = build_colors()
    set_groups(apply_overrides(build_groups(colors), colors))
    set_terminal()
end

---@return table<string, string> palette name -> "#rrggbb" (a copy)
function M.palette()
    return vim.deepcopy(require("ukiyo_e.palette").palette)
end

return M
