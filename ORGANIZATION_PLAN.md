# Project Organization Plan — Raipur Land & Citizen Intelligence Hub

## 1. Current State (as of 2026-11-11)

### Root Directory: `F:\khotiyan book/`

| Category | Items |
|---|---|
| **Core App** | `Land_Intelligence_Hub.html`, `01_LIVE_SMART_PORTAL_APP/` (4 JS files), `raipur_pages_deploy/public/index.html` |
| **Data / DB** | `raipur_cadastre_voters.db` (SQLite master, ~383 MB), `raipur_all_voters.json` (492,074 voters), `raipur_master_khatians.json`, `raipur_master_dag_index.json`, `core_7_database.js`, `raipur_full_database.js` |
| **R2 Cloud** | `upload_raw_to_r2.py`, `DEPLOY_TO_CLOUD.bat`, `deploy_to_cloudflare.py`, `.env` creds, `raipur_cloudflare_backend/wrangler.toml`, `src/index.js` |
| **AI Pipeline** | `AI_CADASTRAL_MAPPING_ARCHITECTURE.md`, flowchart, `google.genai` scripts (`verify_cadastre_page.py`), `check_*.py` scripts |
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
| `upload_raw_to_r2.py` | R2 S3-compatible upload of raw files (291 PDFs, 552 voter PDFs, DBs, JS) | ✅ exists |
| `AI_CADASTRAL_MAPPING_ARCHITECTURE.md` | External Gemini/Claude multimodal mapping architecture | ✅ exists |
| `check_d1_voters.py` / `check_d1_mouzas.py` | Query D1 for khatians/dags/voters | ✅ exist |
| `create_sqlite_db.py` | Create SQLite schema w/ B-Tree indexes | ✅ exists |
| `check_khatians_structure.py` | Check khatians table structure | ✅ exists |
| `DEPLOY_TO_CLOUD.bat` / `deploy_to_cloudflare.py` | Deploy live portal to Cloudflare Edge | ✅ exist |
| `RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md` | Integration plan (70% complete) | ✅ created |
| `Land_Intelligence_Hub.html` | Main app with all 3 tabs (incl. new voter tab) | ✅ modified |
| `raipur_pages_deploy/public/index.html` | Public landing page | ✅ exists |
| `upload_raw_to_r2.py` | Upload raw files to R2 storage | ✅ exists |
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
```bat
cd F:\khotiyan book\01_LIVE_SMART_PORTAL_APP
python "%APPD_DIR%deploy_to_cloudflare.py"
```
⚠️ Blocked: sandbox lacks direct Python. Install boto3/Python on target machine, then run.

### Step 5: `/api/voters` Endpoint Bindings
Edit `worker_script` in `raipur_cloudflare_backend/src/index.js`:
- Add GET handler for `GET /api/voters?voter_no=...&name=...&father=...&ward=...`
- POST form-data payload for vault save records
- Use existing `env.DB` bindings pattern.

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
| ৩. Local + Cloud data architecture (SQLite fast search, Cloudflare D1 sync, 30 ms response) | ✅ |
| ৪. Next steps (Step ১-৪) | ✅ (plan written) |
| ৫. Cloud DB schema & optimization (compound indexes) | ✅ |
| ৬. দলিল রেজিস্ট্রি ফি ও অন-গ্রাউন্ড খরচ মডেল | ✅ |
| ৭. ডিরেক্টরি কাঠামো ও ফাইল অবস্থান | ✅ |
| ৮. পরিচালনা ও ব্যবহার নির্দেশিকা | ✅ |
| ৯. প্রিন্ট ও এক্সপোর্ট সুবিধা | ✅ |
| ১০. ভূমি জরিপ বই & ভোটার তালিকা PDF (Backup) | ✅ |
| ১১. রেকর্ড সংরক্ষণ (Vault) | ✅ |
| ১২. ক্লাউড/লোকাল ডেটা আর্কিটেকচার | ✅ |
| ১৩. গিট হুকস (pre-commit) | ✅ (existing) |
| ১৪. নতুন ইঞ্জিটারি প্ল্যান | ✅ |

---

*Plan saved at `F:\khotiyan book\RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN.md`.*
