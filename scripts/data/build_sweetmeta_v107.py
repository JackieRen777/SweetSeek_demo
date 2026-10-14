#!/usr/bin/env python3
"""Build the reviewed SweetMeta v1.0.7 release from the 2026-10-05 package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = ROOT / "outputs/sweetmeta-literature-rescan/SweetDatabase_v1.0.6_20260921.sqlite"
DEFAULT_REVIEWED = ROOT / "data/sweetmeta_reviewed_20261005"
DEFAULT_OUTPUT_DIR = ROOT / "outputs/sweetmeta-reviewed-v107"
DEFAULT_OUTPUT = DEFAULT_OUTPUT_DIR / "SweetDatabase_v1.0.7_20261005.sqlite"
RELEASE_VERSION = "v1.0.7"
REVIEW_DATE = "2026-10-05"

FILES = {
    "master": "compound_master_1296.csv",
    "taxonomy": "sweetclass_taxonomy_1296.csv",
    "umap": "umap_coordinates_1296.csv",
    "pca": "pca_coordinates_1296.csv",
    "provenance": "compound_provenance_1296.csv",
    "properties": "physicochemical_descriptors_1296.csv",
    "family_summary": "statistics/sweetclass_family_summary.csv",
    "source_to_evidence": "statistics/source_collection_to_evidence_tier.csv",
    "evidence_to_family": "statistics/evidence_tier_to_molecular_family.csv",
    "evidence_by_family": "statistics/evidence_tier_by_molecular_family.csv",
    "module_counts": "statistics/information_module_counts.csv",
    "source_lineage": "statistics/umap_source_lineage_1296.csv",
    "benchmark_metrics": "benchmark/model_metrics.csv",
    "benchmark_splits": "benchmark/split_class_counts.csv",
    "benchmark_summary": "benchmark/benchmark_summary.json",
    "data_dictionary": "DATA_DICTIONARY.md",
}

EXTENSION_TABLES = (
    "literature_records",
    "literature_compound_links",
    "food_occurrences",
    "regulatory_substances",
    "regulatory_evaluations",
    "receptor_activities",
    "taste_assertions",
    "sweetness_measurements",
)

EXPECTED_REVIEWED_OVERRIDES = {
    ("CMP_WBYWAXJHAXSJNI-VOTSOKGWSA-N", "preferred_name"): ("trans-Cinnamic acid", "182_Fnb"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require_rows(name: str, rows: list[dict[str, str]], expected: int = 1296) -> set[str]:
    if len(rows) != expected:
        raise ValueError(f"{name}: expected {expected} rows, found {len(rows)}")
    ids = {row["compound_id"].strip() for row in rows}
    if len(ids) != expected or "" in ids:
        raise ValueError(f"{name}: compound_id must contain {expected} unique non-empty values")
    return ids


def number(value: str) -> float | None:
    return None if value is None or str(value).strip() == "" else float(value)


def integer(value: str) -> int | None:
    parsed = number(value)
    return None if parsed is None else int(parsed)


def existing_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {table: conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in EXTENSION_TABLES}


def validate_sources(reviewed: Path, conn: sqlite3.Connection) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
    data = {key: read_csv(reviewed / rel) for key, rel in FILES.items() if rel.endswith(".csv")}
    master_ids = require_rows("master", data["master"])
    for key in ("taxonomy", "umap", "pca", "provenance", "properties", "source_lineage"):
        ids = require_rows(key, data[key])
        if ids != master_ids:
            raise ValueError(f"{key}: compound_id set differs from reviewed master")

    taxonomy = data["taxonomy"]
    if len({row["sweetclass_level1"] for row in taxonomy}) != 7:
        raise ValueError("taxonomy: expected 7 SweetClass level-1 families")
    if len({row["sweetclass_level2"] for row in taxonomy}) != 28:
        raise ValueError("taxonomy: expected 28 SweetClass level-2 families")
    if any(not row["PC1"].strip() or not row["PC2"].strip() for key in ("umap", "pca") for row in data[key]):
        raise ValueError("projection: every reviewed compound must have two coordinates")
    property_fields = ("molecular_weight", "clogp", "tpsa", "rotatable_bonds", "hba", "hbd", "bertz_complexity", "fraction_csp3", "heavy_atom_count")
    missing = [(row["compound_id"], field) for row in data["properties"] for field in property_fields if not row[field].strip()]
    if missing:
        raise ValueError(f"properties: {len(missing)} required values are missing")
    if sum(int(row["molecule_count"]) for row in data["source_to_evidence"]) != 1296:
        raise ValueError("evidence flow: source-to-evidence counts do not sum to 1296")
    if sum(int(row["molecule_count"]) for row in data["evidence_to_family"]) != 1296:
        raise ValueError("evidence flow: evidence-to-family counts do not sum to 1296")

    db_rows = {
        row["compound_id"]: dict(row)
        for row in conn.execute("""
            SELECT c.* FROM compounds c
            JOIN release_v1_compound_status r ON r.compound_id=c.compound_id
        """)
    }
    if set(db_rows) != master_ids:
        raise ValueError("database public compound IDs differ from reviewed master")
    overlap = (
        "preferred_name", "parent_inchikey", "parent_isomeric_smiles",
        "parent_canonical_smiles", "molecular_formula", "molecular_weight",
    )
    mismatches: list[dict[str, str]] = []
    for row in data["master"]:
        current = db_rows[row["compound_id"]]
        for field in overlap:
            left, right = str(current[field] or "").strip(), str(row[field] or "").strip()
            try:
                equal = abs(float(left) - float(right)) < 1e-9
            except ValueError:
                equal = left == right
            if not equal:
                mismatches.append({"compound_id": row["compound_id"], "field": field, "database": left, "reviewed": right})
    observed = {
        (row["compound_id"], row["field"]): (row["database"], row["reviewed"])
        for row in mismatches
    }
    if observed != EXPECTED_REVIEWED_OVERRIDES:
        raise ValueError(
            "reviewed master contains unexpected identity differences: "
            + json.dumps(mismatches, ensure_ascii=False)
        )
    return data, mismatches


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS compound_sweetclass;
        DROP TABLE IF EXISTS compound_projection;
        DROP TABLE IF EXISTS compound_provenance;
        DROP TABLE IF EXISTS compound_physicochemical;
        DROP TABLE IF EXISTS compound_stereo_review;
        DROP TABLE IF EXISTS reviewed_stat_sweetclass_family;
        DROP TABLE IF EXISTS reviewed_stat_source_evidence;
        DROP TABLE IF EXISTS reviewed_stat_evidence_family;
        DROP TABLE IF EXISTS reviewed_stat_evidence_by_family;
        DROP TABLE IF EXISTS reviewed_stat_module_counts;
        DROP TABLE IF EXISTS reviewed_benchmark_metrics;
        DROP TABLE IF EXISTS reviewed_benchmark_splits;
        DROP TABLE IF EXISTS reviewed_release_metadata;

        CREATE TABLE compound_sweetclass (
          compound_id TEXT PRIMARY KEY REFERENCES compounds(compound_id),
          level1 TEXT NOT NULL, level2 TEXT NOT NULL,
          assignment_basis TEXT, classification_status TEXT,
          analysis_chemical_class TEXT, classification_provenance TEXT,
          classyfire_kingdom TEXT, classyfire_superclass TEXT,
          classyfire_class TEXT, classyfire_subclass TEXT,
          classyfire_direct_parent TEXT, recovery_method TEXT,
          recovery_confidence TEXT
        );
        CREATE TABLE compound_projection (
          compound_id TEXT NOT NULL REFERENCES compounds(compound_id),
          method TEXT NOT NULL CHECK(method IN ('umap','pca')),
          x REAL NOT NULL, y REAL NOT NULL,
          fingerprint TEXT NOT NULL, metric TEXT NOT NULL,
          random_seed INTEGER NOT NULL,
          PRIMARY KEY (compound_id, method)
        );
        CREATE TABLE compound_provenance (
          compound_id TEXT PRIMARY KEY REFERENCES compounds(compound_id),
          source_collection TEXT NOT NULL, source_names TEXT NOT NULL,
          evidence_grade TEXT NOT NULL CHECK(evidence_grade IN ('E1','E2','E3')),
          evidence_tier TEXT NOT NULL, evidence_lineage_status TEXT NOT NULL,
          family_short TEXT NOT NULL
        );
        CREATE TABLE compound_physicochemical (
          compound_id TEXT PRIMARY KEY REFERENCES compounds(compound_id),
          molecular_weight REAL NOT NULL, clogp REAL NOT NULL, tpsa REAL NOT NULL,
          rotatable_bonds INTEGER NOT NULL, hba INTEGER NOT NULL, hbd INTEGER NOT NULL,
          bertz_complexity REAL NOT NULL, log10_bertz_complexity REAL NOT NULL,
          fraction_csp3 REAL NOT NULL, heavy_atom_count INTEGER NOT NULL,
          calculation_source TEXT NOT NULL
        );
        CREATE TABLE compound_stereo_review (
          compound_id TEXT PRIMARY KEY REFERENCES compounds(compound_id),
          qc_applicable TEXT NOT NULL, source_structure_decision TEXT,
          source_supported_isomeric_smiles TEXT, source_supported_inchi TEXT,
          source_supported_inchikey TEXT, unresolved_stereocenter_count INTEGER,
          unresolved_stereocenter TEXT, candidate_2r_isomeric_smiles TEXT,
          candidate_2r_inchi TEXT, candidate_2r_inchikey TEXT,
          candidate_2s_isomeric_smiles TEXT, candidate_2s_inchi TEXT,
          candidate_2s_inchikey TEXT, sweetness_evidence TEXT,
          strict_exact_benchmark_status TEXT
        );
        CREATE TABLE reviewed_release_metadata (
          key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE reviewed_stat_sweetclass_family (
          level1 TEXT PRIMARY KEY, molecule_count INTEGER NOT NULL,
          share_percent REAL NOT NULL, display_name TEXT NOT NULL
        );
        CREATE TABLE reviewed_stat_source_evidence (
          source_collection TEXT NOT NULL, evidence_grade TEXT NOT NULL,
          molecule_count INTEGER NOT NULL, PRIMARY KEY(source_collection, evidence_grade)
        );
        CREATE TABLE reviewed_stat_evidence_family (
          evidence_grade TEXT NOT NULL, family_short TEXT NOT NULL,
          molecule_count INTEGER NOT NULL, PRIMARY KEY(evidence_grade, family_short)
        );
        CREATE TABLE reviewed_stat_evidence_by_family (
          family_short TEXT NOT NULL, evidence_grade TEXT NOT NULL,
          molecule_count INTEGER NOT NULL, family_total INTEGER NOT NULL,
          within_family_percent REAL NOT NULL, PRIMARY KEY(family_short, evidence_grade)
        );
        CREATE TABLE reviewed_stat_module_counts (
          module TEXT PRIMARY KEY, display_metric TEXT NOT NULL,
          native_grain TEXT NOT NULL, count INTEGER NOT NULL, color TEXT NOT NULL
        );
        CREATE TABLE reviewed_benchmark_metrics (
          model TEXT NOT NULL, split TEXT NOT NULL, seed TEXT NOT NULL,
          n INTEGER NOT NULL, threshold REAL NOT NULL, roc_auc REAL NOT NULL,
          pr_auc REAL NOT NULL, balanced_accuracy REAL NOT NULL, f1 REAL NOT NULL,
          mcc REAL NOT NULL, precision REAL NOT NULL, recall REAL NOT NULL,
          brier REAL NOT NULL, tn INTEGER NOT NULL, fp INTEGER NOT NULL,
          fn INTEGER NOT NULL, tp INTEGER NOT NULL, display_model TEXT NOT NULL,
          PRIMARY KEY(model, split, seed)
        );
        CREATE TABLE reviewed_benchmark_splits (
          split TEXT PRIMARY KEY, negative_count INTEGER NOT NULL,
          positive_count INTEGER NOT NULL, total INTEGER NOT NULL
        );
        CREATE INDEX idx_sweetclass_level1 ON compound_sweetclass(level1);
        CREATE INDEX idx_sweetclass_level2 ON compound_sweetclass(level2);
        CREATE INDEX idx_provenance_grade ON compound_provenance(evidence_grade);
        CREATE INDEX idx_physicochemical_mw ON compound_physicochemical(molecular_weight);
        CREATE INDEX idx_physicochemical_clogp ON compound_physicochemical(clogp);
        CREATE INDEX idx_physicochemical_tpsa ON compound_physicochemical(tpsa);
    """)


def populate(conn: sqlite3.Connection, reviewed: Path, data: dict[str, list[dict[str, str]]]) -> None:
    for row in data["master"]:
        conn.execute("""
            UPDATE compounds SET preferred_name=?, parent_inchikey=?, parent_isomeric_smiles=?,
                parent_canonical_smiles=?, molecular_formula=?, molecular_weight=?
            WHERE compound_id=?
        """, (row["preferred_name"], row["parent_inchikey"], row["parent_isomeric_smiles"],
              row["parent_canonical_smiles"], row["molecular_formula"], number(row["molecular_weight"]), row["compound_id"]))

    sweetclass_columns = (
        "compound_id", "sweetclass_level1", "sweetclass_level2", "sweetclass_assignment_basis",
        "classification_status", "analysis_chemical_class", "analysis_classification_provenance",
        "classyfire_kingdom", "classyfire_superclass", "classyfire_class", "classyfire_subclass",
        "classyfire_direct_parent", "recovery_method", "recovery_confidence",
    )
    conn.executemany(
        "INSERT INTO compound_sweetclass VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [tuple(row.get(column, "") or None for column in sweetclass_columns) for row in data["taxonomy"]],
    )
    projection_specs = {
        "umap": ("Jaccard distance", 20260825),
        "pca": ("Euclidean PCA on binary ECFP4 matrix", 20260825),
    }
    for method, (metric, seed) in projection_specs.items():
        conn.executemany(
            "INSERT INTO compound_projection VALUES (?,?,?,?,?,?,?)",
            [(row["compound_id"], method, float(row["PC1"]), float(row["PC2"]),
              "Morgan / ECFP4 (radius 2, 2048 bits)", metric, seed) for row in data[method]],
        )
    conn.executemany(
        "INSERT INTO compound_provenance VALUES (?,?,?,?,?,?,?)",
        [(row["compound_id"], row["source_collection"], row["source_names"], row["evidence_short"],
          row["evidence_tier"], row["evidence_lineage_status"], row["family_short"])
         for row in data["provenance"]],
    )
    conn.executemany(
        "INSERT INTO compound_physicochemical VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(row["compound_id"], number(row["molecular_weight"]), number(row["clogp"]), number(row["tpsa"]),
          integer(row["rotatable_bonds"]), integer(row["hba"]), integer(row["hbd"]),
          number(row["bertz_complexity"]), number(row["log10_bertz_complexity"]),
          number(row["fraction_csp3"]), integer(row["heavy_atom_count"]),
          "RDKit parent-normalized structure; reviewed 2026-10-05") for row in data["properties"]],
    )
    stereo_columns = (
        "compound_id", "huan_stereo_qc_applicable", "huan_source_structure_decision",
        "huan_source_supported_isomeric_smiles", "huan_source_supported_inchi", "huan_source_supported_inchikey",
        "huan_unresolved_stereocenter_count", "huan_unresolved_stereocenter",
        "huan_candidate_2R_isomeric_smiles", "huan_candidate_2R_inchi", "huan_candidate_2R_inchikey",
        "huan_candidate_2S_isomeric_smiles", "huan_candidate_2S_inchi", "huan_candidate_2S_inchikey",
        "huan_sweetness_evidence", "huan_strict_exact_benchmark_status",
    )
    stereo_rows = [row for row in data["master"] if row["huan_stereo_qc_applicable"].strip()]
    conn.executemany(
        "INSERT INTO compound_stereo_review VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [tuple(integer(row[column]) if column == "huan_unresolved_stereocenter_count" else (row[column] or None) for column in stereo_columns)
         for row in stereo_rows],
    )
    conn.executemany(
        "INSERT INTO reviewed_stat_sweetclass_family VALUES (?,?,?,?)",
        [(row["sweetclass_level1"], integer(row["n"]), number(row["share_pct"]), row["display_name"])
         for row in data["family_summary"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_stat_source_evidence VALUES (?,?,?)",
        [(row["source_collection"], row["evidence_short"], integer(row["molecule_count"]))
         for row in data["source_to_evidence"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_stat_evidence_family VALUES (?,?,?)",
        [(row["evidence_short"], row["family_short"], integer(row["molecule_count"]))
         for row in data["evidence_to_family"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_stat_evidence_by_family VALUES (?,?,?,?,?)",
        [(row["family_short"], row["evidence_short"], integer(row["molecule_count"]),
          integer(row["family_total"]), number(row["within_family_percent"]))
         for row in data["evidence_by_family"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_stat_module_counts VALUES (?,?,?,?,?)",
        [(row["module"], row["display_metric"], row["native_grain"], integer(row["count"]), row["color"])
         for row in data["module_counts"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_benchmark_metrics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(row["model"], row["split"], row["seed"], integer(row["n"]), number(row["threshold"]),
          number(row["roc_auc"]), number(row["pr_auc"]), number(row["balanced_accuracy"]),
          number(row["f1"]), number(row["mcc"]), number(row["precision"]), number(row["recall"]),
          number(row["brier"]), integer(row["tn"]), integer(row["fp"]), integer(row["fn"]),
          integer(row["tp"]), row["display_model"]) for row in data["benchmark_metrics"]],
    )
    conn.executemany(
        "INSERT INTO reviewed_benchmark_splits VALUES (?,?,?,?)",
        [(row["split"], integer(row["0"]), integer(row["1"]), integer(row["total"]))
         for row in data["benchmark_splits"]],
    )
    metadata = {
        "version": RELEASE_VERSION,
        "review_date": REVIEW_DATE,
        "release_label": "SweetMeta v1.0.7 (2026-10-05 reviewed snapshot)",
        "source_release": "SweetDatabase_v1.0.6_20260921.sqlite",
        "public_compounds": "1296",
        "sweetclass_level1_count": "7",
        "sweetclass_level2_count": "28",
        "stereo_review_count": str(len(stereo_rows)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for key, rel in FILES.items():
        path = reviewed / rel
        metadata[f"sha256_{key}"] = sha256(path)
    conn.executemany("INSERT INTO reviewed_release_metadata VALUES (?,?)", metadata.items())


def package_sources(reviewed: Path, output_dir: Path) -> Path:
    archive = output_dir / "SweetMeta_v1.0.7_reviewed_sources_20261005.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(reviewed.rglob("*")):
            if path.is_file():
                bundle.write(path, Path("SweetMeta_v1.0.7_reviewed_sources_20261005") / path.relative_to(reviewed))
    return archive


def write_manifest(output_dir: Path, reviewed: Path, database: Path, sources: Path, before: dict[str, int], after: dict[str, int], overrides: list[dict[str, str]]) -> Path:
    manifest = {
        "version": RELEASE_VERSION,
        "label": "SweetMeta v1.0.7 (2026-10-05 reviewed snapshot)",
        "reviewDate": REVIEW_DATE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "validation": {"publicCompounds": 1296, "sweetClassLevel1": 7, "sweetClassLevel2": 28, "extensionCountsPreserved": before == after},
        "extensionCounts": after,
        "reviewedOverrides": overrides,
        "artifacts": [
            {"key": "database", "filename": database.name, "bytes": database.stat().st_size, "sha256": sha256(database)},
            {"key": "sources", "filename": sources.name, "bytes": sources.stat().st_size, "sha256": sha256(sources)},
            {"key": "dictionary", "filename": "DATA_DICTIONARY.md", "bytes": (reviewed / "DATA_DICTIONARY.md").stat().st_size, "sha256": sha256(reviewed / "DATA_DICTIONARY.md")},
        ],
        "sourceFiles": {rel: sha256(reviewed / rel) for rel in FILES.values()},
    }
    path = output_dir / "release_manifest_v1.0.7.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build(source: Path, reviewed: Path, output: Path) -> dict[str, Any]:
    if not source.is_file():
        raise FileNotFoundError(source)
    for rel in FILES.values():
        if not (reviewed / rel).is_file():
            raise FileNotFoundError(reviewed / rel)
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, output)
    conn = sqlite3.connect(output)
    conn.row_factory = sqlite3.Row
    try:
        before = existing_counts(conn)
        data, overrides = validate_sources(reviewed, conn)
        create_tables(conn)
        populate(conn, reviewed, data)
        conn.commit()
        after = existing_counts(conn)
        if before != after:
            raise ValueError("extension module counts changed during reviewed release build")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SQLite integrity check failed: {integrity}")
    except Exception:
        conn.close()
        output.unlink(missing_ok=True)
        raise
    finally:
        if conn:
            conn.close()
    sources = package_sources(reviewed, output.parent)
    manifest = write_manifest(output.parent, reviewed, output, sources, before, after, overrides)
    return {"database": str(output), "manifest": str(manifest), "sources": str(sources), "sha256": sha256(output), "extensionCounts": after}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--reviewed", type=Path, default=DEFAULT_REVIEWED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.reviewed, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
