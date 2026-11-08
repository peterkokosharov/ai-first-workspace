# deb/ — Debian package build scripts

This folder contains build scripts for creating Debian/Ubuntu `.deb` packages
from the portable workspace.

## Structure

```
deb/
├── README.md                    # this file
├── kikolib/
│   └── build-deb.sh             # builds python3-kikolib deb from lib/kikolib/
└── ai-workspace/
    └── build-deb.sh             # builds ai-workspace deb (tools, scripts)
```

## Prerequisites

On Debian/Ubuntu/Mint/Q4OS:

```bash
sudo apt-get update -qq
sudo apt-get install -y debhelper-compat dh-python python3-all python3-setuptools \
    python3-hatchling pybuild-plugin-pyproject dpkg-dev build-essential
```

## How to build

### kikolib

```bash
cd deb/kikolib
./build-deb.sh
# produces: ../python3-kikolib_0.1.0-1_all.deb
```

### ai-workspace

```bash
cd deb/ai-workspace
./build-deb.sh
# produces: ../ai-workspace_0.1.0-1_all.deb
```

## Install on target machine

```bash
sudo dpkg -i python3-kikolib_0.1.0-1_all.deb
sudo apt-get install -f   # pull missing dependencies
sudo dpkg -i ai-workspace_0.1.0-1_all.deb
```

## Notes

- `kikolib` is installed into `/usr/lib/python3/dist-packages/kikolib/`
- `ai-workspace` installs tools into `/usr/local/bin/` and config into `/opt/ai-workspace/`
- Both packages are `Architecture: all` (pure Python)
