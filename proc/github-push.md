# Push to GitHub

This project is hosted at `https://github.com/peterkokosharov/ai-first-workspace.git`.

## Prerequisites

You need a GitHub **Personal Access Token (PAT)** with `repo` scope:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained personal access tokens
2. Create a new token with `repo` scope (read and write repository contents)
3. Copy it — you won't see it again

## Store the token

The key path `github/personal/token` must exist in the inventory database and in your OS native credential store:

```bash
python3 tools/inventory.py init          # ensure database exists
python3 tools/secret.py --backend auto set github/personal/token
```

Enter your PAT when prompted. It will be stored in your OS native credential store (Keychain, secret-tool, KWallet, DCOP on Q4OS).

## Push

```bash
git push origin main
```

Git will ask for:
- **Username:** `peterkokosharov`
- **Password:** your **Personal Access Token** (not your GitHub login password)

## Never type the token again

Run once:

```bash
git config --global credential.helper store
```

After the first successful push, Git will cache the token locally.

## Never commit tokens

Never write a PAT into any project file. `data/inventory.db` is gitignored and never committed.
