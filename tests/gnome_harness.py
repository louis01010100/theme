"""Run install.sh scenarios inside an isolated D-Bus session.

usage: python3 gnome_harness.py <scenario> <repo>

Must be started through dbus-run-session with DBUS_SESSION_BUS_ADDRESS
unset beforehand, XDG_CONFIG_HOME and XDG_RUNTIME_DIR pointing at
scratch directories, and UKIYO_E_OUTER_BUS holding the outer bus
address. Before any write, the isolation guard proves that gsettings
talks to a fresh scratch database; otherwise it aborts (exit 97).
Prints one JSON object with the guard result and every step.
"""

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass

SCHEMA_DEFAULT_LIST = "['b1dcc9dd-5262-4d8d-a863-c897e6d979b9']"
PROFILES_LIST = "org.gnome.Terminal.ProfilesList"
PROFILE_SCHEMA = "org.gnome.Terminal.Legacy.Profile"
PROFILE_ROOT = "/org/gnome/terminal/legacy/profiles:/"
PROFILE_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
PROFILE_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
GUARD_FAILED = 97


@dataclass(frozen=True)
class Step:
    """One scenario step: install.sh exit code, stderr, and dump."""

    name: str
    code: int
    stderr: str
    dump: str


class IsolationError(Exception):
    """The session is not provably isolated from the real database."""


def command(argv, env=None):
    proc = subprocess.run(argv, capture_output=True, text=True,
                          env=env, check=False, stdin=subprocess.DEVNULL)
    return proc


def dump():
    return command(["dconf", "dump", "/org/gnome/terminal/"]).stdout


def gsettings(*args):
    proc = command(["gsettings", *args])
    if proc.returncode != 0:
        raise RuntimeError(f"gsettings {args}: {proc.stderr}")
    return proc.stdout.strip()


def check_isolation():
    """Abort unless bus, database, and profile list are all fresh."""
    bus = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    outer = os.environ.get("UKIYO_E_OUTER_BUS", "")
    if not bus or not outer or bus == outer:
        raise IsolationError(f"bus not isolated: {bus!r}")
    config = os.environ.get("XDG_CONFIG_HOME", "")
    scratch = os.environ.get("TMPDIR", "")
    if not config or not scratch or not config.startswith(scratch):
        raise IsolationError(f"XDG_CONFIG_HOME not in scratch: {config}")
    listed = gsettings("get", PROFILES_LIST, "list")
    if listed != SCHEMA_DEFAULT_LIST:
        raise IsolationError(f"profile list is not default: {listed}")
    if dump() != "":
        raise IsolationError("scratch dconf database is not empty")


def profile_key(uuid, key, value):
    path = f"{PROFILE_SCHEMA}:{PROFILE_ROOT}:{uuid}/"
    gsettings("set", path, key, value)


def seed_two_profiles():
    """Profiles A and B with list = [A, B] and default = A."""
    for uuid, name in ((PROFILE_A, "Alpha"), (PROFILE_B, "Beta")):
        profile_key(uuid, "visible-name", f"'{name}'")
        profile_key(uuid, "palette", "['#010203', '#040506']")
        profile_key(uuid, "font", "'Monospace 11'")
    both = f"['{PROFILE_A}', '{PROFILE_B}']"
    gsettings("set", PROFILES_LIST, "list", both)
    gsettings("set", PROFILES_LIST, "default", f"'{PROFILE_A}'")


def seed_empty_list():
    gsettings("set", PROFILES_LIST, "list", "@as []")


def installer_env(variant):
    """Environment for install.sh: normal, no gsettings, or no schema."""
    env = dict(os.environ)
    empty = tempfile.mkdtemp(dir=os.environ["XDG_RUNTIME_DIR"])
    if variant == "no_gsettings":
        env["PATH"] = empty
    elif variant == "no_schema":
        env.pop("GSETTINGS_SCHEMA_DIR", None)
        env["XDG_DATA_DIRS"] = empty
        env["XDG_DATA_HOME"] = empty
    return env


def run_installer(repo, name, args, variant="normal"):
    script = os.path.join(repo, "gnome-terminal", "install.sh")
    proc = command(["/usr/bin/bash", script, *args],
                   env=installer_env(variant))
    return Step(name, proc.returncode, proc.stderr, dump())


def lifecycle(repo):
    seed_two_profiles()
    return [
        Step("seeded", 0, "", dump()),
        run_installer(repo, "install", []),
        run_installer(repo, "reinstall", []),
        run_installer(repo, "set_default", ["--set-default"]),
        run_installer(repo, "uninstall", ["--uninstall"]),
        run_installer(repo, "uninstall_again", ["--uninstall"]),
    ]


def single_profile(repo):
    seed_empty_list()
    return [
        Step("seeded", 0, "", dump()),
        run_installer(repo, "set_default", ["--set-default"]),
        run_installer(repo, "uninstall", ["--uninstall"]),
    ]


def failures(repo):
    seed_two_profiles()
    return [
        Step("seeded", 0, "", dump()),
        run_installer(repo, "no_gsettings", [], "no_gsettings"),
        run_installer(repo, "no_schema", [], "no_schema"),
        run_installer(repo, "both_flags", ["--set-default", "--uninstall"]),
        run_installer(repo, "unknown_flag", ["--frobnicate"]),
        run_installer(repo, "help", ["--help"]),
    ]


def install_only(repo):
    return [run_installer(repo, "install", [])]


SCENARIOS = {
    "lifecycle": lifecycle,
    "single_profile": single_profile,
    "failures": failures,
    "install_only": install_only,
}


def main(argv):
    scenario, repo = SCENARIOS[argv[0]], argv[1]
    try:
        check_isolation()
    except (IsolationError, RuntimeError) as exc:
        print(json.dumps({"guard": str(exc), "steps": []}))
        return GUARD_FAILED
    steps = scenario(repo)
    print(json.dumps({"guard": "ok", "steps": [asdict(s) for s in steps]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
