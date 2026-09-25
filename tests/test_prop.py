"""V-PROP: one palette change propagates to Neovim, tmux, and GNOME."""

import json
import unittest

import support
from test_nvim import NeovimRun, nvim_dump

OLD_BLUE = 0x8BA4B0
NEW_BLUE = 0x123456
COLOUR_ATTRIBUTES = ("fg", "bg", "sp")
UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"


def setUpModule():
    support.RealDconfGuard.take()


def tearDownModule():
    support.RealDconfGuard.verify()


def recoloured(groups: dict) -> dict:
    """Baseline groups with every old-blue attribute set to new blue."""
    result = {}
    for name, spec in groups.items():
        if isinstance(spec, dict):
            spec = {k: NEW_BLUE if k in COLOUR_ATTRIBUTES and v == OLD_BLUE
                    else v for k, v in spec.items()}
        result[name] = spec
    return result


def uses_old_blue(spec) -> bool:
    return isinstance(spec, dict) and any(
        spec.get(k) == OLD_BLUE for k in COLOUR_ATTRIBUTES)


class PropagationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = support.copy_repo()
        support.set_ansi_entry(cls.root, 1, "#ff0000")
        support.replace_line(cls.root / "palette.toml", "dragonBlue2 ",
                             'dragonBlue2 = "#123456"')
        result = support.generate(cls.root)
        if result.code != 0:
            raise AssertionError(result.stderr)

    @classmethod
    def tearDownClass(cls):
        support.remove_tree(cls.root)

    def test_neovim(self):
        opts = "{ transparent = false }"
        base = nvim_dump(NeovimRun("ukiyo_e", str(support.REPO), opts))
        new = nvim_dump(NeovimRun("ukiyo_e", str(self.root), opts))
        self.assertEqual(new["terminal"][1].lower(), "#ff0000")
        self.assertEqual(new["terminal"][4].lower(), "#123456")
        changed = [n for n, s in base["groups"].items() if uses_old_blue(s)]
        self.assertGreater(len(changed), 10)
        self.assertEqual(new["groups"], recoloured(base["groups"]))

    def test_tmux(self):
        server = support.TmuxServer.start(self)
        self.assertEqual(server.run_theme(self.root).code, 0)
        self.assertEqual(server.value("clock-mode-colour"), "#123456")
        self.assertEqual(server.value("pane-active-border-style"),
                         "fg=#123456")
        for option in ("status-left", "status-right"):
            self.assertIn("bg=#123456", server.value(option))

    def test_gnome(self):
        result = support.run_gnome_harness("install_only", self.root)
        report = json.loads(result.stdout)
        self.assertEqual(report["guard"], "ok")
        step = report["steps"][0]
        self.assertEqual(step["code"], 0, step["stderr"])
        section = support.parse_dump(step["dump"])[
            f"legacy/profiles:/:{UUID}"]
        palette = [c.strip(" '") for c in
                   section["palette"].strip("[]").split(",")]
        self.assertEqual(palette[1], "#ff0000")
        self.assertEqual(palette[4], "#123456")
        self.assertEqual(palette, support.resolved_ansi(self.root))


if __name__ == "__main__":
    unittest.main()
