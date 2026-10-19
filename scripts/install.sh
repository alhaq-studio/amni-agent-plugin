#!/usr/bin/env bash
# Amni Ecosystem Plugin Installer & Updater for macOS / Linux
# Alhaq Studio (alhaq.uk) - Zero-Emoji Compliant

set -e

PLUGIN_DIR="${HOME}/.agents/plugins/amni-ecosystem"
REPO_URL="https://github.com/alhaq-studio/amni-agent-plugin.git"

echo "[INFO] Installing / Updating Amni Ecosystem Plugin for Alhaq Studio..."

if [ -d "${PLUGIN_DIR}/.git" ]; then
    echo "[INFO] Existing git repository found at ${PLUGIN_DIR}. Pulling latest updates..."
    git -C "${PLUGIN_DIR}" pull --ff-only
elif [ -d "${PLUGIN_DIR}" ]; then
    echo "[WARNING] Directory ${PLUGIN_DIR} exists but is not a git repository."
    BACKUP_DIR="${PLUGIN_DIR}.bak.$(date +%Y%m%d%H%M%S)"
    mv "${PLUGIN_DIR}" "${BACKUP_DIR}"
    echo "[INFO] Backed up to ${BACKUP_DIR}. Cloning fresh..."
    git clone "${REPO_URL}" "${PLUGIN_DIR}"
else
    echo "[INFO] Cloning ${REPO_URL} to ${PLUGIN_DIR}..."
    mkdir -p "$(dirname "${PLUGIN_DIR}")"
    git clone "${REPO_URL}" "${PLUGIN_DIR}"
fi

# Update ~/.gemini/config/plugins.json if jq / python is available
CONFIG_DIR="${HOME}/.gemini/config"
PLUGINS_CONFIG="${CONFIG_DIR}/plugins.json"

mkdir -p "${CONFIG_DIR}"

if [ ! -f "${PLUGINS_CONFIG}" ]; then
    cat <<EOF > "${PLUGINS_CONFIG}"
{
  "entries": [
    {
      "path": "${PLUGIN_DIR}"
    }
  ]
}
EOF
    echo "[INFO] Created ${PLUGINS_CONFIG} with plugin registration"
fi

echo "[OK] Amni Ecosystem Plugin successfully installed and synchronized."
echo "[INFO] Location: ${PLUGIN_DIR}"

