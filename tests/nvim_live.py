"""A long-running headless Neovim addressed through --listen."""

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import support


@dataclass(frozen=True)
class NvimServer:
    """Neovim with `root` on the runtimepath and ukiyo_e loaded."""

    socket: Path
    env: dict

    @classmethod
    def start(cls, case, root, socket_dir, env):
        """Start it; the socket lives in a short /tmp directory."""
        socket = Path(socket_dir) / "nvim.sock"
        argv = ["nvim", "--clean", "--headless", "--listen", str(socket),
                "--cmd", f"set runtimepath^={root}",
                "-c", "colorscheme ukiyo_e"]
        proc = subprocess.Popen(argv, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        support.later(case, stop, proc)
        wait_for(socket)
        return cls(socket, env)

    def expr(self, expression):
        argv = ["nvim", "--server", str(self.socket), "--remote-expr",
                expression]
        result = support.run(argv, env=self.env, stdin="")
        if result.code != 0:
            raise AssertionError(f"remote-expr: {result.stderr}")
        return result.stdout.strip()

    def lua(self, chunk):
        return self.expr(f"luaeval('{chunk}')")

    def group_fg(self, name):
        return int(self.lua(f'vim.api.nvim_get_hl(0, {{name = "{name}"}})'
                            f'.fg or -1'))

    def colorscheme(self):
        self.expr('execute("colorscheme ukiyo_e")')


def wait_for(socket, timeout=10.0):
    deadline = time.monotonic() + timeout
    while not socket.exists():
        if time.monotonic() > deadline:
            raise AssertionError(f"nvim did not listen on {socket}")
        time.sleep(0.05)


def stop(proc):
    proc.terminate()
    proc.wait(timeout=10)
