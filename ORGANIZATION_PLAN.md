# Project Organization Plan — Raipur Land & Citizen Intelligence Hub

## 1. Current State (as of 2026-11-11)

> **Status correction (12 Nov 2026):** This file is a historical organization plan, not an authoritative completion checklist. The audit found zero rows in the local SQLite application tables and partial production D1 coverage. The old “done” marks and instructions below are superseded where noted; do not treat them as proof of complete ingestion, cross-survey mapping, or live deployment.

### Root Directory: `F:\khotiyan book/`

| Category | Items |
|---|---|
| **Core App** | `Land_Intelligence_Hub.html`, `01_LIVE_SMART_PORTAL_APP/` (4 JS files), `raipur_pages_deploy/public/index.html` |
| **Data / DB** | `raipur_cadastre_voters.db` (application tables were empty in the audit), source JSONs (157,657 khatians / 492,074 voters), derived dag index, local JS data assets |
| **R2 Cloud** | `upload_raw_to_r2.py`, `DEPLOY_TO_CLOUD.bat`, `deploy_to_cloudflare.py`, `.env` creds, `raipur_cloudflare_backend/wrangler.toml`, `src/index.js` |
| **AI Pipeline** | `AI_CADASTRAL_MAPPING_ARCHITECTURE.md` proposal; PDF provenance/AI verification pipeline not confirmed as implemented |
| **Backup/Raw** | `02_BACKUP_AND_RAW_DATA/` (291 PDFs, 552 voter PDFs) |
| **Config** | `.env.example`, `.gitignore`, `README_কিভাবে_চালাবেন.txt`, pre-commit hooks |
| **Docs** | `PROJECT_DOCUMENTATION.md`, `PROJECT_DOCUMENTATION_CATALOG_BANGLA.md`, `RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md` |

### Open Tabs (3-Tab Navigation)
- Tab ১. ভূমি ও খতিয়ান অনুসন্ধান → `btn-view-cadastre`
- Tab ২. দলিল রেজিস্ট্রি ফি ক্যালকুলেটর → `btn-view-registry`
- Tab ৩. ভোটার ও নাগরিক অনুসন্ধান → **`btn-view-voter` + `switchMainPortalView('voter')` ✅**

---

## 2. Proposed Organized Structure (per .gitignore)

```
F:\khotiyan book/
├── .env          # CLOUDFLARE credentials (BLOCKED - never commit!)
├── .env.local    # Local overrides
├── .env.*.local  # Local variants
├── *.pem         # Private keys (BLOCKED)
├── *.key         # API tokens (BLOCKED)
├── README_কিভাবে_চালাবেন.txt   # How to run
├── RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md   # NEW (integration doc)
├── upload_raw_to_r2.py                        # R2 uploader (NEW)
├── AI_CADASTRAL_MAPPING_ARCHITECTURE.md      # NEW (AI pipeline doc)
├── check_d1_voters.py                         # D1 voters query
├── check_d1_mouzas.py                          # D1 mouza query
├── CREATE_BRANCH_AND_PR.bat                    # Branch creation
├── check_khatians_structure.py                 # Khatian schema check
├── Land_Intelligence_Hub.html                   # Main app (all tabs incl. new voter tab)
├── deploy_to_cloudflare.py                     # Cloud deploy script
├── DEPLOY_TO_CLOUD.bat                          # Local deploy bat
├── create_sqlite_db.py                          # SQLite creator
├── RAIPUR_REGISTRY_RATES_2025_2026.json         # Registry rates data
├── raipur_registry_rates.js                     # Registry rates JS
├── raipur_full_database.js                      # Full database JS
├── core_7_database.js                            # Core database JS
├── raipur_pages_deploy/public/index.html        # Public landing page
├── raipur_cloudflare_backend/wrangler.toml      # Cloudflare wrangler config
├── src/index.js                                  # Cloudflare backend worker
├── RUN_LOCAL_PORTAL.bat                          # Local portal runner
└── 01_LIVE_SMART_PORTAL_APP/                    # App dir
    ├── Land_Intelligence_Hub.html                # Main HTML (with new voter tab)
    ├── raipur_registry_rates.js                  # Registry rates JS
    ├── raipur_full_database.js                   # Full DB JS
    ├── raipur_voters_database.js                 # Voters DB JS
    └── README_কিভাবে_চালাবেন.txt                   # Run guide

From .gitignore:
- BLOCKED: `.env`, `.env.local`, `*.pdf`, `*.PDF`, `raipur_cadastre_voters.db`,
  `raipur_all_voters.json`, `raipur_voters_database.js`
- Heavy JS (>10MB): `raipur_voters_database.js`, `raipur_full_database.js`, 
  `core_7_database.js`, `01_LIVE_SMART_PORTAL_APP/raipur_*.js`
- Local DBs: `*.db`, `raipur_cadastre_voters.db`
- JSON >40MB: `raipur_all_voters.json`, `raipur_master_khatians.json`, `raipur_master_dag_index.json`
- Dependencies: `node_modules/`, `.wrangler/`, `dist/`, `.cache/`

---

## ৩. File Inventory Summary

| File | Purpose | Status |
|---|---|---|
| `upload_raw_to_r2.py` | Public-safe registry-rate upload by default; sensitive data requires private-bucket safeguards | ✅ exists |
| `AI_CADASTRAL_MAPPING_ARCHITECTURE.md` | Proposed external AI workflow; not validated or production-connected | ⚠️ proposal |
| `check_d1_voters.py` / `check_d1_mouzas.py` | Query D1 for khatians/dags/voters | ✅ exist |
| `create_sqlite_db.py` | Build/validate SQLite from partition JSON; must still be executed locally | ⚠️ code prepared, DB not yet rebuilt |
| `check_khatians_structure.py` | Check khatians table structure | ✅ exists |
| `DEPLOY_TO_CLOUD.bat` / `deploy_to_cloudflare.py` | Deploy live portal to Cloudflare Edge | ✅ exist |
| `RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md` | Historical plan; complete D1 ingestion and live tests pending | ⚠️ revised |
| `Land_Intelligence_Hub.html` | Main app with all 3 tabs (incl. new voter tab) | ✅ modified |
| `raipur_pages_deploy/public/index.html` | Public landing page | ✅ exists |
| `upload_raw_to_r2.py` | Public-safe registry-rate upload by default; sensitive uploads are blocked without safeguards | ✅ exists |
| `RAIPUR_REGISTRY_RATES_2025_2026.json` | Registry rates data | ✅ exists |
| `raipur_pages_deploy/src/index.js` | Cloudflare Worker backend | ✅ exists |

---

## ৪. GITHUB BRANCHES
- Active branch(s) visible in git history (from `git log --oneline -10` earlier context).

---

## ৫. PRE-COMMIT SECURITY CHECKS
- `pre_commit_check.py`: blocks `.env`, `.env.local`, `*.db`, `*.sqlite`, oversized files (>50MB), secret leaks.
- `githooks/pre-commit` (153 lines) runs this check.
- Files like `raipur_cadastre_voters.db` are BLOCKED per `.gitignore`.

---

## ৬. NEXT STEPS (High Priority)

### Step 4: `DEPLOY_TO_CLOUD.bat` → Live Deploy
```powershell
Set-Location 'F:\khotiyan book'
python .\deploy_to_cloudflare.py          # local build only
# Use --apply only after D1 backup, migration and exact full-load validation.
```
⚠️ Pending: local terminal validation, reviewed D1 migrations, backup, exact full-load counts and approval. Deploy script fails closed on missing secret/schema/counts.

### Step 5: `/api/voters` Endpoint Bindings
The secured `/api/voters` and vault routes exist in `raipur_cloudflare_backend/src/index.js`; validate them against the migrated D1 schema and integration tests. The voter route accepts one exact voter number or a 3+ character name/father query and returns at most five minimized records.

---

## ৭. ORGANIZATIONAL DIRECTORY PLAN

### New Directories (to be created):
- `src/` — AI/mapping scripts, utilities
- `data/` — extracted JSON datasets, mapping index
- `scripts/` — Python executables (`upload_raw_to_r2.py`, `check_*.py`)
- `config/` — `.env` templates, API keys, R2 credentials
- `docs/` — architecture docs, integration plan
- `raw/` — raw scanned PDFs, extraction dumps
- `backup/` — backup copies

### Moved / Already Placed:
- All existing files remain where they are (maintain current layout).
- New files go into appropriate dirs above.

### Updated `.gitignore` additions:
- Remove `*.pdf`, `*.PDF`, `*.pem`, `*.key` (already there but ensure new files don't re-trigger)
- Add: `RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md`, `upload_raw_to_r2.py`, `AI_CADASTRAL_MAPPING_ARCHITECTURE.md`, `check_d1_voters.py`, `check_d1_mouzas.py`, `create_sqlite_db.py`, `RAIPUR_REGISTRY_RATES_2025_2026.json`, `raipur_master_khatians.json`, `raipur_master_dag_index.json`, `README_किभावে_चालাবেন.txt`, `upload_raw_to_r2.py`

---

## ৮. SUMMARY OF COMPLETION STATUS

| Item | Status |
|---|---|
| ১. User journey & ৩-ট্যাব ন্যাভিগেশন আর্কিটেক্যার | ✅ |
| ২. UI/UX design features (flexible search, result cards, land link button, print/slip) | ✅ |
| ৩. Local + Cloud data architecture (complete SQLite/D1 sync, 30 ms response) | ⚠️ not verified; local DB was empty and D1 partial |
| ৪. Next steps (Step ১-৪) | ✅ (plan written) |
| ৫. Cloud DB schema & optimization (compound indexes) | ✅ |
| ৬. দলিল রেজিস্ট্রি ফি ও অন-গ্রাউন্ড খরচ মডেল | ✅ |
| ৭. ডিরেক্টরি কাঠামো ও ফাইল অবস্থান | ✅ |
| ৮. পরিচালনা ও ব্যবহার নির্দেশিকা | ✅ |
| ৯. প্রিন্ট ও এক্সপোর্ট সুবিধা | ✅ |
| ১০. ভূমি জরিপ বই & ভোটার তালিকা PDF (Backup) | ✅ |
| ১১. রেকর্ড সংরক্ষণ (Vault) | ⚠️ endpoints exist; migration/integration tests pending |
| ১২. ক্লাউড/লোকাল ডেটা আর্কিটেকচার | ⚠️ local DB was empty; D1 incomplete |
| ১৩. গিট হুকস (pre-commit) | ✅ (existing) |
| ১৪. নতুন ইঞ্জিটারি প্ল্যান | ✅ |

---

*Plan saved at `F:\khotiyan book\RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md`.*
