#!/usr/bin/env python3
"""Low-memory administration for SweetSeek's four RAG domains."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import platform
import resource
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Tuple

import faiss
import ijson
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from knowledge_paths import get_domain_paths  # noqa: E402
from sweetseek.metadata_db import MetadataDB  # noqa: E402


DOMAINS = ("sweetness", "dual_protein", "encapsulation", "proteoglycan")
DEFAULT_ORDER = DOMAINS
REQUIRED_FREE_GB = 12.0
ABORT_FREE_GB = 8.0
DEFAULT_MAX_RSS_GB = 5.5


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def free_gb(path: Path) -> float:
    return shutil.disk_usage(path).free / (1024 ** 3)


def rss_gb() -> float:
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 ** 3 if sys.platform == "darwin" else 1024 ** 2
    return raw / divisor


def resource_guard(path: Path, max_rss_gb: float, initial: bool = False) -> None:
    minimum = REQUIRED_FREE_GB if initial else ABORT_FREE_GB
    available = free_gb(path)
    if available < minimum:
        raise RuntimeError(f"磁盘余量 {available:.1f} GB，低于安全阈值 {minimum:.1f} GB")
    memory = rss_gb()
    if memory > max_rss_gb:
        raise RuntimeError(f"构建进程 RSS {memory:.2f} GB，超过上限 {max_rss_gb:.2f} GB")


def index_format(index_dir: Path) -> str:
    current = index_dir / "current"
    if all((current / name).is_file() for name in ("index.faiss", "index.ids.txt", "metadata.db")):
        return "faiss_sqlite"
    vector = index_dir / "default__vector_store.json"
    if not vector.is_file():
        return "missing"
    with vector.open("rb") as handle:
        first = handle.read(16).lstrip()
    return "legacy_json" if first[:1] in {b"{", b"["} else "legacy_faiss"


def parse_doc_record(doc_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    data = record.get("__data__", {})
    if isinstance(data, str):
        data = json.loads(data)
    return {"doc_id": doc_id, "content": data.get("text", ""), "metadata": data.get("metadata", {}) or {}}


def iter_docs(docstore: Path) -> Iterator[Tuple[str, Dict[str, Any]]]:
    with docstore.open("rb") as handle:
        yield from ijson.kvitems(handle, "docstore/data")


def iter_embeddings(vector_store: Path) -> Iterator[Tuple[str, List[float]]]:
    with vector_store.open("rb") as handle:
        yield from ijson.kvitems(handle, "embedding_dict")


def model_fingerprint(dimension: int) -> str:
    value = ":".join((os.getenv("EMBED_MODEL_SOURCE", "modelscope"),
                      os.getenv("EMBED_MODEL_NAME", "BAAI/bge-small-zh-v1.5"), str(dimension)))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _status_path(index_dir: Path) -> Path:
    return index_dir / "build_status.json"


def _read_status(index_dir: Path) -> Dict[str, Any]:
    path = _status_path(index_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _save_status(index_dir: Path, **updates: Any) -> Dict[str, Any]:
    status = _read_status(index_dir)
    status.update(updates, updated_at=utc_now(), rss_gb=round(rss_gb(), 3), free_gb=round(free_gb(index_dir), 2))
    write_json(_status_path(index_dir), status)
    return status


def append_vectors(index: Any, rows: List[List[float]]):
    array = np.asarray(rows, dtype=np.float32)
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    array = array / norms
    if index is None:
        index = faiss.IndexFlatIP(int(array.shape[1]))
    if int(array.shape[1]) != int(index.d):
        raise RuntimeError(f"混合 embedding 维度: expected={index.d}, actual={array.shape[1]}")
    index.add(array)
    return index


def append_ids(path: Path, ids: Iterable[str]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for doc_id in ids:
            handle.write(f"{doc_id}\n")
        handle.flush()
        os.fsync(handle.fileno())


def verify_paths(directory: Path) -> Dict[str, Any]:
    required = ("index.faiss", "index.ids.txt", "metadata.db", "manifest.json")
    missing = [name for name in required if not (directory / name).is_file()]
    if missing:
        raise RuntimeError(f"索引文件缺失: {missing}")
    index = faiss.read_index(str(directory / "index.faiss"))
    ids = [line for line in (directory / "index.ids.txt").read_text(encoding="utf-8").splitlines() if line]
    with sqlite3.connect(directory / "metadata.db") as conn:
        sqlite_count = int(conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0])
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    counts = {"faiss": int(index.ntotal), "ids": len(ids), "sqlite": sqlite_count,
              "manifest": int(manifest.get("chunk_count", -1))}
    if len(set(counts.values())) != 1:
        raise RuntimeError(f"索引数量不一致: {counts}")
    if len(ids) != len(set(ids)):
        raise RuntimeError("ID 映射包含重复 chunk")
    return {"state": "ready", "counts": counts, "embedding_dimension": int(index.d)}


def verify_domain(domain: str) -> Dict[str, Any]:
    result = verify_paths(get_domain_paths(domain).index / "current")
    return {"domain": domain, "index_format": "faiss_sqlite", **result}


def migrate_json(domain: str, batch_size: int, resume: bool, max_rss_gb: float) -> Dict[str, Any]:
    paths = get_domain_paths(domain)
    index_dir = paths.index
    vector_store = index_dir / "default__vector_store.json"
    docstore = index_dir / "docstore.json"
    if index_format(index_dir) == "faiss_sqlite" and not resume:
        result = verify_domain(domain)
        _save_status(index_dir, **result, error=None)
        return result
    if index_format(index_dir) != "legacy_json":
        raise RuntimeError(f"{domain} 当前格式不支持流式迁移: {index_format(index_dir)}")
    resource_guard(index_dir, max_rss_gb, initial=not resume)
    stage = index_dir / "hybrid.staging"
    if stage.exists() and not resume:
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)

    lock_path = index_dir / ".rag-build.lock"
    with lock_path.open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _save_status(index_dir, domain=domain, state="building_documents", batch_size=batch_size, error=None)
        db = MetadataDB(str(stage / "metadata.db"))
        existing_ids = set(db.all_ids()) if resume else set()
        pending: List[Dict[str, Any]] = []
        scanned_docs = 0
        for doc_id, record in iter_docs(docstore):
            scanned_docs += 1
            if doc_id in existing_ids:
                continue
            pending.append(parse_doc_record(doc_id, record))
            if len(pending) >= batch_size:
                db.insert_batch(pending); pending.clear()
                resource_guard(index_dir, max_rss_gb)
                _save_status(index_dir, state="building_documents", scanned_documents=scanned_docs,
                             stored_documents=db.count())
        if pending:
            db.insert_batch(pending)

        valid_ids = set(db.all_ids())
        faiss_path = stage / "index.faiss"
        ids_path = stage / "index.ids.txt"
        completed = 0
        faiss_index = None
        if resume and faiss_path.is_file() and ids_path.is_file():
            faiss_index = faiss.read_index(str(faiss_path))
            completed = sum(bool(line.strip()) for line in ids_path.read_text(encoding="utf-8").splitlines())
            if completed != faiss_index.ntotal:
                raise RuntimeError("断点中的 FAISS 数量与 ID 映射不一致")

        _save_status(index_dir, state="building_vectors", stored_documents=db.count(), completed_vectors=completed)
        vector_batch: List[List[float]] = []
        id_batch: List[str] = []
        valid_seen = 0
        for doc_id, vector in iter_embeddings(vector_store):
            if doc_id not in valid_ids:
                continue
            if valid_seen < completed:
                valid_seen += 1
                continue
            valid_seen += 1
            vector_batch.append(vector); id_batch.append(doc_id)
            if len(vector_batch) >= batch_size:
                faiss_index = append_vectors(faiss_index, vector_batch)
                append_ids(ids_path, id_batch)
                completed += len(id_batch)
                faiss.write_index(faiss_index, str(faiss_path))
                vector_batch.clear(); id_batch.clear()
                resource_guard(index_dir, max_rss_gb)
                _save_status(index_dir, state="building_vectors", completed_vectors=completed,
                             embedding_dimension=faiss_index.d)
        if vector_batch:
            faiss_index = append_vectors(faiss_index, vector_batch)
            append_ids(ids_path, id_batch)
            completed += len(id_batch)
            faiss.write_index(faiss_index, str(faiss_path))
        if faiss_index is None:
            raise RuntimeError("源索引没有可迁移向量")

        manifest = {
            "schema_version": 1, "domain": domain, "index_format": "faiss_sqlite",
            "embedding_dimension": int(faiss_index.d),
            "embedding_fingerprint": model_fingerprint(int(faiss_index.d)),
            "document_count": len({
                (db.get_by_id(doc_id) or {}).get("metadata", {}).get("file_path", doc_id)
                for doc_id in valid_ids
            }),
            "chunk_count": int(faiss_index.ntotal), "created_at": utc_now(),
            "source_format": "legacy_json",
        }
        write_json(stage / "manifest.json", manifest)
        verify_paths(stage)

        current = index_dir / "current"
        previous = index_dir / "current.previous"
        if previous.exists():
            shutil.rmtree(previous)
        if current.exists():
            os.replace(current, previous)
        try:
            os.replace(stage, current)
        except Exception:
            if previous.exists() and not current.exists():
                os.replace(previous, current)
            raise
        result = verify_domain(domain)
        _save_status(index_dir, **result)
        return result


def diagnose_domain(domain: str) -> Dict[str, Any]:
    paths = get_domain_paths(domain)
    pdfs = list(paths.papers.rglob("*.pdf")) if paths.papers.exists() else []
    try:
        metadata = json.loads(paths.metadata.read_text(encoding="utf-8")) if paths.metadata.is_file() else {}
    except Exception as exc:
        metadata, metadata_error = {}, f"{type(exc).__name__}: {exc}"
    else:
        metadata_error = None
    largest = sorted(pdfs, key=lambda item: item.stat().st_size, reverse=True)[:10]
    return {
        "domain": domain, "papers": len(pdfs),
        "paper_bytes": sum(item.stat().st_size for item in pdfs),
        "metadata_records": len(metadata), "metadata_gap": len(pdfs) - len(metadata),
        "metadata_error": metadata_error, "index_format": index_format(paths.index),
        "free_gb": round(free_gb(paths.index), 2),
        "largest_pdfs": [{"path": str(item), "bytes": item.stat().st_size} for item in largest],
    }


def show_status(domain: str) -> Dict[str, Any]:
    paths = get_domain_paths(domain)
    return _read_status(paths.index) or {"domain": domain, "state": "idle", "index_format": index_format(paths.index)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("diagnose", "status", "verify"):
        command = sub.add_parser(name)
        command.add_argument("--domain", choices=(*DOMAINS, "all"), default="all")
    for name in ("build", "resume"):
        command = sub.add_parser(name)
        command.add_argument("--domain", choices=(*DOMAINS, "all"), default="all")
        command.add_argument("--batch-size", type=int, default=5)
        command.add_argument("--max-rss-gb", type=float, default=DEFAULT_MAX_RSS_GB)
    args = parser.parse_args()
    domains = DEFAULT_ORDER if args.domain == "all" else (args.domain,)
    results = []
    try:
        for domain in domains:
            if args.command == "diagnose": results.append(diagnose_domain(domain))
            elif args.command == "status": results.append(show_status(domain))
            elif args.command == "verify": results.append(verify_domain(domain))
            else: results.append(migrate_json(domain, args.batch_size, args.command == "resume", args.max_rss_gb))
    except Exception as exc:
        if "domain" in locals():
            _save_status(get_domain_paths(domain).index, domain=domain, state="failed",
                         error=f"{type(exc).__name__}: {exc}")
        print(json.dumps({"success": False, "error": f"{type(exc).__name__}: {exc}", "results": results},
                         ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"success": True, "results": results,
                      "runtime": {"python": platform.python_version(), "platform": platform.platform()}},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
