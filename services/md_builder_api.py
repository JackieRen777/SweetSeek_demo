from __future__ import annotations

import json
import io
import re
from typing import Callable

from flask import Blueprint, Request as FlaskRequest, jsonify, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from pydantic import ValidationError

from services.md_builder import (
    MAX_UPLOAD_BYTES,
    MDBuilderError,
    MDConfig,
    build_zip,
    fetch_rcsb_pdb,
    inspect_input,
    suggest_system,
    validate_input_counts,
)


class InMemoryUploadRequest(FlaskRequest):
    """Keep accepted structure uploads in memory instead of spooling to disk."""

    max_form_memory_size = MAX_UPLOAD_BYTES

    def _get_file_stream(self, total_content_length, content_type, filename=None, content_length=None):
        if total_content_length is not None and total_content_length > MAX_UPLOAD_BYTES:
            raise RequestEntityTooLarge()
        return io.BytesIO()


def _error(message: str, status: int = 400):
    return jsonify({"success": False, "error": message}), status


def _read_uploads():
    uploads = request.files.getlist("files")
    if not uploads:
        raise MDBuilderError("No structure files were provided")
    inputs = []
    total = 0
    for upload in uploads:
        content = upload.read(MAX_UPLOAD_BYTES + 1)
        total += len(content)
        if total > MAX_UPLOAD_BYTES:
            raise MDBuilderError("Combined input size exceeds 20 MB")
        inputs.append(inspect_input(upload.filename or "", content))
    validate_input_counts(inputs)
    return inputs


def _extraction_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "project_name": {"type": "string"},
            "system_type": {"type": "string", "enum": ["single_protein", "protein_protein", "protein_ligand"]},
            "simulation_time_ns": {"type": "number"},
            "temperature_k": {"type": "number"},
            "pressure_bar": {"type": "number"},
            "preset": {"type": "string", "enum": ["standard", "compatibility"]},
            "salt_molar": {"type": "number"},
            "charge_method": {"type": "string", "enum": ["am1bcc", "resp", "existing"]},
            "ligand_net_charge": {"type": "integer"},
            "ligand_multiplicity": {"type": "integer"},
        },
        "additionalProperties": False,
    }


def _extract_explicit_values(text: str) -> dict:
    """Deterministically retain simple values that an LLM may omit."""
    values = {}
    patterns = {
        "simulation_time_ns": r"\b(\d+(?:\.\d+)?)\s*(?:ns|nanoseconds?)\b",
        "temperature_k": r"\b(\d+(?:\.\d+)?)\s*(?:k|kelvin)\b",
        "pressure_bar": r"\b(\d+(?:\.\d+)?)\s*bar\b",
        "salt_molar": r"\b(\d+(?:\.\d+)?)\s*(?:m|molar)\s*(?:nacl|salt)?\b",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values[key] = float(match.group(1))
    charge = re.search(r"\b(?:net\s+)?charge\s*(?:of|=|is|:)?\s*([+-]?\d+)\b", text, flags=re.IGNORECASE)
    if charge:
        values["ligand_net_charge"] = int(charge.group(1))
    lowered = text.lower()
    if "am1-bcc" in lowered or "am1bcc" in lowered:
        values["charge_method"] = "am1bcc"
    elif "resp" in lowered:
        values["charge_method"] = "resp"
    elif "existing charge" in lowered or "keep charge" in lowered:
        values["charge_method"] = "existing"
    return values


def create_md_builder_blueprint(llm_client_getter: Callable):
    blueprint = Blueprint("md_builder", __name__, url_prefix="/api/md-builder")

    @blueprint.post("/inspect")
    def inspect_uploads():
        try:
            inputs = _read_uploads()
            inspections = [item.inspection for item in inputs]
            return jsonify({"success": True, "structures": inspections, "suggestion": suggest_system(inspections)})
        except MDBuilderError as exc:
            return _error(str(exc))

    @blueprint.post("/inspect-pdb-id")
    def inspect_pdb_id():
        data = request.get_json(silent=True) or {}
        try:
            item = fetch_rcsb_pdb(data.get("pdb_id", ""), data.get("unit", "asymmetric"), int(data.get("assembly_id", 1)))
            return jsonify({
                "success": True,
                "structures": [item.inspection],
                "suggestion": suggest_system([item.inspection]),
                "source": {"source": "rcsb", "pdb_id": data.get("pdb_id", "").upper(), "unit": data.get("unit", "asymmetric"), "assembly_id": int(data.get("assembly_id", 1)), "filename": item.filename},
            })
        except (MDBuilderError, ValueError) as exc:
            return _error(str(exc), 502 if "RCSB" in str(exc) else 400)

    @blueprint.post("/extract")
    def extract_parameters():
        data = request.get_json(silent=True) or {}
        text = str(data.get("text", "")).strip()
        if len(text) < 3:
            return _error("Describe the simulation you want to generate")
        client = llm_client_getter()
        if client is None:
            return _error("The language model service is not configured", 503)
        current = data.get("parameters") if isinstance(data.get("parameters"), dict) else {}
        locked = {str(item) for item in data.get("locked_fields", []) if isinstance(item, str)}
        structures = data.get("structures") if isinstance(data.get("structures"), list) else []
        messages = [
            {
                "role": "system",
                "content": "Extract only explicitly stated AMBER MD setup preferences. Do not invent file names, chains, or durations. Return valid JSON matching the schema.",
            },
            {
                "role": "user",
                "content": json.dumps({"request": text, "current_parameters": current, "structure_metadata": structures}, ensure_ascii=False),
            },
        ]
        try:
            proposed = client.structured_chat(messages, schema=_extraction_schema(), function_name="extract_md_parameters")
        except Exception as exc:
            return _error(f"Parameter extraction failed: {exc}", 502)
        proposed = {**proposed, **_extract_explicit_values(text)}
        merged = dict(current)
        for key, value in proposed.items():
            if key not in locked and value is not None:
                merged[key] = value
        missing = []
        if not structures:
            missing.append("structure")
        if not merged.get("simulation_time_ns"):
            missing.append("simulation_time_ns")
        return jsonify({
            "success": True,
            "parameters": merged,
            "missing_info": missing,
            "needs_clarification": bool(missing),
            "summary": "More information is required." if missing else "Parameters extracted. Review them before generation.",
        })

    @blueprint.post("/generate")
    def generate():
        try:
            raw_config = request.form.get("config", "")
            config_data = json.loads(raw_config)
            config = MDConfig.model_validate(config_data)
            inputs = []
            uploads = {upload.filename: upload for upload in request.files.getlist("files")}
            total = 0
            for source in config.structures:
                if source.get("source") == "rcsb":
                    item = fetch_rcsb_pdb(source.get("pdb_id", ""), source.get("unit", "asymmetric"), int(source.get("assembly_id", 1)))
                else:
                    filename = source.get("filename", "")
                    upload = uploads.get(filename)
                    if upload is None:
                        raise MDBuilderError(f"Missing uploaded file: {filename}")
                    content = upload.read(MAX_UPLOAD_BYTES + 1)
                    total += len(content)
                    if total > MAX_UPLOAD_BYTES:
                        raise MDBuilderError("Combined input size exceeds 20 MB")
                    item = inspect_input(filename, content)
                inputs.append(item)
            archive = build_zip(config, inputs)
            return send_file(
                archive,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{config.project_name}.zip",
                max_age=0,
            )
        except json.JSONDecodeError:
            return _error("Invalid configuration JSON")
        except ValidationError as exc:
            return _error("; ".join(error["msg"] for error in exc.errors()))
        except (MDBuilderError, ValueError) as exc:
            return _error(str(exc))

    return blueprint
