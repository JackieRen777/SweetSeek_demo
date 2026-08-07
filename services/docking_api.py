from __future__ import annotations

import json
from flask import Blueprint, jsonify, request

from services.docking import DockingError, docking_manager, engine_status


def create_docking_blueprint() -> Blueprint:
    blueprint = Blueprint("docking", __name__, url_prefix="/api/docking")

    @blueprint.get("/status")
    def status():
        return jsonify({"success": True, "engines": engine_status()})

    @blueprint.post("/jobs")
    def create_job():
        try:
            options = json.loads(request.form.get("options", "{}"))
            if not isinstance(options, dict):
                raise DockingError("options must be an object")
            kind = str(request.form.get("kind", ""))
            uploads = {}
            for role in ("receptor", "ligand"):
                upload = request.files.get(role)
                if upload is None:
                    raise DockingError(f"Missing {role} upload")
                uploads[role] = (upload.filename or "", upload.read())
            job = docking_manager.create(kind, options, uploads)
            return jsonify({"success": True, "job": job.public()}), 202
        except (DockingError, json.JSONDecodeError) as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

    @blueprint.get("/jobs/<job_id>")
    def get_job(job_id: str):
        job = docking_manager.get(job_id)
        if job is None:
            return jsonify({"success": False, "error": "Docking job not found"}), 404
        return jsonify({"success": True, "job": job.public()})

    return blueprint
