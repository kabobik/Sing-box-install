from __future__ import annotations

import os
import sys
from pathlib import Path


APP_ID = "singbox-gui"
APP_NAME = "Singbox GUI"


def config_home() -> Path:
    override = os.environ.get("SINGBOX_GUI_CONFIG_DIR")
    if override:
        return Path(override).expanduser()

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home).expanduser() / APP_ID

    return Path.home() / ".config" / APP_ID


def profiles_dir() -> Path:
    return config_home() / "profiles"


def settings_path() -> Path:
    return config_home() / "settings.json"


def autostart_dir() -> Path:
    return Path.home() / ".config" / "autostart"


def autostart_path() -> Path:
    return autostart_dir() / f"{APP_ID}.desktop"


def source_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def asset_path(name: str) -> Path:
    return package_dir() / "assets" / name


def module_command() -> list[str]:
    return [sys.executable, "-m", "singbox_gui"]
