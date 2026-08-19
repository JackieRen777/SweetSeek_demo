#!/usr/bin/env python3
"""Validate release-local citation catalogs and their manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.citation_catalog import validate_catalog  # noqa: E402

MINIMUM_COUNTS = {"sweetness": 1000, "dual_protein": 400, "encapsulation": 600, "proteoglycan": 1300}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-root", type=Path, default=ROOT / "data" / "citations")
    args = parser.parse_args()
    manifest_path = args.catalog_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("citation_style") != "GB/T 7714-2015":
        raise ValueError("citation style must be GB/T 7714-2015")
    results = {}
    for domain, minimum in MINIMUM_COUNTS.items():
        result = validate_catalog(domain, args.catalog_root / f"{domain}.json", minimum_records=minimum)
        expected = (manifest.get("domains") or {}).get(domain) or {}
        if result["record_count"] != expected.get("record_count") or result["sha256"] != expected.get("sha256"):
            raise ValueError(f"{domain}: manifest mismatch")
        results[domain] = result
    print(json.dumps({"status": "ready", "domains": results}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
