# Push to GitHub — exact procedure

This project travels as a self-contained folder. When you clone it, the remote
origin points to `https://github.com/peterkokosharov/ai-first-workspace.git`.
You must change it to **your own GitHub username** before you can push.

## Step 0 — Prepare

```bash
cd ~/ai-first-workspace   # the folder where you cloned this project
```

Make sure you have committed locally:

```bash
git status
```

If there are modified files, commit them first:

```bash
git add .
git commit -m "your commit message"
```

## Step 1 — Change the remote URL to yours

Point `origin` at your own repository (replace `YOUR_USERNAME`):

```bash
git remote set-url origin https://github.com/YOUR_USERNAME/ai-first-workspace.git
```

Confirm:

```bash
git remote -v
```

## Step 2 — Store your secret key (Personal Access Token)

The key path `github/personal/token` must exist in the inventory database:

```bash
python3 tools/inventory.py init          # create database if missing
python3 tools/secret.py --backend auto set github/personal/token
```

Enter your PAT when prompted. It will be stored in your OS native credential store
(Keychain, secret-tool, KWallet, TDE DCOP on Q4OS).

## Step 3 — Push

```bash
git push origin main
```

Git will ask for:

- **username:** your GitHub username
- **password:** your Personal Access Token — **not** your GitHub login password

## Step 4 — Remember the token (optional)

Use the operating system's credential store, not a plain-text file:

```bash
# Windows (Git for Windows ships Git Credential Manager)
git config --global credential.helper manager
# Linux: keep the token in memory for one hour
git config --global credential.helper 'cache --timeout=3600'
```

Do not use `credential.helper store`: it writes the token in plain text to `~/.git-credentials`.

## Never commit tokens

Never write a PAT into any project file. `data/inventory.db` is gitignored and never committed.

## New machine setup

1. `git clone https://github.com/<your-username>/ai-first-workspace.git`
2. `cd ai-first-workspace`
3. `python3 tools/autodiscovery.py`
4. `python3 tools/inventory.py init`
5. `python3 tools/secret.py --backend auto set github/personal/token`
6. `git push origin main` — when you have changes to share