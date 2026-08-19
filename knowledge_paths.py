"""Central paths for SweetSeek's domain-specific paper databases."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent


def _resolve(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


CITATION_CATALOG_ROOT = _resolve(
    os.getenv("CITATION_CATALOG_ROOT", PROJECT_ROOT / "data" / "citations")
)


PAPER_DATABASE_ROOT = _resolve(
    os.getenv("PAPER_DATABASE_ROOT", PROJECT_ROOT / "SweetSeek_paper_database")
)


@dataclass(frozen=True)
class KnowledgeDomainPaths:
    papers: Path
    metadata: Path
    citation_catalog: Path
    index: Path


_DOMAIN_DEFAULTS = {
    "sweetness": ("sweetness", "faiss_db", "DATA_DIR", "METADATA_PATH", "PERSIST_DIR"),
    "dual_protein": (
        "dual_protein", "storage_dual_protein", "DUAL_PROTEIN_DATA_DIR",
        "DUAL_PROTEIN_METADATA_PATH", "DUAL_PROTEIN_PERSIST_DIR",
    ),
    "encapsulation": (
        "encapsulation", "storage_encapsulation", "ENCAPSULATION_DATA_DIR",
        "ENCAPSULATION_METADATA_PATH", "ENCAPSULATION_PERSIST_DIR",
    ),
    "proteoglycan": (
        "proteoglycan", "storage_proteoglycan", "PROTEOGLYCAN_DATA_DIR",
        "PROTEOGLYCAN_METADATA_PATH", "PROTEOGLYCAN_PERSIST_DIR",
    ),
}


def _env_path(name: str, default: Path) -> Path:
    return _resolve(os.getenv(name, str(default)))


def get_domain_paths(domain: str) -> KnowledgeDomainPaths:
    try:
        folder, index_folder, data_env, metadata_env, index_env = _DOMAIN_DEFAULTS[domain]
    except KeyError as exc:
        raise ValueError(f"Unknown knowledge domain: {domain}") from exc
    domain_root = PAPER_DATABASE_ROOT / folder
    return KnowledgeDomainPaths(
        papers=_env_path(data_env, domain_root / "papers"),
        metadata=_env_path(metadata_env, domain_root / "metadata.json"),
        citation_catalog=CITATION_CATALOG_ROOT / f"{domain}.json",
        index=_env_path(index_env, PROJECT_ROOT / index_folder),
    )


def get_runtime_metadata_path(domain: str) -> Path:
    """Return explicit metadata override or the release-local read-only catalog."""
    paths = get_domain_paths(domain)
    metadata_env = _DOMAIN_DEFAULTS[domain][3]
    if os.getenv(metadata_env):
        return paths.metadata
    return paths.citation_catalog if paths.citation_catalog.is_file() else paths.metadata
