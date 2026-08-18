from __future__ import annotations

import hmac
import json
import os
from flask import Blueprint, jsonify, request, send_file

from services.docking import DockingError, docking_manager, engine_status


def _enabled() -> bool:
    return os.getenv("DOCKING_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def create_docking_blueprint(manager=None, enabled=None) -> Blueprint:
    manager = manager or docking_manager
    blueprint = Blueprint("docking", __name__, url_prefix="/api/docking")

    def feature_enabled() -> bool:
        return _enabled() if enabled is None else bool(enabled)

    def local_smoke_authorized() -> bool:
        expected = os.getenv("DOCKING_SMOKE_TOKEN", "")
        supplied = request.headers.get("X-Docking-Smoke-Token", "")
        return bool(
            expected
            and supplied
            and request.remote_addr in {"127.0.0.1", "::1"}
            and hmac.compare_digest(expected, supplied)
        )

    @blueprint.get("/status")
    def status():
        enabled = feature_enabled()
        worker = manager.worker_status()
        engines = worker.get("engines") or engine_status()
        if not enabled or not worker["online"]:
            engines = {key: {**value, "available": False} for key, value in engines.items()}
        return jsonify({"success": True, "enabled": enabled, "worker": worker, "engines": engines})

    @blueprint.post("/jobs")
    def create_job():
        if not feature_enabled() and not local_smoke_authorized():
            return jsonify({
                "success": False,
                "status": "maintenance",
                "error": "Docking is not enabled on this deployment",
            }), 503
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
            job = manager.create(kind, options, uploads)
            return jsonify({"success": True, "job": job.public()}), 202
        except (DockingError, json.JSONDecodeError) as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

    @blueprint.get("/jobs/<job_id>")
    def get_job(job_id: str):
        job = manager.get(job_id)
        if job is None:
            return jsonify({"success": False, "error": "Docking job not found"}), 404
        return jsonify({"success": True, "job": job.public()})

    @blueprint.get("/jobs/<job_id>/poses/<pose_id>/complex.pdb")
    def download_pose(job_id: str, pose_id: str):
        try:
            path = manager.pose_artifact(job_id, pose_id, "complex")
            return send_file(path, mimetype="chemical/x-pdb", as_attachment=True, download_name=f"{pose_id}-complex.pdb")
        except DockingError as exc:
            return jsonify({"success": False, "error": str(exc)}), 404

    @blueprint.get("/jobs/<job_id>/poses/<pose_id>/structure")
    def pose_structure(job_id: str, pose_id: str):
        try:
            path = manager.pose_artifact(job_id, pose_id, "structure")
            return send_file(path, mimetype="chemical/x-pdb", conditional=True)
        except DockingError as exc:
            return jsonify({"success": False, "error": str(exc)}), 404

    return blueprint
