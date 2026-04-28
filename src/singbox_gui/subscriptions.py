from __future__ import annotations

import json
import ssl
import urllib.request

from .config_adapter import adapt_config_for_linux
from .models import Profile, SOURCE_REMOTE_CONFIG, SOURCE_REMOTE_SUBSCRIPTION, utc_now_iso
from .profiles import ProfileStore


class SubscriptionError(RuntimeError):
    pass


class SubscriptionUpdater:
    def __init__(self, store: ProfileStore) -> None:
        self.store = store

    def update_profile(self, profile: Profile) -> str:
        if profile.source_type not in {SOURCE_REMOTE_CONFIG, SOURCE_REMOTE_SUBSCRIPTION}:
            raise SubscriptionError("Profile is not URL-based")
        if not profile.subscription_url:
            raise SubscriptionError("Subscription URL is empty")

        text = self._download(profile)
        text = adapt_config_for_linux(text).text
        self._validate_singbox_json(text)

        profile.last_update_status = "ok"
        profile.last_error = None
        profile.updated_at = utc_now_iso()
        self.store.save_profile(profile, config_text=text)
        return text

    def _download(self, profile: Profile) -> str:
        options = profile.subscription_options
        request = urllib.request.Request(
            profile.subscription_url,
            headers={"User-Agent": options.user_agent},
            method="GET",
        )

        context = None
        if options.allow_insecure:
            context = ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(request, timeout=30, context=context) as response:
                content = response.read(10 * 1024 * 1024)
        except Exception as exc:  # noqa: BLE001 - user-facing network error
            profile.last_update_status = "error"
            profile.last_error = str(exc)
            self.store.save_profile(profile)
            raise SubscriptionError(str(exc)) from exc

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError as exc:
            profile.last_update_status = "error"
            profile.last_error = "Response is not valid UTF-8"
            self.store.save_profile(profile)
            raise SubscriptionError(profile.last_error) from exc

    @staticmethod
    def _validate_singbox_json(text: str) -> None:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SubscriptionError(f"Downloaded data is not JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise SubscriptionError("Downloaded JSON must be an object")
