import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from services.docking import (
    DockingError,
    DockingManager,
    finalize_outputs,
    validate_options,
)
from services.docking_api import create_docking_blueprint


def pdb_bytes(chain="A", x=10.0):
    return (f"ATOM      1  CA  ALA {chain}   1      {x:6.3f}  10.000  10.000  1.00 20.00           C  \nEND\n").encode()


def mol2_bytes():
    return b"""@<TRIPOS>MOLECULE
LIG
1 0 0 0 0
SMALL
USER_CHARGES
@<TRIPOS>ATOM
1 C1 0.0 0.0 0.0 C.3 1 LIG 0.0
"""


def make_manager(tmp_path):
    return DockingManager(tmp_path / "docking")


def create_job(manager, kind="protein_ligand", options=None):
    files = {"receptor": ("receptor.pdb", pdb_bytes("A"))}
    files["ligand"] = ("ligand.mol2", mol2_bytes()) if kind == "protein_ligand" else ("partner.pdb", pdb_bytes("A", 20))
    return manager.create(kind, options or {"mode": "rigid", "poses": 3}, files)


def client(manager):
    app = Flask(__name__)
    app.register_blueprint(create_docking_blueprint(manager, enabled=True))
    return app.test_client()


def test_api_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("DOCKING_ENABLED", raising=False)
    app = Flask(__name__)
    app.register_blueprint(create_docking_blueprint(make_manager(tmp_path)))
    api = app.test_client()
    assert api.get("/api/docking/status").get_json()["enabled"] is False
    assert api.post("/api/docking/jobs").status_code == 503


def test_disabled_api_accepts_smoke_token_only_from_loopback(tmp_path, monkeypatch):
    monkeypatch.delenv("DOCKING_ENABLED", raising=False)
    monkeypatch.setenv("DOCKING_SMOKE_TOKEN", "one-time-token")
    app = Flask(__name__)
    app.register_blueprint(create_docking_blueprint(make_manager(tmp_path)))
    api = app.test_client()
    headers = {"X-Docking-Smoke-Token": "one-time-token"}
    assert api.post("/api/docking/jobs", headers=headers).status_code == 400
    assert api.post(
        "/api/docking/jobs",
        headers=headers,
        environ_base={"REMOTE_ADDR": "198.51.100.8"},
    ).status_code == 503


def test_protein_ligand_search_options_and_flexible_residue_limits():
    result = validate_options("protein_ligand", {
        "mode": "flexible", "poses": 10, "exhaustiveness": 8,
        "center_mode": "manual", "center_x": 1, "center_y": 2, "center_z": 3,
        "size_x": 20, "size_y": 30, "size_z": 40, "flex_residues": ["A:42", "B:7"],
    })
    assert result["center"] == {"x": 1, "y": 2, "z": 3}
    assert result["flex_residues"] == ["A:42", "B:7"]
    with pytest.raises(DockingError, match="at least one"):
        validate_options("protein_ligand", {"mode": "flexible"})
    with pytest.raises(DockingError, match="At most 8"):
        validate_options("protein_ligand", {"mode": "flexible", "flex_residues": [f"A:{i}" for i in range(1, 10)]})
    with pytest.raises(DockingError, match="size_x"):
        validate_options("protein_ligand", {"size_x": 50})


def test_protein_protein_limits_are_server_safe():
    options = validate_options("protein_protein", {"mode": "flexible", "swarms": 100, "steps": 50, "anm_modes": 10})
    assert options == {"mode": "flexible", "poses": 10, "swarms": 100, "steps": 50, "anm_modes": 10}
    with pytest.raises(DockingError, match="swarms"):
        validate_options("protein_protein", {"swarms": 101})


def test_jobs_are_persistent_and_claimed_once(tmp_path):
    first = make_manager(tmp_path)
    queued = create_job(first)
    second = DockingManager(first.root)
    assert second.get(queued.id).status == "queued"
    claimed = second.claim_next()
    assert claimed and claimed.id == queued.id and claimed.status == "preparing"
    assert second.claim_next() is None
    assert second.recover_interrupted() == 1
    assert second.get(queued.id).status == "failed"


def test_protein_partner_chains_are_made_unique(tmp_path):
    manager = make_manager(tmp_path)
    job = create_job(manager, "protein_protein")
    partner = manager.input_artifact(job.id, "ligand").read_text()
    manifest = json.loads((manager.job_dir(job.id) / "docking_manifest.json").read_text())
    assert " A " not in partner
    assert manifest["chain_groups"] == {"partner1": ["A"], "partner2": ["B"]}
    assert manifest["partner_chain_map"] == {"A": "B"}


def test_finalize_ligand_pose_writes_complex_and_docked_mol2(tmp_path):
    manager = make_manager(tmp_path)
    job = create_job(manager)
    workspace = manager.job_dir(job.id) / "work"
    workspace.mkdir()
    (workspace / "pose_1.pdb").write_text("HETATM    1  C1  UNL     1       1.000   2.000   3.000  1.00  0.00           C\nEND\n")
    (workspace / "pose_1.mol2").write_bytes(mol2_bytes())
    (workspace / "poses.pdbqt").write_text("REMARK VINA RESULT: -7.4 0.0 0.0\n")
    poses = finalize_outputs(manager, job, workspace)
    complex_text = manager.pose_artifact(job.id, "pose-1", "complex") if manager.get(job.id).status == "complete" else manager.job_dir(job.id) / "poses/pose-1/complex.pdb"
    text = complex_text.read_text()
    assert "ATOM" in text and "HETATM" in text and "LIG" in text
    assert poses[0]["score"] == -7.4
    assert poses[0]["score_unit"] == "kcal/mol"
    assert (manager.job_dir(job.id) / "poses/pose-1/docked_ligand.mol2").is_file()


def test_api_queues_and_serves_completed_pose(tmp_path):
    manager = make_manager(tmp_path)
    response = client(manager).post("/api/docking/jobs", data={
        "kind": "protein_ligand", "options": json.dumps({"poses": 1}),
        "receptor": (io.BytesIO(pdb_bytes()), "receptor.pdb"),
        "ligand": (io.BytesIO(mol2_bytes()), "ligand.mol2"),
    }, content_type="multipart/form-data")
    assert response.status_code == 202
    job_id = response.get_json()["job"]["id"]
    pose_dir = manager.job_dir(job_id) / "poses/pose-1"
    pose_dir.mkdir(parents=True)
    (pose_dir / "complex.pdb").write_bytes(pdb_bytes())
    manager.update(job_id, status="complete", poses=[{"id": "pose-1", "rank": 1}])
    downloaded = client(manager).get(f"/api/docking/jobs/{job_id}/poses/pose-1/complex.pdb")
    assert downloaded.status_code == 200
    assert downloaded.mimetype == "chemical/x-pdb"


def test_status_requires_a_fresh_worker_heartbeat(tmp_path):
    manager = make_manager(tmp_path)
    offline = client(manager).get("/api/docking/status").get_json()
    assert offline["worker"]["online"] is False
    assert all(not item["available"] for item in offline["engines"].values())
    manager.write_worker_status({"protein_ligand": {"engine": "mock", "available": True}})
    online = client(manager).get("/api/docking/status").get_json()
    assert online["worker"]["online"] is True
    assert online["engines"]["protein_ligand"]["available"] is True


def test_expired_jobs_remove_artifacts(tmp_path):
    manager = make_manager(tmp_path)
    job = create_job(manager)
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    with manager._connect() as connection:
        connection.execute("UPDATE jobs SET expires_at=? WHERE id=?", (old, job.id))
    assert manager.expire_old() == 1
    assert manager.get(job.id).status == "expired"
    assert not manager.job_dir(job.id).exists()
