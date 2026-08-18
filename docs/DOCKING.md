# Amber MD Builder docking worker

Docking is the first step at `/amber-md-builder`; legacy `/docking` URLs open
the same builder. The Flask process validates uploads and writes SQLite queue
records. It never runs Vina or LightDock itself.

## ECS installation

The production host has 2 vCPU and 3.5 GB RAM, so the worker is deliberately
single-concurrency and resource limited.

```bash
chmod +x scripts/docking/*.sh
DOCKING_VENV=/www/wwwroot/FCN_SweetSeek/.venv-docking \
  scripts/docking/install_docking.sh

sudo install -m 0644 scripts/docking/sweetseek.service.docking.conf \
  /etc/systemd/system/sweetseek.service.d/docking.conf
sudo install -m 0644 scripts/docking/sweetseek-docking-worker.service \
  /etc/systemd/system/sweetseek-docking-worker.service
sudo systemctl daemon-reload
sudo systemctl enable --now sweetseek-docking-worker
```

The API and worker must use the same `DOCKING_DATA_DIR`. Completed and failed
jobs are retained for 24 hours, with a 2 GB total storage guard. Vina is capped
at 30 minutes; LightDock is capped at 60 minutes. The systemd unit applies a
90% CPU quota, 1.2 GB memory cap and controlled swap usage.

## Runtime contract

- `POST /api/docking/jobs` queues a validated job.
- `GET /api/docking/jobs/<id>` reports queue and engine stages.
- Pose structure and complex downloads are served from persistent artifacts.
- `POST /api/md-builder/generate` resolves `docking_pose.job_id` and
  `docking_pose.id`; browsers do not send trusted pose coordinates back.

Protein-ligand jobs preserve docked MOL2 coordinates for AMBER topology and
also produce a merged complex PDB for inspection. Protein-protein partner chain
IDs are normalized before LightDock so the selected complex can be passed to
AMBER as a single PDB with unambiguous partner groups.
