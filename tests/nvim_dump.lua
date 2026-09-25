-- Load one colorscheme headlessly and dump its state as JSON.
-- Environment:
--   UKIYO_E_SIDE         "seed" (kanagawa-dragon) or "ukiyo_e"
--   UKIYO_E_ROOT         directory prepended to the runtimepath
--   UKIYO_E_OPTS         Lua expression for the setup() options
--   UKIYO_E_PRELUDE      optional Lua chunk run before setup()
--   UKIYO_E_POSTLUDE     optional Lua chunk run after :colorscheme
--   UKIYO_E_DUMP_OUT     output file for the JSON result

local SCHEMES = {
    seed = { module = "kanagawa", scheme = "kanagawa-dragon" },
    ukiyo_e = { module = "ukiyo_e", scheme = "ukiyo_e" },
}

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

local function load_side(side)
    local entry = assert(SCHEMES[side], "unknown side")
    vim.opt.rtp:prepend(os.getenv("UKIYO_E_ROOT"))
    eval_chunk(os.getenv("UKIYO_E_PRELUDE"))
    local opts = eval_chunk("return " .. os.getenv("UKIYO_E_OPTS"))
    require(entry.module).setup(opts)
    vim.cmd.colorscheme(entry.scheme)
    eval_chunk(os.getenv("UKIYO_E_POSTLUDE"))
end

local function snapshot(side)
    local palette = vim.NIL
    if side == "ukiyo_e" then
        palette = require("ukiyo_e").palette()
    end
    return {
        groups = vim.api.nvim_get_hl(0, {}),
        terminal = terminal_colors(),
        colors_name = vim.g.colors_name or vim.NIL,
        kanagawa_loaded = package.loaded.kanagawa ~= nil,
        kanagawa_files = #vim.api.nvim_get_runtime_file(
            "lua/kanagawa/init.lua",
            true
        ),
        palette = palette,
    }
end

local function main()
    local side = os.getenv("UKIYO_E_SIDE")
    local ok, err = pcall(load_side, side)
    local result = ok and snapshot(side) or { error = tostring(err) }
    local out = assert(io.open(os.getenv("UKIYO_E_DUMP_OUT"), "w"))
    out:write(vim.json.encode(result))
    out:close()
end

main()
