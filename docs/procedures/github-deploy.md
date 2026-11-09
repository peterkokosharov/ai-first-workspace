# Publish to GitHub

Goal: put local commits on GitHub. **The agent never pushes.** Steps marked
HUMAN are done by the user. The agent may prepare and print the commands.

## Agent steps
1. Run `git status`. It must say "nothing to commit, working tree clean".
   If not: follow docs/procedures/commit.md first.
2. Run `git branch --show-current`. Note the branch name.
3. Run `git remote -v`. Note where `origin` points.
4. Run `git log --oneline origin/<branch>..HEAD` to list what will be published.
   (If that fails, the branch is not on GitHub yet; say so.)
5. Print the push line for the user, with the real branch name:
   `git push origin <branch>`
6. Stop. Wait for the user.

## HUMAN: once per clone
1. A fresh clone points `origin` to the author's repository. Create your own empty
   repository on GitHub, then point `origin` to it:
   `git remote set-url origin https://github.com/<you>/<repo>.git`
2. Check: `git remote -v`.

## HUMAN: once per machine
1. Create a Personal Access Token (PAT) on github.com:
   Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens.
   Give it access to your repository only (Contents: read and write).
2. Choose where git remembers it (never in a plain file):
   - Windows: `git config --global credential.helper manager`
     (Git Credential Manager, ships with Git for Windows; the PAT goes to Windows
     Credential Manager).
   - Linux: `git config --global credential.helper 'cache --timeout=3600'`
     (in memory for one hour).
   - Never `credential.helper store`: it writes the token in plain text to `~/.git-credentials`.
3. git uses this helper, not tools/secret.py. Do not store the PAT with secret.py
   for pushing; git never reads it from there.

## HUMAN: push
1. Run the line the agent printed: `git push origin <branch>`.
2. When git asks: username = your GitHub user name, password = the PAT
   (not your GitHub login password).
3. Tags are pushed only on purpose: `git push origin <tag>`.
