#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION="$(PYTHONPATH=src python3 -c 'import singbox_gui; print(singbox_gui.__version__)')"
ARCH="$(dpkg --print-architecture)"
PACKAGE="singbox-gui"

if [ ! -x .venv/bin/python ]; then
  echo "Missing .venv. Run scripts/install_dev_deps.sh first." >&2
  exit 1
fi

if ! .venv/bin/python -c 'import PySide6' >/dev/null 2>&1; then
  echo "PySide6 is missing in .venv. Run scripts/install_dev_deps.sh first." >&2
  exit 1
fi

mkdir -p build dist
BUILD_ROOT="$(mktemp -d -p "$PWD/build" deb.XXXXXX)"
STAGE="$BUILD_ROOT/${PACKAGE}_${VERSION}_${ARCH}"
DEBIAN="$STAGE/DEBIAN"
APP_DIR="$STAGE/opt/singbox-gui"

install -d "$DEBIAN"
install -d "$APP_DIR"
install -d "$STAGE/usr/bin"
install -d "$STAGE/usr/lib/singbox-gui"
install -d "$STAGE/usr/share/polkit-1/actions"
install -d "$STAGE/usr/share/applications"
install -d "$STAGE/usr/share/icons/hicolor/scalable/apps"
install -d "$STAGE/usr/share/doc/singbox-gui"

cp -a src "$APP_DIR/src"
cp -a .venv "$APP_DIR/venv"

find "$APP_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$APP_DIR" -name '*.pyc' -delete

install -m 0755 packaging/singbox-gui "$STAGE/usr/bin/singbox-gui"
install -m 0755 packaging/singbox-gui-helper "$STAGE/usr/lib/singbox-gui/singbox-gui-helper"
install -m 0644 packaging/polkit/org.singbox.gui.policy "$STAGE/usr/share/polkit-1/actions/org.singbox.gui.policy"
install -m 0644 packaging/singbox-gui.desktop "$STAGE/usr/share/applications/singbox-gui.desktop"
install -m 0644 src/singbox_gui/assets/singbox-gui.svg "$STAGE/usr/share/icons/hicolor/scalable/apps/singbox-gui.svg"
install -m 0644 README.md "$STAGE/usr/share/doc/singbox-gui/README.md"
install -m 0755 packaging/deb/postinst "$DEBIAN/postinst"
install -m 0755 packaging/deb/postrm "$DEBIAN/postrm"

INSTALLED_SIZE="$(du -sk "$STAGE" | awk '{print $1}')"
sed \
  -e "s/@VERSION@/$VERSION/g" \
  -e "s/@ARCH@/$ARCH/g" \
  -e "s/@INSTALLED_SIZE@/$INSTALLED_SIZE/g" \
  packaging/deb/control.template > "$DEBIAN/control"

fakeroot dpkg-deb --build "$STAGE" "dist/${PACKAGE}_${VERSION}_${ARCH}.deb"

echo "Built dist/${PACKAGE}_${VERSION}_${ARCH}.deb"
