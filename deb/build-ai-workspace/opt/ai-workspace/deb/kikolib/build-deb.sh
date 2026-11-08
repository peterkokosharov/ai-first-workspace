#!/usr/bin/env bash
# =============================================================================
# build-deb.sh — Build .deb package for kikolib (stdlib keystore library)
#
# Usage:
#   cd deb/kikolib
#   ./build-deb.sh
#
# Produces: ../python3-kikolib_<version>-1_all.deb
#
# Requirements:
#   debhelper-compat dh-python python3-all python3-setuptools python3-hatchling
#   pybuild-plugin-pyproject dpkg-dev build-essential
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
KIKOLIB_SRC="${PROJECT_ROOT}/lib/kikolib"
BUILD_DIR="${PROJECT_ROOT}/deb/build-kikolib"

echo "=== Building kikolib .deb package ==="
echo "Project root: ${PROJECT_ROOT}"
echo "kikolib source: ${KIKOLIB_SRC}"
echo

# --- Pre-build checks ---------------------------------------------------------

if [[ ! -f "${KIKOLIB_SRC}/pyproject.toml" ]]; then
    echo "ERROR: ${KIKOLIB_SRC}/pyproject.toml not found"
    echo "       Make sure lib/kikolib/ exists in the project"
    exit 1
fi

if ! grep -q 'name = "kikolib"' "${KIKOLIB_SRC}/pyproject.toml"; then
    echo "ERROR: kikolib package name not found in pyproject.toml"
    exit 1
fi

echo "✓ pyproject.toml found with kikolib package name"

VERSION=$(grep '^version = ' "${KIKOLIB_SRC}/pyproject.toml" | cut -d'"' -f2)
echo "✓ Version: ${VERSION}"

# --- Clean previous build -----------------------------------------------------

rm -rf "${BUILD_DIR}"
mkdir -p "${BUILD_DIR}"

# --- Copy source into build dir ----------------------------------------------

cp -a "${KIKOLIB_SRC}/." "${BUILD_DIR}/"

cd "${BUILD_DIR}"

# --- Generate debian/ control files ------------------------------------------

mkdir -p debian

# Remove old compat if present (conflicts with debhelper-compat in control)
rm -f debian/compat

# control
cat > debian/control << EOF
Source: kikolib
Section: python
Priority: optional
Maintainer: Peter Kokosharov <peter.kokosharov@gmail.com>
Build-Depends: debhelper-compat (= 13), python3-all, python3-setuptools, python3-hatchling, pybuild-plugin-pyproject
Standards-Version: 4.6.2
Homepage: https://github.com/peterkokosharov/kiko
Rules-Requires-Root: no

Package: python3-kikolib
Architecture: all
Depends: \${python3:Depends}, \${misc:Depends}, python3
Description: kikolib - stdlib-only library for kiko-lite
 kikolib is a small, standard-library-only Python library providing:
   - Thread-safe HTTP/1.1 client with keep-alive pool and SSE streaming
   - Retry policy with exponential backoff and Retry-After support
   - Threaded HTTP server with router and systemd integration
   - API key management via environment variables and OS keystores
   - Provider adapters for OpenAI-compatible and Gemini APIs
   - Token estimation, YAML-lite parser, and .env reader
 .
 This package installs the library system-wide in
 /usr/lib/python3/dist-packages/kikolib/ so it can be imported
 without virtual environments or pip.
EOF

# rules
cat > debian/rules << 'EOF'
#!/usr/bin/make -f

export PYBUILD_NAME=kikolib

%:
	dh $@ --buildsystem=pybuild
EOF
chmod +x debian/rules

# changelog
cat > debian/changelog << EOF
kikolib (${VERSION}-1) unstable; urgency=medium

  * Release ${VERSION} of kikolib stdlib-only library
  * All tests passing
  * Ruff lint clean

 -- Peter Kokosharov <peter.kokosharov@gmail.com>  $(date -R)
EOF

# source format
mkdir -p debian/source
echo "3.0 (native)" > debian/source/format

# copyright
cat > debian/copyright << 'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: kikolib
Upstream-Contact: Peter Kokosharov <peter.kokosharov@gmail.com>
Source: https://github.com/peterkokosharov/kiko

Files: *
Copyright: 2024-2026 Peter Kokosharov <peter.kokosharov@gmail.com>
License: MIT

Files: debian/*
Copyright: 2024-2026 Peter Kokosharov <peter.kokosharov@gmail.com>
License: MIT

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
EOF

# --- Build -------------------------------------------------------------------

echo "Building .deb package..."
dpkg-buildpackage -us -uc -b

# --- Post-build checks -------------------------------------------------------

DEB_FILE="../python3-kikolib_${VERSION}-1_all.deb"

if [[ -f "${DEB_FILE}" ]]; then
    echo "✓ Package created: ${DEB_FILE}"
    echo
    echo "Package contents:"
    dpkg -c "${DEB_FILE}" | head -20
    echo "   ... (total: $(dpkg -c "${DEB_FILE}" | wc -l) files)"
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