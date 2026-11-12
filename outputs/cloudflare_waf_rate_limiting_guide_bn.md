# Cloudflare WAF রেট লিমিটিং কনফিগারেশন নির্দেশিকা (Production WAF Rule Setup)

**প্রজেক্ট:** রায়পুর স্মার্ট ভূমি ও নাগরিক পোর্টাল (Raipur Land & Citizen Portal)  
**লক্ষ্য:** ডিস্ট্রিবিউটেড ব্রুট-ফোর্স ও স্ক্র্যাপিং রোধে Cloudflare এজ-স্তরে রেট লিমিট সক্রিয় করা।

---

## ১. Cloudflare ড্যাশবোর্ডে প্রবেশের ধাপ

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)-এ লগইন করুন।
2. আপনার অ্যাকাউন্ট ও ডোমেইন নির্বাচন করুন (অথবা Workers & Pages ট্যাবে যান)।
3. বাম পাশের মেনু থেকে **Security** ➔ **WAF (Web Application Firewall)** নির্বাচন করুন।
4. ওপরের ট্যাবগুলো থেকে **Rate limiting rules**-এ ক্লিক করুন।
5. **Create rule** বাটনে ক্লিক করুন।

---

## ২. রুল কনফিগারেশন প্যারামিটার (Rule Configuration)

### ক. রুলের নাম ও বর্ণনা
* **Rule name:** `Protect-Raipur-Auth-Endpoints`
* **Description:** `Rate limit brute-force attempts on login and registration endpoints`

### খ. ফিল্টার শর্ত (Expression Filter)
**Custom filter expression** অপশনে নিচের কোডটি হুবহু পেস্ট করুন:
```text
(http.request.uri.path in {"/api/auth/login" "/api/auth/register"})
```
*(অথবা ফিল্ড সিলেক্টরে: `URI Path` `is in` `/api/auth/login, /api/auth/register`)*

### গ. রেট লিমিট থ্রেশহোল্ড (Rate Limiting Criteria)
* **When rate exceeds:** `10 requests` (১০টি অনুরোধ)
* **Time window:** `1 minute` (১ মিনিট)
* **Count requests by:** `IP address` (ক্লায়েন্ট আইপি অনুসারে)

### ঘ. অ্যাকশন (Action when exceeded)
* **Choose action:** `Block` (অথবা সন্দেহজনক ট্রাফিকের জন্য `Managed Challenge`)
* **Response type:** `Custom JSON` (অথবা Default 429)
* **Duration:** `10 minutes` (১০ মিনিটের জন্য ব্লক থাকবে)
* **Custom JSON Response Body (ঐচ্ছিক):**
  ```json
  {
    "success": false,
    "error": "অতিরিক্ত অনুরোধ শনাক্ত হয়েছে। অনুগ্রহ করে ১০ মিনিট পর আবার চেষ্টা করুন।"
  }
  ```

---

## ৩. সংরক্ষণ ও সক্রিয়করণ
1. নিচে স্ক্রল করে **Deploy** বাটনে ক্লিক করুন।
2. রুলটি সক্রিয় হলে স্ট্যাটাস **Active** হিসেবে প্রদর্শিত হবে।
3. এটি ব্যাকএন্ড ওয়ার্কারে পৌঁছানোর আগেই Cloudflare-এর বৈশ্বিক এজ নেটওয়ার্ক থেকেই ক্ষতিকর ট্রাফিক প্রতিহত করবে।

