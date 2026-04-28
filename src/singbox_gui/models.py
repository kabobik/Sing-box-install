from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


SOURCE_DIRECT_CONFIG = "direct_config"
SOURCE_REMOTE_CONFIG = "remote_config"
SOURCE_REMOTE_SUBSCRIPTION = "remote_subscription"

SOURCE_TYPES = (
    SOURCE_DIRECT_CONFIG,
    SOURCE_REMOTE_CONFIG,
    SOURCE_REMOTE_SUBSCRIPTION,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def make_profile_id() -> str:
    return uuid4().hex[:12]


@dataclass
class SubscriptionOptions:
    auto_update: bool = False
    update_interval_hours: int = 24
    allow_insecure: bool = False
    use_proxy_for_update: bool = False
    user_agent: str = "singbox-gui/0.1"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "SubscriptionOptions":
        if not data:
            return cls()
        return cls(
            auto_update=bool(data.get("auto_update", False)),
            update_interval_hours=int(data.get("update_interval_hours", 24)),
            allow_insecure=bool(data.get("allow_insecure", False)),
            use_proxy_for_update=bool(data.get("use_proxy_for_update", False)),
            user_agent=str(data.get("user_agent", "singbox-gui/0.1")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "auto_update": self.auto_update,
            "update_interval_hours": self.update_interval_hours,
            "allow_insecure": self.allow_insecure,
            "use_proxy_for_update": self.use_proxy_for_update,
            "user_agent": self.user_agent,
        }


@dataclass
class Profile:
    id: str
    name: str
    source_type: str = SOURCE_DIRECT_CONFIG
    subscription_url: str | None = None
    subscription_options: SubscriptionOptions = field(default_factory=SubscriptionOptions)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    last_check_status: str = "unknown"
    last_update_status: str = "never"
    last_error: str | None = None

    @classmethod
    def new(
        cls,
        name: str,
        *,
        source_type: str = SOURCE_DIRECT_CONFIG,
        subscription_url: str | None = None,
    ) -> "Profile":
        return cls(
            id=make_profile_id(),
            name=name.strip() or "New profile",
            source_type=source_type,
            subscription_url=subscription_url,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Profile":
        source_type = str(data.get("source_type", SOURCE_DIRECT_CONFIG))
        if source_type not in SOURCE_TYPES:
            source_type = SOURCE_DIRECT_CONFIG

        return cls(
            id=str(data["id"]),
            name=str(data.get("name", "Unnamed profile")),
            source_type=source_type,
            subscription_url=data.get("subscription_url"),
            subscription_options=SubscriptionOptions.from_dict(
                data.get("subscription_options")
            ),
            created_at=str(data.get("created_at", utc_now_iso())),
            updated_at=str(data.get("updated_at", utc_now_iso())),
            last_check_status=str(data.get("last_check_status", "unknown")),
            last_update_status=str(data.get("last_update_status", "never")),
            last_error=data.get("last_error"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "subscription_url": self.subscription_url,
            "subscription_options": self.subscription_options.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_check_status": self.last_check_status,
            "last_update_status": self.last_update_status,
            "last_error": self.last_error,
        }

    def touch(self) -> None:
        self.updated_at = utc_now_iso()
