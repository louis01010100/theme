"""V-GT: install.sh inside an isolated D-Bus session and dconf db."""

import json
import unittest

import support

UUID = "5a1c0e9b-7d3f-4b6a-8e2d-4f0a9c6b1e37"
PROFILE_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
PROFILE_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
ROOT_SECTION = "legacy/profiles:"
OWN_SECTION = f"legacy/profiles:/:{UUID}"


def setUpModule():
    support.RealDconfGuard.take()


def tearDownModule():
    support.RealDconfGuard.verify()


def expected_profile(root=support.REPO):
    """The 12 profile keys of REQ-GT-4, as dconf dump values."""
    doc = support.load_palette_toml(root)
    term = {k: support.resolve_ref(doc, v)
            for k, v in doc["terminal"].items() if k != "ansi"}
    ansi = ", ".join(f"'{c}'" for c in support.resolved_ansi(root))
    return {
        "visible-name": "'Ukiyo-e'",
        "use-theme-colors": "false",
        "background-color": f"'{term['background']}'",
        "foreground-color": f"'{term['foreground']}'",
        "palette": f"[{ansi}]",
        "cursor-colors-set": "true",
        "cursor-background-color": f"'{term['cursor_bg']}'",
        "cursor-foreground-color": f"'{term['cursor_fg']}'",
        "highlight-colors-set": "true",
        "highlight-background-color": f"'{term['selection_bg']}'",
        "highlight-foreground-color": f"'{term['selection_fg']}'",
        "bold-color-same-as-fg": "true",
    }


def harness(scenario, root=support.REPO):
    """Run a scenario; return {step name: step} after the guard passed."""
    result = support.run_gnome_harness(scenario, root)
    report = json.loads(result.stdout)
    if report["guard"] != "ok":
        raise AssertionError(f"isolation guard: {report['guard']}")
    return {step["name"]: step for step in report["steps"]}


def lowered(section):
    return {k: v.lower() for k, v in section.items()}


class IsolationGuardTest(unittest.TestCase):
    def test_guard_rejects_outer_bus(self):
        env_bus = support.os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
        argv = [support.sys.executable, str(support.GNOME_HARNESS),
                "install_only", str(support.REPO)]
        env = dict(support.os.environ, UKIYO_E_OUTER_BUS=env_bus)
        result = support.run(argv, env=env)
        self.assertEqual(result.code, 97)
        self.assertEqual(json.loads(result.stdout)["steps"], [])


class LifecycleTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steps = harness("lifecycle")

    def dump(self, name):
        return support.parse_dump(self.steps[name]["dump"])

    def test_install(self):
        step = self.steps["install"]
        self.assertEqual(step["code"], 0, step["stderr"])
        dump = self.dump("install")
        self.assertEqual(lowered(dump[OWN_SECTION]),
                         lowered(expected_profile()))
        root = dump[ROOT_SECTION]
        self.assertEqual(root["list"],
                         f"['{PROFILE_A}', '{PROFILE_B}', '{UUID}']")
        self.assertEqual(root["default"], f"'{PROFILE_A}'")
        seeded = self.dump("seeded")
        for uuid in (PROFILE_A, PROFILE_B):
            section = f"legacy/profiles:/:{uuid}"
            self.assertEqual(dump[section], seeded[section])

    def test_reinstall_changes_nothing(self):
        self.assertEqual(self.steps["reinstall"]["code"], 0)
        self.assertEqual(self.steps["reinstall"]["dump"],
                         self.steps["install"]["dump"])

    def test_set_default(self):
        step = self.steps["set_default"]
        self.assertEqual(step["code"], 0, step["stderr"])
        dump = self.dump("set_default")
        before = self.dump("reinstall")
        self.assertEqual(dump[ROOT_SECTION]["default"], f"'{UUID}'")
        before[ROOT_SECTION]["default"] = f"'{UUID}'"
        self.assertEqual(dump, before)

    def test_uninstall_restores_seeded_state(self):
        step = self.steps["uninstall"]
        self.assertEqual(step["code"], 0, step["stderr"])
        self.assertEqual(step["dump"], self.steps["seeded"]["dump"])
        self.assertNotIn(OWN_SECTION, self.dump("uninstall"))

    def test_uninstall_again_is_noop(self):
        step = self.steps["uninstall_again"]
        self.assertEqual(step["code"], 0, step["stderr"])
        self.assertEqual(step["dump"], self.steps["seeded"]["dump"])


class SingleProfileTest(unittest.TestCase):
    def test_uninstall_resets_list_and_default(self):
        steps = harness("single_profile")
        installed = support.parse_dump(steps["set_default"]["dump"])
        self.assertEqual(installed[ROOT_SECTION],
                         {"default": f"'{UUID}'", "list": f"['{UUID}']"})
        step = steps["uninstall"]
        self.assertEqual(step["code"], 0, step["stderr"])
        self.assertEqual(step["dump"], "")


class FailureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.steps = harness("failures")

    def assert_unchanged(self, name, code, message):
        step = self.steps[name]
        self.assertEqual(step["code"], code, step["stderr"])
        self.assertIn(message, step["stderr"])
        self.assertEqual(step["dump"], self.steps["seeded"]["dump"])

    def test_missing_gsettings(self):
        self.assert_unchanged("no_gsettings", 3, "install.sh: gsettings")

    def test_missing_schema(self):
        self.assert_unchanged("no_schema", 3,
                              "org.gnome.Terminal.ProfilesList")

    def test_both_flags(self):
        self.assert_unchanged("both_flags", 2, "usage")

    def test_unknown_flag(self):
        self.assert_unchanged("unknown_flag", 2, "usage")

    def test_help(self):
        self.assertEqual(self.steps["help"]["code"], 0)
        self.assertEqual(self.steps["help"]["dump"],
                         self.steps["seeded"]["dump"])


if __name__ == "__main__":
    unittest.main()
