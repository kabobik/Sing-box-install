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

STRICT_ROUTE_REDIRECT_REASON = (
    "при auto_redirect и route.auto_detect_interface/default_interface strict_route может вернуть "
    "собственные outbound-подключения sing-box обратно в TUN; отключено, чтобы избежать "
    "петли proxy/DNS"
)


def adapt_config_for_linux(text: str) -> AdaptationResult:
    data = json.loads(text)
    adapted = deepcopy(data)
    changes: list[AdaptationChange] = []

    for path, reason in LINUX_UNSUPPORTED_FIELDS:
        if _delete_path(adapted, path):
            changes.append(AdaptationChange(".".join(path), reason))

    changes.extend(_disable_tun_strict_route_redirect_loop(adapted))

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


def _disable_tun_strict_route_redirect_loop(data: Any) -> list[AdaptationChange]:
    if not isinstance(data, dict):
        return []

    route = data.get("route")
    if not _route_binds_outbound_interface(route):
        return []

    inbounds = data.get("inbounds")
    if not isinstance(inbounds, list):
        return []

    changes: list[AdaptationChange] = []
    for index, inbound in enumerate(inbounds):
        if not isinstance(inbound, dict):
            continue
        if inbound.get("type") != "tun":
            continue
        if inbound.get("auto_redirect") is not True:
            continue
        if inbound.get("strict_route") is not True:
            continue

        inbound["strict_route"] = False
        changes.append(
            AdaptationChange(
                f"inbounds[{index}].strict_route",
                STRICT_ROUTE_REDIRECT_REASON,
            )
        )

    return changes


def _route_binds_outbound_interface(route: Any) -> bool:
    if not isinstance(route, dict):
        return False
    if route.get("auto_detect_interface") is True:
        return True
    default_interface = route.get("default_interface")
    return isinstance(default_interface, str) and bool(default_interface.strip())
