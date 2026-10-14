"""SweetMeta HTTP API backed by the versioned read-only SQLite release."""

from __future__ import annotations

import hashlib
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from services.sweetmeta_db import SweetMetaDatabase


def create_sweetmeta_blueprint(db: SweetMetaDatabase | None = None) -> Blueprint:
    database = db or SweetMetaDatabase()
    blueprint = Blueprint("sweetmeta", __name__, url_prefix="/api/sweetmeta")

    @blueprint.get("/health")
    def health():
        if not database.available:
            return jsonify({"ok": False, "status": "unavailable", "databasePath": str(database.path)}), 503
        try:
            return jsonify({"ok": True, "status": "healthy", **database.integrity()})
        except Exception as exc:
            return jsonify({"ok": False, "status": "degraded", "error": str(exc)}), 503

    @blueprint.get("/stats")
    def stats():
        return jsonify({"success": True, "data": database.stats()})

    @blueprint.get("/statistics")
    def statistics():
        if not database.available:
            return jsonify({"success": False, "error": "SweetMeta SQLite database is unavailable"}), 503
        try:
            return jsonify({"success": True, "data": database.statistics()})
        except (FileNotFoundError, OSError) as exc:
            return jsonify({"success": False, "error": str(exc)}), 503

    @blueprint.get("/releases")
    def releases():
        metadata = database.metadata()
        return jsonify({"success": True, "data": {"active": metadata.get("reviewedRelease") or metadata.get("reviewRelease") or metadata.get("rescanRelease") or metadata.get("release", {}), "releaseV1": metadata.get("releaseV1", {}), "rescanRelease": metadata.get("rescanRelease", {}), "reviewRelease": metadata.get("reviewRelease", {}), "reviewedRelease": metadata.get("reviewedRelease", {}), "sha256": metadata.get("databaseSha256")}})

    @blueprint.get("/compounds")
    def compounds():
        data = database.list_compounds(
            query=request.args.get("q", request.args.get("query", "")),
            page=request.args.get("page", 1, type=int),
            page_size=request.args.get("pageSize", request.args.get("limit", 25), type=int),
            tier=request.args.get("tier", ""),
            review=request.args.get("review", ""),
            domain=request.args.get("domain", ""),
            food_group=request.args.get("foodGroup", ""),
            sweetness_min_log10=request.args.get("sweetnessMinLog10", type=float),
            sweetness_max_log10=request.args.get("sweetnessMaxLog10", type=float),
            quality_metric=request.args.get("qualityMetric", ""),
            quality_state=request.args.get("qualityState", ""),
            sweet_class_l1=request.args.get("sweetClassL1", ""),
            sweet_class_l2=request.args.get("sweetClassL2", ""),
            evidence_grade=request.args.get("evidenceGrade", ""),
            source_collection=request.args.get("sourceCollection", ""),
            mw_min=request.args.get("mwMin", type=float),
            mw_max=request.args.get("mwMax", type=float),
            clogp_min=request.args.get("clogpMin", type=float),
            clogp_max=request.args.get("clogpMax", type=float),
            tpsa_min=request.args.get("tpsaMin", type=float),
            tpsa_max=request.args.get("tpsaMax", type=float),
        )
        return jsonify({"success": True, "data": data})

    @blueprint.get("/search")
    def search():
        data = database.list_compounds(query=request.args.get("q", ""), page=1, page_size=request.args.get("limit", 25, type=int), tier=request.args.get("tier", ""), review=request.args.get("review", ""))
        return jsonify({"success": True, "data": data})

    @blueprint.get("/literature")
    def literature():
        data = database.literature(
            query=request.args.get("q", request.args.get("query", "")),
            page=request.args.get("page", 1, type=int),
            page_size=request.args.get("pageSize", request.args.get("limit", 25), type=int),
            year=request.args.get("year", type=int),
            year_from=request.args.get("yearFrom", type=int),
            year_to=request.args.get("yearTo", type=int),
            pmid_only=request.args.get("pmidOnly", "").lower() in {"1", "true", "yes"},
            doi_only=request.args.get("doiOnly", "").lower() in {"1", "true", "yes"},
            review_status=request.args.get("reviewStatus", ""),
            relation_type=request.args.get("relationType", ""),
            compound_id=request.args.get("compoundId", ""),
            compound_family=request.args.get("compoundFamily", ""),
        )
        return jsonify({"success": True, "data": data})

    @blueprint.get("/compounds/<compound_id>")
    def compound(compound_id: str):
        data = database.compound(compound_id)
        if data is None:
            return jsonify({"success": False, "error": "Compound not found in the public release"}), 404
        literature = list({item["record_id"]: item for item in data.pop("literature", [])}.values())
        food = data.pop("foodOccurrences", [])
        regulatory = data.pop("regulatory", [])
        receptors = data.pop("receptorActivities", [])
        module_counts = data.pop("moduleCounts", {})
        assertions = data.pop("tasteAssertions", [])
        measurements = data.pop("measurements", [])
        conflicts = []
        try:
            with database.connection() as conn:
                conflicts = [dict(row) for row in conn.execute("SELECT * FROM data_conflicts WHERE compound_id=?", (compound_id,)).fetchall()]
        except Exception:
            conflicts = []
        result = {
            "compound": data,
            "identity": {
                "stableId": compound_id,
                "displayId": data.get("display_id"),
                "preferredName": data.get("preferred_name"),
                "preferredNameSource": data.get("preferred_name_source"),
                "aliases": data.get("aliases", []),
                "externalIds": data.get("externalIds", []),
            },
            "release": {key: data.get(key) for key in ("release_tier", "release_gap", "manual_review_required", "status_note")},
            "quality": {key: data.get(key) for key in data if key.startswith("qc_") or key in {"structure_verified", "stereochemistry_verified", "form_verified"}},
            "aliases": data.pop("aliases", []),
            "externalIds": data.pop("externalIds", []),
            "classification": data.pop("classification", None),
            "provenance": data.pop("provenance", None),
            "physicochemical": data.pop("physicochemical", None),
            "projections": data.pop("projections", []),
            "stereoReview": data.pop("stereoReview", None),
            "evidence": {"tasteAssertions": assertions, "measurements": measurements, "conflicts": conflicts},
            "literature": literature,
            "literatureReview": {"candidateCount": data.get("literatureCandidateCount", 0), "reviewRequiredCount": data.get("literatureReviewRequiredCount", 0)},
            "food": {"count": len(food), "items": food},
            "regulatory": {"count": len(regulatory), "items": regulatory},
            "receptors": {"count": len(receptors), "items": receptors},
            "modules": {
                "sweetness": module_counts.get("sweetness", len(measurements)),
                "literature": module_counts.get("literature", len(literature)),
                "food": module_counts.get("food", len(food)),
                "receptors": module_counts.get("receptors", len(receptors)),
                "regulatory": module_counts.get("regulatory", len(regulatory)),
                "conflicts": module_counts.get("conflicts", len(conflicts)),
            },
        }
        return jsonify({"success": True, "data": result})

    @blueprint.get("/compounds/<compound_id>/projection-context")
    def compound_projection_context(compound_id: str):
        data = database.projection_context(compound_id)
        if data is None:
            return jsonify({"success": False, "error": "Compound not found in the public release"}), 404
        return jsonify({"success": True, "data": data})

    def download_files() -> dict[str, Path]:
        root = Path(__file__).resolve().parents[1]
        release_dir = database.path.parent
        return {
            "database": database.path,
            "sources": release_dir / "SweetMeta_v1.0.7_reviewed_sources_20261005.zip",
            "dictionary": root / "data" / "sweetmeta_reviewed_20261005" / "DATA_DICTIONARY.md",
            "manifest": release_dir / "release_manifest_v1.0.7.json",
        }

    @blueprint.get("/downloads")
    def downloads():
        labels = {
            "database": "Reviewed SQLite database", "sources": "Reviewed CSV source package",
            "dictionary": "Data dictionary", "manifest": "Checksum manifest",
        }
        files = download_files()
        items = []
        for key, path in files.items():
            if not path.is_file():
                continue
            items.append({
                "key": key, "label": labels[key], "filename": path.name,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "url": f"/api/sweetmeta/downloads/{key}",
            })
        return jsonify({"success": True, "data": {
            "version": "v1.0.7", "reviewDate": "2026-10-05", "recordCount": 1296,
            "items": items,
        }})

    @blueprint.get("/downloads/<key>")
    def download(key: str):
        path = download_files().get(key)
        if path is None or not path.is_file():
            return jsonify({"success": False, "error": "Download not found"}), 404
        return send_file(path, as_attachment=True, download_name=path.name)

    @blueprint.get("/literature/<record_id>")
    def literature_detail(record_id: str):
        data = database.literature_detail(record_id)
        if data is None:
            return jsonify({"success": False, "error": "Literature record not found"}), 404
        return jsonify({"success": True, "data": data})

    return blueprint
