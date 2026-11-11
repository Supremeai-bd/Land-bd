# রায়পুর ভোটার সার্চ ইঞ্জিটারি প্রোগ্রাম (RAIPUR_VOTER_SEARCH_INTEGRATION_PLAN)

## Overview
Integration plan for **Voter Search** module — Tab 3 of Raipur Smart Portal (3-Tab Navigation). Builds on the completed 3-tab navigation (Land Cadastre, Registry Fee Calculator, Voter & Citizen Search), the 492,074 registered voter database (SQLite + Cloud D1 indexed API), unified 3-pillar cross-match view, and dedicated citizen profile cards.

> **Project:** Raipur Smart Land Cadastre & Citizen Intelligence Hub  
> **Coverage area:** Raipur Upazila, Lakshmipur District, Chattogram Division  
> **Live cloud URL:** https://raipur-land-portal.raipur-land.workers.dev  
> **Prep date:** 11 Nov 2026  

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
- **F1:** ভোটার নম্বর (Voter No / NID)
- **F2:** নাগরিকের নাম (Bangla Name)
- **F3:** পিতার নাম (Father's Name)
- **F4:** মাতার নাম (Mother's Name)
- **F5:** ওয়ার্ড / ইউনিয়ন নির্বাচন (Ward / Union)
- **F6:** গ্রাম / পাড়া / ঠিকানা (Gram / Village / Address)

### Engine Architecture
- **Local:** `raipur_voters_database.js` → fast in-memory/SQLite search (fast client in-mem / SQLite)
- **Cloud:** `deploy_to_cloudflare.py` → D1 Edge Serverless `/api/voters?voter_no=...&name=...&father=...&ward=...` (30 ms response)
- **Output:** `OutputCards` → citizen profile card + smart profile result card

---

## ২. সার্চ ইন্টারফেস (UI/UX) ডিজাইন বৈশিষ্ট্য

### ১. Flexible Multi-Parameter Search
- User provides **any single field** (e.g., only voter number, only name, only father) → still searches.
- Multiple fields → finer filtering (e.g., name "হারুন" + পিতা "আব্দুল" + ওয়ার্ড "কেরোয়া").
- **Partial match / LIKE %name%** supported for Bengali names.

### ২. রেজাল্ট কার্ডে প্রদর্শিত পূর্ণাঙ্গ তথ্য (Citizen Profile Card)
- 🆔 **ভোটার নম্বর (NID):** copyable ID
- 👤 **নাগরিকের নাম:** Full Bangla name
- 👨‍👦 **পিতার নাম:** Father's name
- 👩‍👧 **মাতার নাম:** Mother's name
- 🔗 **লিঙ্গ:** পুরুষ / মহিলা / হিজড়া (gender inference via similarity)
- 📍 **ওয়ার্ড ও ইউনিয়ন:** Ward & Union
- 🏠 **গ্রাম ও বাড়ি/ঠিকানা:** Full address (e.g., পাঠারী বাড়ী, চর আবাবিল, রায়পুর, লক্ষ্মীপুর)
- 🔗 **ভূমি রেকর্ড লিঙ্কার বাটন:** "এই ব্যক্তির ভূমি রেকর্ড খুঁজুন" → opens Cadastre tab, searches by name

### ৩. Print & Export
- One or multiple voters selected → instant clean slips print.
- Browser print available; vault save records for each voter.

### ৪. রেজাল্ট কার্ড (Rendered Cards)
- Global status pill: "One glance voter search results"
- 3 Pillar Matrix: Sabek (CS/SA) Records · Haal Modern Records · Voter/Cross-Match
- Cross-match: name + father + land owner matching (0.45 threshold)

---

## ৩. ক্লাউড ও লোকাল ডেটা আর্কিটেকচার

### ১. Localhost Mode
- `01_LIVE_SMART_PORTAL_APP\Land_Intelligence_Hub.html` loads locally (port 8080) offline — super-fast results.

### ২. Cloudflare Edge / D1
- Syncs voter index into Cloudflare D1; launches live worker `raipur-land-portal` (worker `raipur-land-portal`, account `f8642291c490425e5bdc4070e28a3953`).
- New binding: `GET /api/voters?voter_no=...&name=...&father=...&ward=...` (30 ms, no heavy file download).

---

## ৪. বাস্তবায়নের পদক্ষেপ (Next Implementation Steps)

| Step | Action | Status |
|------|--------|--------|
| ১ | Add 3rd nav button & container (done) | ✅ |
| ২ | Multi-field input form & citizen result card UI (done) | ✅ |
| ৩ | Local search logic + CloudFlare Worker API sync (done) | ✅ |
| ৪ | Run `DEPLOY_TO_CLOUD.bat` → live deploy to Cloud (blocked: Python not installed in sandbox) | ⏳ pending |
| ৫ | Add `/api/voters` endpoint bindings to `worker_script` (form-data POST for vault save) | ⏳ pending |

---

## ৫. ক্লাউড ডেটাবেস স্কিমা & অপ্টিমাইজেশন (D1 Distributed SQLite)
- Compound indexes: `khatians(mouza, survey, khatian_no)`, `dag_khatian_map(dag_no, mouza, survey)`
- Indexed search for fast lookups (milliseconds per query)

---

## ৬. দলিক রেজিস্ট্রি ফি ও বাস্তব অন-গ্রাউন্ড খরচ
- Govt Statutory Fees (1%), Stamp Duty (1.5%), Local Govt (2%/3%), AIT 53H, etc. — model complete.

---

## ৭. ডিরেক্টরি কাঠামো ও ফাইল অবস্থান
- `.env` holds CLOUDFLARE credentials (email, global key, D1 DB id, worker name, live URL, local SQLite path).
- `01_LIVE_SMART_PORTAL_APP/`: HTML, registry rates JS, full DB JS, voter DB, mapping data, README.

---

## ৮. পরিচালনা ও ব্যবহার নির্দেশিকা

1. **Local run:** Open `Land_Intelligence_Hub.html` in any browser → fully offline portal.
2. **Online cloud access:** Directly from phone/computer → https://raipur-land-portal.raipur-land.workers.dev
3. **Free tier monitoring:** Cloudflare D1 → 50K queries/day free.
4. **Response time:** 30–50 ms per search (responsive).

---

## ৮.১ ভূমি জরিপ বই & ভোটার তালিকা PDF (Backup)
- Raw sources preserved in `02_BACKUP_AND_RAW_DATA/`.

---

## ৯. রেকর্ড সংরক্ষণ (Vault)
- Save Khatian, Voter, Saved items via `/api/user/save-khatian`, `/api/user/save-voter`, `/api/user/saved-items?userId=…`

---

*Last updated: 2026-11-11*
