from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from .command import CommandResult, run_command
from .paths import source_dir


SERVICE_NAME = "sing-box"


@dataclass(frozen=True)
class ServiceState:
    active_state: str
    enabled_state: str
    error: str | None = None

    @property
    def is_active(self) -> bool:
        return self.active_state == "active"

    @property
    def is_failed(self) -> bool:
        return self.active_state == "failed"


class SingBoxService:
    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self.service_name = service_name

    def state(self) -> ServiceState:
        active = run_command(["systemctl", "is-active", self.service_name], timeout=5)
        enabled = run_command(["systemctl", "is-enabled", self.service_name], timeout=5)

        active_state = active.stdout.strip() or "unknown"
        enabled_state = enabled.stdout.strip() or "unknown"
        error = None
        if active.returncode not in {0, 3} and active.stderr.strip():
            error = active.stderr.strip()

        return ServiceState(active_state, enabled_state, error)

    def start(self) -> CommandResult:
        return self._privileged_systemctl("start")

    def stop(self) -> CommandResult:
        return self._privileged_systemctl("stop")

    def restart(self) -> CommandResult:
        return self._privileged_systemctl("restart")

    def check_config(self, config_path: Path) -> CommandResult:
        return run_command(
            ["sing-box", "check", "-c", str(config_path)],
            timeout=30,
        )

    def deploy_config(self, config_path: Path) -> CommandResult:
        return self._privileged_module("deploy-config", str(config_path))

    def recent_errors(self, lines: int = 80) -> CommandResult:
        return run_command(
            [
                "journalctl",
                "-u",
                self.service_name,
                "-p",
                "warning..alert",
                "-n",
                str(lines),
                "--no-pager",
                "--output",
                "short-iso",
            ],
            timeout=10,
        )

    def _privileged_systemctl(self, action: str) -> CommandResult:
        return run_command(["pkexec", "systemctl", action, self.service_name], timeout=120)

    def _privileged_module(self, *args: str) -> CommandResult:
        env_path = shutil.which("env") or "/usr/bin/env"
        pythonpath = str(source_dir())
        return run_command(
            [
                "pkexec",
                env_path,
                f"PYTHONPATH={pythonpath}",
                sys.executable,
                "-m",
                "singbox_gui.privileged",
                *args,
            ],
            timeout=120,
        )
