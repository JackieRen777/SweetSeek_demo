import io
import json
import subprocess
import zipfile

import pytest
from flask import Flask

from services.md_builder import (
    MDBuilderError,
    MDConfig,
    build_zip,
    fetch_rcsb_pdb,
    inspect_input,
    render_project,
    safe_filename,
    suggest_system,
)
from services.md_builder_api import create_md_builder_blueprint
from services.md_builder_api import _expert_intent_hint, _extract_explicit_values
from services.llm_client import ChatDelta


def pdb_bytes(chains=("A",), hetero=None):
    lines = []
    serial = 1
    for chain_index, chain in enumerate(chains, 1):
        for atom, element, offset in (("N", "N", 0.0), ("CA", "C", 1.2), ("C", "C", 2.3)):
            lines.append(
                f"ATOM  {serial:5d} {atom:^4s} ALA {chain}{chain_index:4d}    "
                f"{10 + offset:8.3f}{10 + chain_index:8.3f}{10:8.3f}  1.00 20.00          {element:>2s}  "
            )
            serial += 1
    if hetero:
        lines.append(
            f"HETATM{serial:5d} {hetero:>4s} {hetero:>3s} Z{1:4d}    "
            f"{20:8.3f}{20:8.3f}{20:8.3f}  1.00 20.00          {hetero[:2]:>2s}  "
        )
    lines.append("END")
    return ("\n".join(lines) + "\n").encode()


def mol2_bytes(with_charges=True):
    charge = "-0.1000" if with_charges else "0.0000"
    second_charge = "0.1000" if with_charges else "0.0000"
    return f"""@<TRIPOS>MOLECULE
LIG
2 1 0 0 0
SMALL
USER_CHARGES
@<TRIPOS>ATOM
1 C1 0.0 0.0 0.0 C.3 1 LIG {charge}
2 O1 1.2 0.0 0.0 O.3 1 LIG {second_charge}
@<TRIPOS>BOND
1 1 2 1
""".encode()


def source(item):
    return {"source": "upload", "filename": item.filename}


def test_inspection_and_system_suggestions():
    single = inspect_input("single.pdb", pdb_bytes())
    complex_input = inspect_input("complex.pdb", pdb_bytes(("A", "B")))
    ligand = inspect_input("ligand.mol2", mol2_bytes())
    assert single.inspection["chains"][0]["id"] == "A"
    assert suggest_system([single.inspection])["system_type"] == "single_protein"
    suggestion = suggest_system([complex_input.inspection])
    assert suggestion == {
        "system_type": "protein_protein",
        "input_mode": "single_complex",
        "needs_chain_grouping": True,
    }
    assert suggest_system([single.inspection, ligand.inspection])["system_type"] == "protein_ligand"
    assert ligand.inspection["has_charges"] is True


def test_special_chemistry_is_rejected():
    metal = inspect_input("metal.pdb", pdb_bytes(hetero="ZN"))
    assert metal.inspection["valid"] is False
    assert "Metal centers" in metal.inspection["unsupported"][0]


@pytest.mark.parametrize("unsafe", ["../protein.pdb", "/tmp/protein.pdb", "folder/protein.pdb", "folder\\protein.pdb", "bad\x00.pdb"])
def test_unsafe_filenames_are_rejected(unsafe):
    with pytest.raises(MDBuilderError):
        safe_filename(unsafe)


def test_single_protein_zip_contains_inputs_and_valid_shell(tmp_path):
    protein = inspect_input("protein.pdb", pdb_bytes())
    config = MDConfig(simulation_time_ns=20, structures=[source(protein)])
    archive = build_zip(config, [protein])
    with zipfile.ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        assert "amber_md_project/inputs/protein.pdb" in names
        assert "amber_md_project/md/prod.in" in names
        leap = zipped.read("amber_md_project/leap.in").decode()
        assert "com = protein" in leap
        assert "loadmol2" not in leap.lower()
        for name in names:
            if name.endswith(".sh"):
                target = tmp_path / name.replace("/", "_")
                target.write_bytes(zipped.read(name))
                subprocess.run(["bash", "-n", str(target)], check=True)


def test_single_complex_and_two_partner_templates_are_distinct():
    complex_input = inspect_input("complex.pdb", pdb_bytes(("A", "B")))
    complex_config = MDConfig(
        system_type="protein_protein", input_mode="single_complex", simulation_time_ns=10,
        partner1_chains=["A"], partner2_chains=["B"], structures=[source(complex_input)],
    )
    complex_files = render_project(complex_config, [complex_input])
    assert "com = protein" in complex_files["leap.in"]
    assert '"A,B"' in complex_files["run_md.sh"]

    first = inspect_input("one.pdb", pdb_bytes())
    second = inspect_input("two.pdb", pdb_bytes(("B",)))
    pair_config = MDConfig(
        system_type="protein_protein", input_mode="two_partners", simulation_time_ns=10,
        structures=[source(first), source(second)],
    )
    pair_files = render_project(pair_config, [first, second])
    assert "combine { partner1 partner2 }" in pair_files["leap.in"]


@pytest.mark.parametrize("charge_method,has_prep", [("am1bcc", True), ("resp", True), ("existing", False)])
def test_ligand_charge_modes(charge_method, has_prep):
    protein = inspect_input("protein.pdb", pdb_bytes())
    ligand = inspect_input("ligand.mol2", mol2_bytes())
    config = MDConfig(
        system_type="protein_ligand", simulation_time_ns=5, charge_method=charge_method,
        structures=[source(protein), source(ligand)],
    )
    files = render_project(config, [protein, ligand])
    assert ("prepare_lig.sh" in files) is has_prep
    assert "loadamberparams ligand.frcmod" in files["leap.in"].lower()
    assert "barostat=2" in files["md/prod.in"]


def test_existing_ligand_charge_mode_requires_charged_mol2():
    protein = inspect_input("protein.pdb", pdb_bytes())
    ligand = inspect_input("ligand.mol2", mol2_bytes(with_charges=False))
    config = MDConfig(
        system_type="protein_ligand", simulation_time_ns=5, charge_method="existing",
        structures=[source(protein), source(ligand)],
    )
    with pytest.raises(MDBuilderError, match="does not contain usable atomic charges"):
        render_project(config, [protein, ligand])


def test_rcsb_fetch_is_inspected(monkeypatch):
    class Response:
        status_code = 200
        content = pdb_bytes(("A", "B"))

    monkeypatch.setattr("services.md_builder.requests.get", lambda *args, **kwargs: Response())
    item = fetch_rcsb_pdb("1abc")
    assert item.filename == "1ABC.pdb"
    assert len(item.inspection["chains"]) == 2


def test_blueprint_inspect_and_generate_without_persistence():
    app = Flask(__name__)
    app.register_blueprint(create_md_builder_blueprint(lambda: None))
    client = app.test_client()
    inspection = client.post(
        "/api/md-builder/inspect",
        data={"files": (io.BytesIO(pdb_bytes()), "protein.pdb")},
        content_type="multipart/form-data",
    )
    assert inspection.status_code == 200
    assert inspection.get_json()["suggestion"]["system_type"] == "single_protein"

    config = MDConfig(
        simulation_time_ns=10,
        structures=[{"source": "upload", "filename": "protein.pdb"}],
    ).model_dump()
    generated = client.post(
        "/api/md-builder/generate",
        data={
            "config": json.dumps(config),
            "files": (io.BytesIO(pdb_bytes()), "protein.pdb"),
        },
        content_type="multipart/form-data",
    )
    assert generated.status_code == 200
    assert generated.mimetype == "application/zip"


def test_explicit_parameter_values_are_not_lost_by_llm_extraction():
    values = _extract_explicit_values(
        "Run 50 ns at 310 K and 1 bar with 0.15 M NaCl; ligand net charge is -1 using RESP."
    )
    assert values == {
        "simulation_time_ns": 50.0,
        "temperature_k": 310.0,
        "pressure_bar": 1.0,
        "salt_molar": 0.15,
        "ligand_net_charge": -1,
        "charge_method": "resp",
    }


def test_expert_chat_auto_applies_setup_values_but_preserves_locked_fields():
    class ExpertClient:
        def structured_chat(self, messages, **kwargs):
            assert kwargs["function_name"] == "answer_md_expert"
            assert "current_parameters" in messages[-1]["content"]
            return {
                "answer": "The requested production protocol is internally consistent.",
                "intent": "setup",
                "confidence": "high",
                "auto_apply": True,
                "parameter_updates": {
                    "simulation_time_ns": 80, "temperature_k": 280, "salt_molar": 0.15,
                    "heating_ps": 100, "charge_method": "existing",
                },
                "diagnostic_checks": [],
            }

    app = Flask(__name__)
    app.register_blueprint(create_md_builder_blueprint(lambda: ExpertClient()))
    response = app.test_client().post("/api/md-builder/chat", json={
        "message": "Set up 100 ns at 310 K with 0.15 M NaCl",
        "parameters": {"simulation_time_ns": 50, "temperature_k": 315, "salt_molar": 0},
        "locked_fields": ["temperature_k"],
        "structures": [],
        "history": [],
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["auto_apply"] is True
    assert data["parameter_updates"] == {"simulation_time_ns": 100.0, "salt_molar": 0.15}
    assert data["confidence"] == "high"


def test_expert_chat_never_auto_applies_troubleshooting_advice():
    class ExpertClient:
        def structured_chat(self, _messages, **_kwargs):
            return {
                "answer": "Check whether this is a periodic-boundary imaging artifact before changing the force field.",
                "intent": "setup",
                "confidence": "medium",
                "auto_apply": True,
                "parameter_updates": {"solvent_padding_a": 16, "timestep_fs": 1},
                "diagnostic_checks": ["Run cpptraj autoimage and inspect the imaged trajectory."],
            }

    app = Flask(__name__)
    app.register_blueprint(create_md_builder_blueprint(lambda: ExpertClient()))
    response = app.test_client().post("/api/md-builder/chat", json={
        "message": "My ligand escaped from the binding site after 10 ns. What failed?",
        "parameters": {},
        "locked_fields": [],
        "structures": [],
    })
    data = response.get_json()
    assert response.status_code == 200
    assert data["intent"] == "troubleshooting"
    assert data["auto_apply"] is False
    assert data["parameter_updates"] == {"solvent_padding_a": 16, "timestep_fs": 1}
    assert "autoimage" in data["diagnostic_checks"][0]


def test_general_expert_questions_stream_without_structured_parameter_extraction():
    class GeneralClient:
        def stream_chat(self, messages, **kwargs):
            assert messages[-1]["content"] == "What is the difference between ff19SB and ff14SB?"
            assert kwargs == {"temperature": 0.2, "max_tokens": 500}
            yield ChatDelta(content="ff19SB refines ")
            yield ChatDelta(content="backbone torsions.")

        def structured_chat(self, *_args, **_kwargs):
            raise AssertionError("General questions must use the streaming path")

    app = Flask(__name__)
    app.register_blueprint(create_md_builder_blueprint(lambda: GeneralClient()))
    response = app.test_client().post("/api/md-builder/chat-stream", json={
        "message": "What is the difference between ff19SB and ff14SB?",
        "history": [],
    })
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert response.mimetype == "text/event-stream"
    assert '"type": "delta"' in body
    assert "backbone torsions" in body
    assert '"type": "done"' in body


@pytest.mark.parametrize("question, expected", [
    ("What does SHAKE do?", "general"),
    ("Set up 100 ns at 310 K", "setup"),
    ("100 ns at 310 K with ff19SB", "setup"),
    ("My ligand escaped after 8 ns", "troubleshooting"),
])
def test_expert_intent_hint_selects_the_fast_path(question, expected):
    assert _expert_intent_hint(question) == expected
