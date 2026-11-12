#!/usr/bin/env python3
"""Safe D1 ingestion planner; never writes remotely.

The previous scripts inserted arbitrary voter prefixes, were not idempotent,
and could silently produce incomplete D1 state. This replacement reports
partition counts only. A production full-load needs a verified backup, the D1
migration, duplicate disposition, and explicit approval before remote writes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def count_shards(folder: Path) -> tuple[int, int]:
    files = sorted(folder.glob("*.json")) if folder.is_dir() else []
    total = 0
    for path in files:
        with path.open("r", encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise ValueError(f"Expected JSON array: {path}")
        total += len(rows)
    return len(files), total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Not supported by this planner; no remote writes are implemented.")
    args = parser.parse_args()
    if args.apply:
        print("BLOCKED: this planner cannot perform a production D1 write. Do not use the deprecated partial loaders.", file=sys.stderr)
        print("Required before an approved full load: database backup, schema migration, idempotent load design, duplicate policy, and verified row-count report.", file=sys.stderr)
        return 2
    try:
        kh_files, kh_rows = count_shards(DATA_DIR / "khatians")
        voter_files, voter_rows = count_shards(DATA_DIR / "voters")
        manifest_path = DATA_DIR / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
        expected_kh = manifest.get("metadata", {}).get("total_khatians")
        expected_voters = manifest.get("metadata", {}).get("total_voters")
        print("D1 sync planner (read-only; no network calls made)")
        print(f"Khatian source: {kh_rows:,} rows / {kh_files} partition files")
        print(f"Voter source:   {voter_rows:,} rows / {voter_files} partition files")
        if expected_kh is not None:
            print(f"Manifest khatian count: {expected_kh:,}; matches={kh_rows == int(expected_kh)}")
        if expected_voters is not None:
            print(f"Manifest voter count:   {expected_voters:,}; matches={voter_rows == int(expected_voters)}")
        print("Next: apply the reviewed D1 migrations, verify the D1 backup, then use an approved resumable full-load procedure.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
