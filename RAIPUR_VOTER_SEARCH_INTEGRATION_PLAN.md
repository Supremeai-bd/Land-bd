# রায়পুর ভোটার সার্চ ইঞ্জিটারি প্রোগ্রাম (RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN)

## Overview
Historical integration plan for **Voter Search** module — Tab 3 of Raipur Smart Portal. UI/code elements exist, but the local SQLite build and complete Cloud D1 voter ingestion are not verified; the production D1 count was only 108 voters in the 12 Nov 2026 audit.

> **Project:** Raipur Smart Land Cadastre & Citizen Intelligence Hub  
> **Coverage area:** Raipur Upazila, Lakshmipur District, Chattogram Division  
> **Live cloud URL:** https://raipur-land-portal.raipur-land.workers.dev  
> **Prep date:** 11 Nov 2026

> **Current API/privacy contract:** Cloud `/api/voters` requires an active approved deed-writer/admin token. It accepts one of: exact `voter_no`, name substring (minimum 3 characters), or father-name substring (minimum 3 characters); max 5 results. It returns only voter number, name, father and ward. Mother, gender and full address are not part of the cloud response. Fuzzy owner↔voter matches are unverified leads, never legal inheritance/ownership proof.

---

## ১. USER JOURNEY & ৩-ট্যাব বিশিষ্ট ন্যাভিগেশন আর্কিটেক্যার (Unified Top Switcher)

```
NavBar ──► Tab ১. ভূমি ও খতিয়ান অনুসন্ধান (Cadastre)      [btn-view-cadastre]
       │
NavBar ──► Tab ২. দলিল রেজিস্ট্রি ফি ক্যালকুলেটর (Registry)    [btn-view-registry]
       │
NavBar ──► Tab ৩. ভোটার ও নাগরিক অনুসন্ধান (NEW TAB)          [btn-view-voter] ← ✅ added
```

### Tab ৩ — Flexible Querying Panel (`InputConsole` → `Engine`)
- **F1:** ভোটার নম্বর (Voter number; not an NID field)
- **F2:** নাগরিকের নাম (Bangla Name)
- **F3:** পিতার নাম (Father's Name)
- **F4–F6:** mother/ward/address filters are not supported by the current cloud API; if retained locally, keep access local and privacy-restricted.

### Engine Architecture
- **Local:** `raipur_voters_database.js` → fast in-memory/SQLite search (fast client in-mem / SQLite)
- **Cloud:** `deploy_to_cloudflare.py` → secured D1 API with exactly one of `voter_no`, `name` or `father`; no cloud `ward` parameter or response-time SLA is promised.
- **Output:** `OutputCards` → citizen profile card + smart profile result card

---

## ২. সার্চ ইন্টারফেস (UI/UX) ডিজাইন বৈশিষ্ট্য

### ১. Current single-condition search modes
- User provides **any single field** (e.g., only voter number, only name, only father) → still searches.
- Current cloud API accepts one search mode at a time; combined name+father+ward filtering is not implemented.
- **Partial match / LIKE %name%** supported for Bengali names.

### ২. Cloud result — ন্যূনতম field
- **ভোটার নম্বর, নাম, পিতার নাম ও ward** — current Worker response contract; voter number-কে NID বলা যাবে না।
- Mother, gender, full address, export/print ও extended profile এই secured cloud endpoint দেয় না; local-only display হলে access, retention ও disclosure policy আলাদা করে নির্ধারণ করুন।
- Land-record name search একটি সম্ভাব্য match দেখাতে পারে; confirmed owner/heir হিসেবে label নয়, source citation ও human review ছাড়া সিদ্ধান্ত নয়।

### ৩. Print & Export
- Any local print/export feature must be reviewed for personal-data disclosure; current cloud response is minimized and does not include mother, gender or full address.
- Vault endpoints exist, but D1 schema migration and end-to-end integration tests remain pending.

### ৪. রেজাল্ট কার্ড (Rendered Cards)
- Global status pill: "One glance voter search results"
- 3 Pillar Matrix: Sabek (CS/SA) Records · Haal Modern Records · Voter/Cross-Match
- Cross-match: নাম/পিতার নামের similarity হলে কেবল unverified candidate; কোনো validated threshold বা legal match নেই।

---

## ৩. ক্লাউড ও লোকাল ডেটা আর্কিটেকচার

### ১. Localhost Mode
- `01_LIVE_SMART_PORTAL_APP\Land_Intelligence_Hub.html` loads locally (port 8080) offline — super-fast results.

### ২. Cloudflare Edge / D1
- Worker name `raipur-land-portal`; D1 schema/data migration ও full voter ingestion এখনো pending; audit-এ voter count 108 ছিল।
- Current secured API accepts `voter_no` OR `name` OR `father`; ward filter ও 30 ms SLA দাবি করা হয় না.

---

## ৪. বাস্তবায়নের পদক্ষেপ (Next Implementation Steps)

| Step | Action | Status |
|------|--------|--------|
| ১ | Add 3rd nav button & container (done) | ✅ |
| ২ | Multi-field input form & citizen result card UI (done) | ✅ |
| ৩ | Local search UI / Worker endpoint code exists; complete D1 data sync unverified | ⚠️ partial |
| ৪ | Local build/tests, D1 backup/migrations/full-load validation, then deploy | ⏳ pending |
| ৫ | Current Worker voter endpoint exists; vault requires migrated schema and integration tests | ⚠️ pending validation |

---

## ৫. ক্লাউড ডেটাবেস স্কিমা & অপ্টিমাইজেশন (D1 Distributed SQLite)
- Proposed/expected indexes: `khatians(mouza, survey, khatian_no)`, `dag_khatian_map(dag_no, mouza, survey)`; migration and live presence require verification.
- No milliseconds response SLA until full-load data and real query latency are measured.

---

## ৬. দলিক রেজিস্ট্রি ফি ও বাস্তব অন-গ্রাউন্ড খরচ
- Govt Statutory Fees (1%), Stamp Duty (1.5%), Local Govt (2%/3%), AIT 53H, etc. — model complete.

---

## ৭. ডিরেক্টরি কাঠামো ও ফাইল অবস্থান
- `.env` holds CLOUDFLARE credentials (email, global key, D1 DB id, worker name, live URL, local SQLite path).
- `01_LIVE_SMART_PORTAL_APP/`: HTML, registry rates JS, full DB JS, voter DB, mapping data, README.

---

## ৮. পরিচালনা ও ব্যবহার নির্দেশিকা

1. **Local run:** use `RUN_LOCAL_PORTAL.bat` (loopback only); local data assets contain personal information.
2. **Online access:** the Worker requires an active approved deed-writer/admin account for voter search; the current D1 dataset is incomplete.
3. Do not promise full coverage or response-time SLAs until D1 is loaded, verified and measured.

---

## ৮.১ ভূমি জরিপ বই & ভোটার তালিকা PDF (Backup)
- Raw sources preserved in `02_BACKUP_AND_RAW_DATA/`.

---

## ৯. রেকর্ড সংরক্ষণ (Vault)
- Routes exist, but save/read behavior depends on the versioned D1 migration and must pass end-to-end tests before describing as production-ready.

---

*Last updated: 2026-11-11*
