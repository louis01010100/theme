"""Isolated D-Bus sessions with a scratch dconf database.

A session is a long-lived `dbus-run-session` whose child prints the
private bus address and waits on stdin; closing stdin ends the child
and with it the bus and its dconf service. Before any write, the
isolation guard proves that gsettings talks to a fresh scratch
database; otherwise the test aborts.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import support

SCHEMA_DEFAULT_LIST = "['b1dcc9dd-5262-4d8d-a863-c897e6d979b9']"
PROFILES_LIST = "org.gnome.Terminal.ProfilesList"
PROFILE_SCHEMA = "org.gnome.Terminal.Legacy.Profile"
PROFILE_ROOT = "/org/gnome/terminal/legacy/profiles:/"
PROFILE_A = "aaaaaaaa-1111-4111-8111-aaaaaaaaaaaa"
PROFILE_B = "bbbbbbbb-2222-4222-8222-bbbbbbbbbbbb"
PTYXIS = "org.gnome.Ptyxis"
PTYXIS_PROFILE = "org.gnome.Ptyxis.Profile"
PTYXIS_ROOT = "/org/gnome/Ptyxis/Profiles/"
PROFILE_P = "11111111111141118111111111111111"
PROFILE_Q = "22222222222242228222222222222222"
SYSTEM_SCHEMAS = Path("/usr/share/glib-2.0/schemas")
SINGLE = {
    "ptyxis": ("org.gnome.Ptyxis.gschema.xml", "*ptyxis*.gschema.override"),
    "gnome": ("org.gnome.Terminal.gschema.xml",
              "*gnome-terminal*.gschema.override"),
    "none": (),
}
TERMINAL_OF = {PROFILES_LIST: "gnome", PTYXIS: "ptyxis"}
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


def dump(env, path="/org/gnome/terminal/"):
    """The session's dconf dump (outer PATH so dconf is found)."""
    env = dict(env, PATH=os.environ["PATH"])
    return command(env, ["dconf", "dump", path]).stdout


def dump_ptyxis(env):
    return dump(env, "/org/gnome/Ptyxis/")


def snapshot_dconf(env):
    """Both terminals' dconf dumps (the Verification dconf snapshot)."""
    return (dump(env), dump_ptyxis(env))


def schema_ids(env, verb):
    """gsettings list-schemas / list-relocatable-schemas as a set."""
    proc = command(env, ["gsettings", verb])
    if proc.returncode != 0 and "No schemas installed" in proc.stderr:
        return set()
    if proc.returncode != 0:
        raise RuntimeError(f"gsettings {verb}: {proc.stderr}")
    return set(proc.stdout.split())


def listed_schemas(env):
    """Every schema id gsettings lists, relocatable ones included."""
    return (schema_ids(env, "list-schemas")
            | schema_ids(env, "list-relocatable-schemas"))


def visible_terminals(env):
    """"gnome"/"ptyxis" whose list schema the session can see."""
    listed = schema_ids(env, "list-schemas")
    return {name for schema, name in TERMINAL_OF.items()
            if schema in listed}


def stop(proc):
    proc.stdin.close()
    proc.wait(timeout=30)


def start_session(case, env, expect=None):
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
    check_isolation(session.vars, expect)
    return session


def check_isolation(env, expect=None):
    """Abort unless bus, database, and terminal lists are all fresh.

    expect: the exact set of terminals ("gnome", "ptyxis") whose
    schemas must be visible; None accepts whatever is installed.
    """
    check_bus(env)
    problem = support.isolation_problem(env)
    if problem:
        raise IsolationError(problem)
    if dump(env, "/") != "":
        raise IsolationError("scratch dconf database is not empty")
    visible = visible_terminals(env)
    if expect is not None and visible != set(expect):
        raise IsolationError(f"terminal schemas {visible} != {expect}")
    for problem in list_problems(env, visible):
        raise IsolationError(problem)


def list_problems(env, visible):
    """Terminal list keys that do not read as their schema default."""
    wanted = []
    if "gnome" in visible:
        wanted.append((PROFILES_LIST, "list", SCHEMA_DEFAULT_LIST))
    if "ptyxis" in visible:
        wanted += [(PTYXIS, "profile-uuids", "@as []"),
                   (PTYXIS, "default-profile-uuid", "''")]
    for schema, key, value in wanted:
        found = gsettings(env, "get", schema, key)
        if found != value:
            yield f"{schema} {key} is not default: {found}"


def build_schemas(root, which):
    """A compiled scratch schema dir with one terminal's schemas."""
    folder = root / f"schemas-{which}"
    folder.mkdir()
    for pattern in SINGLE[which]:
        for source in SYSTEM_SCHEMAS.glob(pattern):
            shutil.copy(source, folder / source.name)
    proc = command(None, ["glib-compile-schemas", "--strict",
                          str(folder)])
    if proc.returncode != 0:
        raise RuntimeError(f"glib-compile-schemas: {proc.stderr}")
    return folder


def single_schema(case, env, which):
    """A session that sees only one terminal's schemas (or none)."""
    empty = env.root / "empty-data-dirs"
    empty.mkdir(exist_ok=True)
    folder = build_schemas(env.root, which)
    env = env.with_vars(GSETTINGS_SCHEMA_DIR=folder, XDG_DATA_DIRS=empty)
    expect = set() if which == "none" else {which}
    session = start_session(case, env, expect)
    prefix = {"ptyxis": "org.gnome.Ptyxis", "gnome": "org.gnome.Terminal",
              "none": None}[which]
    stray = {s for s in listed_schemas(session.vars)
             if prefix is None or not s.startswith(prefix)}
    if stray:
        raise IsolationError(f"unexpected schemas: {sorted(stray)}")
    return session


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


def ptyxis_profile(uuid):
    return f"{PTYXIS_PROFILE}:{PTYXIS_ROOT}{uuid}/"


def seed_ptyxis(env):
    """Profiles P and Q; profile-uuids = [P, Q], default P."""
    for uuid, label in ((PROFILE_P, "Pea"), (PROFILE_Q, "Queue")):
        gsettings(env, "set", ptyxis_profile(uuid), "label", f"'{label}'")
        gsettings(env, "set", ptyxis_profile(uuid), "palette", "'Ubuntu'")
        gsettings(env, "set", ptyxis_profile(uuid), "opacity", "0.9")
    gsettings(env, "set", PTYXIS, "profile-uuids",
              f"['{PROFILE_P}', '{PROFILE_Q}']")
    gsettings(env, "set", PTYXIS, "default-profile-uuid",
              f"'{PROFILE_P}'")


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
