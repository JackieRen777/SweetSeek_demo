# Docking deployment

The UI is available at `/docking`. It submits `protein_ligand` and
`protein_protein` jobs to the Flask API and polls `/api/docking/jobs/<id>`.
The API keeps one worker by default (`DOCKING_WORKERS=1`) so docking cannot
starve the web process.

## ECS installation

```bash
chmod +x scripts/docking/*.sh
DOCKING_VENV=/opt/sweetseek/.venv-docking scripts/docking/install_docking.sh
```

Set the command used by the worker before starting Gunicorn:

```bash
export DOCKING_COMMAND='/opt/sweetseek/scripts/docking/run_docking.sh {kind} "{receptor}" "{ligand}" "{workspace}" "{poses}" "{exhaustiveness}"'
export DOCKING_OUTPUT_FILE=poses.pdb
export DOCKING_WORKERS=1
```

Install `scripts/docking/sweetseek.service.docking.conf` as
`/etc/systemd/system/sweetseek.service.d/docking.conf`, then run
`systemctl daemon-reload && systemctl restart sweetseek`. Do not start a
second Gunicorn service: the queue worker intentionally lives inside the
existing Flask process and has a strict concurrency limit.

The Vina adapter uses Meeko for PDBQT preparation and Open Babel when present
to convert poses to PDB. LightDock remains isolated in its adapter because its
output layout changes between upstream versions. Jobs report an explicit
`engine unavailable` or command error instead of returning fake poses.
