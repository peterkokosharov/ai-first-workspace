# Commit at a milestone

Goal: save finished work as a local git commit. A human pushes later.

## A milestone is
- The tests pass: `python3 -m unittest discover -s tools/tests -t . -v`
  (on Windows: `py -m unittest discover -s tools/tests -t . -v`).
- The review passed (docs/procedures/step-review.md).

## Steps
1. Run `git status`.
2. Check the list against the "Git" rules in AGENTS.md (files that never go into git).
3. Add the files of this step by name: `git add <file1> <file2>`.
   Never use `git add .` or `git add -A`.
4. Run `git diff --cached --stat` and check the list again.
5. Commit with a short English message:
   `git commit -m "<area>: <what changed>"`
   Put the review result in the message body, e.g. `Review: PASS (<model>)`.
6. If the pre-commit hook blocks the commit:
   - It found a key or token. The value is not printed; the file name is.
   - Remove the key from that file. Keys belong in the OS store (tools/secret.py).
   - Add the file again and commit again.
   - Never use `--no-verify`.
7. Run `git log --oneline -1` and check the commit is there.
8. Tell the user: "Commit <hash> is ready. Publishing: docs/procedures/github-deploy.md".

## Never
- Never `git push`. A human pushes.
- Never rewrite history (`git commit --amend` on a pushed commit, `git rebase`, `git reset --hard`)
  without an order from the user.
