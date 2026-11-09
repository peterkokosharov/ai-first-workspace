# lib

Vendored libraries used by the project tools. The folder is part of the project and
travels with the archive, so the tools do not depend on a system-wide installation.

## kikolib

- Source: vendored from kikolib (the author's own MIT library)
- Copied: 2026-11-07
- License: MIT (the SPDX headers and author lines are kept in every file)
- Author: Peter Kokosharov
- Included: the Python package and its `README.md`.
- Excluded: `__pycache__`, `.pyc`, Debian packaging and build artifacts.

`tools/secret.py` imports two modules from this copy:

- `kikolib.factory` — registration, probes and backend selection;
- `kikolib.keystore` — the native credential-store calls (WCM, Keychain,
  `secret-tool`, KWallet, TDE DCOP).

The upstream README links to `docs/kikolib/INVENTORY.md`, which belongs to the kiko
repository and is not part of this project.
