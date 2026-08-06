from __future__ import annotations

import json
import io
import re
from typing import Callable

from flask import Blueprint, Request as FlaskRequest, Response, jsonify, request, send_file, stream_with_context
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
            "protein_force_field": {"type": "string", "enum": ["ff19SB", "ff14SB"]},
            "water_model": {"type": "string", "enum": ["OPCBOX", "TIP3PBOX"]},
            "solvent_padding_a": {"type": "number"},
            "cutoff_a": {"type": "number"},
            "salt_molar": {"type": "number"},
            "timestep_fs": {"type": "number"},
            "heating_ps": {"type": "number"},
            "equilibration_ps": {"type": "number"},
            "trajectory_interval_ps": {"type": "number"},
            "charge_method": {"type": "string", "enum": ["am1bcc", "resp", "existing"]},
            "ligand_net_charge": {"type": "integer"},
            "ligand_multiplicity": {"type": "integer"},
        },
        "additionalProperties": False,
    }


def _expert_schema() -> dict:
    parameter_properties = dict(_extraction_schema()["properties"])
    parameter_properties.pop("system_type", None)
    return {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "intent": {"type": "string", "enum": ["setup", "troubleshooting", "general"]},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "auto_apply": {"type": "boolean"},
            "parameter_updates": {
                "type": "object",
                "properties": parameter_properties,
                "additionalProperties": False,
            },
            "diagnostic_checks": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
        },
        "required": ["answer", "intent", "confidence", "auto_apply", "parameter_updates", "diagnostic_checks"],
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
    advanced_patterns = {
        "solvent_padding_a": r"(?:padding|buffer|solvent\s+shell)\D{0,16}(\d+(?:\.\d+)?)\s*(?:a|angstroms?|å)",
        "cutoff_a": r"(?:cutoff|nonbonded\s+cutoff)\D{0,12}(\d+(?:\.\d+)?)\s*(?:a|angstroms?|å)",
        "timestep_fs": r"(?:time\s*step|timestep|dt)\D{0,12}(\d+(?:\.\d+)?)\s*fs\b",
        "heating_ps": r"(?:heat(?:ing)?)\D{0,16}(\d+(?:\.\d+)?)\s*ps\b",
        "equilibration_ps": r"(?:equilibrat(?:e|ion|ing))\D{0,16}(\d+(?:\.\d+)?)\s*ps\b",
        "trajectory_interval_ps": r"(?:trajectory|output|write|save|ntwx)\D{0,20}(\d+(?:\.\d+)?)\s*ps\b",
    }
    for key, pattern in advanced_patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values[key] = float(match.group(1))
    charge = re.search(r"\b(?:net\s+)?charge\s*(?:of|=|is|:)?\s*([+-]?\d+)\b", text, flags=re.IGNORECASE)
    if charge:
        values["ligand_net_charge"] = int(charge.group(1))
    multiplicity = re.search(r"\bmultiplicity\s*(?:of|=|is|:)?\s*(\d+)\b", text, flags=re.IGNORECASE)
    if multiplicity:
        values["ligand_multiplicity"] = int(multiplicity.group(1))
    lowered = text.lower()
    if "am1-bcc" in lowered or "am1bcc" in lowered:
        values["charge_method"] = "am1bcc"
    elif "resp" in lowered:
        values["charge_method"] = "resp"
    elif "existing charge" in lowered or "keep charge" in lowered:
        values["charge_method"] = "existing"
    if "ff19sb" in lowered:
        values["protein_force_field"] = "ff19SB"
    elif "ff14sb" in lowered:
        values["protein_force_field"] = "ff14SB"
    if re.search(r"\bopc(?:box)?\b", lowered):
        values["water_model"] = "OPCBOX"
    elif re.search(r"\btip3p(?:box)?\b", lowered):
        values["water_model"] = "TIP3PBOX"
    if re.search(r"\bstandard\s+preset\b", lowered):
        values["preset"] = "standard"
    elif re.search(r"\bcompatibility\s+preset\b", lowered):
        values["preset"] = "compatibility"
    return values


def _explicit_parameter_keys(text: str) -> set[str]:
    lowered = text.lower()
    evidence = {
        "project_name": r"\bproject\s+name\b",
        "simulation_time_ns": r"\b(?:ns|nanoseconds?|production\s+(?:time|length)|duration)\b",
        "temperature_k": r"\b(?:temperature|temp|kelvin)\b|\d\s*k\b",
        "pressure_bar": r"\b(?:pressure|bar|atm)\b",
        "preset": r"\b(?:standard|compatibility)\s+preset\b",
        "protein_force_field": r"\b(?:ff19sb|ff14sb|force\s*field)\b",
        "water_model": r"\b(?:opc(?:box)?|tip3p(?:box)?|water\s+model)\b",
        "solvent_padding_a": r"\b(?:padding|buffer|solvent\s+shell)\b",
        "cutoff_a": r"\b(?:cutoff|nonbonded\s+cutoff)\b",
        "salt_molar": r"\b(?:salt|nacl|molar)\b|\d\s*m\b",
        "timestep_fs": r"\b(?:time\s*step|timestep|dt|fs)\b",
        "heating_ps": r"\bheat(?:ing)?\b",
        "equilibration_ps": r"\bequilibrat(?:e|ion|ing)\b",
        "trajectory_interval_ps": r"\b(?:trajectory|output|write|save|ntwx)\b",
        "charge_method": r"\b(?:am1-?bcc|resp|existing\s+charges?|keep\s+charges?)\b",
        "ligand_net_charge": r"\b(?:ligand\s+)?(?:net\s+)?charge\b",
        "ligand_multiplicity": r"\b(?:multiplicity|spin\s+state)\b",
    }
    return {key for key, pattern in evidence.items() if re.search(pattern, lowered, flags=re.IGNORECASE)}


def _is_troubleshooting(text: str) -> bool:
    return bool(re.search(
        r"\b(?:error|failed?|failure|crash(?:ed)?|nan|blow(?:n|ing)?\s+up|unstable|"
        r"drift(?:ed|ing)?|escaped?|left\s+the\s+(?:site|box)|unbound|dissociat(?:ed|ion))\b|"
        r"跑出|跑飞|失败|报错|崩溃|爆炸|不稳定|解离|漂移",
        text,
        flags=re.IGNORECASE,
    ))


def _clean_history(value, *, limit: int = 6, content_limit: int = 2400) -> list[dict]:
    if not isinstance(value, list):
        return []
    cleaned = []
    for item in value[-limit:]:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            continue
        content = str(item.get("content", "")).strip()[:content_limit]
        if content:
            cleaned.append({"role": item["role"], "content": content})
    return cleaned


def _expert_intent_hint(text: str) -> str:
    if _is_troubleshooting(text):
        return "troubleshooting"
    lowered = text.lower()
    question_form = bool(re.search(r"\b(?:what|why|how|when|which|difference)\b|什么|为什么|如何|怎么|区别", lowered))
    setup_action = bool(re.search(
        r"\b(?:set\s*up|configure|prepare|build|generate|simulate|run)\b|设置|配置|生成|准备.*模拟|运行.*模拟",
        lowered,
    ))
    if setup_action or (_extract_explicit_values(text) and not question_form):
        return "setup"
    return "general"


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
            proposed = client.structured_chat(
                messages,
                schema=_extraction_schema(),
                function_name="extract_md_parameters",
                max_tokens=600,
            )
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

    @blueprint.post("/chat")
    def expert_chat():
        data = request.get_json(silent=True) or {}
        question = str(data.get("message", "")).strip()
        if len(question) < 3:
            return _error("Enter a simulation setup or troubleshooting question")
        if len(question) > 12000:
            return _error("The message exceeds the 12,000 character limit")
        client = llm_client_getter()
        if client is None:
            return _error("The language model service is not configured", 503)

        current = data.get("parameters") if isinstance(data.get("parameters"), dict) else {}
        structures = data.get("structures") if isinstance(data.get("structures"), list) else []
        locked = {str(item) for item in data.get("locked_fields", []) if isinstance(item, str)}
        history = _clean_history(data.get("history"))
        system_prompt = (
            "You are an expert AMBER molecular-dynamics consultant for standard soluble single-protein, "
            "protein-protein, and protein-small-molecule systems. Respond in the user's language while "
            "preserving exact AMBER keywords and concise code snippets. For setup requests, extract only "
            "explicitly requested parameters. For setup intent, answer in at most 120 words and do not write "
            "complete AMBER input files or execution scripts; the Builder templates are the source of truth. "
            "Set auto_apply=true only when the user directly asks to set, "
            "configure, or generate a simulation with those conditions. For troubleshooting, set "
            "auto_apply=false, rank plausible causes, state what evidence distinguishes them, and provide "
            "actionable tleap, pmemd/sander, cpptraj, or input-file changes. Never assume apparent ligand "
            "escape is real before checking periodic-boundary imaging with cpptraj autoimage. Check preparation, "
            "protonation, ligand charge/GAFF parameters, minimization, heating, equilibration, restraints, box "
            "size, timestep, SHAKE, thermostat/barostat, and trajectory imaging as relevant. Keep troubleshooting "
            "answers under 450 words. The generated workflow uses two-stage minimization, 200 ps restrained heating, "
            "1 ns staged equilibration, and Monte Carlo barostat settings unless the user explicitly changes them. "
            "Its heating restraint is 5 kcal/mol/A^2 on protein backbone atoms @CA,C,N,O; equilibration uses 1 "
            "kcal/mol/A^2 on the same mask; the ligand is not restrained by default. Do not state a current value "
            "unless it is present in the supplied parameters or generated_protocol context. "
            "Do not invent log "
            "messages or claim certainty without evidence. Flag unsupported metal, covalent, membrane, nucleic-acid, "
            "glycosylated, or other special chemistry instead of giving a routine-protein recipe."
        )
        context = {
            "question": question,
            "current_parameters": current,
            "locked_fields": sorted(locked),
            "structure_metadata": structures,
            "generated_protocol": {
                "minimization": "two stages",
                "heating": "restrained NVT; default 200 ps; protein backbone restraint 5 kcal/mol/A^2",
                "equilibration": "NPT; default 1000 ps; protein backbone restraint 1 kcal/mol/A^2",
                "production": "NPT; Langevin thermostat; Monte Carlo barostat; SHAKE; 2 fs default timestep",
                "ligand_restraints": "none by default",
            },
        }
        messages = [{"role": "system", "content": system_prompt}, *history, {
            "role": "user", "content": json.dumps(context, ensure_ascii=False),
        }]
        try:
            result = client.structured_chat(
                messages,
                schema=_expert_schema(),
                function_name="answer_md_expert",
                max_tokens=900 if _is_troubleshooting(question) else 650,
            )
        except Exception as exc:
            return _error(f"MD Expert is unavailable: {exc}", 502)

        intent = result.get("intent") if result.get("intent") in {"setup", "troubleshooting", "general"} else "general"
        if _is_troubleshooting(question):
            intent = "troubleshooting"
        raw_updates = result.get("parameter_updates") if isinstance(result.get("parameter_updates"), dict) else {}
        allowed = set(_expert_schema()["properties"]["parameter_updates"]["properties"])
        updates = {key: value for key, value in raw_updates.items() if key in allowed and key not in locked and value is not None}
        auto_apply = bool(result.get("auto_apply")) and intent == "setup"
        if auto_apply:
            explicit_keys = _explicit_parameter_keys(question)
            updates = {key: value for key, value in updates.items() if key in explicit_keys}
            updates = {**updates, **{key: value for key, value in _extract_explicit_values(question).items() if key not in locked}}
        checks = result.get("diagnostic_checks") if isinstance(result.get("diagnostic_checks"), list) else []
        return jsonify({
            "success": True,
            "answer": (str(result.get("answer", "")).strip() or "I could not form a reliable answer from the available context.")[:6000],
            "intent": intent,
            "confidence": result.get("confidence") if result.get("confidence") in {"low", "medium", "high"} else "low",
            "auto_apply": auto_apply,
            "parameter_updates": updates,
            "diagnostic_checks": [str(item)[:500] for item in checks[:6] if str(item).strip()],
        })

    @blueprint.post("/chat-stream")
    def expert_chat_stream():
        data = request.get_json(silent=True) or {}
        question = str(data.get("message", "")).strip()
        if len(question) < 3:
            return _error("Enter a simulation setup or troubleshooting question")
        if len(question) > 12000:
            return _error("The message exceeds the 12,000 character limit")

        # Structured setup and troubleshooting responses retain the existing safety path.
        if _expert_intent_hint(question) != "general":
            return expert_chat()

        client = llm_client_getter()
        if client is None:
            return _error("The language model service is not configured", 503)
        history = _clean_history(data.get("history"), limit=6, content_limit=1800)
        messages = [{
            "role": "system",
            "content": (
                "You are a concise AMBER molecular-dynamics expert. Answer the user's general question in the "
                "user's language in at most 220 words. Preserve exact AMBER and cpptraj keywords and include a "
                "short command or input snippet only when it adds practical value. Cover standard soluble protein, "
                "protein-protein, and protein-small-molecule systems. Clearly flag membrane, metal, covalent, "
                "nucleic-acid, glycosylated, or other special chemistry as requiring a specialized workflow."
            ),
        }, *history, {"role": "user", "content": question}]

        def generate_events():
            yield f"data: {json.dumps({'type': 'meta', 'intent': 'general'})}\n\n"
            try:
                for delta in client.stream_chat(messages, temperature=0.2, max_tokens=500):
                    if delta.content:
                        payload = {"type": "delta", "content": delta.content}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'confidence': 'medium'})}\n\n"
            except Exception as exc:
                payload = {"type": "error", "error": f"MD Expert is unavailable: {exc}"}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(generate_events()),
            mimetype="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
