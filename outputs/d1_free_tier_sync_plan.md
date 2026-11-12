# Cloudflare D1 ফ্রি-টিয়ার রিসেট ও প্রোডাকশন সিঙ্ক অ্যাকশন প্ল্যান

**তারিখ:** ১২ নভেম্বর ২০২৬  
**লক্ষ্য:** Cloudflare D1-এর দৈনিক ফ্রি-টিয়ার রাইট কোটা (100k rows/day) রিসেট হওয়ার পর ধাপে ধাপে মাইগ্রেশন, ব্যাচ ইনজেশন এবং ডিপ্লয়মেন্ট সম্পন্ন করা।

---

## ১. বর্তমান পরিস্থিতি ও পরিকাঠামো সীমাবদ্ধতা

* **লোকাল অবস্থা (১০০% প্রস্তুত):**  
  লোকাল SQLite ডেটাবেস (`raipur_cadastre_voters.db`) সম্পূর্ণ তৈরি ও যাচাইকৃত:
  * খতিয়ান: **১,৫৭,৬৫৭**
  * দাগ-খতিয়ান সম্পর্ক: **৪১৮,৯৬৭**
  * ভোটার: **৪৯২,০৭৪**
  * `PRAGMA quick_check`: **`ok`**
* **Cloudflare D1 অবস্থা:**  
  পূর্বে সিঙ্ক চলার কারণে দৈনিক ১০০,০০০ রো রাইট সীমা অতিক্রম করেছে (`Code 7500: daily row write limit exceeded`)।
* **কোটা রিসেট সময়:**  
  প্রতিদিন **00:00:00 UTC** (বাংলাদেশ সময় **সকাল ০৬:০০ AM**)।

---

## ২. ফ্রি-টিয়ার মাল্টি-ডে সিঙ্ক কৌশল (Free-Tier Strategy)

মোট ডেটা সাইজ:  
`157,657 (Khatians) + 418,967 (Dag relations) + 492,074 (Voters) = 1,068,698 rows`  
যেহেতু দৈনিক সীমা **১,০০,০০০ রো**, তাই ফ্রি-টিয়ারে এটি একটি ধারাবাহিক মাল্টি-স্টেপ প্রসেস:

| ধাপ | লক্ষ্য ও টার্গেট ডেটা | আনুমানিক রো সংখ্যা | অগ্রাধিকার |
|---|---|---:|---|
| **ধাপ ১ (আজ সকাল ৬:০০ AM)** | D1 মাইগ্রেশন অ্যাপ্লাই + বাকি খতিয়ান পূরণ | ~১,১৫,০০০ (D1-তে বর্তমানে ৪১,৬৩২ আছে) | **P0** (জমি সার্চ সক্রিয়করণ) |
| **ধাপ ২ (পরবর্তী দিন)** | `dag_khatian_map` ১ম অংশ সিঙ্ক | ~১,০০,০০০ | **P1** (দাগ দিয়ে খতিয়ান অনুসন্ধান) |
| **ধাপ ৩ (পরবর্তী দিন)** | `dag_khatian_map` ২য় অংশ সিঙ্ক | ~১,০০,০০০ | **P1** |
| **ধাপ ৪ (পরবর্তী দিন)** | `dag_khatian_map` ৩য় অংশ সিঙ্ক | ~১,০০,০০০ | **P1** |
| **ধাপ ৫ (পরবর্তী দিন)** | `dag_khatian_map` শেষ অংশ ও ভোটার শুরু | ~১,০০,০০০ | **P2** |
| **ধাপ ৬+ (পরবর্তী দিনগুলো)** | অবশিষ্ট ভোটার তালিকা সিঙ্ক | ~৮০,০০০/দিন | **P2** (নাগরিক যাচাই) |

---

## ৩. সকাল ৬:০০ AM-এর পর এক্সিকিউশন স্টেপস (Runbook)

### ধাপ ১: কোটা রিসেট ভেরিফিকেশন
টার্মিনালে নিচের কমান্ড চালিয়ে চেক করুন API আবার রাইট পারমিশন দিচ্ছে কি না:
```powershell
python -c "
import os, urllib.request, json
from dotenv import load_dotenv
load_dotenv('F:/khotiyan book/.env')
acc, db = os.getenv('CLOUDFLARE_ACCOUNT_ID'), os.getenv('CLOUDFLARE_D1_DATABASE_ID')
email, key = os.getenv('CLOUDFLARE_EMAIL'), os.getenv('CLOUDFLARE_GLOBAL_API_KEY')
req = urllib.request.Request(f'https://api.cloudflare.com/client/v4/accounts/{acc}/d1/database/{db}/query',
    data=json.dumps({'sql': 'SELECT count(*) FROM khatians;'}).encode(),
    headers={'X-Auth-Email': email, 'X-Auth-Key': key, 'Content-Type': 'application/json'})
print(json.loads(urllib.request.urlopen(req).read().decode()))
"
```

---

### ধাপ ২: D1 স্কিমা মাইগ্রেশন এক্সিকিউশন
কোটা রিসেট হলে `raipur_cloudflare_backend/migrations/0002_contract_and_lookup_indexes.sql` মাইগ্রেশনটি সরাসরি D1-তে রান করুন:
1. `saved_khatians` এবং `saved_voters`-এর `id` টেক্সট প্রাইমারি কি-তে কনভার্ট হবে।
2. `notes` কলাম যুক্ত হবে।
3. `voters` টেবিলে `source_pdf` কলাম এবং লুকআপ ইনডেক্সগুলো তৈরি হবে।

---

### ধাপ ৩: খতিয়ান ডেটা ইনজেশন (First Batch ~100k)
আমরা রেজুমেবল এবং আইডেমপোটেন্ট (Idempotent) সিঙ্ক স্ক্রিপ্ট রান করব যা:
1. আগে চেক করবে কোন খতিয়ানগুলো অলরেডি D1-তে আছে।
2. শুধুমাত্র মিসিং খতিয়ানগুলো ব্যাচে ইনসার্ট করবে।
3. দৈনিক ১০০,০০০ কোটা হিট করার সাথে সাথে নিরাপদে কারেন্ট স্টেট সেভ করে থেমে যাবে।

---

### ধাপ ৪: ক্লাউড ডিপ্লয়মেন্ট রান করা
```powershell
python deploy_to_cloudflare.py --apply
```
*(এই স্ক্রিপ্টটি স্বয়ংক্রিয়ভাবে D1 স্কিমা ও সিকিউরিটি টোকেন যাচাই করে প্রোডাকশনে Worker API পাবলিশ করবে।)*

