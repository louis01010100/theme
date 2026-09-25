"""REQ-INST-1: resolve $DATA, $INSTALL and $VERSIONS."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from configurator.files import Layout
from configurator.palette import InputError

INSTALL_NAME = "ukiyo_e"
VERSIONS_NAME = "ukiyo_e.versions"


def data_dir(env: Mapping[str, str]) -> Path:
    """$XDG_DATA_HOME when absolute, else $HOME/.local/share."""
    xdg = env.get("XDG_DATA_HOME", "")
    if xdg and Path(xdg).is_absolute():
        return Path(xdg)
    home = env.get("HOME", "")
    if not home or not Path(home).is_absolute():
        raise InputError("cannot resolve the install directory: set "
                         "HOME or an absolute XDG_DATA_HOME")
    return Path(home) / ".local" / "share"


def resolve(env: Mapping[str, str]) -> Layout:
    data = data_dir(env)
    return Layout(data, data / INSTALL_NAME, data / VERSIONS_NAME)
