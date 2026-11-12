# রায়পুর Land & Citizen Portal — Project ও Data/Database Audit

**প্রাথমিক পর্যালোচনা:** ১২ নভেম্বর ২০২৬  
**পরিধি:** `F:\khotiyan book`-এর source/config/docs, raw ও partitioned data-র inventory ও aggregate profiling, local SQLite schema/count, এবং Cloudflare D1-তে read-only schema/count/query checks।  
**Remediation update:** source/config/schema/importer files পরিবর্তিত হয়েছে; production D1-তে কোনো write/deploy করা হয়নি। এই প্রতিবেদনে কোনো নাম, ভোটার নম্বর, ফোন, ঠিকানা বা credential রাখা হয়নি।

## ১. নির্বাহী সারাংশ

প্রজেক্টে যথেষ্ট raw source ও extracted/partitioned data আছে, এবং partition count যাচাইয়ে মূল JSON থেকে হারানো record পাওয়া যায়নি। কিন্তু “raw data থেকে production database তৈরি” অংশটি **সম্পূর্ণ/বিশ্বস্ত বলে গণ্য করা যাবে না**: local SQLite database schema-only/খালি; Cloudflare D1-তে source-এর তুলনায় অল্প data; import path অসম্পূর্ণ ও idempotent নয়; raw PDF থেকে current canonical JSON তৈরির reproducible extraction pipeline inventory-তে পাওয়া যায়নি। উপরন্তু, production API/security ও কয়েকটি search/vault route-এ কার্যকরী ত্রুটি আছে।

সবচেয়ে জরুরি তিনটি বিষয়:

1. Worker-এ hard-coded fallback signing secret আছে; secret binding না থাকলে forged admin token সম্ভব।
2. voter search endpoint authentication ছাড়াই পূর্ণ ব্যক্তিগত voter fields ফেরত দেয়; root cause-এর পাশাপাশি public/static deployment exposure-ও পর্যালোচনা দরকার।
3. D1 অসম্পূর্ণ: source-এ 157,657 khatians ও 492,074 voters; D1-তে যথাক্রমে 41,632 ও 108। dag-index-ও 418,967 expected relation-এর বদলে 77,825 row।

## ২. ডেটা-ফ্লো ও interconnection

বর্তমান ফাইল ও code অনুযায়ী intended path:

```text
মূল PDF/অন্যান্য source
       │  (reproducible extraction code এখানে নিশ্চিত নয়)
       ▼
raipur_master_khatians.json ──► raipur_master_dag_index.json
raipur_all_voters.json       ──► data/khatians/ (69 shard)
                              └─► data/voters/ (185 shard)
       │
       ├─► create_sqlite_db.py ──► local SQLite schema (কিন্তু record import নেই)
       └─► sync scripts ────────► Cloudflare D1 (আংশিক voter sync path; full ETL নেই)
                                      │
                                      ▼
                              Cloudflare Worker API
                                      │
                                      ▼
                               Portal HTML/UI
```

### Land records ও dag index

Canonical khatian record-এর fields: `mouza`, `survey`, `khatianNo`, `owners`, `guardian`, `dags`, `totalLand`। Reconciliation script khatian-এর প্রতিটি `dags` থেকে `(mouza, survey, dag_no) → khatian_no[]` inverted index তৈরি করে। `raipur_master_dag_index.json`-এ 69 mouza, 170 mouza-survey bucket, 273,358 distinct dag key ও 418,967 unique dag→khatian relation আছে। বিদ্যমান verification summary অনুযায়ী এই index master khatian-এর dags-এর সঙ্গে bidirectionally consistent এবং index target খতিয়ানে মেলে। এটি **একই survey-এর dag-to-khatian lookup**; এটি নিজে CS/SA/RS থেকে BRS-এ সাবেক-হাল crosswalk নয়।

### Voter ও land-owner relation

Voter source-এ 492,074 record, 185 ward ও 552 source PDF শনাক্ত হয়েছে। Land owner/guardian থেকে voter-এ কোনো shared stable key/foreign key দেখা যায়নি; UI-তে heir/citizen correlation মূলত নাম/পিতার নামের similarity search। তাই এটি সম্ভাব্য match, আইনি উত্তরাধিকার বা মালিকানা প্রমাণ নয়; official record/manual verification ছাড়া নিশ্চিত সম্পর্ক হিসেবে দেখানো ঝুঁকিপূর্ণ।

### Registry rates

Registry rate JSON/JS ও calculator flow আলাদা asset/code path-এ আছে; D1 relational schema-তে rates-এর table নেই। বর্তমান deployment script rates JS inline করে, কিন্তু মূল land/voter DB JS assets-কে একইভাবে inline/bundle করে না।

## ৩. পরিমাণগত অবস্থা

| অংশ | Local source / shards | Production D1 / local DB | মূল্যায়ন |
|---|---:|---:|---|
| Khatians | 157,657; 69 mouza shard | D1: 41,632; 9 distinct mouza | D1 source-এর প্রায় 26.4% |
| Voters | 492,074; 185 ward shard | D1: 108 | source-এর প্রায় 0.022% |
| Dag→khatian relation | 418,967 unique derived/index relation | D1: 77,825; 380 orphan target | expected relation-এর প্রায় 18.6%; D1 mismatch আছে |
| Local SQLite | `khatians`, `dag_khatian_map`, `voters`, `users`, saved tables | সব application table-এ 0 row | schema আছে; database population হয়নি |
| Partition integrity | 69 khatian + 185 voter files | 157,657 + 492,074 rows | আগের report-এ lossless count pass; independent aggregate-এও row sum মেলে |

Local database `raipur_cadastre_voters.db` SQLite `quick_check`-এ structurally ঠিক, কিন্তু data-শূন্য। Production D1-তে 1,376 duplicate `(mouza,survey,khatian_no)` group (1,945 extra row), এবং 380 dag-map row কোনো khatian-এ resolve হয় না। D1 voters-এ 25 duplicate voter-ID group (30 extra row)। D1-তে একটি active admin account আছে; ব্যক্তিগত account তথ্য ইচ্ছাকৃতভাবে এখানে প্রকাশ করা হয়নি।

## ৪. যাচাইকৃত ডেটা মান ও mapping সমস্যা

1. **Khatian identity duplicate:** raw master-এ 4,160 duplicate `(mouza,survey,khatianNo)` group, 5,345 অতিরিক্ত row। এগুলো duplicate OCR/data-entry error, multiple source version, নাকি বৈধ multiple entry—source book-এ sample adjudication ছাড়া বলা যাবে না। বর্তমানে uniqueness policy নেই।
2. **Voter-ID duplicate:** raw voter source-এ 755 duplicate voter number group, 772 অতিরিক্ত row। Existing exception JSON এগুলো audit-এ তুলেছে; কিন্তু sync schema-তে `voter_no` unique নয় এবং import behavior পরিষ্কার নয়।
3. **অস্বাভাবিক survey label:** raw khatian-এ documented 5 survey value (CS/SA/RS/BRS/Mutation)-এর বাইরে `৪৯)` 3,259 record এবং `রাখালিয়া` 1,685 record—মোট 4,944 record। এগুলো 3.14% dataset; ভুল field alignment/label/OCR বা অনির্ধারিত source type হতে পারে। সরাসরি canonical survey-তে auto-convert করা যাবে না; quarantine ও PDF verification দরকার।
4. **মৌজা বানান/alias ও export-version drift:** canonical raw master-এ 69 mouza; আলাদা `mouza_data` directory-তে 73 JSON export file। বিভিন্ন spelling/space/variant নাম আছে। `data/manifest.json`-এর `missing_from_khatians`-এ 4 mouza লেখা, অথচ তার 69 manifest entry-ই বর্তমান canonical master-এর 69 mouza-র সঙ্গে মেলে—এই metadata stale/পরস্পরবিরোধী। `mouza_manifest.json` পরে update হলেও `data/manifest.json` আগের timestamp-এর।
5. **Coverage verification সীমিত:** `mapping_verification.json`-এ 8/10 checks pass, duplicate identity ও duplicate voter ID fail। Partition equality ও dag-index synchronization pass মানে কেবল JSON↔JSON consistency; মূল PDF-র বিরুদ্ধে extracted value correctness বা legal cross-survey mapping যাচাই নয়। এটি generated verification snapshot; বর্তমান source PDFs-এর full page-by-page OCR audit করা হয়নি।
6. **Cross-survey dag mapping নেই:** বর্তমান relational map `(mouza,survey,dag,khatian)`-এ, ফলে এটি per-survey lookup। CS/SA/RS→BRS parcel lineage, split/merge ও share/provenance-এর আলাদা evidence-backed relation table দেখা যায়নি; ডকুমেন্টেশনের cross-survey “automatic mapping” দাবির তুলনায় data model অপর্যাপ্ত।
7. **Owner↔voter match অনিশ্চিত:** owner name/father name fuzzy matching common names, বানানভেদ, জীবিত/মৃত/ওয়ারিশ, ও একই নামের ব্যক্তিকে নির্ভরযোগ্যভাবে আলাদা করতে পারে না। confidence, source page, match reason, human review status ও false-positive audit trail persist হওয়ার relational model/API দেখা যায়নি।


## ૫. Code / deployment / database defects

### P0 — Authentication/security

- `raipur_cloudflare_backend/src/index.js`-এ production fallback হিসেবে hard-coded token signing secret আছে। `.env.example`-এ `TOKEN_SECRET` নেই; deployment code secret ঐচ্ছিকভাবে inject করে। তাই secret না দিলে source-এ থাকা default ব্যবহার হতে পারে। এই অবস্থায় attacker নিজের মতো `admin` role-সহ signed token তৈরি করে admin route-এ যেতে পারে। Default secret বাদ দিয়ে secret অনুপস্থিত হলে startup/deployment fail-closed করতে হবে; production secret rotate করতে হবে।
- `GET /api/voters`-এ login/authorization নেই এবং no-filter request-ও 50 voter record ফেরত দেয়। Response-এ voter number, নাম, বাবা-মা, gender, ward ও address আছে। CORS allowlist authentication নয়—server-side request বা non-browser client দিয়ে endpoint access করা যায়। Rate limit, least-data response, strict access policy, audit এবং production voter data exposure review জরুরি।
- Local frontend directory-তে 171.9 MB voter JS data asset আছে; Git ignore করলেও local static server বা ভুলভাবে public asset deploy হলে raw PII client-এ চলে যায়। `upload_raw_to_r2.py` raw/data folder-ও upload target করে; public bucket/domain configured কি না আলাদাভাবে যাচাই করা প্রয়োজন।

### P1 — Database ingestion/completeness

- `create_sqlite_db.py` বিদ্যমান `.db` delete করে fresh schema বানায়, কিন্তু JSON পড়া/insert করা হয় না—insert calls empty list-এ চলে। Script-এর “indexes” বর্ণনা থাকলেও custom search index তৈরি নেই। Data-bearing DB তৈরি করতে এটি ব্যবহারযোগ্য ETL নয়; destructive delete behavior-ও ঝুঁকিপূর্ণ।
- D1-তে schema আছে কিন্তু row count source-এর তুলনায় অনেক কম। `sync_to_d1.py` voters-এ সীমিত max-record sync করে; `sync_batch_d1.py` কেবল নির্দিষ্ট প্রথম কয়েকটি ward নেয়; `fast_d1_sync.py`-তে `base_dir` undefined, তাই `main()` path-এ runtime failure হবে। Khatian ও full dag-index-এর production-safe, repeatable importer/migration নেই।
- Sync SQL simple INSERT; unique constraints/upsert/checkpoint/restart strategy/duplicate quarantine/atomic full-load verify নেই। Re-run duplicate rows বাড়াতে পারে। Database build “actual complete source” হিসেবে verified নয়।
- D1 index coverage query path-এর জন্য অসম্পূর্ণ: `khatians` compound index `(mouza,survey,khatian_no)`, কিন্তু search অনেক সময় khatian number একা দিয়ে; `dag_khatian_map` index `(mouza,survey,dag_no)`, কিন্তু dag একা দিয়ে lookup হয়। `voters`-এ `voter_no` index নেই। `LIKE '%term%'` pattern-এ সাধারণ B-tree name/father indexও কার্যকর হয় না।

### P1 — Production query/runtime bugs

- Worker-এর dag search join-এ mouza/survey filter append হলে `mouza`/`survey` columns দুই table-এই থাকায় unqualified SQL ambiguous। D1-তে read-only query দিয়ে `ambiguous column name: mouza` 400 error reproduce হয়েছে। UI mouza selection দিয়ে dag search করলে route ভাঙতে পারে; সব shared fields `m.`/`k.` alias দিয়ে qualify করতে হবে।
- Survey grouping mismatch: Worker SABEK filter-এ RS অন্তর্ভুক্ত, local UI SABEK-এ শুধু CS ও SA; Worker result bucketing-এ Mutation-কে `haalRecords` না দিয়ে default `sabekRecords`-এ ফেলে। Cloud/local search তাই category ও result-এ একরকম নয়।
- `saved_voters` production schema-তে `id INTEGER PRIMARY KEY AUTOINCREMENT`, কিন্তু Worker string ID (`sv_...`) insert করে; schema-তে `notes` column নেই, অথচ Worker `notes` insert করে। এই route save করতে গেলে schema mismatch/type failure হবে। Existing schema-তে `relation_tag` আছে। Schema migration ও Worker payload একই contract-এ আনতে হবে।
- Worker `saved-items` query token user ID অনুযায়ী scope করে—ভালো—কিন্তু front-end fetch userId query param পাঠায়; API authorization contract/documentation পরিষ্কার করা উচিত।

### P1 — App asset/deploy mismatch

- HTML তিনটি external local data JS (`raipur_full_database.js`, `core_7_database.js`, `raipur_voters_database.js`) লোড করে। Git-এ raw/large JS assets ignore করা, tracked file list-এ নেই। `deploy_to_cloudflare.py` rates JS inline করে, কিন্তু এই data JS assets inline/bundle করে না; Worker-ও static JS file route দেয় না। GitHub Actions checkout-এ asset অনুপস্থিত থাকবে এবং deployed HTML-এর local fallback data load ভাঙবে। D1 API complete না হওয়ায় fallback-ও জরুরি।
- `wrangler.toml`-এর Worker name `raipur-land-api`, অথচ deploy Python/README-এর target `raipur-land-portal`। Wrangler বনাম custom deployment path কোনটি authoritative তা একীভূত করতে হবে।

### P2 — Reproducibility/docs/ops

- Inventory-তে raw PDF ingestion-এর reproducible extraction/ETL script বা PDF/OCR dependency নেই; `generate_checklist.py`/`retry_missing.py` checklist/download automation। ফলে canonical JSON থেকে কোন PDF/page-এ কোন row এসেছে তার source provenance পুনরুৎপাদন ও যাচাই কঠিন।
- README ও project docs full/secure/serverless ingestion-কে সম্পন্ন বললেও local DB খালি এবং D1 partial; statements current state-এর সঙ্গে মেলে না। Raw PDF folder-এ 291 survey PDF ও 552 voter PDF আছে; mapping-data subfolder-এ আরও 16 PDF, মোট inventory 859 PDF।
- `partition_datasets.py` expected counts hard-code করে এবং mismatch হলেও শেষের status text “100% zero-loss” বলে; এটি নির্ভরযোগ্য success gate নয়।

## ৬. Git/privacy posture — ভালো দিক ও সীমাবদ্ধতা

বর্তমান Git tracked-file list-এ `.env`, local `.db`, raw JSON/PDF ও বড় voter JS assets নেই; `.gitignore` allowlist/denylist ও pre-commit secret/size check আছে। এই অংশ ইতিবাচক। কিন্তু এতে production API বা public R2/static serving নিরাপদ প্রমাণ হয় না। Hard-coded token-secret source code-এ আছে—Git ignore সেটি ঢাকে না।

## ৭. করণীয় — প্রস্তাবিত ক্রম

1. **তাৎক্ষণিক:** Worker fallback signing secret সরিয়ে fail-closed; `TOKEN_SECRET` rotate ও required binding; voter API-তে authentication/authorization, rate limit, response minimization; public asset/R2 exposure audit।
2. **Schema contract/migration:** schema versioned migration-এ freeze করুন; `saved_voters`-এর id type/notes field ঠিক করুন; FK/enforcement/PK/unique policy ও consistent types লিখিত করুন।
3. **Canonicalization:** duplicate khatian/voter rows ও 4,944 abnormal survey rows PDF-page provenance-সহ quarantine; approved mouza alias table/JL number যোগ; source decisions audit-log-এ রাখুন।
4. **একটি ETL:** raw/canonical JSON → staging → validation → transactional/upsert load → indexes → count/checksum report; all 157,657 khatians, 418,967 unique dag links ও 492,074 voter rows (approved dedupe policy অনুযায়ী) load না হওয়া পর্যন্ত “complete” mark নয়। Restart-safe checkpoint ও idempotence আবশ্যক।
5. **Relation model:** same-survey dag lookup থেকে আলাদা explicit cross-survey parcel-lineage table (source, page, mapping type, split/merge, confidence, reviewed status) তৈরি; fuzzy owner-voter match-কে probabilistic lead হিসেবে চিহ্নিত, verified ownership হিসেবে নয়।
6. **App/API repair:** join field qualify; CS/SA/RS/BRS/Mutation categories এক contract-এ; voter_no lookup/index; full-text/fuzzy query plan; vault schema/API integration tests।
7. **Deploy/test:** Worker HTML-এ bundled assets/API-only fallback architecture বেছে নিন; GitHub Actions checkout test-এ external script 404 এবং critical routes পরীক্ষা; `wrangler.toml` ও Python deployment name sync করুন।
8. **Manifest/docs:** reconcile/partition শেষে manifest regenerate; counts ও timestamps automate; stale documentation/claims আপডেট করুন।

## ৮. সীমা ও সতর্কতা

এই audit raw/source files-এর inventory ও aggregate structure/count, existing verification report/script, local SQLite এবং production D1-এর read-only table/count/query metadata নিয়ে। 859টি PDF page-by-page OCR/visual verification করা হয়নি; ফলে raw PDF-এর বিরুদ্ধে নাম, দাগ, জমির পরিমাণ বা legal ownership-এর সঠিকতা এই audit certify করে না। জমি/উত্তরাধিকার বিষয়ে database match আইনি প্রমাণ নয়; original official record ও authorized human review প্রয়োজন।

## ৯. Root remediation status (১২ নভেম্বর ২০২৬)

### Source-level fixes applied

- Worker থেকে hard-coded token secret বাদ; 32-byte minimum secret check, strict expiry/header validation, active-user DB lookup, এবং authorization role DB থেকে নেওয়া হয়। Missing secret-এ auth routes fail-closed।
- Voter lookup এখন active approved deed-writer/admin-এ সীমিত, voter number exact match, নাম/পিতার নাম কমপক্ষে ৩ অক্ষর, সর্বোচ্চ ৫ ফল, এবং response-এ ন্যূনতম field। Global response-এ `no-store`/`nosniff` যোগ। Distributed rate limiting এখনও যোগ করা হয়নি।
- Dag search-এ `k.` alias এবং shared mouza/survey filter qualify; `Mutation`/`নামজারি` Worker grouping-এ হাল record।
- `0001` baseline ও `0002` D1 migration যোগ: saved record ID text, voter notes/provenance, query indexes; deployment script schema ও exact expected row-count preflight ছাড়া Worker upload করবে না। Migration এখনও চালানো হয়নি।
- `create_sqlite_db.py` এখন partition JSON insert করে, dag map তৈরি করে, source/manifest count, quick-check ও foreign-key check চালায়; বিদ্যমান DB স্পষ্ট `--replace` ছাড়া overwrite করে না এবং backup রাখে। Script এখনও চালিয়ে local DB populate করা হয়নি।
- Partitioner hard-coded expected counts/“100% zero-loss” দাবি বাদ দিয়ে source-derived counts, stale shard cleanup, safe filename collision handling, unknown survey quality flags ও honest manifest লিখে। Reconciliation output atomic; duplicate exception file-এ voter fields-এর বদলে non-identifying record indexes রাখা হয়।
- Cloud build local heavy data JS-asset references বাদ দিয়ে API-only `DATABASE` fallback, secured voter token header, dry-run default, strong secret requirement ও D1 schema/row-count preflight ব্যবহার করে। GitHub Actions push-এ test করে; production deploy কেবল explicit manual input-এ চালু হয়। Wrangler/Worker name একীভূত।
- R2 uploader default-এ শুধু registry-rate JSON; raw voter/land data আপলোডে explicit sensitive flag, public-domain unset, ও private-bucket confirmation লাগে। Local static server `127.0.0.1`-এ bind হয়।
- Legacy partial D1 sync scripts read-only planner-এ নামানো হয়েছে; accidental voter-prefix partial/duplicate write আর করবে না।

### এখনও বাকি / যাচাই হয়নি

1. এই desktop session-এ terminal initialization ব্যর্থ (`terminal:config home unavailable`) হওয়ায় Python/Node/SQL/CI tests চালানো যায়নি। Local SQLite file এখনও আগের অবস্থায়; নতুন builder execute হয়নি।
2. Production D1 schema migration, backup, এবং full source load করা হয়নি। D1-র পুরোনো aggregate counts (এই audit-এ 41,632 khatians, 108 voters, 77,825 dag links) এখনও অসম্পূর্ণ; load-এর আগে duplicate/ambiguous rows-এর retention policy ও resumable import পরিকল্পনা দরকার।
3. Local মূল HTML >1 MB হওয়ায় সরাসরি source edit সম্ভব হয়নি। Cloud deploy script-এ online voter token/category fixes transform করা হয়েছে; local UI-র SABEK filter এখনও RS include করে কি না এবং live-render integration test CI-তে যাচাই বাকি।
4. 4,944 unknown survey-label records, duplicate khatian/voter groups, PDF/page provenance, এবং true cross-survey parcel lineage হাতে/PDF-তে review করা হয়নি; কোনো legal owner↔voter relation assert করা হচ্ছে না।
5. Deploy, D1 migration বা production data upload স্বয়ংক্রিয়ভাবে চালানো হয়নি। প্রথমে local build/tests, তারপর backup ও migration review এবং approved full-load plan প্রয়োজন।
