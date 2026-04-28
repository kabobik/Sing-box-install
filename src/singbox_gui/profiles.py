from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .models import Profile, SOURCE_DIRECT_CONFIG, utc_now_iso
from .paths import config_home, profiles_dir, settings_path


SYSTEM_CONFIG_PATH = Path("/etc/sing-box/config.json")


class ProfileStore:
    def __init__(self) -> None:
        self.base_dir = config_home()
        self.profiles_dir = profiles_dir()
        self.settings_file = settings_path()
        self.ensure_layout()

    def ensure_layout(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        if not self.settings_file.exists():
            self._write_json(self.settings_file, {"active_profile_id": None})

    def ensure_initial_profile(self) -> None:
        if self.list_profiles():
            return
        if not SYSTEM_CONFIG_PATH.exists():
            return

        try:
            config_text = SYSTEM_CONFIG_PATH.read_text(encoding="utf-8")
            json.loads(config_text)
        except (OSError, json.JSONDecodeError):
            return

        profile = Profile.new("Current system config", source_type=SOURCE_DIRECT_CONFIG)
        profile.last_check_status = "imported"
        self.save_profile(profile, config_text=config_text)
        self.set_active_profile_id(profile.id)

    def list_profiles(self) -> list[Profile]:
        profiles: list[Profile] = []
        for profile_dir in sorted(self.profiles_dir.iterdir()):
            if not profile_dir.is_dir():
                continue
            meta_path = profile_dir / "meta.json"
            if not meta_path.exists():
                continue
            try:
                profiles.append(Profile.from_dict(self._read_json(meta_path)))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return sorted(profiles, key=lambda item: item.name.casefold())

    def get_profile(self, profile_id: str) -> Profile | None:
        meta_path = self.profile_dir(profile_id) / "meta.json"
        if not meta_path.exists():
            return None
        return Profile.from_dict(self._read_json(meta_path))

    def save_profile(self, profile: Profile, *, config_text: str | None = None) -> None:
        profile.touch()
        profile_dir = self.profile_dir(profile.id)
        profile_dir.mkdir(parents=True, exist_ok=True)
        self._write_json(profile_dir / "meta.json", profile.to_dict())
        if config_text is not None:
            (profile_dir / "config.json").write_text(config_text, encoding="utf-8")

    def delete_profile(self, profile_id: str) -> None:
        shutil.rmtree(self.profile_dir(profile_id), ignore_errors=True)
        if self.active_profile_id() == profile_id:
            remaining = self.list_profiles()
            self.set_active_profile_id(remaining[0].id if remaining else None)

    def profile_dir(self, profile_id: str) -> Path:
        return self.profiles_dir / profile_id

    def config_path(self, profile_id: str) -> Path:
        return self.profile_dir(profile_id) / "config.json"

    def read_config_text(self, profile_id: str) -> str:
        path = self.config_path(profile_id)
        if not path.exists():
            return "{\n  \"log\": {\n    \"level\": \"info\"\n  }\n}\n"
        return path.read_text(encoding="utf-8")

    def active_profile_id(self) -> str | None:
        return self.settings().get("active_profile_id")

    def active_profile(self) -> Profile | None:
        active_id = self.active_profile_id()
        return self.get_profile(active_id) if active_id else None

    def set_active_profile_id(self, profile_id: str | None) -> None:
        settings = self.settings()
        settings["active_profile_id"] = profile_id
        settings["updated_at"] = utc_now_iso()
        self._write_json(self.settings_file, settings)

    def settings(self) -> dict[str, Any]:
        try:
            return self._read_json(self.settings_file)
        except (OSError, json.JSONDecodeError):
            return {"active_profile_id": None}

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temp_path.replace(path)
