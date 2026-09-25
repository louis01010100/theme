"""V-SAFE: static safety checks over the Runtime Files set (INV-1)."""

import ast
import re
import sys
import unittest

import support

sys.path.insert(0, str(support.REPO / "scripts"))

FORBIDDEN_WORDS = re.compile(r"\b(sudo|curl|wget|git|pip|apt|npm)\b")
HEX_LITERAL = re.compile(r"(?i)#[0-9a-f]{6}")
EXECUTABLES = {"ukiyo_e.tmux", "gnome-terminal/install.sh"}
PROFILE_KEYS = {
    "visible-name", "use-theme-colors", "background-color",
    "foreground-color", "palette", "cursor-colors-set",
    "cursor-background-color", "cursor-foreground-color",
    "highlight-colors-set", "highlight-background-color",
    "highlight-foreground-color", "bold-color-same-as-fg",
}
GSETTINGS_WRITE = re.compile(r"gsettings\s+(reset-recursively|set|reset)")
WRITERS = {"set_profile_key", "set_list_key", "uninstall"}


def runtime_files():
    """The Runtime Files set of INV-1, as repository-relative paths."""
    root = support.REPO
    found = [p for d in ("colors", "lua/ukiyo_e", "scripts")
             for p in (root / d).rglob("*") if p.is_file()]
    found += [root / "ukiyo_e.tmux", root / "gnome-terminal/install.sh"]
    rels = sorted(str(p.relative_to(root)) for p in found)
    return [r for r in rels if r != "lua/ukiyo_e/palette.lua"]


def shell_functions(text):
    """Map each bash function name to its body lines."""
    spans = {}
    name = None
    for line in text.splitlines():
        start = re.match(r"^(\w+)\(\)\s*\{", line)
        if start:
            name = start.group(1)
            spans[name] = []
        elif line.startswith("}"):
            name = None
        elif name:
            spans[name].append(line)
    return spans


class RuntimeFilesTest(unittest.TestCase):
    def test_runtime_set_is_populated(self):
        files = runtime_files()
        for rel in ("colors/ukiyo_e.lua", "lua/ukiyo_e/init.lua",
                    "lua/ukiyo_e/theme.lua", "scripts/generate.py"):
            self.assertIn(rel, files)

    def test_no_forbidden_commands(self):
        for rel in runtime_files():
            text = (support.REPO / rel).read_text()
            self.assertIsNone(FORBIDDEN_WORDS.search(text), rel)

    def test_no_hex_literals(self):
        for rel in runtime_files():
            text = (support.REPO / rel).read_text()
            self.assertIsNone(HEX_LITERAL.search(text), rel)

    def test_generator_imports_stdlib_only(self):
        tree = ast.parse((support.REPO / "scripts/generate.py").read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                self.assertIn(top, sys.stdlib_module_names, name)


class NeovimNamesTest(unittest.TestCase):
    def test_theme_uses_required_names_only(self):
        import generate

        text = (support.REPO / "lua/ukiyo_e/theme.lua").read_text()
        used = set(re.findall(r"\bpalette\.(\w+)", text))
        self.assertTrue(used)
        self.assertLessEqual(used, set(generate.REQUIRED_PALETTE_NAMES))

    def test_required_names_are_46(self):
        import generate

        self.assertEqual(len(set(generate.REQUIRED_PALETTE_NAMES)), 46)

    def test_highlight_modules_use_theme_only(self):
        folder = support.REPO / "lua/ukiyo_e/highlights"
        modules = sorted(p.name for p in folder.glob("*.lua"))
        self.assertEqual(modules, ["editor.lua", "lsp.lua", "plugins.lua",
                                   "syntax.lua", "treesitter.lua"])
        for name in modules:
            text = (folder / name).read_text()
            self.assertIsNone(re.search(r"\bpalette\b", text), name)
            self.assertIsNone(re.search(r"\brequire\b", text), name)

    def test_no_kanagawa_dependency(self):
        for rel in runtime_files():
            text = (support.REPO / rel).read_text()
            self.assertNotIn('require("kanagawa', text, rel)


class LayoutTest(unittest.TestCase):
    def test_single_root_tmux_file(self):
        found = sorted(p.name for p in support.REPO.glob("*.tmux"))
        self.assertEqual(found, ["ukiyo_e.tmux"])

    def test_file_modes(self):
        for path in support.REPO.rglob("*"):
            rel = str(path.relative_to(support.REPO))
            if not path.is_file() or rel.startswith(".git"):
                continue
            executable = bool(path.stat().st_mode & 0o111)
            self.assertEqual(executable, rel in EXECUTABLES, rel)

    def test_no_pycache(self):
        self.assertEqual(list(support.REPO.rglob("__pycache__")), [])


class InstallerWritesTest(unittest.TestCase):
    def text(self):
        return (support.REPO / "gnome-terminal/install.sh").read_text()

    def test_writes_only_in_allowlisted_helpers(self):
        functions = shell_functions(self.text())
        writes = [line for line in self.text().splitlines()
                  if GSETTINGS_WRITE.search(line)]
        self.assertTrue(writes)
        for name, body in functions.items():
            hits = [ln for ln in body if GSETTINGS_WRITE.search(ln)]
            if hits:
                self.assertIn(name, WRITERS, hits)
        inside = sum(1 for body in functions.values() for ln in body
                     if GSETTINGS_WRITE.search(ln))
        self.assertEqual(inside, len(writes))

    def test_uninstall_writes_are_confined(self):
        body = shell_functions(self.text())["uninstall"]
        for line in body:
            match = GSETTINGS_WRITE.search(line)
            if not match:
                continue
            if match.group(1) == "reset-recursively":
                self.assertIn("PROFILE_PATH", line)
            else:
                self.assertRegex(line, r"PROFILES_LIST.*\b(list|default)")

    def test_profile_key_allowlist(self):
        match = re.search(r"PROFILE_KEYS=\(([^)]*)\)", self.text())
        self.assertIsNotNone(match)
        self.assertEqual(set(match.group(1).split()), PROFILE_KEYS)

    def test_fixed_uuid(self):
        self.assertIn("5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37", self.text())


if __name__ == "__main__":
    unittest.main()
