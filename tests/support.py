"""Shared helpers for the Ukiyo-e verification suite."""

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

sys.dont_write_bytecode = True

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
SEED_HASH = "bb85e4bfc8d89b0e62c8fa53ccdd13d12e2f77b3"
IGNORED_COPY = shutil.ignore_patterns(".git", "__pycache__")


@dataclass(frozen=True)
class RunResult:
    """Exit code and captured text of one finished process."""

    code: int
    stdout: str
    stderr: str


def run(argv, cwd=None, env=None, stdin=None):
    """Run a command and capture its text output."""
    proc = subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    return RunResult(proc.returncode, proc.stdout, proc.stderr)


def scratch_dir():
    """Create a fresh directory under TMPDIR (the session scratchpad)."""
    return Path(tempfile.mkdtemp(prefix="ukiyo_e_"))


def copy_repo():
    """Copy the working tree (without .git) into a scratch directory."""
    target = scratch_dir() / "repo"
    shutil.copytree(REPO, target, ignore=IGNORED_COPY, symlinks=True)
    return target


def remove_tree(path):
    """Delete a scratch tree created by this suite."""
    shutil.rmtree(Path(path).parent, ignore_errors=True)


def remove_dir(path):
    """Delete a scratch directory created by scratch_dir()."""
    shutil.rmtree(path, ignore_errors=True)


def resolved_ansi(root=REPO):
    """The 16 ANSI colours resolved against a tree's palette."""
    from configurator import terminal_ansi

    return list(terminal_ansi.resolve_ansi(repo_palette(root)))


def resolved_tmux(root=REPO):
    """Every TMUX_ROLES role resolved to lowercase hex."""
    from configurator import tmux

    return resolved_roles(tmux.TMUX_ROLES, root)


def replace_line(path, prefix, new_line):
    """Replace the unique line of a file that starts with prefix."""
    lines = Path(path).read_text().split("\n")
    hits = [i for i, line in enumerate(lines) if line.startswith(prefix)]
    if len(hits) != 1:
        raise AssertionError(f"{prefix!r}: {len(hits)} matching lines")
    lines[hits[0]] = new_line
    Path(path).write_text("\n".join(lines))


REAL_DATA = Path.home() / ".local" / "share"
TMUX_PREFIX = "/tmp/uk"


@dataclass(frozen=True)
class ScratchEnv:
    """A scratch folder and the environment of a configurator run."""

    root: Path
    vars: dict

    @property
    def data(self):
        return Path(self.vars.get("XDG_DATA_HOME")
                    or Path(self.vars["HOME"]) / ".local/share")

    @property
    def install(self):
        return self.data / "ukiyo_e"

    @property
    def versions(self):
        return self.data / "ukiyo_e.versions"

    def with_vars(self, **changes):
        """A copy with variables set (a None value removes one)."""
        new = dict(self.vars)
        for key, value in changes.items():
            if value is None:
                new.pop(key, None)
            else:
                new[key] = str(value)
        return ScratchEnv(self.root, new)


def later(owner, function, *args):
    """Register a cleanup on a TestCase instance or class."""
    if isinstance(owner, type):
        owner.addClassCleanup(function, *args)
    else:
        owner.addCleanup(function, *args)


def short_tmux_dir(owner):
    """An existing short TMUX_TMPDIR under /tmp, removed on cleanup."""
    folder = Path(tempfile.mkdtemp(dir="/tmp", prefix="uk"))
    later(owner, shutil.rmtree, folder, True)
    return folder


def base_vars():
    """PATH, locale and XDG_DATA_DIRS of the outer environment only."""
    keep = ("PATH", "LANG", "LC_ALL", "XDG_DATA_DIRS", "TMPDIR")
    found = {k: os.environ[k] for k in keep if k in os.environ}
    found["PYTHONDONTWRITEBYTECODE"] = "1"
    return found


def scratch_env(owner):
    """Fresh HOME, XDG_* and TMUX_TMPDIR; no TMUX, no D-Bus."""
    root = scratch_dir()
    later(owner, remove_dir, root)
    names = ("home", "data", "config", "runtime", "cwd")
    for name in names:
        (root / name).mkdir(mode=0o700)
    found = dict(base_vars(), HOME=str(root / "home"),
                 XDG_DATA_HOME=str(root / "data"),
                 XDG_CONFIG_HOME=str(root / "config"),
                 XDG_RUNTIME_DIR=str(root / "runtime"),
                 TMUX_TMPDIR=str(short_tmux_dir(owner)))
    return ScratchEnv(root, found)


def inside(path, folder):
    return Path(path).resolve().is_relative_to(Path(folder).resolve())


def isolation_problem(env):
    """Why env is not provably isolated, or None (LD-7)."""
    scratch = tempfile.gettempdir()
    tmpdir = env.get("TMUX_TMPDIR", "")
    if not tmpdir.startswith(TMUX_PREFIX) or not Path(tmpdir).is_dir():
        return f"TMUX_TMPDIR is not a scratch mkdtemp: {tmpdir!r}"
    tmux = env.get("TMUX", "")
    if tmux and not tmux.startswith(tmpdir + "/"):
        return f"TMUX is not a test socket: {tmux!r}"
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_RUNTIME_DIR"):
        if not env.get(key) or not inside(env[key], scratch):
            return f"{key} is not under scratch: {env.get(key)!r}"
    data = env.get("XDG_DATA_HOME")
    if data and (not inside(data, scratch) or inside(data, REAL_DATA)):
        return f"XDG_DATA_HOME is not scratch: {data!r}"
    return None


def assert_isolated(env):
    problem = isolation_problem(env)
    if problem:
        raise AssertionError(f"ISOLATION: {problem}")


TERMINAL_TARGETS = ("all", "gnome", "ptyxis")


def selects_terminal(args):
    """Whether configure.py <args> may reach gsettings."""
    if "-h" in args or "--help" in args:
        return False
    targets = [a for a in args if not a.startswith("-")]
    return not targets or any(a in TERMINAL_TARGETS for a in targets)


def bus_problem(env, args):
    """A terminal run needs a private bus (or no gsettings at all)."""
    if not selects_terminal(args):
        return None
    if shutil.which("gsettings", path=env.get("PATH", "")) is None:
        return None
    bus = env.get("DBUS_SESSION_BUS_ADDRESS", "")
    if not bus or bus == os.environ.get("DBUS_SESSION_BUS_ADDRESS", ""):
        return f"terminal run without a private bus: {bus!r}"
    return None


def run_configure(env, *args, root=REPO):
    """Run a repository's configure.py in a proven-isolated env."""
    assert_isolated(env.vars)
    problem = bus_problem(env.vars, args)
    if problem:
        raise AssertionError(f"ISOLATION: {problem}")
    argv = [sys.executable, str(Path(root) / "configure.py"), *args]
    return run(argv, cwd=env.root / "cwd", env=env.vars, stdin="")


def configure_ok(env, *args, root=REPO):
    """run_configure that must exit 0."""
    result = run_configure(env, *args, root=root)
    if result.code != 0:
        raise AssertionError(f"configure.py {args}: {result.code}\n"
                             f"{result.stdout}{result.stderr}")
    return result


def repo_palette(root=REPO):
    """The validated palette of a repository tree."""
    from configurator import palette

    raw = palette.read_toml(Path(root) / "palette.toml")
    return palette.make_palette(raw)


def resolved_roles(roles, root=REPO):
    """A role mapping resolved against a tree's palette."""
    colours = repo_palette(root).colors
    return {role: colours[name] for role, name in roles.items()}


def tree_snapshot(root, skip=("runtime",)):
    """relpath -> (type, link target, mode, SHA-256, mtime_ns)."""
    root = Path(root)
    found = {}
    for top, dirs, names in os.walk(root):
        if Path(top) == root:
            dirs[:] = [d for d in dirs if d not in skip]
        for name in dirs + names:
            path = Path(top) / name
            found[str(path.relative_to(root))] = entry_snapshot(path)
    return found


def entry_snapshot(path):
    info = path.lstat()
    if path.is_symlink():
        return ("link", os.readlink(path), 0, "", info.st_mtime_ns)
    if path.is_dir():
        return ("dir", "", info.st_mode & 0o7777, "", info.st_mtime_ns)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return ("file", "", info.st_mode & 0o7777, digest, info.st_mtime_ns)


def changed_paths(before, after):
    return sorted(k for k in set(before) | set(after)
                  if before.get(k) != after.get(k))


def real_dconf_dump(path="/org/gnome/terminal/"):
    """Read-only dump of the user's real settings under path."""
    return run(["dconf", "dump", path]).stdout


def real_data_dir():
    """The real $DATA of REQ-INST-1 (outer environment)."""
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg and Path(xdg).is_absolute():
        return Path(xdg)
    return REAL_DATA


def real_ptx():
    return real_data_dir() / "org.gnome.Ptyxis" / "palettes"


def ptx(env):
    """$PTX of a scratch env."""
    return env.data / "org.gnome.Ptyxis" / "palettes"


def real_entries():
    """Real ukiyo_e, ukiyo_e.versions, .ukiyo_e.new-* (with links)."""
    data = real_data_dir()
    found = {}
    for pattern in ("ukiyo_e*", ".ukiyo_e.new-*"):
        for path in sorted(data.glob(pattern)):
            found[path.name] = entry_snapshot(path)
    return found


def real_state():
    """SAF-8: real dconf dumps, install entries, and real $PTX."""
    folder = real_ptx()
    tree = None
    if os.path.lexists(folder):
        tree = tree_snapshot(folder, skip=())
    return {"terminal": real_dconf_dump(),
            "ptyxis": real_dconf_dump("/org/gnome/Ptyxis/"),
            "entries": real_entries(),
            "ptx": (os.path.lexists(folder), tree)}


TMUX_ALLOWLIST = frozenset({
    "status-style", "window-status-style", "window-status-current-style",
    "window-status-activity-style", "window-status-bell-style",
    "pane-border-style", "pane-active-border-style", "message-style",
    "message-command-style", "mode-style", "clock-mode-colour",
    "display-panes-colour", "display-panes-active-colour",
    "status-left", "status-right", "window-status-format",
    "window-status-current-format", "window-status-separator",
    "@ukiyo_e_status_date", "@ukiyo_e_status_time",
})
_SERVER_COUNT = [0]


@dataclass(frozen=True)
class TmuxServer:
    """A dedicated tmux server on a -L socket under TMUX_TMPDIR."""

    name: str
    config: Path
    tmpdir: str

    @classmethod
    def start(cls, owner, env):
        """Start a server in env's TMUX_TMPDIR; kill it on cleanup."""
        _SERVER_COUNT[0] += 1
        name = f"ukiyo_e_test_{os.getpid()}_{_SERVER_COUNT[0]}"
        config = env.root / f"{name}.conf"
        config.write_text("")
        server = cls(name, config, env.vars["TMUX_TMPDIR"])
        result = server.tmux("new-session", "-d", "-x", "200", "-y", "50")
        if result.code != 0:
            raise AssertionError(f"tmux did not start: {result.stderr}")
        socket = Path(server.display("#{socket_path}"))
        if not inside(socket, server.tmpdir):
            server.tmux("kill-server")
            raise AssertionError(f"ISOLATION: socket {socket}")
        later(owner, socket.unlink, True)
        later(owner, server.tmux, "kill-server")
        return server

    def client_env(self):
        return dict(base_vars(), TMUX_TMPDIR=self.tmpdir)

    def tmux(self, *args):
        argv = ["tmux", "-L", self.name, "-f", str(self.config), *args]
        return run(argv, env=self.client_env(), stdin="")

    def display(self, fmt):
        return self.tmux("display", "-p", fmt).stdout.strip()

    def value(self, option):
        result = self.tmux("show-options", "-gqv", option)
        return result.stdout.rstrip("\n")

    def attach(self, env):
        """env with TMUX naming this server (REQ-LIVE-2)."""
        where = self.display("#{socket_path},#{pid}")
        return env.with_vars(TMUX=f"{where},0")

    def pid(self):
        return self.display("#{pid}")

    def run_script(self, env, script):
        """Run an installed ukiyo_e.tmux against this server."""
        attached = self.attach(env)
        assert_isolated(attached.vars)
        return run([str(script)], env=attached.vars, stdin="")

    def snapshot(self):
        """Global options, window options, and non-option state."""
        return {
            "options": self._options("-g"),
            "window": self._options("-gw"),
            "server": self._options("-s"),
            "keys": self.tmux("list-keys").stdout,
            "hooks": self.tmux("show-hooks", "-g").stdout,
            "environment": self.tmux("show-environment", "-g").stdout,
        }

    def _options(self, scope):
        lines = self.tmux("show-options", scope).stdout.splitlines()
        return dict(line.split(" ", 1) if " " in line else (line, "")
                    for line in lines)


def changed_options(before, after):
    """Option names whose global value differs between snapshots."""
    changed = set()
    for table in ("options", "window", "server"):
        old, new = before[table], after[table]
        changed |= {k for k in set(old) | set(new)
                    if old.get(k) != new.get(k)}
    return changed


def parse_dump(text):
    """dconf dump text -> {section: {key: value}}."""
    sections, current = {}, None
    for line in text.splitlines():
        if line.startswith("[") and line.endswith("]"):
            current = sections.setdefault(line[1:-1], {})
        elif "=" in line and current is not None:
            key, value = line.split("=", 1)
            current[key] = value
    return sections


class RealStateGuard:
    """Fail loudly if the user's real state changes (SAF-8)."""

    before = None

    @classmethod
    def take(cls):
        cls.before = real_state()

    @classmethod
    def verify(cls):
        after = real_state()
        changed = sorted(k for k in after if after[k] != cls.before[k])
        if changed:
            raise AssertionError(f"REAL STATE CHANGED: {changed}")
