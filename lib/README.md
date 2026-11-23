# lib

Vendored libraries used by the project tools. The folder is part of the project and
travels with the archive, so the tools do not depend on a system-wide installation.

## kikolib

- Source: kikolib 0.2.0, release tag `kikolib-v0.2.0` of the author's own kiko repository (MIT; kikolib has one home there).
- Content: the complete, unmodified, pinned copy of the release folder, including its `SHA256SUMS`. Never edit it here.
- `.gitattributes` forces LF endings for `lib/kikolib/**` so the hashes stay valid on Windows.
- Check: `tools/tests/test_vendor_kikolib.py` verifies every file against `SHA256SUMS`, rejects extra files and asserts `__version__ == "0.2.0"`.
- Update: fix it in the kiko repo, release a new tag, replace the whole folder with that release (keep `SHA256SUMS`),
  change the pinned version in the test, run the tests.
- aifw does not use the HTTP client, so no HTTP backend is pinned.

`tools/secret.py` imports two modules from this copy:

- `kikolib.factory` — registration, probes and backend selection;
- `kikolib.keystore` — the native credential-store calls (WCM, Keychain,
  `secret-tool`, KWallet, TDE DCOP).

