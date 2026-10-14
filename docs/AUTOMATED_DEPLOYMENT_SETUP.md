# Automated Deployment Setup

This document explains how to configure automated deployment from GitHub Actions to your production server.

## Overview

When you push to `main` branch:
1. ✅ GitHub Actions runs tests and builds frontend
2. ✅ Creates a release with deployment assets
3. 🚀 **NEW**: Automatically SSH to server and runs deployment script

---

## Required GitHub Secrets

Go to your repository settings and add these secrets:
**Settings → Secrets and variables → Actions → New repository secret**

### 1. `DEPLOY_SSH_KEY`
The private SSH key that can connect to your server as the deploy user.

**How to generate:**
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/sweetseek_deploy_key

# Copy the private key (this goes to GitHub Secrets)
cat ~/.ssh/sweetseek_deploy_key

# Copy the public key to your server
ssh-copy-id -i ~/.ssh/sweetseek_deploy_key.pub your-user@your-server
```

**Value**: Paste the entire private key including header/footer:
```
-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----
```

---

### 2. `DEPLOY_SSH_HOST`
Your production server's hostname or IP address.

**Example**: `sweetseek.example.com` or `123.456.789.0`

---

### 3. `DEPLOY_SSH_USER`
The SSH user that has permission to run the deployment script with sudo.

**Example**: `deploy` or `ubuntu` or your server username

**Important**: This user must be able to run:
```bash
sudo bash /tmp/deploy-*.sh --commit <COMMIT_SHA>
```

without entering a password. Add to `/etc/sudoers.d/deploy`:
```
# Allow CI automated deployment from GitHub-downloaded scripts
deploy ALL=(ALL) NOPASSWD: /bin/bash /tmp/deploy-*.sh*
```

**Why this configuration:**
- CI downloads the deployment script directly from GitHub to `/tmp/deploy-<commit>.sh`
- This ensures the script version matches exactly the code being deployed
- The wildcard pattern `/tmp/deploy-*.sh*` allows any commit hash
- Security: The script comes from your official GitHub repository

---

## Testing the Setup

### Manual Test
After adding secrets, test the SSH connection and deployment flow:

```bash
# From your local machine, test downloading and executing the deploy script
COMMIT=$(git ls-remote https://github.com/JackieRen777/SweetSeek_demo.git refs/heads/main | awk '{print $1}')

ssh -i ~/.ssh/sweetseek_deploy_key deploy@your-server \
  "curl -fsSL --retry 3 \
    'https://raw.githubusercontent.com/JackieRen777/SweetSeek_demo/${COMMIT}/scripts/maintenance/deploy/deploy_from_git.sh' \
    -o '/tmp/deploy-${COMMIT}.sh' && \
   chmod 700 '/tmp/deploy-${COMMIT}.sh' && \
   sudo bash '/tmp/deploy-${COMMIT}.sh' --commit ${COMMIT}"
```

### Automated Test
Push a small change to `main`:
```bash
git commit --allow-empty -m "test: trigger automated deployment"
git push origin main
```

Watch the deployment at:
https://github.com/JackieRen777/SweetSeek_demo/actions

---

## Workflow Details

The new `deploy` job in `.github/workflows/ci.yml`:
- Only runs on `main` branch pushes (not PRs)
- Waits for tests and release to succeed
- Uses secrets to SSH to server
- Executes deployment script with commit SHA
- Reports success/failure in Actions log

---

## Security Notes

- ✅ Private key is encrypted in GitHub Secrets
- ✅ Only runs on `main` branch (protected)
- ✅ Deployment script has built-in safety checks
- ✅ Canary testing happens before production cutover
- ✅ Automatic rollback on failure

---

## Disabling Auto-Deploy

To disable automated deployment but keep tests:

1. Comment out the `deploy` job in `.github/workflows/ci.yml`
2. Or remove the GitHub Secrets (deployment will fail silently)

Manual deployment still works:
```bash
ssh your-server "sudo bash /www/sweetseek/repo.git/../scripts/maintenance/deploy/deploy_ecs_oneclick.sh --commit <SHA>"
```

---

## Troubleshooting

### "Permission denied (publickey)"
- Check `DEPLOY_SSH_KEY` is the complete private key
- Verify public key is in `~/.ssh/authorized_keys` on server
- Check `DEPLOY_SSH_USER` and `DEPLOY_SSH_HOST` are correct

### "sudo: command not found" or permission error
- Add deploy user to sudoers (see setup instructions above)
- Verify script path is correct on server

### Deployment script fails
- Check GitHub Actions logs for details
- Script has preflight checks (disk space, memory, load, etc.)
- Review `/www/sweetseek/shared/logs/` on server

---

## Next Steps

After setup is complete:
1. ✅ Add the three GitHub Secrets
2. ✅ Configure sudoers on server
3. ✅ Test with an empty commit
4. 🎉 Every push to `main` automatically deploys!
