from __future__ import annotations

import shlex
import sys

from .paths import APP_ID, APP_NAME, autostart_dir, autostart_path, source_dir


def autostart_exec_command() -> str:
    return " ".join(
        [
            shlex.quote("/usr/bin/env"),
            shlex.quote(f"PYTHONPATH={source_dir()}"),
            shlex.quote(sys.executable),
            "-m",
            "singbox_gui",
        ]
    )


def desktop_entry() -> str:
    return "\n".join(
        [
            "[Desktop Entry]",
            "Type=Application",
            f"Name={APP_NAME}",
            f"Exec={autostart_exec_command()}",
            "Terminal=false",
            f"X-GNOME-Autostart-enabled=true",
            f"X-Cinnamon-Autostart-enabled=true",
            f"StartupWMClass={APP_ID}",
            "Comment=Tray GUI for sing-box service",
            "",
        ]
    )


def enable_autostart() -> None:
    autostart_dir().mkdir(parents=True, exist_ok=True)
    autostart_path().write_text(desktop_entry(), encoding="utf-8")


def disable_autostart() -> None:
    autostart_path().unlink(missing_ok=True)


def is_autostart_enabled() -> bool:
    return autostart_path().exists()
