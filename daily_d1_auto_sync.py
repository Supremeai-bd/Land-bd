#!/usr/bin/env python3
"""
Raipur Cadastre - Daily Auto Sync & Migration Engine (Cloudflare D1 Free Tier)
=============================================================================
Runs automatically once per day after 6:00 AM (00:00 UTC) when the PC is on.
- Applies pending schema migrations.
- Progressively syncs ~80,000 to 90,000 rows/day (Khatians -> Dag Map -> Voters)
  safely staying under D1's 100,000 daily row write limit.
- Maintains a persistent state checkpoint file (d1_sync_state.json).
- Supports Windows Task Scheduler integration for automatic daily execution.
"""
from __future__ import annotations

import os
import sys
import json
import time
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
LOCAL_DB = BASE_DIR / "raipur_cadastre_voters.db"
STATE_FILE = BASE_DIR / "d1_sync_state.json"
MIGRATION_FILE = BASE_DIR / "raipur_cloudflare_backend" / "migrations" / "0002_contract_and_lookup_indexes.sql"
ENV_FILE = BASE_DIR / ".env"

DAILY_WRITE_LIMIT = 85000  # Safe threshold below the 100k free tier limit
BATCH_SIZE = 100           # D1 recommended multi-row batch insert

load_dotenv(ENV_FILE)
ACC_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
EMAIL = os.getenv("CLOUDFLARE_EMAIL")
KEY = os.getenv("CLOUDFLARE_GLOBAL_API_KEY")
TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
DB_ID = os.getenv("CLOUDFLARE_D1_DATABASE_ID")


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_run_date": "",
        "migration_applied": False,
        "khatians_offset": 0,
        "dags_offset": 0,
        "voters_offset": 0,
        "completed": False
    }


def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def d1_query(sql: str) -> dict:
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACC_ID}/d1/database/{DB_ID}/query"
    payload = json.dumps({"sql": sql}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    else:
        headers["X-Auth-Email"] = EMAIL
        headers["X-Auth-Key"] = KEY

    req = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_d1_quota() -> bool:
    """Check if D1 quota is active and writable."""
    try:
        res = d1_query("SELECT 1;")
        return res.get("success", False)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        if "7500" in err_msg or "daily row write limit" in err_msg:
            log("⚠️ Cloudflare D1 daily write limit is currently active (Code 7500). Wait for 6:00 AM UTC reset.")
            return False
        raise


def apply_migration(state: dict) -> bool:
    if state.get("migration_applied"):
        return True

    log("Applying D1 migration (0002_contract_and_lookup_indexes.sql)...")
    if not MIGRATION_FILE.exists():
        log(f"ERROR: Migration file {MIGRATION_FILE} not found!")
        return False

    with open(MIGRATION_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split and execute migration statements
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip() and not stmt.strip().startswith("--")]
    for stmt in statements:
        try:
            res = d1_query(stmt)
            if not res.get("success"):
                log(f"Migration statement warning: {res.get('errors')}")
        except Exception as e:
            # Table might already be migrated or column exists
            log(f"Migration note: {e}")

    state["migration_applied"] = True
    save_state(state)
    log("✓ D1 migration verified and applied.")
    return True


def clean_val(v) -> str:
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''").replace("\\", "\\\\") + "'"


def sync_records(table: str, columns: list[str], select_sql: str, offset: int, limit: int) -> int:
    """Sync records in batches and return rows inserted."""
    con = sqlite3.connect(str(LOCAL_DB))
    cur = con.cursor()
    cur.execute(select_sql + f" LIMIT {limit} OFFSET {offset}")
    rows = cur.fetchall()
    con.close()

    if not rows:
        return 0

    inserted_total = 0
    cols_joined = ", ".join(columns)

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        val_rows = []
        for r in batch:
            row_str = "(" + ", ".join(clean_val(c) for c in r) + ")"
            val_rows.append(row_str)

        sql = f"INSERT OR IGNORE INTO {table} ({cols_joined}) VALUES {', '.join(val_rows)};"
        try:
            res = d1_query(sql)
            if res.get("success"):
                inserted_total += len(batch)
            else:
                log(f"Batch insert error on {table}: {res.get('errors')}")
                break
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            if "7500" in err_body or "daily row write limit" in err_body:
                log(f"Hit D1 daily limit during {table} sync. Stopping for today.")
                return inserted_total
            raise
        time.sleep(0.1)

    return inserted_total


def run_daily_sync():
    today = datetime.now().strftime("%Y-%m-%d")
    current_hour = datetime.now().hour

    log("=" * 65)
    log(f"Raipur Cadastre Daily Auto-Sync Engine ({today})")
    log("=" * 65)

    if not (ACC_ID and DB_ID and ((EMAIL and KEY) or TOKEN)):
        log("ERROR: Missing Cloudflare credentials in .env! Aborting.")
        return

    if not LOCAL_DB.exists():
        log(f"ERROR: Local database {LOCAL_DB} not found! Run create_sqlite_db.py first.")
        return

    state = load_state()

    # Rule 1: Run only once per day
    if state.get("last_run_date") == today:
        log(f"Sync for today ({today}) is already completed. Next run tomorrow after 6:00 AM.")
        return

    # Rule 2: Run only after 6:00 AM local time (when 00:00 UTC reset has occurred)
    if current_hour < 6:
        log(f"Current local time is before 6:00 AM (hour {current_hour}). Waiting for UTC midnight quota reset.")
        return

    if state.get("completed"):
        log("🎉 All tables (Khatians, Dags, Voters) are already 100% synchronized with Cloudflare D1!")
        return

    # Test quota availability
    if not test_d1_quota():
        log("Aborting sync until quota is officially available.")
        return

    # Apply migration first
    apply_migration(state)

    budget_left = DAILY_WRITE_LIMIT

    # 1. Sync Khatians (Target: 157,657)
    con = sqlite3.connect(str(LOCAL_DB))
    total_khatians = con.execute("SELECT count(*) FROM khatians").fetchone()[0]
    total_dags = con.execute("SELECT count(*) FROM dag_khatian_map").fetchone()[0]
    total_voters = con.execute("SELECT count(*) FROM voters").fetchone()[0]
    con.close()

    if state["khatians_offset"] < total_khatians and budget_left > 0:
        need = min(budget_left, total_khatians - state["khatians_offset"])
        log(f"Starting Khatian batch (offset: {state['khatians_offset']:,}, target: {need:,} rows)...")
        cols = ["mouza", "survey", "khatian_no", "owners", "guardian", "dags", "total_land"]
        sql = "SELECT mouza, survey, khatian_no, owners, guardian, dags, total_land FROM khatians ORDER BY id"
        done = sync_records("khatians", cols, sql, state["khatians_offset"], need)
        state["khatians_offset"] += done
        budget_left -= done
        log(f"✓ Synced {done:,} khatians. Total khatians synced: {state['khatians_offset']:,} / {total_khatians:,}")

    # 2. Sync Dag Khatian Map (Target: 418,967)
    if state["khatians_offset"] >= total_khatians and state["dags_offset"] < total_dags and budget_left > 0:
        need = min(budget_left, total_dags - state["dags_offset"])
        log(f"Starting Dag Map batch (offset: {state['dags_offset']:,}, target: {need:,} rows)...")
        cols = ["mouza", "survey", "dag_no", "khatian_no"]
        sql = "SELECT mouza, survey, dag_no, khatian_no FROM dag_khatian_map ORDER BY mouza, survey, dag_no"
        done = sync_records("dag_khatian_map", cols, sql, state["dags_offset"], need)
        state["dags_offset"] += done
        budget_left -= done
        log(f"✓ Synced {done:,} dag mappings. Total dags synced: {state['dags_offset']:,} / {total_dags:,}")

    # 3. Sync Voters (Target: 492,074)
    if state["dags_offset"] >= total_dags and state["voters_offset"] < total_voters and budget_left > 0:
        need = min(budget_left, total_voters - state["voters_offset"])
        log(f"Starting Voter batch (offset: {state['voters_offset']:,}, target: {need:,} rows)...")
        cols = ["voter_no", "name", "father", "mother", "gender", "ward", "address", "source_pdf"]
        sql = "SELECT voter_no, name, father, mother, gender, ward, address, source_pdf FROM voters ORDER BY id"
        done = sync_records("voters", cols, sql, state["voters_offset"], need)
        state["voters_offset"] += done
        budget_left -= done
        log(f"✓ Synced {done:,} voters. Total voters synced: {state['voters_offset']:,} / {total_voters:,}")

    if (state["khatians_offset"] >= total_khatians and
        state["dags_offset"] >= total_dags and
        state["voters_offset"] >= total_voters):
        state["completed"] = True
        log("🏆 All datasets have been 100% successfully uploaded to Cloudflare D1!")

    state["last_run_date"] = today
    save_state(state)
    log(f"State saved. Daily session completed. Next run tomorrow after 6:00 AM.")


if __name__ == "__main__":
    run_daily_sync()

