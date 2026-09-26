-- Load the colorscheme headlessly and dump its state as JSON.
-- Environment:
--   UKIYO_E_ROOT         directory prepended to the runtimepath
--   UKIYO_E_OPTS         Lua expression for the setup() options
--   UKIYO_E_PRELUDE      optional Lua chunk run before setup()
--   UKIYO_E_POSTLUDE     optional Lua chunk run after :colorscheme
--   UKIYO_E_DUMP_OUT     output file for the JSON result

local MODULES = { "editor", "syntax", "treesitter", "lsp", "plugins" }

local function eval_chunk(source)
    if source == nil or source == "" then
        return nil
    end
    return assert(loadstring(source))()
end

local function terminal_colors()
    local colors = {}
    for i = 0, 15 do
        colors[i + 1] = vim.g["terminal_color_" .. i] or vim.NIL
    end
    return colors
end

local function load()
    vim.opt.rtp:prepend(os.getenv("UKIYO_E_ROOT"))
    eval_chunk(os.getenv("UKIYO_E_PRELUDE"))
    local opts = eval_chunk("return " .. os.getenv("UKIYO_E_OPTS"))
    require("ukiyo_e").setup(opts)
    vim.cmd.colorscheme("ukiyo_e")
    eval_chunk(os.getenv("UKIYO_E_POSTLUDE"))
    return opts
end

-- The colors table the load builds (init.lua build_colors).
local function build_colors()
    local rendered = require("ukiyo_e.palette")
    local palette = vim.deepcopy(rendered.palette)
    local shades = vim.deepcopy(rendered.shades)
    local theme = require("ukiyo_e.theme")(palette, shades)
    return { palette = palette, shades = shades, theme = theme }
end

-- Group names the highlight modules set for this config (REQ-NVIM-10).
local function theme_set(opts)
    local transparent = type(opts) == "table" and opts.transparent
    local config = { transparent = transparent or false }
    local colors = build_colors()
    local found = {}
    for _, name in ipairs(MODULES) do
        local module = require("ukiyo_e.highlights." .. name)
        for group in pairs(module.setup(colors, config)) do
            found[group] = true
        end
    end
    local names = vim.tbl_keys(found)
    table.sort(names)
    return names
end

local function snapshot(opts)
    local rendered = require("ukiyo_e.palette")
    return {
        groups = vim.api.nvim_get_hl(0, {}),
        theme_set = theme_set(opts),
        theme = require("ukiyo_e.theme")(
            require("ukiyo_e").palette(),
            vim.deepcopy(rendered.shades)
        ),
        shades = rendered.shades,
        terminal = terminal_colors(),
        colors_name = vim.g.colors_name or vim.NIL,
        kanagawa_loaded = package.loaded.kanagawa ~= nil,
        kanagawa_files = #vim.api.nvim_get_runtime_file(
            "lua/kanagawa/init.lua",
            true
        ),
        palette = require("ukiyo_e").palette(),
    }
end

local function main()
    local ok, opts = pcall(load)
    local result = ok and snapshot(opts) or { error = tostring(opts) }
    local out = assert(io.open(os.getenv("UKIYO_E_DUMP_OUT"), "w"))
    out:write(vim.json.encode(result))
    out:close()
end

main()
