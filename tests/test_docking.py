import io
import json
import time

from flask import Flask

from services.docking_api import create_docking_blueprint


def pdb_bytes(chain="A"):
    return (f"ATOM      1  CA  ALA {chain}   1      10.000  10.000  10.000  1.00 20.00           C  \nEND\n").encode()


def mol2_bytes():
    return b"""@<TRIPOS>MOLECULE
LIG
1 0 0 0 0
SMALL
USER_CHARGES
@<TRIPOS>ATOM
1 C1 0.0 0.0 0.0 C.3 1 LIG 0.0
"""


def client():
    app = Flask(__name__)
    app.register_blueprint(create_docking_blueprint())
    return app.test_client()


def test_docking_status_exposes_engine_contract():
    response = client().get("/api/docking/status")
    assert response.status_code == 200
    assert set(response.get_json()["engines"]) == {"protein_ligand", "protein_protein"}


def test_job_requires_two_roles_and_returns_json_error():
    response = client().post("/api/docking/jobs", data={"kind": "protein_ligand", "options": "{}"})
    assert response.status_code == 400
    assert "Missing receptor" in response.get_json()["error"]


def test_job_is_queued_and_surfaces_missing_engine(monkeypatch):
    monkeypatch.delenv("DOCKING_COMMAND", raising=False)
    response = client().post(
        "/api/docking/jobs",
        data={
            "kind": "protein_ligand",
            "options": json.dumps({"poses": 3}),
            "receptor": (io.BytesIO(pdb_bytes()), "receptor.pdb"),
            "ligand": (io.BytesIO(mol2_bytes()), "ligand.mol2"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 202
    job_id = response.get_json()["job"]["id"]
    for _ in range(30):
        state = client().get(f"/api/docking/jobs/{job_id}").get_json()["job"]
        if state["status"] == "failed":
            break
        time.sleep(0.02)
    assert state["status"] == "failed"
    assert "engine is not configured" in state["error"]
