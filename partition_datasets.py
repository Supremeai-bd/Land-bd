#!/usr/bin/env python3
"""Partition canonical khatian/voter JSON and write a truthful manifest.

The source arrays are the authority; counts are never hard-coded. Raw values are
preserved (including unknown survey labels and duplicate identities)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "02_BACKUP_AND_RAW_DATA" / "Raipur_Land_Mapping_Data"
DATA_DIR = BASE_DIR / "data"
KHATIANS_OUT = DATA_DIR / "khatians"
VOTERS_OUT = DATA_DIR / "voters"
MANIFEST_OUT = DATA_DIR / "manifest.json"
KHATIANS_SRC = RAW_DIR / "raipur_master_khatians.json"
VOTERS_SRC = RAW_DIR / "raipur_all_voters.json"
MOUZA_MANIFEST_SRC = RAW_DIR / "mouza_manifest.json"
KNOWN_SURVEYS = {"CS", "SA", "RS", "BRS", "Mutation", "সাবেক", "হাল", "নামজারি"}


def load_array(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        value = json.load(f)
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError(f"Expected an array of JSON objects: {path}")
    return value


def safe_slug(value: str) -> str:
    slug = re.sub(r'[\s/\\:*?"<>|.]+', "_", value.strip()).strip("_")
    return slug or "unknown"


def unique_filename(prefix: str, value: str, used: set[str]) -> str:
    slug = safe_slug(value)
    candidate = f"{prefix}_{slug}.json"
    if candidate.casefold() in used:
        suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:10]
        candidate = f"{prefix}_{slug}_{suffix}.json"
    if candidate.casefold() in used:
        raise RuntimeError(f"Filename collision for partition key: {value!r}")
    used.add(candidate.casefold())
    return candidate


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def partition(rows: list[dict[str, Any]], key_name: str, fallback: str, out_dir: Path, prefix: str) -> tuple[list[dict], dict[str, int], Counter]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    missing_identity = 0
    quality = Counter()
    for index, row in enumerate(rows):
        raw = row.get(key_name)
        key = str(raw or "").strip()
        if not key:
            missing_identity += 1
            key = fallback
        grouped[key].append(row)
        if key_name == "mouza":
            survey = str(row.get("survey") or "").strip()
            if survey not in KNOWN_SURVEYS:
                quality[f"unknown_survey:{survey or '(blank)'}"] += 1
            if not str(row.get("khatianNo") or "").strip():
                quality["missing_khatian_no"] += 1
        else:
            for required in ("voterNo", "name"):
                if not str(row.get(required) or "").strip():
                    quality[f"missing_{required}"] += 1
    out_dir.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    meta: list[dict] = []
    expected_files: set[str] = set()
    for key, records in sorted(grouped.items()):
        sort_field = "khatianNo" if key_name == "mouza" else "voterNo"
        records.sort(key=lambda r: str(r.get(sort_field) or ""))
        filename = unique_filename(prefix, key, used)
        expected_files.add(filename)
        target = out_dir / filename
        write_json_atomic(target, records)
        size = target.stat().st_size
        relative = target.relative_to(DATA_DIR).as_posix()
        meta.append({key_name: key, "file": relative, "records": len(records), "size_kb": round(size / 1024, 1)})
    # Remove only stale generated JSON shards; preserve non-JSON files and folders.
    for old in out_dir.glob("*.json"):
        if old.name.casefold() not in expected_files:
            old.unlink()
    counts = {"records": len(rows), "partitions": len(grouped), "blank_partition_key_records": missing_identity}
    return meta, counts, quality


def main() -> int:
    start = time.time()
    for source in (KHATIANS_SRC, VOTERS_SRC):
        if not source.is_file():
            print(f"ERROR: source not found: {source}", file=sys.stderr)
            return 1
    khatians = load_array(KHATIANS_SRC)
    voters = load_array(VOTERS_SRC)

    kh_meta, kh_counts, kh_quality = partition(khatians, "mouza", "__MISSING_MOUZA__", KHATIANS_OUT, "mouza")
    voter_meta, voter_counts, voter_quality = partition(voters, "ward", "__MISSING_WARD__", VOTERS_OUT, "ward")

    source_mouzas = {str(r.get("mouza") or "").strip() for r in khatians if str(r.get("mouza") or "").strip()}
    manifest_only_mouzas: list[str] = []
    if MOUZA_MANIFEST_SRC.is_file():
        manifest_data = json.loads(MOUZA_MANIFEST_SRC.read_text(encoding="utf-8"))
        if isinstance(manifest_data, dict):
            official_names = set(manifest_data.keys())
        elif isinstance(manifest_data, list):
            official_names = {str(x.get("name") or x.get("mouza") or "").strip() for x in manifest_data if isinstance(x, dict)}
        else:
            official_names = set()
        manifest_only_mouzas = sorted(name for name in official_names - source_mouzas if name)

    kh_written = sum(x["records"] for x in kh_meta)
    voter_written = sum(x["records"] for x in voter_meta)
    if kh_written != len(khatians) or voter_written != len(voters):
        print("ERROR: partition count differs from source; manifest not written.", file=sys.stderr)
        return 2

    manifest = {
        "metadata": {
            "project": "Raipur Smart Land Cadastre & Citizen Intelligence Hub",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_khatians": len(khatians),
            "total_voters": len(voters),
            "total_mouzas": kh_counts["partitions"],
            "total_wards": voter_counts["partitions"],
            "blank_mouza_records": kh_counts["blank_partition_key_records"],
            "blank_ward_records": voter_counts["blank_partition_key_records"],
            "manifest_only_mouzas": manifest_only_mouzas,
            "partition_integrity": {
                "khatian_source_rows": len(khatians),
                "khatian_partition_rows": kh_written,
                "voter_source_rows": len(voters),
                "voter_partition_rows": voter_written,
                "row_counts_match": True,
                "note": "Rows are grouped and written from the source arrays; this does not certify OCR correctness against source PDFs."
            },
            "quality_summary": {**dict(kh_quality), **dict(voter_quality)},
        },
        "khatians": kh_meta,
        "voters": voter_meta,
    }
    write_json_atomic(MANIFEST_OUT, manifest)
    print(f"Partitioned khatians: {len(khatians):,} rows / {len(kh_meta)} mouza files")
    print(f"Partitioned voters:   {len(voters):,} rows / {len(voter_meta)} ward files")
    print(f"Manifest: {MANIFEST_OUT}")
    print(f"Quality flags retained (not auto-corrected): {sum(kh_quality.values()) + sum(voter_quality.values())}")
    print(f"Elapsed: {time.time() - start:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
