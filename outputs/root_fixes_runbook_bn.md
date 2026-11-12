# Root fixes — চালানো ও যাচাই করার নির্দেশিকা

এই runbook ১২ নভেম্বর ২০২৬-এ code/config/schema-তে করা remediation-এর জন্য। **এই session-এ terminal চালু হয়নি**, তাই local database build, automated tests, D1 migration, বা deployment চালানো হয়নি।

## Source-level fixes

- Worker-এ default signing secret সরানো হয়েছে; 32-byte secret, strict token expiry, active user এবং DB-backed role যাচাই আছে। Voter endpoint active approved deed-writer/admin-only, exact voter-number বা কমপক্ষে ৩ অক্ষরের name/father query, সর্বোচ্চ ৫ ফল, এবং minimized response ব্যবহার করে।
- Dag lookup-এ ambiguous mouza/survey filter qualify করা, `Mutation`/`নামজারি`-কে হাল ফল হিসেবে bucket করা হয়েছে।
- `raipur_cloudflare_backend/migrations/0001_base_schema.sql` এবং `0002_contract_and_lookup_indexes.sql` তৈরি হয়েছে। এগুলো saved IDs/notes ও `source_pdf` contract এবং exact lookup indexes align করে। D1-তে এখনো migration apply করা হয়নি।
- `create_sqlite_db.py` এখন `data/khatians/*.json` ও `data/voters/*.json` থেকে records, provenance ও dag links import করে; manifest count, SQLite integrity, FK ও table counts check করে। Existing DB স্পষ্ট `--replace` ছাড়া বদলাবে না; replace হলে timestamped backup রাখবে। Duplicate record বাদ দেওয়া হয় না; unknown survey labels review flag পায়।
- Partitioner source-derived count ও safer manifest লিখে; reconciliation atomic output দেয় এবং duplicate exception export-এ ব্যক্তিগত field-এর বদলে array index রাখে। আগের exception dump aggregate-only করে redact করা হয়েছে।
- Cloud deploy bundle বড় local data assets বাদ দিয়ে API-only; voter request session token ব্যবহার করে। Deployment default dry-run, `--apply` ছাড়া upload নয়, `TOKEN_SECRET` ছাড়া deploy নয়, এবং D1 schema বা exact row-count preflight ব্যর্থ হলে upload থামে।
- Legacy partial D1 sync scripts এখন read-only planner; accidental prefix sync/duplicate write করবে না। R2 upload default-এ sensitive voter/land files বাদ; Windows local portal শুধু `127.0.0.1`-এ bind করে।

## Local validation ও পূর্ণ SQLite তৈরি

PowerShell-এ workspace-এ গিয়ে:

```powershell
Set-Location 'F:\khotiyan book'
python -m py_compile .\deploy_to_cloudflare.py .\check_deploy_syntax.py .\create_sqlite_db.py .\partition_datasets.py .\sync_to_d1.py .\sync_batch_d1.py .\fast_d1_sync.py .\upload_raw_to_r2.py .\reconcile_and_normalize.py
python .\check_deploy_syntax.py
python .\partition_datasets.py
python .\create_sqlite_db.py --replace
```

`--replace` পুরোনো SQLite file-কে backup করে তারপর database পুনর্নির্মাণ করবে। Script শেষ হলে printed khatian/voter/dag counts, `quick_check=ok`, foreign-key errors `0` ও unclassified survey count দেখুন। Manifest/source count না মিললে বা required identity missing থাকলে builder target DB প্রতিস্থাপন করবে না।

এই import canonical JSON ও partition files-এর consistency যাচাই করে; মূল PDF-র OCR correctness, duplicate adjudication, বা legal ownership certify করে না। Unknown survey ও duplicate row ইচ্ছাকৃতভাবে রাখা হয়।

## Cloudflare D1 / deployment — এখনো pending

1. Dashboard বা অনুমোদিত backup পদ্ধতিতে বর্তমান D1-এর যাচাইকৃত backup নিন। বর্তমান D1 counts পূর্ণ source coverage-এর সমান নয়।
2. Duplicate voter/khatian rows ও `৪৯)`/`রাখালিয়া` survey-label records কীভাবে রাখতে/পর্যালোচনা করতে হবে তা নির্ধারণ করুন। কোনো dedupe policy স্বয়ংক্রিয়ভাবে প্রয়োগ করা হয়নি।
3. Migration SQL review করে, backup যাচাইয়ের পর:

```powershell
Set-Location 'F:\khotiyan book\raipur_cloudflare_backend'
npx wrangler d1 migrations apply raipur-land-cadastre --remote
```

4. **Full D1 data load-এর approved resumable/idempotent procedure এখনো তৈরি বা চালানো হয়নি.** `sync_to_d1.py` read-only count planner; `--apply` block হয়। Legacy partial loaders disable করা হয়েছে, তাই D1-তে manual partial voter push করবেন না. Deploy preflight exact expected counts (157,657 khatian / 492,074 voter / 418,967 dag relations) মিলিয়ে দেখে; duplicate/dedup policy বদলালে approved config count বদলাতে হবে। Full load/backup/row-count QA ছাড়া Worker deploy হবে না.
5. D1 schema ও full load verified হলে `.env`/CI secret `TOKEN_SECRET`-এ unique random ≥32-byte value দিন। Existing session tokens rotation-এ invalid হবে। `python deploy_to_cloudflare.py` local build-only; approved deploy-এর জন্য `python deploy_to_cloudflare.py --apply` ব্যবহার করুন। Script D1 schema ও exact row-count preflight চালাবে।

GitHub Actions relevant source pushes-এ Python/bundle/Worker syntax checks চালায়; production deploy step default-এ বন্ধ। শুধু `workflow_dispatch`-এ `deploy=true` দিলে deploy চেষ্টা করে, এবং তখনও `TOKEN_SECRET`, migration ও exact-count preflight লাগে। Migration auto-apply করে না। D1 backup, migration ও full-load approval শেষ হওয়ার আগে deploy চালাবেন না।

## এখনো যাচাই/সমাধান বাকি

- এই desktop-এ terminal initialization `terminal:config home unavailable` দেখানোয় উপরোক্ত command ও CI test চালানো হয়নি; local SQLite এখনো build করা হয়েছে বলে দাবি করা হচ্ছে না।
- Production D1 এখনো incomplete; migration/data load/deployment করা হয়নি।
- Local HTML file 1 MB সীমার বেশি হওয়ায় এই session-এ সরাসরি edit হয়নি। Cloud build transform API call, data assets ও auth token handle করে; local UI-র SABEK filter-এ RS inclusion-সহ render/integration checks CI-তে চালাতে হবে।
- Distributed voter-search rate limit, evidence-backed cross-survey lineage, PDF/page-level OCR review ও owner↔voter human-review workflow এখনো বাকি।
