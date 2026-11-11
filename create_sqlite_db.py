#!/usr/bin/env python3
"""Build the local SQLite database from the verified partitioned JSON datasets.

The existing target is never overwritten unless --replace is explicitly passed.
A timestamped backup is retained before replacement. Raw source labels and
rows (including duplicate identities) are preserved; ambiguous survey labels
are flagged, not silently normalized.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEFAULT_DB = BASE_DIR / "raipur_cadastre_voters.db"
KNOWN_SURVEYS = {"CS", "SA", "RS", "BRS", "Mutation", "সাবেক", "হাল", "নামজারি"}
BATCH_SIZE = 1000

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE khatians (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    owners TEXT NOT NULL,
    guardian TEXT,
    dags TEXT,
    total_land TEXT,
    survey_quality TEXT NOT NULL DEFAULT 'known'
);
CREATE TABLE dag_khatian_map (
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    dag_no TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    PRIMARY KEY (mouza, survey, dag_no, khatian_no)
);
CREATE TABLE voters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    gender TEXT,
    ward TEXT NOT NULL,
    address TEXT,
    source_pdf TEXT
);
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    phone TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen',
    status TEXT NOT NULL DEFAULT 'pending',
    association_license_no TEXT,
    password_hash TEXT NOT NULL,
    approved_by TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE saved_khatians (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    mouza TEXT NOT NULL,
    survey TEXT NOT NULL,
    khatian_no TEXT NOT NULL,
    dag_summary TEXT,
    owners_summary TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE saved_voters (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    voter_no TEXT NOT NULL,
    name TEXT NOT NULL,
    father TEXT,
    mother TEXT,
    ward TEXT,
    address TEXT,
    relation_tag TEXT,
    notes TEXT,
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE import_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def json_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def read_partition_files(folder: Path) -> list[Path]:
    files = sorted(p for p in folder.glob("*.json") if p.is_file())
    if not files:
        raise RuntimeError(f"No partition JSON files found in {folder}")
    return files


def batches(rows: Iterable[tuple], size: int = BATCH_SIZE):
    pending = []
    for row in rows:
        pending.append(row)
        if len(pending) >= size:
            yield pending
            pending = []
    if pending:
        yield pending


def load_json_array(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        rows = json.load(f)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"Expected a JSON array of objects: {path}")
    return rows


def verify_manifest_partitions(manifest: dict[str, Any], key: str, files: list[Path]) -> None:
    entries = manifest.get(key)
    if not isinstance(entries, list) or not entries:
        raise RuntimeError(f"Manifest is missing its {key} file list; rerun partition_datasets.py first")
    expected: dict[Path, int] = {}
    for item in entries:
        if not isinstance(item, dict) or not item.get("file") or "records" not in item:
            raise RuntimeError(f"Malformed {key} manifest entry")
        expected[(DATA_DIR / str(item["file"])).resolve()] = int(item["records"])
    actual = {path.resolve() for path in files}
    if set(expected) != actual:
        raise RuntimeError(f"{key} shard files do not match the manifest; rerun partition_datasets.py")
    for path in files:
        if len(load_json_array(path)) != expected[path.resolve()]:
            raise RuntimeError(f"Manifest row count mismatch in {path.name}; rerun partition_datasets.py")


def import_khatians(conn: sqlite3.Connection, files: list[Path]) -> tuple[int, int, Counter]:
    total = 0
    dag_relations = 0
    survey_counts: Counter = Counter()
    for file in files:
        rows = load_json_array(file)
        kh_rows = []
        map_rows = []
        for r in rows:
            mouza = str(r.get("mouza") or "").strip()
            survey = str(r.get("survey") or "").strip()
            khatian_no = str(r.get("khatianNo") or "").strip()
            if not (mouza and survey and khatian_no):
                raise ValueError(f"Missing khatian identity in partition {file.name}; no rows imported")
            survey_counts[survey] += 1
            dags = r.get("dags") or []
            if isinstance(dags, (str, int, float)):
                dags = [dags]
            elif not isinstance(dags, (list, tuple)):
                dags = []
            else:
                dags = list(dags)
            owners = r.get("owners")
            kh_rows.append((
                mouza, survey, khatian_no, json_text(owners),
                str(r.get("guardian") or ""), json_text(dags),
                str(r.get("totalLand") or ""),
                "known" if survey in KNOWN_SURVEYS else "review"
            ))
            for dag in dict.fromkeys(str(d).strip() for d in dags if str(d).strip()):
                map_rows.append((mouza, survey, dag, khatian_no))
        for chunk in batches(kh_rows):
            conn.executemany(
                "INSERT INTO khatians(mouza,survey,khatian_no,owners,guardian,dags,total_land,survey_quality) VALUES(?,?,?,?,?,?,?,?)",
                chunk
            )
        for chunk in batches(map_rows):
            conn.executemany(
                "INSERT OR IGNORE INTO dag_khatian_map(mouza,survey,dag_no,khatian_no) VALUES(?,?,?,?)",
                chunk
            )
        total += len(rows)
        dag_relations += len(map_rows)
    return total, dag_relations, survey_counts


def import_voters(conn: sqlite3.Connection, files: list[Path]) -> int:
    total = 0
    for file in files:
        rows = load_json_array(file)
        values = []
        for r in rows:
            voter_no = str(r.get("voterNo") or "").strip()
            name = str(r.get("name") or "").strip()
            ward = str(r.get("ward") or "").strip()
            if not (voter_no and name and ward):
                raise ValueError(f"Missing required voter identity in partition {file.name}; no rows imported")
            values.append((
                voter_no, name, str(r.get("father") or ""), str(r.get("mother") or ""),
                str(r.get("gender") or ""), ward, str(r.get("address") or ""),
                str(r.get("sourcePdf") or "")
            ))
        for chunk in batches(values):
            conn.executemany(
                "INSERT INTO voters(voter_no,name,father,mother,gender,ward,address,source_pdf) VALUES(?,?,?,?,?,?,?,?)",
                chunk
            )
        total += len(rows)
    return total


def add_indexes(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE INDEX idx_khatians_lookup ON khatians(mouza, survey, khatian_no);
    CREATE INDEX idx_khatians_khatian_no ON khatians(khatian_no);
    CREATE INDEX idx_dag_lookup ON dag_khatian_map(dag_no, mouza, survey);
    CREATE INDEX idx_voters_voter_no ON voters(voter_no);
    CREATE INDEX idx_voters_name ON voters(name);
    CREATE INDEX idx_voters_father ON voters(father);
    CREATE INDEX idx_voters_ward ON voters(ward);
    CREATE INDEX idx_saved_khatians_user ON saved_khatians(user_id, saved_at);
    CREATE INDEX idx_saved_voters_user ON saved_voters(user_id, saved_at);
    """)


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def build_database(target: Path, replace: bool) -> None:
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not replace:
        raise FileExistsError(f"Refusing to overwrite existing database: {target}. Use --replace to retain a backup first.")

    kh_files = read_partition_files(DATA_DIR / "khatians")
    voter_files = read_partition_files(DATA_DIR / "voters")
    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    if not isinstance(manifest, dict):
        raise RuntimeError("data/manifest.json must be a JSON object")
    verify_manifest_partitions(manifest, "khatians", kh_files)
    verify_manifest_partitions(manifest, "voters", voter_files)
    expected_kh = manifest.get("metadata", {}).get("total_khatians")
    expected_voters = manifest.get("metadata", {}).get("total_voters")

    temp = target.with_name(target.name + ".building")
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(str(temp) + suffix)
        if p.exists():
            p.unlink()

    conn = sqlite3.connect(temp)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        conn.executescript(SCHEMA)
        conn.execute("BEGIN")
        kh_count, raw_dag_relations, survey_counts = import_khatians(conn, kh_files)
        voter_count = import_voters(conn, voter_files)
        if expected_kh is not None and kh_count != int(expected_kh):
            raise RuntimeError(f"Khatian partition count {kh_count:,} != manifest {expected_kh:,}")
        if expected_voters is not None and voter_count != int(expected_voters):
            raise RuntimeError(f"Voter partition count {voter_count:,} != manifest {expected_voters:,}")
        add_indexes(conn)
        now = datetime.now(timezone.utc).isoformat()
        metadata = {
            "generated_at": now,
            "khatians": str(kh_count),
            "voters": str(voter_count),
            "dag_relations_raw": str(raw_dag_relations),
            "dag_relations_unique": str(table_count(conn, "dag_khatian_map")),
            "khatians_partitions": str(len(kh_files)),
            "voter_partitions": str(len(voter_files)),
            "unclassified_survey_records": str(sum(n for s, n in survey_counts.items() if s not in KNOWN_SURVEYS)),
        }
        conn.executemany("INSERT INTO import_metadata(key,value) VALUES(?,?)", metadata.items())
        conn.commit()
        conn.execute("PRAGMA optimize")
        check = conn.execute("PRAGMA quick_check").fetchone()[0]
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if check != "ok" or fk_errors:
            raise RuntimeError(f"Database integrity validation failed: quick_check={check}, foreign_key_errors={len(fk_errors)}")
        counts = {name: table_count(conn, name) for name in ("khatians", "dag_khatian_map", "voters")}
        if counts["khatians"] != kh_count or counts["voters"] != voter_count:
            raise RuntimeError("Post-import table counts do not match source partition counts")
        duplicate_kh = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM khatians GROUP BY mouza,survey,khatian_no HAVING COUNT(*)>1)").fetchone()[0]
        duplicate_voters = conn.execute("SELECT COUNT(*) FROM (SELECT 1 FROM voters GROUP BY voter_no HAVING COUNT(*)>1)").fetchone()[0]
    except Exception:
        conn.rollback()
        conn.close()
        for suffix in ("", "-journal", "-wal", "-shm"):
            p = Path(str(temp) + suffix)
            if p.exists():
                p.unlink()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

    backup = None
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = target.with_name(target.name + f".backup.{stamp}")
        os.replace(target, backup)
    try:
        os.replace(temp, target)
    except Exception:
        if backup and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise

    print("SQLite database built and validated.")
    print(f"Target: {target}")
    print(f"Rows: khatians={counts['khatians']:,}; dag_khatian_map={counts['dag_khatian_map']:,}; voters={counts['voters']:,}")
    print(f"Duplicate identity groups retained for review: khatians={duplicate_kh:,}; voters={duplicate_voters:,}")
    print(f"Unclassified survey rows retained and flagged: {metadata['unclassified_survey_records']}")
    if backup:
        print(f"Previous database backup: {backup}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_DB, help="Target SQLite file (default: project root database)")
    parser.add_argument("--replace", action="store_true", help="Replace existing target only after retaining a timestamped backup")
    args = parser.parse_args()
    try:
        build_database(args.output, args.replace)
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
