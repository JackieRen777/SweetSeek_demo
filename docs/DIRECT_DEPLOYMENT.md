# Direct production deployment

SweetSeek production deployment does not require GitHub connectivity. Git is
still the version boundary: every production release must be a clean local
commit, while pushing that commit to `origin` may happen later.

## Release contract

1. Review the working tree and commit the exact version intended for production.
2. Run the backend suite, frontend suite, and production frontend build.
3. Build immutable source, frontend, dependency-lock, and SweetMeta assets.
4. Upload the checksummed assets to `/www/sweetseek/incoming/<commit>` by rsync.
5. Start the durable server-side deployment with `--source-mode local`.
6. Reuse persistent indexes and data, start the candidate on port 5002, and
   verify RAG, prediction, MD Builder, SweetMeta classifications/evidence, and
   SweetMeta statistics before switching traffic.
7. Atomically activate the release, repeat the production checks, and start the
   existing background observation. Any activation failure requests rollback.
8. Push the already-deployed commit to GitHub when network access is available.

## Commands

Build and test without uploading or changing production:

```bash
bash scripts/maintenance/deploy/deploy_from_local.sh --build-only
```

Build, upload, activate, verify, and observe:

```bash
bash scripts/maintenance/deploy/deploy_from_local.sh
```

The script refuses uncommitted production changes. Local research changes may
remain in the working tree. The source archive is produced from `HEAD`, with
`Experiment/`, `evaluation/`, test files, experimental `services/sweet_*`
modules, local UI snapshots, and the experiment document-generation script
explicitly excluded. These exclusions apply even to already tracked files.
Local databases, indexes, credentials and dependency directories are not sent.

The GitHub workflow remains available as a secondary deployment path. A local
release is not considered fully backed up until its commit has later been
pushed to `origin/main`.
