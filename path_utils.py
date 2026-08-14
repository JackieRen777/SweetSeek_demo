"""Path normalization utilities for cross-environment portability.

All persisted paths are stored as relative POSIX paths from BASE_DIR.
At runtime, they are resolved back to absolute paths using the current BASE_DIR.
"""

from pathlib import Path, PurePosixPath

from config import Config
from knowledge_paths import PAPER_DATABASE_ROOT

BASE_DIR = Config.BASE_DIR

_KNOWN_ANCHORS = (
    "SweetSeek_paper_database/",
    "sweet_related_paper/",
    "Dual_Protein_related_paper/",
    "Encapsulation_related_paper/",
    "Proteoglycan_related_paper/",
    "food_research_data/",
    "data/",
)

_LEGACY_PREFIXES = {
    "sweet_related_paper/": "SweetSeek_paper_database/sweetness/",
    "Dual_Protein_related_paper/": "SweetSeek_paper_database/dual_protein/",
    "Encapsulation_related_paper/": "SweetSeek_paper_database/encapsulation/",
    "Proteoglycan_related_paper/": "SweetSeek_paper_database/proteoglycan/",
}


def _canonicalize_legacy_path(path: str) -> str:
    normalized = str(PurePosixPath(path.replace("\\", "/")))
    for old_prefix, new_prefix in _LEGACY_PREFIXES.items():
        index = normalized.find(old_prefix)
        if index != -1:
            return new_prefix + normalized[index + len(old_prefix):]
    return normalized


def to_relative(abs_path: str) -> str:
    """Convert any path to a relative POSIX path from BASE_DIR.

    Handles paths from different machines by scanning for known project anchors.
    """
    if not abs_path:
        return ""

    p = Path(abs_path)

    # Already relative — just normalize to POSIX
    if not p.is_absolute():
        return _canonicalize_legacy_path(str(PurePosixPath(p)))

    # Try direct relative_to
    try:
        rel = p.relative_to(BASE_DIR)
        return _canonicalize_legacy_path(str(PurePosixPath(rel)))
    except ValueError:
        pass

    # Path from another machine — scan for known anchors
    posix = str(PurePosixPath(p))
    for anchor in _KNOWN_ANCHORS:
        idx = posix.find(anchor)
        if idx != -1:
            return _canonicalize_legacy_path(posix[idx:])

    # Last resort: filename only
    return p.name


def to_absolute(rel_path: str) -> str:
    """Resolve a relative POSIX path back to an absolute path using current BASE_DIR."""
    if not rel_path:
        return ""
    canonical = _canonicalize_legacy_path(rel_path)
    p = Path(canonical)
    if p.is_absolute():
        return str(p)
    if canonical.startswith("SweetSeek_paper_database/"):
        suffix = canonical.removeprefix("SweetSeek_paper_database/")
        return str(PAPER_DATABASE_ROOT / suffix)
    return str(BASE_DIR / canonical)


def normalize_for_storage(file_path: str) -> str:
    """Normalize any path (absolute or relative, from any machine) to canonical storage form."""
    return to_relative(file_path)
