# ECS Git deployment

This release path deploys one exact, CI-verified commit from `main`. The legacy
Gate 1/Gate 2 upload workflow is not used.

## Preconditions

- Local Python 3.10 recovery, tests, production frontend build, and the
  30-minute local observation have passed.
- The full 40-character commit is on `origin/main`.
- GitHub Actions has published the prerelease `deploy-<commit>`.
- Port 5001 remains occupied by the current production service until the
  port-5002 canary passes.
- The four verified 512-dimensional indexes already exist under
  `/www/sweetseek/indexes`; they are not uploaded again.

## Workbench command

Run the version of the deployer from the exact commit being deployed. The
first invocation is read-only; only a successful preflight may start the
background deployment:

```bash
COMMIT=<40-character-main-sha>
curl -fL --retry 3 \
  "https://raw.githubusercontent.com/JackieRen777/SweetSeek_demo/${COMMIT}/scripts/maintenance/deploy/deploy_from_git.sh" \
  -o "/tmp/sweetseek-deploy-${COMMIT}.sh" && \
chmod 700 "/tmp/sweetseek-deploy-${COMMIT}.sh" && \
bash "/tmp/sweetseek-deploy-${COMMIT}.sh" --commit "${COMMIT}" --preflight-only && \
bash "/tmp/sweetseek-deploy-${COMMIT}.sh" --commit "${COMMIT}" --background
```

Workbench may disconnect after `DEPLOYMENT_STARTED` is printed. Inspect the
background task without attaching to it:

```bash
systemctl status "sweetseek-deploy-${COMMIT:0:12}.service" --no-pager -l
journalctl -u "sweetseek-deploy-${COMMIT:0:12}.service" --no-pager -n 40
```

The script downloads and verifies the CI assets, creates or reuses the Linux
web environment, validates the four indexes, runs the canary and fixed RAG
questions, then atomically switches production. Structure tools remain
disabled and no Docking worker or engine is installed.

After activation, a background two-hour observation records five samples at
30-minute intervals. Any 502, OOM, RAG failure, or service restart triggers
the commit-scoped rollback script. Reports are written to
`/www/sweetseek/shared/reports/<commit>`.
