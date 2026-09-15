#!/usr/bin/env python3
"""Fetch PubChem property records in retryable, provenance-preserving batches."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


PROPERTIES = (
    "IUPACName,MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,"
    "InChI,InChIKey,XLogP,TPSA,HBondDonorCount,HBondAcceptorCount,"
    "RotatableBondCount,HeavyAtomCount,Charge"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rest-client", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=float, default=4.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.source_json.read_text(encoding="utf-8"))
    rows = payload.get("compounds", payload) if isinstance(payload, dict) else payload
    keys = [
        row.get("parent_inchikey") or row.get("inchiKey")
        for row in rows
        if row.get("parent_inchikey") or row.get("inchiKey")
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    batch_count = (len(keys) + args.batch_size - 1) // args.batch_size

    for batch_index in range(batch_count):
        output_path = args.output_dir / f"pubchem-batch-{batch_index:03d}.json"
        if output_path.exists():
            print(f"[{batch_index + 1}/{batch_count}] cached", flush=True)
            continue

        batch = keys[batch_index * args.batch_size : (batch_index + 1) * args.batch_size]
        request = {
            "base_url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug",
            "path": f"compound/inchikey/property/{PROPERTIES}/JSON",
            "method": "POST",
            "form_body": {"inchikey": ",".join(batch)},
            "record_path": "PropertyTable.Properties",
            "max_items": 1,
            "max_depth": 1,
            "timeout_sec": 180,
            "save_raw": True,
            "raw_output_path": str(output_path),
        }
        payload = json.dumps(request).encode("utf-8")
        success = False
        for attempt in range(1, args.retries + 1):
            result = subprocess.run(
                [sys.executable, str(args.rest_client)],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            try:
                response = json.loads(result.stdout.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                response = {"ok": False, "error": {"message": result.stderr.decode("utf-8")}}
            if response.get("ok") and output_path.exists():
                success = True
                print(f"[{batch_index + 1}/{batch_count}] fetched", flush=True)
                break
            message = response.get("error", {}).get("message", "unknown PubChem error")
            if "404 Client Error" in message:
                output_path.write_text(
                    json.dumps({"PropertyTable": {"Properties": []}, "queried_inchikeys": batch}, indent=2),
                    encoding="utf-8",
                )
                success = True
                print(f"[{batch_index + 1}/{batch_count}] no PubChem records", flush=True)
                break
            print(
                f"[{batch_index + 1}/{batch_count}] attempt {attempt} failed: {message}",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(args.delay * attempt)

        if not success:
            failure_path = args.output_dir / f"pubchem-batch-{batch_index:03d}.failure.json"
            failure_path.write_text(json.dumps({"inchikeys": batch}, indent=2), encoding="utf-8")
        time.sleep(args.delay)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
