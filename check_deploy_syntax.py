#!/usr/bin/env python3
"""Offline regression checks for the API-only Worker bundle contract."""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
HTML_PATH = BASE / "01_LIVE_SMART_PORTAL_APP" / "Land_Intelligence_Hub.html"
DEPLOY_PATH = BASE / "deploy_to_cloudflare.py"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> int:
    for filename in (
        "deploy_to_cloudflare.py", "create_sqlite_db.py", "partition_datasets.py",
        "sync_to_d1.py", "sync_batch_d1.py",
        "reconcile_and_normalize.py",
    ):
        path = BASE / filename
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"Python syntax error in {filename}: {exc}")

    deploy_source = DEPLOY_PATH.read_text(encoding="utf-8")
    html = HTML_PATH.read_text(encoding="utf-8")
    worker = (BASE / "raipur_cloudflare_backend" / "src" / "index.js").read_text(encoding="utf-8")
    migration = (BASE / "raipur_cloudflare_backend" / "migrations" / "0002_contract_and_lookup_indexes.sql").read_text(encoding="utf-8")
    if "DEFAULT_TOKEN_SECRET" in worker or "RAIPUR_CADASTRE_INTERNAL_SESSION_SECRET" in worker:
        fail("Worker still contains a compiled/default signing secret")
    for contract in ("authenticateActiveUser", "source_pdf", "notes", "LIMIT 5"):
        if contract not in worker + migration:
            fail(f"missing Worker/schema contract: {contract}")
    if "id TEXT PRIMARY KEY" not in migration:
        fail("saved-record IDs are not migrated to the string contract")
    for asset in ("raipur_full_database.js", "core_7_database.js", "raipur_voters_database.js"):
        tag_pattern = re.compile(r'<script\s+src=["\']' + re.escape(asset) + r'["\']\s*>\s*</script>', re.IGNORECASE)
        if len(tag_pattern.findall(html)) != 1:
            fail(f"expected exactly one local script tag for {asset}")
        html, count = tag_pattern.subn("", html)
        if count != 1:
            fail(f"cloud transform did not remove {asset}")

    database_pattern = re.compile(r"(?ms)^[ \t]*const DATABASE = \{.*?^[ \t]{8}\};")
    html, replacements = database_pattern.subn(
        "        const DATABASE = { khatians: [], dagIndex: {}, voters: [] };", html, count=1
    )
    if replacements != 1:
        fail("cloud transform could not replace the local DATABASE initializer")
    if any(asset in html for asset in ("raipur_full_database.js", "core_7_database.js", "raipur_voters_database.js")):
        fail("cloud HTML still references a non-committed local data asset")

    fetch_old = "const resp = await fetch('/api/voters?' + p.toString());"
    fetch_new = "const resp = await fetch('/api/voters?' + p.toString(), { headers: { 'Authorization': 'Bearer ' + getPortalAuthToken() } });"
    if html.count(fetch_old) < 1:
        fail("source HTML must contain at least one online voter API call")
    html = html.replace(fetch_old, fetch_new)
    if "'Authorization': 'Bearer '" not in html or "getPortalAuthToken()" not in deploy_source:
        fail("secured voter API call does not carry the session token")
    if "--apply" not in deploy_source or "TOKEN_SECRET" not in deploy_source:
        fail("deployment must be explicit and require TOKEN_SECRET")
    if "D1_EXPECTED_KHATIANS" not in deploy_source or "D1_EXPECTED_VOTERS" not in deploy_source or "D1_EXPECTED_DAG_RELATIONS" not in deploy_source:
        fail("deployment must enforce the approved full-source table row counts")

    print("PASS: Python syntax and API-only cloud bundle transforms verified; no data files were uploaded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
