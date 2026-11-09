# Publish to GitHub

Goal: put local commits on GitHub. The agent may push only after the user confirms
(AGENTS.md, "Confirmation"). Steps marked HUMAN are done by the user only.

## Agent steps
1. Run `git status`. It must say "nothing to commit, working tree clean".
   If not: follow docs/procedures/commit.md first.
2. Run `git branch --show-current`. Note the branch name.
3. Run `git remote -v`. Note where `origin` points. Read `git.remote_url` and
   `git.remote_user` in `settings.json` (copy of `settings.json.example`). If
   `remote_url` is set and `origin` points elsewhere, stop and tell the user; do not
   change the remote yourself. Empty values: use `origin` as it is.
4. Run `git log --oneline origin/<branch>..HEAD` to list what will be pushed.
   If that fails, the branch is not on GitHub yet: run `git log --oneline` (all
   commits will be pushed) and say so.
5. Show the user: the branch, the list of commits, and the exact command
   `git push origin <branch>` (with the real branch name; add `-u` if the branch
   is not on GitHub yet).
6. Ask: "Shall I run this push?" Stop and wait.
7. Confirmed: run exactly the command you showed. Not confirmed: do not push.
   The user may also run the command by hand (see below).
8. If the pre-push hook blocks the push: a commit to be pushed holds a key. A new
   commit that removes it does not help: the old commit would still be published.
   Stop and tell the user: the history must be cleaned first (only on the user's
   order), and the key must be replaced (revoke it, store the new one with
   tools/secret.py).
9. If git asks for a user name or password, stop: the HUMAN steps below are not done.
10. Tag (after docs/procedures/release-audit.md): the same steps with the tag name.
    In step 4 run `git log --oneline -1 <tag>`, in step 5 show
    `git push origin <tag>`. Push one tag at a time, never `--tags`.

## HUMAN: once per clone
1. A fresh clone points `origin` to the author's repository. Create your own empty
   repository on GitHub, then point `origin` to it:
   `git remote set-url origin https://github.com/<you>/<repo>.git`
2. Check: `git remote -v`.
3. Write the same URL and your GitHub user name into `settings.json`:
   `"git": {"remote_url": "...", "remote_user": "...", "token_key": "personal/<repo>/github_token"}`.
   `token_key` only names the token (INSTALL.md, "Key names"); the value stays with git.

## HUMAN: once per machine
1. Create a Personal Access Token (PAT) on github.com:
   Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens.
   Give it access to your repository only (Contents: read and write).
2. Let git's credential helper keep it in the OS store (never in a plain file):
   - Windows: `git config --global credential.helper manager`
     (Git Credential Manager, ships with Git for Windows; the PAT goes to Windows
     Credential Manager).
   - Linux Mint / Ubuntu: `git config --global credential.helper
     /usr/share/doc/git/contrib/credential/libsecret/git-credential-libsecret`
     (GNOME Keyring; build the helper once, see INSTALL.md "What the machine needs").
   - Last fallback only, if libsecret cannot be built:
     `git config --global credential.helper 'cache --timeout=3600'` (memory, one hour).
   - Never `credential.helper store`: it writes the token in plain text to `~/.git-credentials`.
3. git uses this helper, not tools/secret.py. Do not store the PAT with secret.py;
   git never reads it from there. The inventory row (`inventory.py key github`) only
   names it and says "managed by git credential helper, not secret.py".

## Push by hand (instead of agent steps 6-7)
1. Run the line the agent showed: `git push origin <branch>`.
2. When git asks: username = your GitHub user name, password = the PAT
   (not your GitHub login password).
3. Tags are pushed only on purpose, the same way: `git push origin <tag>`.
