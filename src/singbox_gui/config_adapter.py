from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AdaptationChange:
    path: str
    reason: str


@dataclass(frozen=True)
class AdaptationResult:
    text: str
    changes: tuple[AdaptationChange, ...]

    @property
    def changed(self) -> bool:
        return bool(self.changes)

    def summary(self) -> str:
        return "\n".join(f"- {item.path}: {item.reason}" for item in self.changes)


LINUX_UNSUPPORTED_FIELDS: tuple[tuple[tuple[str, ...], str], ...] = (
    (
        ("route", "override_android_vpn"),
        "поле поддерживается только на Android; на Linux upstream-интерфейс определяется через auto_detect_interface/default_interface",
    ),
)


def adapt_config_for_linux(text: str) -> AdaptationResult:
    data = json.loads(text)
    adapted = deepcopy(data)
    changes: list[AdaptationChange] = []

    for path, reason in LINUX_UNSUPPORTED_FIELDS:
        if _delete_path(adapted, path):
            changes.append(AdaptationChange(".".join(path), reason))

    if not changes:
        return AdaptationResult(text, ())

    return AdaptationResult(
        json.dumps(adapted, ensure_ascii=False, indent=2) + "\n",
        tuple(changes),
    )


def _delete_path(data: Any, path: tuple[str, ...]) -> bool:
    current = data
    for key in path[:-1]:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]

    if not isinstance(current, dict):
        return False

    leaf = path[-1]
    if leaf not in current:
        return False

    del current[leaf]
    return True
