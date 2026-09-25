"""Isolated D-Bus sessions with a scratch dconf database.

A session is a long-lived `dbus-run-session` whose child prints the
private bus address and waits on stdin; closing stdin ends the child
and with it the bus and its dconf service. Before any write, the
isolation guard proves that gsettings talks to a fresh scratch
database; otherwise the test aborts.
"""

import os
import subprocess
from dataclasses import dataclass

import support

SCHEMA_DEFAULT_LIST = "['b1dcc9dd-5262-4d8d-a863-c897e6d979b9']"
PROFILES_LIST = "org.gnome.Terminal.ProfilesList"
PROFILE_SCHEMA = "org.gnome.Terminal.Legacy.Profile"
PROFILE_ROOT = "/org/gnome/terminal/legacy/profiles:/"
PROFILE_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
PROFILE_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
CHILD = 'printf "%s\\n" "$DBUS_SESSION_BUS_ADDRESS"; exec cat >/dev/null'


class IsolationError(Exception):
    """The session is not provably isolated from the real database."""


@dataclass(frozen=True)
class Step:
    """One configure.py run: exit code, output, and dconf dump."""

    name: str
    code: int
    stdout: str
    stderr: str
    dump: str


def command(env, argv):
    return subprocess.run(argv, capture_output=True, text=True, env=env,
                          check=False, stdin=subprocess.DEVNULL)


def gsettings(env, *args):
    proc = command(env, ["gsettings", *args])
    if proc.returncode != 0:
        raise RuntimeError(f"gsettings {args}: {proc.stderr}")
    return proc.stdout.strip()


def dump(env):
    """The session's dconf dump (outer PATH so dconf is found)."""
    env = dict(env, PATH=os.environ["PATH"])
    return command(env, ["dconf", "dump", "/org/gnome/terminal/"]).stdout


def stop(proc):
    proc.stdin.close()
    proc.wait(timeout=30)


def start_session(case, env):
    """Start a private bus for a scratch env; returns env with it."""
    support.assert_isolated(env.vars)
    vars_ = {k: v for k, v in env.vars.items()
             if k != "DBUS_SESSION_BUS_ADDRESS"}
    proc = subprocess.Popen(["dbus-run-session", "--", "sh", "-c", CHILD],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, env=vars_)
    support.later(case, stop, proc)
    address = proc.stdout.readline().strip()
    session = env.with_vars(DBUS_SESSION_BUS_ADDRESS=address)
    check_isolation(session.vars)
    return session


def check_isolation(env):
    """Abort unless bus, database, and profile list are all fresh."""
    bus = env.get("DBUS_SESSION_BUS_ADDRESS", "")
    outer = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not bus or bus == outer:
        raise IsolationError(f"bus not isolated: {bus!r}")
    problem = support.isolation_problem(env)
    if problem:
        raise IsolationError(problem)
    listed = gsettings(env, "get", PROFILES_LIST, "list")
    if listed != SCHEMA_DEFAULT_LIST:
        raise IsolationError(f"profile list is not default: {listed}")
    if dump(env) != "":
        raise IsolationError("scratch dconf database is not empty")


def profile_key(env, uuid, key, value):
    path = f"{PROFILE_SCHEMA}:{PROFILE_ROOT}:{uuid}/"
    gsettings(env, "set", path, key, value)


def seed_two_profiles(env):
    """Profiles A and B with list = [A, B] and default = A."""
    for uuid, name in ((PROFILE_A, "Alpha"), (PROFILE_B, "Beta")):
        profile_key(env, uuid, "visible-name", f"'{name}'")
        profile_key(env, uuid, "palette", "['#010203', '#040506']")
        profile_key(env, uuid, "font", "'Monospace 11'")
    both = f"['{PROFILE_A}', '{PROFILE_B}']"
    gsettings(env, "set", PROFILES_LIST, "list", both)
    gsettings(env, "set", PROFILES_LIST, "default", f"'{PROFILE_A}'")


def seed_empty_list(env):
    gsettings(env, "set", PROFILES_LIST, "list", "@as []")


def run_installer(session, name, *args, root=support.REPO):
    """configure.py <args> inside the session; the dump afterwards."""
    check_bus(session.vars)
    result = support.run_configure(session, *args, root=root)
    return Step(name, result.code, result.stdout, result.stderr,
                dump(session.vars))


def check_bus(env):
    outer = os.environ.get("DBUS_SESSION_BUS_ADDRESS", "")
    bus = env.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not bus or bus == outer:
        raise IsolationError(f"bus not isolated: {bus!r}")
