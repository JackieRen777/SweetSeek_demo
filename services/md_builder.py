from __future__ import annotations

import gzip
import io
import json
import math
import re
import shlex
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import requests
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field, field_validator, model_validator


MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PDB_FILES = 2
MAX_MOL2_FILES = 1
ALLOWED_EXTENSIONS = {".pdb", ".ent", ".mol2", ".sdf", ".sd"}

STANDARD_AMINO_ACIDS = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
    "ASH", "CYM", "CYX", "GLH", "HID", "HIE", "HIP", "LYN",
}
WATER_RESIDUES = {"HOH", "WAT", "TIP3", "SOL"}
COMMON_IONS = {"NA", "NA+", "CL", "CL-", "K", "K+"}
METALS = {"ZN", "FE", "MG", "MN", "CA", "CU", "CO", "NI", "CD", "HG"}
NUCLEIC_RESIDUES = {"A", "C", "G", "U", "DA", "DC", "DG", "DT", "DU"}
GLYCAN_RESIDUES = {"NAG", "MAN", "BMA", "FUC", "GAL", "GLC", "SIA"}


class MDBuilderError(ValueError):
    pass


class MDConfig(BaseModel):
    project_name: str = "amber_md_project"
    system_type: str = "single_protein"
    input_mode: str = "single_structure"
    structures: list[dict[str, Any]] = Field(default_factory=list)
    partner1_chains: list[str] = Field(default_factory=list)
    partner2_chains: list[str] = Field(default_factory=list)
    preset: str = "standard"
    protein_force_field: str = "ff19SB"
    water_model: str = "OPCBOX"
    solvent_padding_a: float = Field(12.0, ge=8.0, le=20.0)
    cutoff_a: float = Field(10.0, ge=8.0, le=14.0)
    salt_molar: float = Field(0.0, ge=0.0, le=0.5)
    temperature_k: float = Field(300.0, ge=250.0, le=400.0)
    pressure_bar: float = Field(1.0, ge=0.1, le=10.0)
    simulation_time_ns: float = Field(..., ge=0.1, le=10000.0)
    timestep_fs: float = Field(2.0, ge=1.0, le=2.0)
    heating_ps: int = Field(200, ge=20, le=5000)
    equilibration_ps: int = Field(1000, ge=100, le=10000)
    trajectory_interval_ps: float = Field(10.0, ge=0.1, le=1000.0)
    charge_method: str = "am1bcc"
    ligand_net_charge: int = Field(0, ge=-10, le=10)
    ligand_multiplicity: int = Field(1, ge=1, le=7)
    docking_pose: dict[str, Any] | None = None

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_-")
        if not cleaned:
            raise ValueError("Project name must contain letters or numbers")
        return cleaned[:80]

    @model_validator(mode="after")
    def validate_modes(self):
        if self.system_type not in {"single_protein", "protein_protein", "protein_ligand"}:
            raise ValueError("Unsupported system type")
        if self.input_mode not in {"single_structure", "single_complex", "two_partners"}:
            raise ValueError("Unsupported input mode")
        if self.system_type == "protein_protein" and self.input_mode == "single_complex":
            if not self.partner1_chains or not self.partner2_chains:
                raise ValueError("Both partner chain groups are required")
            if set(self.partner1_chains) & set(self.partner2_chains):
                raise ValueError("A chain cannot belong to both partners")
        if self.system_type == "protein_ligand" and self.charge_method not in {"am1bcc", "resp", "existing"}:
            raise ValueError("Unsupported ligand charge method")
        return self


@dataclass(frozen=True)
class InputFile:
    filename: str
    content: bytes
    inspection: dict[str, Any]


def safe_filename(value: str, *, allowed: set[str] = ALLOWED_EXTENSIONS) -> str:
    if not value or "\x00" in value:
        raise MDBuilderError("Invalid filename")
    if Path(value).is_absolute() or "/" in value or "\\" in value or ".." in PurePosixPath(value).parts:
        raise MDBuilderError("Unsafe filename")
    name = Path(value).name
    ext = Path(name).suffix.lower()
    if ext not in allowed:
        raise MDBuilderError(f"Unsupported file type: {ext or 'none'}")
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(name).stem).strip("._-") or "structure"
    return f"{stem[:100]}{ext}"


def _decode_text(content: bytes) -> str:
    if not content or len(content) > MAX_UPLOAD_BYTES:
        raise MDBuilderError("File is empty or exceeds the 20 MB limit")
    if b"\x00" in content:
        raise MDBuilderError("Binary files are not accepted")
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return content.decode("latin-1")
        except UnicodeDecodeError as exc:
            raise MDBuilderError("Structure file must be plain text") from exc


def inspect_pdb(content: bytes, filename: str) -> dict[str, Any]:
    text = _decode_text(content)
    chains: dict[str, set[tuple[str, str]]] = {}
    residue_names: set[str] = set()
    het_names: set[str] = set()
    atoms = 0
    coordinates: list[tuple[float, float, float]] = []

    for line in text.splitlines():
        if not line.startswith(("ATOM  ", "HETATM")):
            continue
        atoms += 1
        record = line[:6].strip()
        resname = line[17:20].strip().upper()
        chain = line[21:22].strip() or "_"
        resid = line[22:27].strip()
        residue_names.add(resname)
        if record == "ATOM":
            chains.setdefault(chain, set()).add((resid, resname))
        else:
            het_names.add(resname)
        try:
            coordinates.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
        except ValueError:
            pass

    if atoms == 0 or not chains:
        raise MDBuilderError("No protein atoms were found in the PDB file")

    unsupported: list[str] = []
    atom_residues = residue_names - het_names
    nucleic = sorted(atom_residues & NUCLEIC_RESIDUES)
    nonstandard = sorted(atom_residues - STANDARD_AMINO_ACIDS - NUCLEIC_RESIDUES)
    metals = sorted(het_names & METALS)
    glycans = sorted(het_names & GLYCAN_RESIDUES)
    other_hets = sorted(het_names - WATER_RESIDUES - COMMON_IONS - METALS - GLYCAN_RESIDUES)
    if nucleic:
        unsupported.append(f"Nucleic-acid residues detected: {', '.join(nucleic)}")
    if nonstandard:
        unsupported.append(f"Unsupported protein residues detected: {', '.join(nonstandard)}")
    if metals:
        unsupported.append(f"Metal centers detected: {', '.join(metals)}")
    if glycans:
        unsupported.append(f"Glycosylation detected: {', '.join(glycans)}")
    if other_hets:
        unsupported.append(f"Unsupported hetero residues detected: {', '.join(other_hets)}")

    warnings: list[str] = []
    waters = sorted(het_names & WATER_RESIDUES)
    ions = sorted(het_names & COMMON_IONS)
    if waters:
        warnings.append("Existing water molecules will be removed during preparation.")
    if ions:
        warnings.append("Existing free ions will be removed and rebuilt during solvation.")
    if any(line.startswith("CONECT") for line in text.splitlines()) and het_names - WATER_RESIDUES - COMMON_IONS:
        unsupported.append("Covalent or explicitly connected hetero atoms require manual parameterization.")

    chain_rows = [
        {"id": chain, "residues": len(items), "name": sorted({name for _, name in items})[0]}
        for chain, items in sorted(chains.items())
    ]
    bbox = None
    if coordinates:
        xs, ys, zs = zip(*coordinates)
        bbox = {"x": max(xs) - min(xs), "y": max(ys) - min(ys), "z": max(zs) - min(zs)}
    return {
        "filename": filename,
        "format": "pdb",
        "atoms": atoms,
        "residues": sum(len(items) for items in chains.values()),
        "chains": chain_rows,
        "warnings": warnings,
        "unsupported": unsupported,
        "valid": not unsupported,
        "bounding_box": bbox,
    }


def inspect_mol2(content: bytes, filename: str) -> dict[str, Any]:
    text = _decode_text(content)
    in_atoms = False
    atoms = 0
    charges: list[float] = []
    for line in text.splitlines():
        if line.startswith("@<TRIPOS>ATOM"):
            in_atoms = True
            continue
        if line.startswith("@<TRIPOS>"):
            in_atoms = False
            continue
        if in_atoms and line.strip():
            fields = line.split()
            if len(fields) < 6:
                raise MDBuilderError("Invalid MOL2 atom record")
            atoms += 1
            if len(fields) >= 9:
                try:
                    charges.append(float(fields[8]))
                except ValueError:
                    pass
    if atoms == 0:
        raise MDBuilderError("No atoms were found in the MOL2 file")
    return {
        "filename": filename,
        "format": "mol2",
        "atoms": atoms,
        "residues": 1,
        "chains": [],
        "warnings": [],
        "unsupported": [],
        "valid": True,
        "has_charges": len(charges) == atoms and any(abs(charge) > 1e-6 for charge in charges),
        "net_charge": round(sum(charges), 4) if charges else None,
    }


def inspect_sdf(content: bytes, filename: str) -> dict[str, Any]:
    text = _decode_text(content)
    lines = text.splitlines()
    if len(lines) < 4:
        raise MDBuilderError("The SDF file is incomplete")
    fields = lines[3].split()
    try:
        atoms = int(fields[0])
    except (IndexError, ValueError):
        raise MDBuilderError("The SDF counts line is invalid") from None
    if atoms <= 0 or len(lines) < 4 + atoms:
        raise MDBuilderError("No valid atoms were found in the SDF file")
    for line in lines[4:4 + atoms]:
        atom_fields = line.split()
        if len(atom_fields) < 4:
            raise MDBuilderError("An SDF atom line is invalid")
        try:
            float(atom_fields[0]); float(atom_fields[1]); float(atom_fields[2])
        except ValueError:
            raise MDBuilderError("An SDF atom coordinate is invalid") from None
    return {
        "filename": filename, "format": "sdf", "atoms": atoms, "residues": 1,
        "chains": [], "warnings": ["SDF can be viewed now; AMBER generation requires MOL2 conversion."], "unsupported": [], "valid": True,
        "has_charges": False, "net_charge": None,
    }


def inspect_input(filename: str, content: bytes) -> InputFile:
    clean_name = safe_filename(filename)
    if clean_name.endswith(".mol2"):
        inspection = inspect_mol2(content, clean_name)
    elif clean_name.endswith((".sdf", ".sd")):
        inspection = inspect_sdf(content, clean_name)
    else:
        inspection = inspect_pdb(content, clean_name)
    return InputFile(clean_name, content, inspection)


def suggest_system(inspections: list[dict[str, Any]]) -> dict[str, Any]:
    pdbs = [item for item in inspections if item["format"] == "pdb"]
    mol2s = [item for item in inspections if item["format"] in {"mol2", "sdf"}]
    if len(pdbs) == 1 and len(mol2s) == 1:
        return {"system_type": "protein_ligand", "input_mode": "single_structure", "needs_chain_grouping": False}
    if len(pdbs) == 2 and not mol2s:
        return {"system_type": "protein_protein", "input_mode": "two_partners", "needs_chain_grouping": False}
    if len(pdbs) == 1 and not mol2s:
        multi = len(pdbs[0]["chains"]) > 1
        return {
            "system_type": "protein_protein" if multi else "single_protein",
            "input_mode": "single_complex" if multi else "single_structure",
            "needs_chain_grouping": multi,
        }
    return {"system_type": None, "input_mode": None, "needs_chain_grouping": False}


def fetch_rcsb_pdb(pdb_id: str, unit: str = "asymmetric", assembly_id: int = 1) -> InputFile:
    normalized = pdb_id.strip().upper()
    if not re.fullmatch(r"[0-9A-Z]{4}", normalized):
        raise MDBuilderError("PDB ID must contain exactly four letters or numbers")
    if unit not in {"asymmetric", "assembly"}:
        raise MDBuilderError("Unit must be asymmetric or assembly")
    if not 1 <= int(assembly_id) <= 99:
        raise MDBuilderError("Assembly ID must be between 1 and 99")

    if unit == "asymmetric":
        url = f"https://files.rcsb.org/download/{normalized}.pdb"
        filename = f"{normalized}.pdb"
    else:
        url = f"https://files.rcsb.org/download/{normalized}.pdb{int(assembly_id)}.gz"
        filename = f"{normalized}_assembly{int(assembly_id)}.pdb"
    try:
        response = requests.get(url, timeout=15)
    except requests.RequestException as exc:
        raise MDBuilderError("RCSB is temporarily unavailable") from exc
    if response.status_code == 404:
        raise MDBuilderError("This structure is not available safely in PDB format; mmCIF is not supported in this version")
    if response.status_code != 200:
        raise MDBuilderError(f"RCSB returned HTTP {response.status_code}")
    content = response.content
    if unit == "assembly":
        try:
            content = gzip.decompress(content)
        except gzip.BadGzipFile:
            pass
    return inspect_input(filename, content)


def validate_input_counts(inputs: list[InputFile]) -> None:
    if sum(len(item.content) for item in inputs) > MAX_UPLOAD_BYTES:
        raise MDBuilderError("Combined input size exceeds 20 MB")
    pdb_count = sum(item.inspection["format"] == "pdb" for item in inputs)
    mol2_count = sum(item.inspection["format"] in {"mol2", "sdf"} for item in inputs)
    if pdb_count > MAX_PDB_FILES or mol2_count > MAX_MOL2_FILES or not inputs:
        raise MDBuilderError("Provide at most two PDB files and one MOL2 or SDF file")
    if len({item.filename for item in inputs}) != len(inputs):
        raise MDBuilderError("Input filenames must be unique")
    invalid = [item.inspection for item in inputs if not item.inspection["valid"]]
    if invalid:
        messages = [message for item in invalid for message in item["unsupported"]]
        raise MDBuilderError(" ".join(messages))


def _salt_pairs(config: MDConfig, pdb: InputFile) -> int:
    if config.salt_molar <= 0:
        return 0
    bbox = pdb.inspection.get("bounding_box") or {"x": 50, "y": 50, "z": 50}
    volume = math.prod(float(bbox[axis]) + 2 * config.solvent_padding_a for axis in ("x", "y", "z"))
    return max(1, round(0.000602214 * config.salt_molar * volume))


def _template_environment() -> Environment:
    template_dir = Path(__file__).resolve().parent.parent / "md_builder_templates"
    return Environment(
        loader=FileSystemLoader(str(template_dir)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def render_project(config: MDConfig, inputs: list[InputFile]) -> dict[str, str]:
    validate_input_counts(inputs)
    pdbs = [item for item in inputs if item.inspection["format"] == "pdb"]
    mol2s = [item for item in inputs if item.inspection["format"] in {"mol2", "sdf"}]
    if config.system_type == "single_protein" and len(pdbs) != 1:
        raise MDBuilderError("Single-protein projects require one PDB file")
    if config.system_type == "protein_protein" and config.input_mode == "two_partners" and len(pdbs) != 2:
        raise MDBuilderError("Two-partner projects require two PDB files")
    if config.system_type == "protein_protein" and config.input_mode == "single_complex" and len(pdbs) != 1:
        raise MDBuilderError("Single-complex projects require one PDB file")
    if config.system_type == "protein_ligand" and (len(pdbs) != 1 or len(mol2s) != 1):
        raise MDBuilderError("Protein-ligand projects require one PDB and one MOL2 file")
    if config.system_type == "protein_ligand" and mol2s[0].inspection["format"] == "sdf":
        raise MDBuilderError("SDF-to-MOL2 preparation is not available yet; upload a MOL2 file for AMBER generation")
    if config.system_type == "protein_ligand" and config.charge_method == "existing":
        if not mol2s[0].inspection.get("has_charges"):
            raise MDBuilderError("The MOL2 file does not contain usable atomic charges; select AM1-BCC or RESP")

    total_steps = round(config.simulation_time_ns * 1_000_000 / config.timestep_fs)
    rounds = max(1, math.ceil(config.simulation_time_ns / 10.0))
    steps_per_round = math.ceil(total_steps / rounds)
    output_steps = max(1, round(config.trajectory_interval_ps * 1000 / config.timestep_fs))
    heat_steps = round(config.heating_ps * 1000 / config.timestep_fs)
    equil_steps = round(config.equilibration_ps * 1000 / config.timestep_fs)
    context = {
        **config.model_dump(),
        "pdb_files": [item.filename for item in pdbs],
        "mol2_file": mol2s[0].filename if mol2s else "",
        "salt_pairs": _salt_pairs(config, pdbs[0]),
        "production_rounds": rounds,
        "production_steps": steps_per_round,
        "output_steps": output_steps,
        "heat_steps": heat_steps,
        "equil_steps": equil_steps,
        "dt_ps": config.timestep_fs / 1000,
        "partner1_csv": ",".join(config.partner1_chains),
        "partner2_csv": ",".join(config.partner2_chains),
        "all_selected_chains": ",".join(config.partner1_chains + config.partner2_chains),
        "protein_ff_leap": "leaprc.protein.ff19SB" if config.protein_force_field == "ff19SB" else "leaprc.protein.ff14SB",
        "water_leap": "leaprc.water.opc" if config.water_model == "OPCBOX" else "leaprc.water.tip3p",
        "docking_pose": config.docking_pose,
    }
    env = _template_environment()
    templates = {
        "README.md": "README.md.j2",
        "run_md.sh": "run_md.sh.j2",
        "leap.in": "leap.in.j2",
        "md/min1.in": "min1.in.j2",
        "md/min2.in": "min2.in.j2",
        "md/heat.in": "heat.in.j2",
        "md/equil.in": "equil.in.j2",
        "md/prod.in": "prod.in.j2",
        "analyse/analyse.sh": "analyse.sh.j2",
    }
    if config.system_type == "protein_ligand" and config.charge_method != "existing":
        templates["prepare_lig.sh"] = "prepare_lig.sh.j2"
    files = {output: env.get_template(template).render(**context).rstrip() + "\n" for output, template in templates.items()}
    files["parameters.json"] = json.dumps(config.model_dump(), indent=2, sort_keys=True) + "\n"
    return files


def build_zip(config: MDConfig, inputs: list[InputFile], docking_pose: bytes | None = None) -> io.BytesIO:
    files = render_project(config, inputs)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        root = config.project_name
        for item in inputs:
            archive.writestr(f"{root}/inputs/{item.filename}", item.content)
        if docking_pose:
            archive.writestr(f"{root}/inputs/docked_pose.pdb", docking_pose)
        for path, content in files.items():
            info = zipfile.ZipInfo(f"{root}/{path}")
            info.external_attr = (0o755 if path.endswith(".sh") else 0o644) << 16
            archive.writestr(info, content)
    buffer.seek(0)
    return buffer


def shell_quote(value: str) -> str:
    return shlex.quote(value)
