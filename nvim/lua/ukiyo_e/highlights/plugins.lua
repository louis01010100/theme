-- Plugins highlight groups, transcribed from
-- kanagawa.nvim at bb85e4b (dragon theme, default config).

local M = {}

local function part_1(theme)
    local ui = theme.ui
    return {
        -- Gitsigns
        GitSignsAdd = { fg = theme.vcs.added, bg = ui.bg_gutter },
        GitSignsChange = { fg = theme.vcs.changed, bg = ui.bg_gutter },
        GitSignsDelete = { fg = theme.vcs.removed, bg = ui.bg_gutter },
        -- Neogit
        NeogitDiffContextHighlight = { bg = theme.diff.change },
        NeogitHunkHeader = { fg = theme.syn.fun },
        NeogitHunkHeaderHighlight = {
            fg = theme.syn.constant,
            bg = theme.diff.change,
        },
        NeogitDiffAddHighlight = { bg = theme.diff.add },
        NeogitDiffDeleteHighlight = { bg = theme.diff.delete },
        -- TreeSitter Extensions
        TreesitterContext = { link = "Folded" },
        TreesitterContextLineNumber = {
            fg = ui.special,
            bg = ui.bg_gutter,
        },
        -- Telescope
        TelescopeBorder = { fg = ui.float.fg_border, bg = ui.bg },
        TelescopeTitle = { fg = ui.special },
        TelescopeSelection = { link = "CursorLine" },
        TelescopeSelectionCaret = { link = "CursorLineNr" },
        TelescopeResultsClass = { link = "Structure" },
        TelescopeResultsStruct = { link = "Structure" },
        TelescopeResultsField = { link = "@field" },
        TelescopeResultsMethod = { link = "Function" },
        TelescopeResultsVariable = { link = "@variable" },
        -- NvimTree
        NvimTreeNormal = { link = "Normal" },
        NvimTreeNormalNC = { link = "NvimTreeNormal" },
        NvimTreeRootFolder = { fg = theme.syn.identifier, bold = true },
        NvimTreeGitDirty = { fg = theme.vcs.changed },
    }
end

local function part_2(theme)
    local ui = theme.ui
    local modified = "NeoTreeGitModified"
    return {
        NvimTreeGitNew = { fg = theme.vcs.added },
        NvimTreeGitDeleted = { fg = theme.vcs.removed },
        NvimTreeGitStaged = { fg = theme.vcs.added },
        NvimTreeSpecialFile = { fg = theme.syn.special1 },
        NvimTreeImageFile = { fg = theme.syn.special2 },
        NvimTreeSymlink = { link = "Type" },
        NvimTreeFolderName = { link = "Directory" },
        NvimTreeExecFile = { fg = theme.syn.string, bold = true },
        NvimTreeOpenedFile = { fg = theme.syn.special1, italic = true },
        NvimTreeWinSeparator = { link = "WinSeparator" },
        NvimTreeWindowPicker = {
            bg = ui.bg_m1,
            fg = theme.syn.special1,
            bold = true,
        },
        -- NeoTree
        NeoTreeTabInactive = { link = "TabLine" },
        NeoTreeTabActive = { link = "TabLineSel" },
        NeoTreeTabSeparatorInactive = { link = "NeoTreeTabInactive" },
        NeoTreeTabSeparatorActive = { link = "NeoTreeTabActive" },
        NeoTreeRootName = { fg = theme.syn.identifier, bold = true },
        NeoTreeModified = { link = "String" },
        NeoTreeGitModified = { fg = theme.vcs.changed },
        NeoTreeGitAdded = { fg = theme.vcs.added },
        NeoTreeGitDeleted = { fg = theme.vcs.removed },
        NeoTreeGitStaged = { fg = theme.vcs.added },
        NeoTreeGitConflict = { fg = theme.diag.error },
        NeoTreeGitUntracked = { link = modified, default = true },
        NeoTreeGitUnstaged = { link = modified, default = true },
        NeoTreeIndentMarker = { link = "NonText" },
        -- Dashboard
        DashboardShortCut = { fg = theme.syn.special1 },
        DashboardHeader = { fg = theme.vcs.removed },
        DashboardCenter = { fg = theme.syn.identifier },
    }
end

local function part_3(theme)
    return {
        DashboardFooter = { fg = theme.syn.comment },
        DashboardDesc = { fg = theme.syn.identifier },
        DashboardKey = { fg = theme.syn.special1 },
        DashboardIcon = { fg = theme.ui.special },
        -- Notify
        NotifyBackground = { bg = theme.ui.bg },
        NotifyERRORBorder = { link = "DiagnosticError" },
        NotifyWARNBorder = { link = "DiagnosticWarn" },
        NotifyINFOBorder = { link = "DiagnosticInfo" },
        NotifyHINTBorder = { link = "DiagnosticHint" },
        NotifyDEBUGBorder = { link = "Debug" },
        NotifyTRACEBorder = { link = "Comment" },
        NotifyERRORIcon = { link = "DiagnosticError" },
        NotifyWARNIcon = { link = "DiagnosticWarn" },
        NotifyINFOIcon = { link = "DiagnosticInfo" },
        NotifyHINTIcon = { link = "DiagnosticHint" },
        NotifyDEBUGIcon = { link = "Debug" },
        NotifyTRACEIcon = { link = "Comment" },
        NotifyERRORTitle = { link = "DiagnosticError" },
        NotifyWARNTitle = { link = "DiagnosticWarn" },
        NotifyINFOTitle = { link = "DiagnosticInfo" },
        NotifyHINTTitle = { link = "DiagnosticHint" },
        NotifyDEBUGTitle = { link = "Debug" },
        NotifyTRACETitle = { link = "Comment" },
        -- Dap-UI
        DapUIScope = { link = "Special" },
        DapUIType = { link = "Type" },
        DapUIModifiedValue = { fg = theme.syn.special1, bold = true },
        DapUIDecoration = { fg = theme.ui.float.fg_border },
        DapUIThread = { fg = theme.syn.identifier },
        DapUIStoppedThread = { fg = theme.syn.special1 },
        DapUISource = { fg = theme.syn.special2 },
        DapUILineNumber = { fg = theme.syn.special1 },
        DapUIFloatBorder = { fg = theme.ui.float.fg_border },
    }
end

local function part_4(theme)
    local ui = theme.ui
    return {
        DapUIWatchesEmpty = { fg = theme.diag.error },
        DapUIWatchesValue = { fg = theme.syn.identifier },
        DapUIWatchesError = { fg = theme.diag.error },
        DapUIBreakpointsPath = { link = "Directory" },
        DapUIBreakpointsInfo = { fg = theme.diag.info },
        DapUIBreakpointsCurrentLine = {
            fg = theme.syn.identifier,
            bold = true,
        },
        DapUIBreakpointsDisabledLine = { link = "Comment" },
        DapUIStepOver = { fg = theme.syn.special1 },
        DapUIStepInto = { fg = theme.syn.special1 },
        DapUIStepBack = { fg = theme.syn.special1 },
        DapUIStepOut = { fg = theme.syn.special1 },
        DapUIStop = { fg = theme.diag.error },
        DapUIPlayPause = { fg = theme.syn.string },
        DapUIRestart = { fg = theme.syn.string },
        DapUIUnavailable = { fg = theme.syn.comment },
        -- Floaterm
        FloatermBorder = { fg = ui.float.fg_border, bg = ui.bg },
        healthError = { fg = theme.diag.error },
        healthSuccess = { fg = theme.diag.ok },
        healthWarning = { fg = theme.diag.warning },
        -- Cmp
        CmpDocumentation = { link = "NormalFloat" },
        CmpDocumentationBorder = { link = "FloatBorder" },
        CmpCompletion = { link = "Pmenu" },
        CmpCompletionSel = { link = "PmenuSel" },
        CmpCompletionBorder = { fg = ui.bg_search, bg = ui.pmenu.bg },
        CmpCompletionThumb = { link = "PmenuThumb" },
        CmpCompletionSbar = { link = "PmenuSbar" },
        CmpItemAbbr = { fg = ui.pmenu.fg },
        CmpItemAbbrDeprecated = {
            fg = theme.syn.comment,
            strikethrough = true,
        },
        CmpItemAbbrMatch = { fg = theme.syn.fun },
        CmpItemAbbrMatchFuzzy = { link = "CmpItemAbbrMatch" },
        CmpItemKindDefault = { fg = ui.fg_dim },
        CmpItemMenu = { fg = ui.fg_dim },
    }
end

local function part_5(theme)
    local ui = theme.ui
    return {
        CmpGhostText = { fg = theme.syn.comment },
        CmpItemKindText = { fg = ui.fg },
        CmpItemKindMethod = { link = "@function.method" },
        CmpItemKindFunction = { link = "Function" },
        CmpItemKindConstructor = { link = "@constructor" },
        CmpItemKindField = { link = "@variable.member" },
        CmpItemKindVariable = { fg = ui.fg_dim },
        CmpItemKindClass = { link = "Type" },
        CmpItemKindInterface = { link = "Type" },
        CmpItemKindModule = { link = "@module" },
        CmpItemKindProperty = { link = "@property" },
        CmpItemKindUnit = { link = "Number" },
        CmpItemKindValue = { link = "String" },
        CmpItemKindEnum = { link = "Type" },
        CmpItemKindKeyword = { link = "Keyword" },
        CmpItemKindSnippet = { link = "Special" },
        CmpItemKindColor = { link = "Special" },
        CmpItemKindFile = { link = "Directory" },
        CmpItemKindReference = { link = "Special" },
        CmpItemKindFolder = { link = "Directory" },
        CmpItemKindEnumMember = { link = "Constant" },
        CmpItemKindConstant = { link = "Constant" },
        CmpItemKindStruct = { link = "Type" },
        CmpItemKindEvent = { link = "Type" },
        CmpItemKindOperator = { link = "Operator" },
        CmpItemKindTypeParameter = { link = "Type" },
        CmpItemKindCopilot = { link = "String" },
        -- blink.cmp
        BlinkCmpMenu = { link = "Pmenu" },
        BlinkCmpMenuSelection = { link = "PmenuSel" },
        BlinkCmpMenuBorder = { fg = ui.bg_search, bg = ui.pmenu.bg },
        BlinkCmpScrollBarThumb = { link = "PmenuThumb" },
        BlinkCmpScrollBarGutter = { link = "PmenuSbar" },
        BlinkCmpLabel = { fg = ui.pmenu.fg },
    }
end

local function part_6(theme)
    return {
        BlinkCmpLabelMatch = { fg = theme.syn.fun },
        BlinkCmpLabelDetails = { fg = theme.syn.comment },
        BlinkCmpLabelDeprecated = {
            fg = theme.syn.comment,
            strikethrough = true,
        },
        BlinkCmpGhostText = { fg = theme.syn.comment },
        BlinkCmpDoc = { link = "NormalFloat" },
        BlinkCmpDocBorder = { link = "FloatBorder" },
        BlinkCmpDocCursorLine = { link = "Visual" },
        BlinkCmpSignatureHelp = { link = "NormalFloat" },
        BlinkCmpSignatureHelpBorder = { link = "FloatBorder" },
        BlinkCmpSignatureHelpActiveParameter = {
            link = "LspSignatureActiveParameter",
        },
        BlinkCmpKind = { fg = theme.ui.fg_dim },
        BlinkCmpKindText = { fg = theme.ui.fg },
        BlinkCmpKindMethod = { link = "@function.method" },
        BlinkCmpKindFunction = { link = "Function" },
        BlinkCmpKindConstructor = { link = "@constructor" },
        BlinkCmpKindField = { link = "@variable.member" },
        BlinkCmpKindVariable = { fg = theme.ui.fg_dim },
        BlinkCmpKindClass = { link = "Type" },
        BlinkCmpKindInterface = { link = "Type" },
        BlinkCmpKindModule = { link = "@module" },
        BlinkCmpKindProperty = { link = "@property" },
        BlinkCmpKindUnit = { link = "Number" },
        BlinkCmpKindValue = { link = "String" },
        BlinkCmpKindEnum = { link = "Type" },
        BlinkCmpKindKeyword = { link = "Keyword" },
        BlinkCmpKindSnippet = { link = "Special" },
        BlinkCmpKindColor = { link = "Special" },
        BlinkCmpKindFile = { link = "Directory" },
        BlinkCmpKindReference = { link = "Special" },
    }
end

local function part_7(theme)
    local ui = theme.ui
    return {
        BlinkCmpKindFolder = { link = "Directory" },
        BlinkCmpKindEnumMember = { link = "Constant" },
        BlinkCmpKindConstant = { link = "Constant" },
        BlinkCmpKindStruct = { link = "Type" },
        BlinkCmpKindEvent = { link = "Type" },
        BlinkCmpKindOperator = { link = "Operator" },
        BlinkCmpKindTypeParameter = { link = "Type" },
        BlinkCmpKindCopilot = { link = "String" },
        -- IndentBlankline
        IndentBlanklineChar = { fg = ui.whitespace },
        IndentBlanklineSpaceChar = { fg = ui.whitespace },
        IndentBlanklineSpaceCharBlankline = { fg = ui.whitespace },
        IndentBlanklineContextChar = { fg = ui.special },
        IndentBlanklineContextStart = { sp = ui.special, underline = true },
        IblIndent = { fg = ui.whitespace },
        IblWhitespace = { fg = ui.whitespace },
        IblScope = { fg = ui.special },
        -- Lazy
        LazyProgressTodo = { fg = ui.nontext },
        -- Trouble
        TroubleIndent = { fg = ui.whitespace },
        TroublePos = { fg = ui.special },
        -- Nvim-Navic
        NavicIconsFile = { link = "Directory" },
        NavicIconsModule = { link = "@module" },
        NavicIconsNamespace = { link = "@module" },
        NavicIconsPackage = { link = "@module" },
        NavicIconsClass = { link = "Type" },
        NavicIconsMethod = { link = "@function.method" },
        NavicIconsProperty = { link = "@property" },
        NavicIconsField = { link = "@variable.member" },
        NavicIconsConstructor = { link = "@constructor" },
        NavicIconsEnum = { link = "Type" },
        NavicIconsInterface = { link = "Type" },
    }
end

local function part_8(theme)
    return {
        NavicIconsFunction = { link = "Function" },
        NavicIconsVariable = { link = "@variable" },
        NavicIconsConstant = { link = "Constant" },
        NavicIconsString = { link = "String" },
        NavicIconsNumber = { link = "Number" },
        NavicIconsBoolean = { link = "Boolean" },
        NavicIconsArray = { link = "Type" },
        NavicIconsObject = { link = "Type" },
        NavicIconsKey = { link = "Identifier" },
        NavicIconsNull = { link = "Type" },
        NavicIconsEnumMember = { link = "Constant" },
        NavicIconsStruct = { link = "Structure" },
        NavicIconsEvent = { link = "Structure" },
        NavicIconsOperator = { link = "Operator" },
        NavicIconsTypeParameter = { link = "Type" },
        NavicText = { fg = theme.ui.fg },
        NavicSeparator = { fg = theme.ui.fg },
        -- Aerial icons
        AerialFileIcon = { link = "Directory" },
        AerialModuleIcon = { link = "@module" },
        AerialNamespaceIcon = { link = "@module" },
        AerialPackageIcon = { link = "@module" },
        AerialClassIcon = { link = "Type" },
        AerialMethodIcon = { link = "@function.method" },
        AerialPropertyIcon = { link = "@property" },
        AerialFieldIcon = { link = "@variable.member" },
        AerialConstructorIcon = { link = "@constructor" },
        AerialEnumIcon = { link = "Type" },
        AerialInterfaceIcon = { link = "Type" },
        AerialFunctionIcon = { link = "Function" },
        AerialVariableIcon = { link = "@variable" },
        AerialConstantIcon = { link = "Constant" },
        AerialStringIcon = { link = "String" },
        AerialNumberIcon = { link = "Number" },
    }
end

local function part_9(theme)
    return {
        AerialBooleanIcon = { link = "Boolean" },
        AerialArrayIcon = { link = "Type" },
        AerialObjectIcon = { link = "Type" },
        AerialKeyIcon = { link = "Identifier" },
        AerialNullIcon = { link = "Type" },
        AerialEnumMemberIcon = { link = "Constant" },
        AerialStructIcon = { link = "Structure" },
        AerialEventIcon = { link = "Structure" },
        AerialOperatorIcon = { link = "Operator" },
        AerialTypeParameterIcon = { link = "Type" },
        -- Mini
        MiniAnimateCursor = { reverse = true, nocombine = true },
        MiniAnimateNormalFloat = { link = "NormalFloat" },
        MiniClueBorder = { link = "FloatBorder" },
        MiniClueDescGroup = { link = "DiagnosticFloatingWarn" },
        MiniClueDescSingle = { link = "NormalFloat" },
        MiniClueNextKey = { link = "DiagnosticFloatingHint" },
        MiniClueNextKeyWithPostkeys = { link = "DiagnosticFloatingError" },
        MiniClueSeparator = { link = "DiagnosticFloatingInfo" },
        MiniClueTitle = { link = "FloatTitle" },
        MiniCompletionActiveParameter = { underline = true },
        MiniCursorword = { underline = true },
        MiniCursorwordCurrent = { underline = true },
        MiniDepsChangeAdded = { link = "diffAdded" },
        MiniDepsChangeRemoved = { link = "diffRemoved" },
        MiniDepsHint = { fg = theme.diag.hint },
        MiniDepsInfo = { fg = theme.diag.info },
        MiniDepsMsgBreaking = { fg = theme.diag.warning },
        MiniDepsPlaceholder = { link = "Comment" },
        MiniDepsTitle = { link = "Title" },
        MiniDepsTitleError = { link = "DiffDelete" },
        MiniDepsTitleSame = { link = "DiffText" },
        MiniDepsTitleUpdate = { link = "DiffAdd" },
        MiniDiffSignAdd = { fg = theme.vcs.added, bg = theme.ui.bg_gutter },
    }
end

local function part_10(theme)
    local ui = theme.ui
    return {
        MiniDiffSignChange = { fg = theme.vcs.changed, bg = ui.bg_gutter },
        MiniDiffSignDelete = { fg = theme.vcs.removed, bg = ui.bg_gutter },
        MiniDiffOverAdd = { link = "DiffAdd" },
        MiniDiffOverChange = { link = "DiffText" },
        MiniDiffOverContext = { link = "DiffChange" },
        MiniDiffOverDelete = { link = "DiffDelete" },
        MiniFilesBorder = { link = "FloatBorder" },
        MiniFilesBorderModified = { link = "DiagnosticFloatingWarn" },
        MiniFilesCursorLine = { link = "CursorLine" },
        MiniFilesDirectory = { link = "Directory" },
        MiniFilesFile = { fg = ui.fg },
        MiniFilesNormal = { link = "NormalFloat" },
        MiniFilesTitle = {
            fg = ui.special,
            bg = ui.float.bg_border,
            bold = true,
        },
        MiniFilesTitleFocused = {
            fg = ui.fg,
            bg = ui.float.bg_border,
            bold = true,
        },
        MiniHipatternsFixme = {
            fg = ui.bg,
            bg = theme.diag.error,
            bold = true,
        },
        MiniHipatternsHack = {
            fg = ui.bg,
            bg = theme.diag.warning,
            bold = true,
        },
    }
end

local function part_11(theme)
    return {
        MiniHipatternsNote = {
            fg = theme.ui.bg,
            bg = theme.diag.info,
            bold = true,
        },
        MiniHipatternsTodo = {
            fg = theme.ui.bg,
            bg = theme.diag.hint,
            bold = true,
        },
        MiniIconsAzure = { fg = theme.syn.special1 },
        MiniIconsBlue = { fg = theme.syn.fun },
        MiniIconsCyan = { fg = theme.syn.type },
        MiniIconsGreen = { fg = theme.syn.string },
        MiniIconsGrey = { fg = theme.ui.fg },
        MiniIconsOrange = { fg = theme.syn.constant },
        MiniIconsPurple = { fg = theme.syn.keyword },
        MiniIconsRed = { fg = theme.syn.special3 },
        MiniIconsYellow = { fg = theme.syn.identifier },
        MiniIndentscopeSymbol = { fg = theme.syn.special1 },
        MiniIndentscopePrefix = { nocombine = true },
        MiniJump = { link = "SpellRare" },
        MiniJump2dDim = { link = "Comment" },
        MiniJump2dSpot = {
            fg = theme.syn.constant,
            bold = true,
            nocombine = true,
        },
        MiniJump2dSpotAhead = {
            fg = theme.diag.hint,
            bg = theme.ui.bg_dim,
            nocombine = true,
        },
    }
end

local function part_12(theme)
    local ui = theme.ui
    return {
        MiniJump2dSpotUnique = {
            fg = theme.syn.special1,
            bold = true,
            nocombine = true,
        },
        MiniMapNormal = { link = "NormalFloat" },
        MiniMapSymbolCount = { link = "Special" },
        MiniMapSymbolLine = { link = "Title" },
        MiniMapSymbolView = { link = "Delimiter" },
        MiniNotifyBorder = { link = "FloatBorder" },
        MiniNotifyNormal = { link = "NormalFloat" },
        MiniNotifyTitle = { link = "FloatTitle" },
        MiniOperatorsExchangeFrom = { link = "IncSearch" },
        MiniPickBorder = { link = "FloatBorder" },
        MiniPickBorderBusy = { link = "DiagnosticFloatingWarn" },
        MiniPickBorderText = { link = "FloatTitle" },
        MiniPickIconDirectory = { link = "Directory" },
        MiniPickIconFile = { link = "MiniPickNormal" },
        MiniPickHeader = { link = "DiagnosticFloatingHint" },
        MiniPickMatchCurrent = { link = "CursorLine" },
        MiniPickMatchMarked = { link = "Visual" },
        MiniPickMatchRanges = { link = "DiagnosticFloatingHint" },
        MiniPickNormal = { link = "NormalFloat" },
        MiniPickPreviewLine = { link = "CursorLine" },
        MiniPickPreviewRegion = { link = "IncSearch" },
        MiniPickPrompt = { fg = theme.syn.fun, bg = ui.float.bg_border },
        MiniStarterCurrent = { nocombine = true },
        MiniStarterFooter = { fg = theme.syn.deprecated },
        MiniStarterHeader = { link = "Title" },
        MiniStarterInactive = { link = "Comment" },
        MiniStarterItem = { link = "Normal" },
        MiniStarterItemBullet = { link = "Delimiter" },
        MiniStarterItemPrefix = { fg = theme.diag.warning },
        MiniStarterSection = { fg = theme.diag.ok },
    }
end

local function part_13(theme)
    local ui = theme.ui
    return {
        MiniStarterQuery = { fg = theme.diag.info },
        MiniStatuslineDevinfo = { fg = ui.fg_dim, bg = ui.bg_p1 },
        MiniStatuslineFileinfo = { fg = ui.fg_dim, bg = ui.bg_p1 },
        MiniStatuslineFilename = { fg = ui.fg_dim, bg = ui.bg_dim },
        MiniStatuslineInactive = { link = "StatusLineNC" },
        MiniStatuslineModeCommand = {
            fg = ui.bg,
            bg = theme.syn.operator,
            bold = true,
        },
        MiniStatuslineModeInsert = {
            fg = ui.bg,
            bg = theme.diag.ok,
            bold = true,
        },
        MiniStatuslineModeNormal = {
            fg = ui.bg_m3,
            bg = theme.syn.fun,
            bold = true,
        },
        MiniStatuslineModeOther = {
            fg = ui.bg,
            bg = theme.syn.type,
            bold = true,
        },
        MiniStatuslineModeReplace = {
            fg = ui.bg,
            bg = theme.syn.constant,
            bold = true,
        },
    }
end

local function part_14(theme)
    return {
        MiniStatuslineModeVisual = {
            fg = theme.ui.bg,
            bg = theme.syn.keyword,
            bold = true,
        },
        MiniSurround = { link = "IncSearch" },
        MiniTablineCurrent = {
            fg = theme.ui.fg_dim,
            bg = theme.ui.bg_p1,
            bold = true,
        },
        MiniTablineFill = { link = "TabLineFill" },
        MiniTablineHidden = { fg = theme.ui.special, bg = theme.ui.bg_m3 },
        MiniTablineModifiedCurrent = {
            fg = theme.ui.bg_p1,
            bg = theme.ui.fg_dim,
            bold = true,
        },
        MiniTablineModifiedHidden = {
            fg = theme.ui.bg_m3,
            bg = theme.ui.special,
        },
        MiniTablineModifiedVisible = {
            fg = theme.ui.bg_m3,
            bg = theme.ui.special,
            bold = true,
        },
        MiniTablineTabpagesection = {
            fg = theme.ui.fg,
            bg = theme.ui.bg_search,
            bold = true,
        },
    }
end

local function part_15(theme)
    return {
        MiniTablineVisible = {
            fg = theme.ui.special,
            bg = theme.ui.bg_m3,
            bold = true,
        },
        MiniTestEmphasis = { bold = true },
        MiniTestFail = { fg = theme.diag.error, bold = true },
        MiniTestPass = { fg = theme.diag.ok, bold = true },
        MiniTrailspace = { bg = theme.vcs.removed },
        NeotestAdapterName = { fg = theme.syn.special3 },
        NeotestDir = { fg = theme.syn.fun },
        NeotestExpandMarker = { fg = theme.syn.punct, bold = true },
        NeotestFailed = { fg = theme.diag.error },
        NeotestFile = { fg = theme.syn.fun },
        NeotestFocused = { bold = true, underline = true },
        NeotestIndent = { fg = theme.ui.special, bold = true },
        NeotestMarked = { fg = theme.diag.warning, italic = true },
        NeotestNamespace = { fg = theme.syn.fun },
        NeotestPassed = { fg = theme.diag.ok },
        NeotestRunning = { fg = theme.vcs.changed },
        NeotestWinSelect = { fg = theme.diag.hint },
        NeotestSkipped = { fg = theme.syn.special1 },
        NeotestTarget = { fg = theme.syn.special3 },
        NeotestTest = { fg = theme.ui.float.fg },
        NeotestUnknown = { fg = theme.syn.deprecated },
        NeotestWatching = { fg = theme.vcs.changed },
    }
end

---@param colors table colours; only colors.theme is used
---@param config table { transparent }
---@return table<string, table> group name -> highlight spec
function M.setup(colors, config)
    local groups = {}
    for _, part in ipairs({
        part_1,
        part_2,
        part_3,
        part_4,
        part_5,
        part_6,
        part_7,
        part_8,
        part_9,
        part_10,
        part_11,
        part_12,
        part_13,
        part_14,
        part_15,
    }) do
        for name, spec in pairs(part(colors.theme, config)) do
            groups[name] = spec
        end
    end
    return groups
end

return M
