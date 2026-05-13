#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$(id -u)" -ne 0 ]; then
  exec sudo "$0" "$@"
fi

install -D -m 0755 packaging/singbox-gui-helper /usr/lib/singbox-gui/singbox-gui-helper
install -D -m 0644 packaging/polkit/org.singbox.gui.policy /usr/share/polkit-1/actions/org.singbox.gui.policy

if command -v pkaction >/dev/null 2>&1; then
  pkaction --action-id org.singbox.gui.manage >/dev/null
fi

echo "Installed singbox-gui PolicyKit helper:"
echo "  /usr/lib/singbox-gui/singbox-gui-helper"
echo "  /usr/share/polkit-1/actions/org.singbox.gui.policy"
