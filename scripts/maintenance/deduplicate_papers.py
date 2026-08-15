#!/usr/bin/env python3
"""Find and quarantine high-confidence duplicate PDFs in one knowledge domain."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from knowledge_paths import get_domain_paths  # noqa: E402


DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
DUPLICATE_SUFFIX_RE = re.compile(r"(?:\s*\(\d+\)|\s*\[\d+\]|\s+copy|\s+副本)$", re.IGNORECASE)


@dataclass
class Paper:
    path: str
    size: int
    sha256: str
    pages: int
    title: str
    doi: str
    valid: bool
    error: str = ""


class UnionFind:
    def __init__(self, count: int) -> None:
        self.parent = list(range(count))

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def normalize_doi(value: str) -> str:
    return value.strip().lower().rstrip(".,;:)]}")


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_pdf(path: Path, papers_root: Path) -> Paper:
    relative = path.relative_to(papers_root).as_posix()
    size = path.stat().st_size
    if size == 0:
        return Paper(relative, 0, hashlib.sha256(b"").hexdigest(), 0, "", "", False, "zero-byte file")

    digest = sha256(path)
    if digest == hashlib.sha256(b"").hexdigest():
        return Paper(relative, size, digest, 0, "", "", False, "dataless placeholder")
    try:
        document = fitz.open(path)
        if not document.is_pdf or document.page_count == 0:
            raise ValueError("not a readable PDF")
        metadata = document.metadata or {}
        title = (metadata.get("title") or "").strip()
        first_page = document[0].get_text()
        metadata_text = " ".join((metadata.get("subject") or "", metadata.get("keywords") or ""))
        doi_matches = DOI_RE.findall(metadata_text) or DOI_RE.findall(first_page[:16000])
        doi = normalize_doi(doi_matches[0]) if doi_matches else ""
        pages = document.page_count
        document.close()
        return Paper(relative, size, digest, pages, title, doi, True)
    except Exception as exc:
        return Paper(relative, size, digest, 0, "", "", False, str(exc))


def keeper_score(paper: Paper) -> tuple[int, int, int, float, int, int]:
    stem = Path(paper.path).stem
    has_duplicate_suffix = bool(DUPLICATE_SUFFIX_RE.search(stem))
    normalized_stem = normalize_title(DUPLICATE_SUFFIX_RE.sub("", stem))
    normalized_pdf_title = normalize_title(paper.title)
    similarity = SequenceMatcher(None, normalized_stem, normalized_pdf_title).ratio() if normalized_pdf_title else 0.0
    author_year_style = bool(re.search(r"\s-\s(?:19|20)\d{2}\s-\s", stem))
    generic_download_name = stem.lower().startswith("1-s2.0-")
    return (
        int(not has_duplicate_suffix),
        paper.pages,
        int(not generic_download_name),
        similarity,
        int(author_year_style),
        paper.size,
    )


def group_duplicates(papers: list[Paper]) -> list[dict[str, object]]:
    valid_indices = [index for index, paper in enumerate(papers) if paper.valid]
    union_find = UnionFind(len(papers))

    def merge_by(key_getter) -> None:
        grouped: dict[str, list[int]] = defaultdict(list)
        for index in valid_indices:
            key = key_getter(papers[index])
            if key:
                grouped[key].append(index)
        for indices in grouped.values():
            for other in indices[1:]:
                union_find.union(indices[0], other)

    merge_by(lambda paper: paper.sha256)
    # A DOI found in first-page text can occasionally belong to a cited paper.
    # Requiring the embedded title to agree keeps DOI grouping high-confidence.
    merge_by(
        lambda paper: f"{paper.doi}|{normalize_title(paper.title)}"
        if paper.doi and len(normalize_title(paper.title)) >= 30
        else ""
    )
    merge_by(lambda paper: normalize_title(paper.title) if len(normalize_title(paper.title)) >= 30 else "")

    components: dict[int, list[int]] = defaultdict(list)
    for index in valid_indices:
        components[union_find.find(index)].append(index)

    groups = []
    for indices in components.values():
        if len(indices) < 2:
            continue
        keeper = max(indices, key=lambda index: keeper_score(papers[index]))
        members = [papers[index] for index in indices]
        reason = "sha256" if len({paper.sha256 for paper in members}) == 1 else (
            "doi" if len({paper.doi for paper in members if paper.doi}) == 1 else "title"
        )
        groups.append({
            "reason": reason,
            "keep": papers[keeper].path,
            "quarantine": sorted(paper.path for index, paper in zip(indices, members) if index != keeper),
            "doi": papers[keeper].doi,
            "title": papers[keeper].title,
        })
    return sorted(groups, key=lambda group: str(group["keep"]))


def scan(domain: str) -> tuple[Path, list[Paper], list[dict[str, object]]]:
    paths = get_domain_paths(domain)
    papers_root = paths.papers
    papers = [inspect_pdf(path, papers_root) for path in sorted(papers_root.rglob("*.pdf"))]
    return papers_root, papers, group_duplicates(papers)


def index_has_entries(domain: str) -> bool:
    tracking = get_domain_paths(domain).index / "indexed_files.json"
    if not tracking.is_file():
        return False
    try:
        return bool(json.loads(tracking.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return True


def rollback(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "applied":
        raise RuntimeError(f"manifest is not in applied state: {manifest.get('status')}")
    papers_root = Path(manifest["papers_root"]).resolve()
    quarantine_root = manifest_path.parent / "files"
    restored = 0
    for value in manifest["quarantined_files"]:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"unsafe manifest path: {value}")
        source = quarantine_root / relative
        destination = papers_root / relative
        if destination.exists():
            raise RuntimeError(f"rollback target already exists: {destination}")
        if not source.is_file():
            raise RuntimeError(f"quarantined file is missing: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        restored += 1
    manifest["status"] = "rolled_back"
    manifest["rolled_back_at"] = datetime.now().isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "rolled_back", "restored_files": restored, "manifest": str(manifest_path)}


def purge(manifest_path: Path) -> dict[str, object]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "applied":
        raise RuntimeError(f"manifest is not in applied state: {manifest.get('status')}")

    quarantine_root = manifest_path.parent / "files"
    expected = {Path(value) for value in manifest["quarantined_files"]}
    actual = {path.relative_to(quarantine_root) for path in quarantine_root.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("quarantine contents do not exactly match the manifest")

    purged = 0
    for relative in sorted(expected):
        (quarantine_root / relative).unlink()
        purged += 1
    shutil.rmtree(quarantine_root)

    papers_root = Path(manifest["papers_root"]).resolve()
    purged_unavailable = []
    empty_digest = hashlib.sha256(b"").hexdigest()
    for item in manifest.get("unavailable_files", []):
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"unsafe unavailable path: {relative}")
        candidate = papers_root / relative
        if candidate.is_file() and candidate.stat().st_size > 0 and sha256(candidate) == empty_digest:
            candidate.unlink()
            purged_unavailable.append(relative.as_posix())

    manifest["status"] = "purged"
    manifest["purged_at"] = datetime.now().isoformat()
    manifest["purged_files_count"] = purged
    manifest["purged_unavailable_files"] = purged_unavailable
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "purged",
        "purged_quarantine_files": purged,
        "purged_unavailable_files": len(purged_unavailable),
        "manifest": str(manifest_path),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", choices=("sweetness", "dual_protein", "encapsulation", "proteoglycan"))
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--apply", action="store_true", help="Move duplicates and invalid PDFs into a recoverable quarantine")
    action.add_argument("--rollback", type=Path, metavar="MANIFEST", help="Restore files from an applied quarantine manifest")
    action.add_argument("--purge", type=Path, metavar="MANIFEST", help="Permanently delete quarantined and unavailable PDFs")
    parser.add_argument("--details", action="store_true", help="Print the complete scan manifest")
    args = parser.parse_args()

    if args.rollback:
        print(json.dumps(rollback(args.rollback.expanduser().resolve()), ensure_ascii=False, indent=2))
        return 0
    if args.purge:
        print(json.dumps(purge(args.purge.expanduser().resolve()), ensure_ascii=False, indent=2))
        return 0
    if not args.domain:
        parser.error("--domain is required unless --rollback is used")

    if args.apply and index_has_entries(args.domain):
        raise RuntimeError(f"{args.domain} already has indexed files; update or rebuild its index before deduplicating")

    papers_root, papers, groups = scan(args.domain)
    unavailable = [paper for paper in papers if paper.error == "dataless placeholder"]
    invalid = [paper for paper in papers if not paper.valid and paper.error != "dataless placeholder"]
    duplicate_paths = [path for group in groups for path in group["quarantine"]]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = ROOT / ".codex-backups" / f"paper-dedup-{args.domain}-{timestamp}"
    manifest = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "domain": args.domain,
        "papers_root": str(papers_root),
        "scanned_count": len(papers),
        "duplicate_groups": groups,
        "invalid_files": [asdict(paper) for paper in invalid],
        "unavailable_files": [asdict(paper) for paper in unavailable],
        "quarantined_files": sorted([*duplicate_paths, *(paper.path for paper in invalid)]),
        "remaining_count": len(papers) - len(duplicate_paths) - len(invalid),
        "status": "applied" if args.apply else "dry-run",
    }

    if args.apply:
        quarantine_root = backup_root / "files"
        for relative in manifest["quarantined_files"]:
            source = papers_root / relative
            destination = quarantine_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
        backup_root.mkdir(parents=True, exist_ok=True)
        (backup_root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    summary = {
        "status": manifest["status"],
        "scanned_count": manifest["scanned_count"],
        "duplicate_groups": len(groups),
        "duplicate_files": len(duplicate_paths),
        "invalid_files": len(invalid),
        "unavailable_files": len(unavailable),
        "remaining_count": manifest["remaining_count"],
        "backup_root": str(backup_root) if args.apply else None,
    }
    print(json.dumps(manifest if args.details else summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Deduplication failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
