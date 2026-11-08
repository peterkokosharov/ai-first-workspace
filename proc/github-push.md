# Push to GitHub

This project is hosted at the remote URL defined in `settings.json`:

```json
{
  "remote": {
    "origin": "https://github.com/peterkokosharov/ai-first-workspace.git"
  }
}
```

Before you can push, you need a GitHub **Personal Access Token (PAT)** with `repo` scope:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained personal access tokens
2. Create a new token with `repo` scope
3. Copy it — you won't see it again

## Store the token

The key path `github/personal/token` must exist in the inventory database and in your OS native credential store:

```bash
python3 tools/inventory.py init          # create database if missing
python3 tools/secret.py --backend auto set github/personal/token
```

Enter your PAT when prompted. It will be stored in your OS native credential store (Keychain, secret-tool, KWallet, TDE DCOP).

## Push

```bash
git add .
git commit -m "your commit message"
git push origin main
```

Git will ask for:
- **Username:** `peterkokosharov` (or your GitHub username)
- **Password:** your **Personal Access Token** (not your GitHub login password)

## Never type the token again

Run once:

```bash
git config --global credential.helper store
```

After the first successful push, Git will cache the token locally.

## Never commit tokens

Never write a PAT into any project file. `data/inventory.db` is gitignored and never committed.

## Change the remote URL

If you fork this project and push to your own GitHub account:

```bash
git remote set-url origin https://github.com/your-username/ai-first-workspace.git
```

And update `settings.json`:

```json
{
  "remote": {
    "origin": "https://github.com/your-username/ai-first-workspace.git"
  }
}
```

Replace `your-username` with your GitHub username.

## New machine setup

1. `git clone https://github.com/peterkokosharov/ai-first-workspace.git`
2. `cd ai-first-workspace`
3. `python3 tools/autodiscovery.py`
4. `python3 tools/inventory.py init`
5. `python3 tools/secret.py --backend auto set github/personal/token`
6. `python3 tools/ping_direct.py nvidia nemotron-3-5-bolt-e4b "hi"` — optional test