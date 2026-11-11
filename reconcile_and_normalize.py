#!/usr/bin/env python3
"""Derive the dag index and mouza manifest without rewriting source records."""
from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


def write_json_atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def reconcile() -> int:
    base_dir = Path(__file__).resolve().parent
    raw_dir = base_dir / "02_BACKUP_AND_RAW_DATA" / "Raipur_Land_Mapping_Data"
    khatians_path = raw_dir / "raipur_master_khatians.json"
    target_dag_index_path = raw_dir / "raipur_master_dag_index.json"
    mouza_manifest_path = raw_dir / "mouza_manifest.json"
    voters_path = raw_dir / "raipur_all_voters.json"
    exceptions_path = base_dir / ".work" / "verification" / "voter_duplicates_exception.json"

    start = time.time()
    if not khatians_path.is_file():
        raise FileNotFoundError(f"Khatian source missing: {khatians_path}")
    with khatians_path.open("r", encoding="utf-8") as f:
        khatians = json.load(f)
    if not isinstance(khatians, list) or any(not isinstance(r, dict) for r in khatians):
        raise ValueError("Khatian master must be an array of objects")

    dag_index: dict[str, dict[str, dict[str, list[str]]]] = {}
    relation_count = 0
    incomplete_identity_rows = 0
    for record in khatians:
        mouza = str(record.get("mouza") or "").strip()
        survey = str(record.get("survey") or "").strip()
        khatian_no = str(record.get("khatianNo") or "").strip()
        dags = record.get("dags") or []
        if not isinstance(dags, (list, tuple, set)):
            dags = [dags]
        if not mouza or not survey or not khatian_no:
            incomplete_identity_rows += 1
            continue
        by_survey = dag_index.setdefault(mouza, {}).setdefault(survey, {})
        for dag in dags:
            dag_no = str(dag or "").strip()
            if not dag_no:
                continue
            khatian_list = by_survey.setdefault(dag_no, [])
            if khatian_no not in khatian_list:
                khatian_list.append(khatian_no)
                relation_count += 1
    write_json_atomic(target_dag_index_path, dag_index)

    raw_mouzas = sorted({str(r.get("mouza") or "").strip() for r in khatians if str(r.get("mouza") or "").strip()})
    manifest = {name: {"index": idx + 1} for idx, name in enumerate(raw_mouzas)}
    write_json_atomic(mouza_manifest_path, manifest)

    if voters_path.is_file():
        with voters_path.open("r", encoding="utf-8") as f:
            voters = json.load(f)
        if not isinstance(voters, list) or any(not isinstance(r, dict) for r in voters):
            raise ValueError("Voter source must be an array of objects")
        records_by_number: dict[str, list[int]] = defaultdict(list)
        missing_voter_no = 0
        for idx, record in enumerate(voters):
            voter_no = str(record.get("voterNo") or "").strip()
            if voter_no:
                records_by_number[voter_no].append(idx)
            else:
                missing_voter_no += 1
        duplicate_groups = [indices for indices in records_by_number.values() if len(indices) > 1]
        duplicate_records = sum(len(indices) for indices in duplicate_groups)
        # Indices point into the source array but contain no voter number, name, or address.
        write_json_atomic(exceptions_path, {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_duplicate_ids": len(duplicate_groups),
            "total_duplicate_records": duplicate_records,
            "missing_voter_no_records": missing_voter_no,
            "exceptions": [{"record_indices": indices} for indices in duplicate_groups],
        })
        print(f"Voter duplicate groups: {len(duplicate_groups):,}; exception output contains record indexes only.")

    print(f"Khatian records read: {len(khatians):,}")
    print(f"Unique dag-to-khatian relations derived: {relation_count:,}")
    print(f"Rows with incomplete dag-index identity (kept in source, not indexed): {incomplete_identity_rows:,}")
    print(f"Canonical mouza names: {len(manifest):,}")
    print(f"Reconciliation completed in {time.time() - start:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(reconcile())
