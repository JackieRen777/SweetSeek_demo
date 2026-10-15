#!/usr/bin/env python3
"""Extract and validate the immutable SweetMeta v1.0.7 SQLite release."""

from __future__ import annotations

import argparse
import hashlib
import lzma
import shutil
import sqlite3
import tempfile
from pathlib import Path

EXPECTED_TABLE_COUNTS = {
    "compound_sweetclass": 1296,
    "compound_provenance": 1296,
    "compound_projection": 2592,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(database: Path, expected_sha256: str) -> None:
    actual_sha256 = sha256(database)
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"SweetMeta database SHA-256 mismatch: {actual_sha256} != {expected_sha256}"
        )

    connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"SweetMeta integrity check failed: {integrity}")
        metadata = dict(connection.execute("SELECT key, value FROM reviewed_release_metadata"))
        if metadata.get("version") != "v1.0.7" or metadata.get("public_compounds") != "1296":
            raise ValueError(f"unexpected SweetMeta release metadata: {metadata}")
        for table, expected in EXPECTED_TABLE_COUNTS.items():
            actual = connection.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            if actual != expected:
                raise ValueError(f"{table}: expected {expected} rows, found {actual}")
    finally:
        connection.close()


def extract(archive: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with lzma.open(archive, "rb") as source, temporary.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.output:
        extract(args.archive, args.output)
        validate(args.output, args.expected_sha256)
        print(args.output)
        return 0

    with tempfile.TemporaryDirectory(prefix="sweetmeta-release-") as directory:
        database = Path(directory) / "SweetDatabase_v1.0.7_20261005.sqlite"
        extract(args.archive, database)
        validate(database, args.expected_sha256)
    print("SweetMeta v1.0.7 release verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
