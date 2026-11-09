# Audit before a release or tag

Goal: no tag without an independent audit of everything since the last tag.
On Windows type `py` instead of `python3`.

## Steps
1. Find the last tag: `git describe --tags --abbrev=0`.
   - No tag yet: the audit covers the whole tree (`git ls-files`).
2. Collect what changed:
   - `git log --oneline <lasttag>..HEAD`
   - `git diff --stat <lasttag>`
3. Run the checks yourself and keep the output:
   - Secret scan: `python3 tools/secret_scan.py --all` (must print no finding).
   - Tests: `python3 -m unittest discover -s tools/tests -t . -v` (must pass).
4. Pick the strongest model you can use as auditor. It must not be the model that wrote
   the code. Start it as in docs/procedures/step-review.md, step 4.
5. Give the auditor this prompt (fill in the tag):
   ```text
   Audit this folder for a release. Changes since <lasttag>: run
   `git log <lasttag>..HEAD` and `git diff <lasttag>` (no tag: read all tracked files).
   Do not edit, create or delete any file. Check:
   1. No key, token or password in any file.
   2. Code matches its docs; README and INSTALL steps are true.
   3. AGENTS.md and docs/procedures/ match the real tools.
   List each finding as file:line - problem - fix - PASS or FAIL.
   End with one line: PASS or FAIL.
   ```
6. Save the answer in `out/audit-<YYYY-MM-DD>.md` (out/ is not in git).
7. Any FAIL blocks the release. Fix it (review + commit), then audit again.
8. All PASS: ask the user "Shall I create tag vX.Y.Z?".
   Only a reply that starts with "да" or "yes" confirms it.
9. Create the tag locally: `git tag vX.Y.Z`.
10. Do not push the tag. Tell the user it is ready: docs/procedures/github-deploy.md.
