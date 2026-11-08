# Pushing to remote GitHub repository

## Procedure

Before pushing to a remote repository, make sure you have:

1. A **Personal Access Token (PAT)** from GitHub:
   - Go to **GitHub Settings → Developer settings → Personal access tokens → Fine-grained personal access tokens**
   - Create a new token with `repo` scope (read and write repository contents)
   - Copy the token — you won't see it again

2. **Configure your username and email** (one time per machine):

```bash
git config --global user.name "peterkokosharov"
git config --global user.email "peter.kokosharov@gmail.com"
```

3. **Push** to the remote repository:

```bash
git push origin main
```

4. **Authentication:**
   - Git will ask for **username**: enter `peterkokosharov`
   - **Password**: paste your **Personal Access Token** (not your GitHub login password)

## To avoid typing the token every time

Run once:

```bash
git config --global credential.helper store
```

The first time you push, enter your username and PAT. Git will cache them in `~/.git-credentials` and won't ask again.

## Important

- Never commit `PAT` or any secret value into the project files.
- `data/inventory.db` is gitignored — never commit it.
- If you change the remote URL, remove any embedded credentials from the URL string. Use HTTPS with `git credential.helper` or SSH keys instead.
