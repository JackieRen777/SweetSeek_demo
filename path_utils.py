"""Path normalization utilities for cross-environment portability.

All persisted paths are stored as relative POSIX paths from BASE_DIR.
At runtime, they are resolved back to absolute paths using the current BASE_DIR.
"""

from pathlib import Path, PurePosixPath

from config import Config

BASE_DIR = Config.BASE_DIR

_KNOWN_ANCHORS = (
    "sweet_related_paper/",
    "Dual_Protein_related_paper/",
    "food_research_data/",
    "data/",
)


def to_relative(abs_path: str) -> str:
    """Convert any path to a relative POSIX path from BASE_DIR.

    Handles paths from different machines by scanning for known project anchors.
    """
    if not abs_path:
        return ""

    p = Path(abs_path)

    # Already relative — just normalize to POSIX
    if not p.is_absolute():
        return str(PurePosixPath(p))

    # Try direct relative_to
    try:
        rel = p.relative_to(BASE_DIR)
        return str(PurePosixPath(rel))
    except ValueError:
        pass

    # Path from another machine — scan for known anchors
    posix = str(PurePosixPath(p))
    for anchor in _KNOWN_ANCHORS:
        idx = posix.find(anchor)
        if idx != -1:
            return posix[idx:]

    # Last resort: filename only
    return p.name


def to_absolute(rel_path: str) -> str:
    """Resolve a relative POSIX path back to an absolute path using current BASE_DIR."""
    if not rel_path:
        return ""
    p = Path(rel_path)
    if p.is_absolute():
        return str(p)
    return str(BASE_DIR / rel_path)


def normalize_for_storage(file_path: str) -> str:
    """Normalize any path (absolute or relative, from any machine) to canonical storage form."""
    return to_relative(file_path)
