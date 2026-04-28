from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path


TARGET_CONFIG = Path("/etc/sing-box/config.json")
BACKUP_DIR = Path("/etc/sing-box/backups")


def deploy_config(source: Path) -> int:
    source = source.expanduser().resolve()
    if not source.exists():
        raise SystemExit(f"Source config does not exist: {source}")
    if not source.is_file():
        raise SystemExit(f"Source config is not a file: {source}")

    text = source.read_text(encoding="utf-8")
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Source config is not valid JSON: {exc}") from exc

    TARGET_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET_CONFIG.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = BACKUP_DIR / f"config.json.{stamp}.bak"
        shutil.copy2(TARGET_CONFIG, backup)
        os.chmod(backup, 0o600)

    temp_target = TARGET_CONFIG.with_suffix(".json.tmp")
    temp_target.write_text(text, encoding="utf-8")
    os.chmod(temp_target, 0o644)
    os.chown(temp_target, 0, 0)
    temp_target.replace(TARGET_CONFIG)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    deploy_parser = subparsers.add_parser("deploy-config")
    deploy_parser.add_argument("source")

    args = parser.parse_args(argv)
    if args.command == "deploy-config":
        return deploy_config(Path(args.source))

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
