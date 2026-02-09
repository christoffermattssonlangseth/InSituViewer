#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/dist}"
APP_NAME="InSituCore"
APP_PATH="${OUT_DIR}/${APP_NAME}.app"
LAUNCH_SCRIPT="${REPO_ROOT}/scripts/launch_insitucore.sh"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "osacompile not found. This script is macOS-only." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
chmod +x "${LAUNCH_SCRIPT}"

# Escape backslashes/quotes for AppleScript string literal.
ESCAPED_LAUNCH_SCRIPT="${LAUNCH_SCRIPT//\\/\\\\}"
ESCAPED_LAUNCH_SCRIPT="${ESCAPED_LAUNCH_SCRIPT//\"/\\\"}"

TMP_AS="$(mktemp)"
cat > "${TMP_AS}" <<EOF
do shell script quoted form of "${ESCAPED_LAUNCH_SCRIPT}" & " >/dev/null 2>&1 &"
EOF

rm -rf "${APP_PATH}"
osacompile -o "${APP_PATH}" "${TMP_AS}"
rm -f "${TMP_AS}"

echo "Created ${APP_PATH}"
echo "Double-click it from Finder to launch InSituCore without Terminal."
