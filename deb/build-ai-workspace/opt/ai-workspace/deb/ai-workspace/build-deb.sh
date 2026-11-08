#!/usr/bin/env bash
# =============================================================================
# build-deb.sh — Build .deb package for ai-workspace (portable dev studio)
#
# Usage:
#   cd deb/ai-workspace
#   ./build-deb.sh
#
# Produces: ../ai-workspace_<version>-1_all.deb
#
# Installs:
#   /usr/local/bin/secret.py        -> python3 tools/secret.py wrapper
#   /usr/local/bin/inventory.py     -> python3 tools/inventory.py wrapper
#   /usr/local/bin/autodiscovery.py -> python3 tools/autodiscovery.py wrapper
#   /usr/local/bin/ping_direct.py   -> python3 tools/ping_direct.py wrapper
#   /usr/local/bin/setup_providers.py -> python3 tools/setup_providers.py wrapper
#   /opt/ai-workspace/               -> full project tree
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BUILD_DIR="${PROJECT_ROOT}/deb/build-ai-workspace"

echo "=== Building ai-workspace .deb package ==="
echo "Project root: ${PROJECT_ROOT}"
echo

# --- Pre-build checks --------------------------------------------------------

if [[ ! -f "${PROJECT_ROOT}/AGENTS.md" ]]; then
    echo "ERROR: AGENTS.md not found in project root"
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/tools/secret.py" ]]; then
    echo "ERROR: tools/secret.py not found"
    exit 1
fi

VERSION="0.1.0"
echo "✓ Version: ${VERSION}"

# --- Clean previous build ----------------------------------------------------

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}/usr/local/bin"
mkdir -p "${BUILD_DIR}/opt/ai-workspace"

# --- Copy project files ------------------------------------------------------

# Copy everything except .git, __pycache__, .tmp, out, data/inventory.db
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
      --exclude='.tmp' --exclude='out' --exclude='data/inventory.db' \
      "${PROJECT_ROOT}/" "${BUILD_DIR}/opt/ai-workspace/"

# Make Python tools executable
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/secret.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/inventory.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/autodiscovery.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/ping_direct.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/ping.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/setup_providers.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/robota.py"
chmod +x "${BUILD_DIR}/opt/ai-workspace/tools/gen_models_xml.py"

# --- Create wrapper scripts in /usr/local/bin --------------------------------

cat > "${BUILD_DIR}/usr/local/bin/secret.py" << 'EOF'
#!/usr/bin/env bash
exec python3 /opt/ai-workspace/tools/secret.py "$@"
EOF
chmod +x "${BUILD_DIR}/usr/local/bin/secret.py"

cat > "${BUILD_DIR}/usr/local/bin/inventory.py" << 'EOF'
#!/usr/bin/env bash
exec python3 /opt/ai-workspace/tools/inventory.py "$@"
EOF
chmod +x "${BUILD_DIR}/usr/local/bin/inventory.py"

cat > "${BUILD_DIR}/usr/local/bin/autodiscovery.py" << 'EOF'
#!/usr/bin/env bash
exec python3 /opt/ai-workspace/tools/autodiscovery.py "$@"
EOF
chmod +x "${BUILD_DIR}/usr/local/bin/autodiscovery.py"

cat > "${BUILD_DIR}/usr/local/bin/ping_direct.py" << 'EOF'
#!/usr/bin/env bash
exec python3 /opt/ai-workspace/tools/ping_direct.py "$@"
EOF
chmod +x "${BUILD_DIR}/usr/local/bin/ping_direct.py"

cat > "${BUILD_DIR}/usr/local/bin/setup_providers.py" << 'EOF'
#!/usr/bin/env bash
exec python3 /opt/ai-workspace/tools/setup_providers.py "$@"
EOF
chmod +x "${BUILD_DIR}/usr/local/bin/setup_providers.py"

# --- Debian control files ----------------------------------------------------

mkdir -p "${BUILD_DIR}/DEBIAN"

cat > "${BUILD_DIR}/DEBIAN/control" << EOF
Package: ai-workspace
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: all
Maintainer: Peter Kokosharov <peter.kokosharov@gmail.com>
Depends: python3 (>= 3.10), python3-kikolib
Installed-Size: $(du -sk "${BUILD_DIR}/opt" | cut -f1)
Description: Portable AI-assisted development workspace
 A self-contained, portable folder for AI-assisted software development.
 The folder itself is the product: rules, inventory, tooling and
 configuration live here. It can be archived, moved to another machine,
 unpacked and continued without missing pieces.
 .
 Provides command-line tools: secret.py, inventory.py, autodiscovery.py,
 ping_direct.py, setup_providers.py, robota.py, gen_models_xml.py.
Homepage: https://github.com/peterkokosharov/default-project
EOF

cat > "${BUILD_DIR}/DEBIAN/postinst" << 'EOF'
#!/usr/bin/env bash
set -e
echo "ai-workspace installed at /opt/ai-workspace/"
echo "Tools available: secret.py, inventory.py, autodiscovery.py, ping_direct.py"
echo ""
echo "Quick start:"
echo "  cd /opt/ai-workspace"
echo "  python3 tools/inventory.py init"
echo "  python3 tools/autodiscovery.py"
echo ""
EOF
chmod +x "${BUILD_DIR}/DEBIAN/postinst"

# --- Build -------------------------------------------------------------------

dpkg-deb --build "${BUILD_DIR}" "${PROJECT_ROOT}/deb/ai-workspace_${VERSION}-1_all.deb"

DEB_FILE="${PROJECT_ROOT}/deb/ai-workspace_${VERSION}-1_all.deb"

if [[ -f "${DEB_FILE}" ]]; then
    echo "✓ Package created: ${DEB_FILE}"
    echo
    echo "Package info:"
    dpkg -I "${DEB_FILE}"
else
    echo "ERROR: Package file not found at ${DEB_FILE}"
    exit 1
fi

echo
echo "=== ALL DONE ==="
echo "Install on target machine:"
echo "  sudo dpkg -i ${DEB_FILE}"
echo "  sudo apt-get install -f   # pull missing dependencies"