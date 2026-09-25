"""STYLE: line width and function length of hand-written sources."""

import ast
import re
import unittest

import support

MAX_WIDTH = 77
MAX_FUNCTION_LINES = 49
GENERATED = set(support.GENERATED_PATHS)


def hand_written(suffixes):
    """Hand-written repository files with one of the given suffixes."""
    root = support.REPO
    found = []
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        if rel.startswith(".git") or "__pycache__" in rel:
            continue
        if path.is_file() and path.suffix in suffixes:
            found.append(rel)
    return [rel for rel in found if rel not in GENERATED]


def block_lengths(lines, opener, closer):
    """Line counts of blocks from an opener to its same-indent closer."""
    lengths = {}
    for number, line in enumerate(lines):
        match = re.match(opener, line)
        if not match:
            continue
        indent = match.group(1)
        for end in range(number + 1, len(lines)):
            if re.match(closer.format(re.escape(indent)), lines[end]):
                lengths[f"{number + 1}:{line.strip()}"] = end - number + 1
                break
    return lengths


class LineWidthTest(unittest.TestCase):
    def test_lines_fit(self):
        files = hand_written({".py", ".lua", ".sh", ".tmux"})
        self.assertIn("scripts/generate.py", files)
        for rel in files:
            text = (support.REPO / rel).read_text()
            for number, line in enumerate(text.splitlines(), 1):
                self.assertLessEqual(len(line), MAX_WIDTH,
                                     f"{rel}:{number}")


class FunctionLengthTest(unittest.TestCase):
    def test_python_functions(self):
        for rel in hand_written({".py"}):
            tree = ast.parse((support.REPO / rel).read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef,
                                     ast.AsyncFunctionDef)):
                    span = node.end_lineno - node.lineno + 1
                    self.assertLessEqual(span, MAX_FUNCTION_LINES,
                                         f"{rel}:{node.name}")

    def test_lua_functions(self):
        files = hand_written({".lua"})
        self.assertIn("lua/ukiyo_e/init.lua", files)
        opener = r"^(\s*)(?:local\s+)?(?:function\b|.*=\s*function\()"
        for rel in files:
            lines = (support.REPO / rel).read_text().splitlines()
            lengths = block_lengths(lines, opener, r"^{}end\b")
            for name, span in lengths.items():
                self.assertLessEqual(span, MAX_FUNCTION_LINES,
                                     f"{rel}:{name}")

    def test_bash_functions(self):
        files = hand_written({".sh", ".tmux"})
        self.assertIn("gnome-terminal/install.sh", files)
        for rel in files:
            lines = (support.REPO / rel).read_text().splitlines()
            lengths = block_lengths(lines, r"^(\s*)\w+\(\)\s*\{",
                                    r"^{}\}}")
            for name, span in lengths.items():
                self.assertLessEqual(span, MAX_FUNCTION_LINES,
                                     f"{rel}:{name}")


if __name__ == "__main__":
    unittest.main()
