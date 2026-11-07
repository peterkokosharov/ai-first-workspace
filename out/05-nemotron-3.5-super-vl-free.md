# Review — nemotron-3.5-super-vl-free

## Summary
The document defines a portable, self-contained workspace: an inventory model, six governing rules, and a secret manager with native OS backends plus a file export. It is largely internally consistent and candid about known issues, but the export-file contract contradicts itself (§5.3 vs §5.5) and secret transport has no encryption. The portability claim rests on a secrets mechanism that is not yet fully specified.

## Strengths
- The key-path scheme (`provider/scope/kind`, §5.1) is sound: it prevents collisions between personal and project credentials, scales by adding scope levels, and doubles as a Windows Credential Manager target name.
- Keeping values out of the archive, git, and project files (§3 principle 3, §5.3) is correct; `~/SECRETS` lives outside the project.
- CLI hygiene is good: `set` reads from stdin (§5.4), writes are atomic at mode `600` (§5.3, §5.6), and `list` never prints values.
- The phased roadmap lets phase 1 start without the uncertain KWallet probe (§9).

## Weaknesses
- §5.3 defines `~/SECRETS` with `KEY_PATH | value` lines, while §5.5 step 5 writes `secrets-import.txt` with `KEY_PATH = value` lines: two paths and two formats for one export.
- The security risk not addressed is interception of the plaintext export file: it has mode `600` only, no encryption or integrity check, and the transfer channel is unspecified ("separately transferred," §5.5 step 4).
- `~/github_token` with mode `664` (§8) is a secret file the manager never touches, contradicting §5.3's claim that `~/SECRETS` is the only values file.
- Over-engineering: five native backends (§5.2) for two machines (§4.1); macOS and Mint/GNOME have no machine, and the DCOP probe precedes any need despite §10's own warning.
- `.tmp/` is never cleaned before archiving, so the "no file left behind" criterion (§1) can fail.

## Gaps
- OpenCode is excluded from the archive (§6), but nothing specifies how its provider/model configuration is recreated; `INVENTORY.md` (§4) is not agent configuration.
- No archive verification (manifest or checksums) after unpack; §6 verification covers only secrets and tests.
- SSH and GPG scope is open (§12 Q5); `.gitignore` excludes only `.tmp/` (§3).
- Export backup frequency (§12 Q6) and KWallet wallet name/unlock (§12 Q1) are undecided, yet phase 2 depends on them.
- The layout lacks `assets/fonts/` (§3) despite the Cyrillic-font rule (§4.2), and no lockfile exists despite the restorable-dependencies promise (§3).

## Recommendations
1. First, unify the export contract: one path, one format for `export`/`import` and first-run import, plus a defined machine-to-machine transfer channel.
2. Encrypt the export file, or at least add an explicit warning and an integrity check, since it carries every value in plaintext.
3. Remove the macOS and Mint/GNOME backends until a machine needs them.
4. Add `.tmp/` cleanup before archiving and close the SSH/GPG scope question.

## Verdict
6 — Coherent and honest, but the contradictory, unencrypted export contract undermines both portability and security; fix the export mechanism before trusting the workspace on another machine.
