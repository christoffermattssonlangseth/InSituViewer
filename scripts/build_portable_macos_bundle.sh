#!/usr/bin/env bash
set -euo pipefail

# Build a portable macOS bundle:
# - InSituCore-portable/
#   - InSituCore/            (project copy)
#   - InSituCore.app/        (double-click launcher)
#   - InSituCore.log         (runtime log)
#
# Optional:
#   --zip  -> create InSituCore-portable.zip next to the bundle directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUT_DIR="${1:-${REPO_ROOT}/dist}"
MAKE_ZIP="${2:-}"

APP_NAME="InSituCore"
BUNDLE_ROOT="${OUT_DIR}/${APP_NAME}-portable"
PROJECT_DIR="${BUNDLE_ROOT}/${APP_NAME}"
APP_PATH="${BUNDLE_ROOT}/${APP_NAME}.app"
VENV_DIR="${PROJECT_DIR}/.venv"
ICON_ICNS="${PROJECT_DIR}/assets/InSituCore.icns"
ICON_GEN_SCRIPT="${PROJECT_DIR}/scripts/generate_macos_icon.py"
ENV_YML="${PROJECT_DIR}/environment.yml"

if ! command -v osacompile >/dev/null 2>&1; then
  echo "osacompile not found. This script is macOS-only." >&2
  exit 1
fi

if ! command -v rsync >/dev/null 2>&1; then
  echo "rsync not found. Please install rsync first." >&2
  exit 1
fi

mkdir -p "${OUT_DIR}"
rm -rf "${BUNDLE_ROOT}"
mkdir -p "${BUNDLE_ROOT}"

echo "Copying project..."
rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'dist' \
  "${REPO_ROOT}/" "${PROJECT_DIR}/"

if [[ -f "${ENV_YML}" ]]; then
  cp "${ENV_YML}" "${BUNDLE_ROOT}/environment.yml"
fi

if [[ ! -f "${ICON_ICNS}" && -f "${ICON_GEN_SCRIPT}" ]]; then
  python3 "${ICON_GEN_SCRIPT}" || true
fi

echo "Creating virtual environment..."
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt"
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements-optional.txt" || true
"${VENV_DIR}/bin/pip" install PySide6-QtWebEngine || true

echo "Creating app launcher..."
TMP_AS="$(mktemp)"
cat > "${TMP_AS}" <<'EOF'
ObjC.import("Foundation");
var app = Application.currentApplication();
app.includeStandardAdditions = true;
var bundlePath = $.NSBundle.mainBundle.bundlePath.js;
var launchPath = bundlePath + "/Contents/Resources/launch_insitucore.sh";
app.doShellScript('"' + launchPath.replace(/"/g, '\\"') + '" >/dev/null 2>&1 &');
EOF

osacompile -l JavaScript -o "${APP_PATH}" "${TMP_AS}"
rm -f "${TMP_AS}"

mkdir -p "${APP_PATH}/Contents/Resources"
cat > "${APP_PATH}/Contents/Resources/launch_insitucore.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
PROJECT_DIR="${BUNDLE_ROOT}/InSituCore"
LOG_FILE="${BUNDLE_ROOT}/InSituCore.log"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python"

cd "${PROJECT_DIR}"
exec "${PYTHON_BIN}" -m app.main >>"${LOG_FILE}" 2>&1
EOF
chmod +x "${APP_PATH}/Contents/Resources/launch_insitucore.sh"

if [[ -f "${PROJECT_DIR}/assets/logo.png" ]]; then
  cp "${PROJECT_DIR}/assets/logo.png" "${APP_PATH}/Contents/Resources/logo.png"
fi
if [[ -f "${ICON_ICNS}" ]]; then
  cp "${ICON_ICNS}" "${APP_PATH}/Contents/Resources/applet.icns"
fi

if [[ "${MAKE_ZIP}" == "--zip" ]]; then
  echo "Creating zip archive..."
  (cd "${OUT_DIR}" && rm -f "${APP_NAME}-portable.zip" && zip -qry "${APP_NAME}-portable.zip" "${APP_NAME}-portable")
  echo "Created: ${OUT_DIR}/${APP_NAME}-portable.zip"
fi

echo "Done."
echo "Bundle: ${BUNDLE_ROOT}"
echo "App:    ${APP_PATH}"
echo "Run by double-clicking InSituCore.app"
