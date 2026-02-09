#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/dist}"
APP_NAME="InSituCore"
APP_PATH="${OUT_DIR}/${APP_NAME}.app"
LAUNCH_SCRIPT="${REPO_ROOT}/scripts/launch_insitucore.sh"
ICON_ICNS="${REPO_ROOT}/assets/InSituCore.icns"
ICON_GEN_SCRIPT="${REPO_ROOT}/scripts/generate_macos_icon.py"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "osacompile not found. This script is macOS-only." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
if [[ ! -f "${ICON_ICNS}" && -f "${ICON_GEN_SCRIPT}" ]]; then
  python3 "${ICON_GEN_SCRIPT}" || true
fi

# Escape backslashes/quotes for JXA string literal.
ESCAPED_LAUNCH_SCRIPT="${LAUNCH_SCRIPT//\\/\\\\}"
ESCAPED_LAUNCH_SCRIPT="${ESCAPED_LAUNCH_SCRIPT//\"/\\\"}"

TMP_AS="$(mktemp)"
cat > "${TMP_AS}" <<EOF
var app = Application.currentApplication();
app.includeStandardAdditions = true;
app.doShellScript("/bin/bash \\"${ESCAPED_LAUNCH_SCRIPT}\\" >/dev/null 2>&1 &");
EOF

rm -rf "${APP_PATH}"
osacompile -l JavaScript -o "${APP_PATH}" "${TMP_AS}"
rm -f "${TMP_AS}"

if [[ -f "${ICON_ICNS}" ]]; then
  cp "${ICON_ICNS}" "${APP_PATH}/Contents/Resources/applet.icns"
fi

echo "Created ${APP_PATH}"
echo "Double-click it from Finder to launch InSituCore without Terminal."
