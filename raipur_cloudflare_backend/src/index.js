/**
 * Raipur Land & Citizen Intelligence Portal - Cloudflare Worker Backend
 * Secured Production Engine:
 *  - PBKDF2 with Salt Password Hashing
 *  - Cryptographic Session Token Verification
 *  - Strict Admin Authorization
 *  - User-Scoped Saved Vault Endpoints
 *  - Wildcard Input Sanitization against DB Scraping
 *  - Unified Cadastre Search Helpers
 */

function getTokenSecret(env) {
  const secret = env && env.TOKEN_SECRET;
  if (typeof secret !== "string" || new TextEncoder().encode(secret).length < 32) return null;
  return secret;
}

// 1. Password Hashing: PBKDF2 with Salt (Zero Unsalted Hashes)
async function hashPassword(password, saltHex = null) {
  const enc = new TextEncoder();
  const salt = saltHex ? hexToBytes(saltHex) : crypto.getRandomValues(new Uint8Array(16));
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    { name: "PBKDF2" },
    false,
    ["deriveBits", "deriveKey"]
  );
  const derivedKey = await crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt: salt,
      iterations: 100000,
      hash: "SHA-256"
    },
    keyMaterial,
    { name: "HMAC", hash: "SHA-256", length: 256 },
    true,
    ["sign"]
  );
  const exported = await crypto.subtle.exportKey("raw", derivedKey);
  const hashHex = bytesToHex(new Uint8Array(exported));
  const saltOut = bytesToHex(salt);
  return { hash: `pbkdf2:${saltOut}:${hashHex}`, salt: saltOut };
}

async function verifyPassword(password, storedHash) {
  if (!storedHash) return false;
  // If legacy unsalted sha256
  if (!storedHash.startsWith("pbkdf2:")) {
    const legacyBuf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(password));
    const legacyHex = bytesToHex(new Uint8Array(legacyBuf));
    return legacyHex === storedHash;
  }
  const parts = storedHash.split(":");
  if (parts.length !== 3) return false;
  const saltHex = parts[1];
  const { hash } = await hashPassword(password, saltHex);
  return hash === storedHash;
}

// 2. Cryptographic Session Token (HMAC SHA-256)
async function generateSessionToken(userId, role, secret) {
  const enc = new TextEncoder();
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const exp = Date.now() + (7 * 24 * 60 * 60 * 1000); // 7 days (reduced from 30 days)
  const payload = btoa(JSON.stringify({ sub: userId, role, exp }));
  const dataToSign = `${header}.${payload}`;

  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const signatureBuf = await crypto.subtle.sign("HMAC", key, enc.encode(dataToSign));
  const sig = bytesToHex(new Uint8Array(signatureBuf));
  return `${dataToSign}.${sig}`;
}

async function verifySessionToken(authHeader, secret) {
  if (typeof secret !== "string" || !secret || !authHeader || !authHeader.startsWith("Bearer ")) return null;
  const token = authHeader.substring(7).trim();
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  const [header, payload, sig] = parts;
  const dataToSign = `${header}.${payload}`;

  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );

  const isValid = await crypto.subtle.verify("HMAC", key, hexToBytes(sig), enc.encode(dataToSign));
  if (!isValid) return null;

  try {
    const headerObj = JSON.parse(atob(header));
    const payloadObj = JSON.parse(atob(payload));
    if (headerObj.alg !== "HS256" || !payloadObj || typeof payloadObj.sub !== "string" || !payloadObj.sub) return null;
    if (typeof payloadObj.exp !== "number" || !Number.isFinite(payloadObj.exp) || Date.now() >= payloadObj.exp) return null;
    if (typeof payloadObj.role !== "string" || !payloadObj.role) return null;
    return payloadObj;
  } catch (e) {
    return null;
  }
}

async function authenticateActiveUser(request, env, secret) {
  if (!secret) return null;
  const claims = await verifySessionToken(request.headers.get("Authorization"), secret);
  if (!claims) return null;
  const user = await env.DB.prepare("SELECT id, role, status FROM users WHERE id = ?").bind(claims.sub).first();
  if (!user || user.status !== "active") return null;
  return { ...claims, role: user.role };
}

// 3. Helpers
function bytesToHex(bytes) {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

function hexToBytes(hex) {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < bytes.length; i++) {
    bytes[i] = parseInt(hex.substr(i * 2, 2), 16);
  }
  return bytes;
}

function escapeSqlWildcards(str) {
  return str.replace(/[%_\\]/g, "\\$&");
}

function parseArrayField(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val;
  val = String(val).trim();
  if (val.startsWith("[") && val.endsWith("]")) {
    try {
      return JSON.parse(val);
    } catch (e) {}
  }
  return val.split(",").map(s => s.trim()).filter(Boolean);
}

function mapKhatianRow(r) {
  return {
    mouza: r.mouza,
    survey: r.survey,
    khatianNo: String(r.khatian_no),
    owners: parseArrayField(r.owners),
    guardian: r.guardian || "—",
    dags: parseArrayField(r.dags),
    totalLand: r.total_land || "—"
  };
}

export default {
  async fetch(request, env) {
    const tokenSecret = getTokenSecret(env);
    const url = new URL(request.url);
    const origin = request.headers.get("Origin") || "";
    const allowedOrigins = [
      "https://raipur-land-portal.raipur-land.workers.dev",
      "https://data.supremeai.bd"
    ];
    const isDev = env && env.ENVIRONMENT === "development";
    const isAllowedOrigin = allowedOrigins.includes(origin) || (isDev && (origin.startsWith("http://localhost:") || origin.startsWith("http://127.0.0.1:")));
    const allowOriginHeader = isAllowedOrigin ? origin : (origin ? allowedOrigins[0] : "*");

    const headers = {
      "Access-Control-Allow-Origin": allowOriginHeader,
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Vary": "Origin",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Content-Type": "application/json; charset=utf-8"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    // Basic rate limiting (per IP) for authentication endpoints
    const clientIP = request.headers.get("CF-Connecting-IP") || "unknown";
    if (url.pathname.startsWith("/api/auth/")) {
      const rateLimitKey = `rate_${clientIP}`;
      const now = Date.now();
      const windowMs = 60 * 1000; // 1 minute
      const maxRequests = 10;
      if (!globalThis._rateLimitMap) globalThis._rateLimitMap = new Map();
      const record = globalThis._rateLimitMap.get(rateLimitKey) || { count: 0, resetAt: now + windowMs };
      if (now > record.resetAt) {
        record.count = 0;
        record.resetAt = now + windowMs;
      }
      record.count++;
      globalThis._rateLimitMap.set(rateLimitKey, record);
      if (record.count > maxRequests) {
        return new Response(JSON.stringify({ success: false, error: "অতিরিক্ত অনুরোধ। কিছুক্ষণ পর আবার চেষ্টা করুন।" }), { status: 429, headers });
      }
    }

    try {
      // 1. Cadastral search endpoint
      if (url.pathname === "/api/search") {
        const mouza = url.searchParams.get("mouza") || "ALL";
        const survey = url.searchParams.get("survey") || "ALL";
        const dag = escapeSqlWildcards((url.searchParams.get("dag") || "").trim());
        const khatian = escapeSqlWildcards((url.searchParams.get("khatian") || "").trim());
        const name = escapeSqlWildcards((url.searchParams.get("name") || "").trim());
        const father = escapeSqlWildcards((url.searchParams.get("father") || "").trim());

        let sabekRecords = [];
        let haalRecords = [];

        let query = "";
        let params = [];

        if (dag) {
          query = "SELECT k.* FROM dag_khatian_map m JOIN khatians k ON m.mouza = k.mouza AND m.survey = k.survey AND m.khatian_no = k.khatian_no WHERE m.dag_no = ?";
          params = [dag];
        } else if (khatian) {
          query = "SELECT k.* FROM khatians k WHERE k.khatian_no = ?";
          params = [khatian];
        } else if (name) {
          query = "SELECT k.* FROM khatians k WHERE k.owners LIKE ? ESCAPE '\\'";
          params = [`%${name}%`];
        } else if (father) {
          query = "SELECT k.* FROM khatians k WHERE k.guardian LIKE ? ESCAPE '\\'";
          params = [`%${father}%`];
        }

        if (query) {
          if (mouza !== "ALL") { query += " AND k.mouza = ?"; params.push(mouza); }
          if (survey !== "ALL") {
            if (survey === "SABEK") {
              query += " AND k.survey IN ('CS', 'SA', 'RS', 'সাবেক')";
            } else if (survey === "HAAL") {
              query += " AND k.survey IN ('BRS', 'Mutation', 'নামজারি', 'হাল')";
            } else {
              query += " AND k.survey = ?";
              params.push(survey);
            }
          }
          query += " LIMIT 100";

          const { results } = await env.DB.prepare(query).bind(...params).all();
          (results || []).forEach(r => {
            const item = mapKhatianRow(r);
            if (["BRS", "Mutation", "নামজারি", "হাল"].includes(item.survey)) {
              haalRecords.push(item);
            } else {
              sabekRecords.push(item);
            }
          });
        }

        // Distinct mouzas for dropdown
        const mouzaRows = await env.DB.prepare("SELECT DISTINCT mouza FROM khatians WHERE mouza IS NOT NULL ORDER BY mouza ASC").all();
        const distinctMouzas = (mouzaRows.results || []).map(r => r.mouza).filter(Boolean);

        return new Response(JSON.stringify({
          success: true,
          count: sabekRecords.length + haalRecords.length,
          sabekRecords,
          haalRecords,
          distinctMouzas
        }), { headers });
      }

      // 2. Authentication: Register
      if (url.pathname === "/api/auth/register" && request.method === "POST") {
        if (!tokenSecret) return new Response(JSON.stringify({ success: false, error: "Authentication is temporarily unavailable." }), { status: 503, headers });
        const body = await request.json();
        const { phone, name, password, role, association_license_no } = body;

        if (!phone || !name || !password) {
          return new Response(JSON.stringify({ success: false, error: "নাম, ফোন ও পাসওয়ার্ড আবশ্যক" }), { status: 400, headers });
        }

        const cleanPhone = phone.trim();
        if (!/^01[3-9]\d{8}$/.test(cleanPhone)) {
          return new Response(JSON.stringify({ success: false, error: "সঠিক ১১ ডিজিটের বাংলাদেশী মোবাইল নম্বর দিন (যেমন: 017xxxxxxxx)" }), { status: 400, headers });
        }
        // Stronger password policy: min 8 chars, at least one number and one special character
        if (password.length < 8 || !/\d/.test(password) || !/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
          return new Response(JSON.stringify({ success: false, error: "পাসওয়ার্ড ন্যূনতম ৮ অক্ষরের হতে হবে এবং কমপক্ষে একটি সংখ্যা ও একটি বিশেষ চিহ্ন থাকতে হবে।" }), { status: 400, headers });
        }
        // Validate association_license_no for deed writers
        if (role === "deed_writer" && (!association_license_no || String(association_license_no).trim().length < 5)) {
          return new Response(JSON.stringify({ success: false, error: "দলিল লেখকদের জন্য বৈধ অ্যাসোসিয়েশন লাইসেন্স নম্বর আবশ্যক।" }), { status: 400, headers });
        }

        const { hash: pHash } = await hashPassword(password);
        const userId = "u_" + crypto.randomUUID().replace(/-/g, "").substring(0, 12);
        const userRole = role === "deed_writer" ? "deed_writer" : "citizen";
        const status = userRole === "deed_writer" ? "pending" : "active";

        const existing = await env.DB.prepare("SELECT id FROM users WHERE phone = ?").bind(cleanPhone).first();
        if (existing) {
          return new Response(JSON.stringify({ success: false, error: "এই মোবাইল নম্বরে ইতিমধ্যে একাউন্ট রয়েছে।" }), { status: 409, headers });
        }

        await env.DB.prepare(
          "INSERT INTO users (id, phone, name, role, status, association_license_no, password_hash) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind(userId, cleanPhone, name.trim(), userRole, status, association_license_no || null, pHash).run();

        const token = await generateSessionToken(userId, userRole, tokenSecret);

        return new Response(JSON.stringify({
          success: true,
          token,
          user: {
            id: userId,
            phone: cleanPhone,
            name: name.trim(),
            role: userRole,
            status,
            association_license_no
          },
          message: status === "pending"
            ? "দলিল লেখক রেজিস্ট্রেশন সম্পন্ন হয়েছে। এডমিন অনুমোদনের পর প্রো মোড চালু হবে।"
            : "সফলভাবে রেজিস্ট্রেশন সম্পন্ন হয়েছে।"
        }), { headers });
      }

      // 3. Authentication: Login
      if (url.pathname === "/api/auth/login" && request.method === "POST") {
        if (!tokenSecret) return new Response(JSON.stringify({ success: false, error: "Authentication is temporarily unavailable." }), { status: 503, headers });
        const body = await request.json();
        const { phone, password } = body;

        if (!phone || !password) {
          return new Response(JSON.stringify({ success: false, error: "মোবাইল নম্বর ও পাসওয়ার্ড প্রদান করুন" }), { status: 400, headers });
        }

        const cleanPhone = phone.trim();
        const user = await env.DB.prepare(
          "SELECT id, phone, name, role, status, association_license_no, password_hash FROM users WHERE phone = ?"
        ).bind(cleanPhone).first();

        if (!user || user.status !== "active" || !(await verifyPassword(password, user.password_hash))) {
          return new Response(JSON.stringify({ success: false, error: "ভুল মোবাইল নম্বর অথবা পাসওয়ার্ড!" }), { status: 401, headers });
        }

        const token = await generateSessionToken(user.id, user.role, tokenSecret);

        return new Response(JSON.stringify({
          success: true,
          token,
          user: {
            id: user.id,
            phone: user.phone,
            name: user.name,
            role: user.role,
            status: user.status,
            association_license_no: user.association_license_no
          }
        }), { headers });
      }

      // 4. Admin Management: Pending deed writers (AUTHENTICATED ADMIN ONLY)
      if (url.pathname === "/api/admin/writers/pending") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth || (auth.role !== "admin" && auth.role !== "superadmin")) {
          return new Response(JSON.stringify({ success: false, error: "অননুমোদিত অ্যাক্সেস! শুধুমাত্র এডমিন প্রবেশাধিকার।" }), { status: 403, headers });
        }

        const { results } = await env.DB.prepare(
          "SELECT id, phone, name, role, status, association_license_no, created_at FROM users WHERE role = 'deed_writer' AND status = 'pending' ORDER BY created_at DESC"
        ).all();
        return new Response(JSON.stringify({ success: true, pendingWriters: results || [] }), { headers });
      }

      // 5. Admin Management: Approve / Reject writer (AUTHENTICATED ADMIN ONLY)
      if (url.pathname === "/api/admin/writers/action" && request.method === "POST") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth || (auth.role !== "admin" && auth.role !== "superadmin")) {
          return new Response(JSON.stringify({ success: false, error: "অননুমোদিত অ্যাক্সেস! শুধুমাত্র এডমিন অনুমোদন দিতে পারেন।" }), { status: 403, headers });
        }

        const body = await request.json();
        const { userId, action } = body;
        if (!userId || !action) {
          return new Response(JSON.stringify({ success: false, error: "userId ও action আবশ্যক" }), { status: 400, headers });
        }

        const newStatus = action === "approve" ? "active" : "rejected";
        await env.DB.prepare(
          "UPDATE users SET status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?"
        ).bind(newStatus, auth.sub, userId).run();

        return new Response(JSON.stringify({ success: true, newStatus }), { headers });
      }

      // 6. Restricted voter lookup: active, approved deed writers/admins only.
      if (url.pathname === "/api/voters") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth) return new Response(JSON.stringify({ success: false, error: "লগইন আবশ্যক" }), { status: 401, headers });
        if (!["deed_writer", "admin", "superadmin"].includes(auth.role)) {
          return new Response(JSON.stringify({ success: false, error: "অনুমোদিত দলিল লেখক বা এডমিন অ্যাক্সেস প্রয়োজন" }), { status: 403, headers });
        }

        const voterNo = escapeSqlWildcards((url.searchParams.get("voter_no") || "").trim());
        const name = escapeSqlWildcards((url.searchParams.get("name") || "").trim());
        const father = escapeSqlWildcards((url.searchParams.get("father") || "").trim());
        if (voterNo && (name || father)) return new Response(JSON.stringify({ success: false, error: "একবারে একটি নির্দিষ্ট অনুসন্ধান শর্ত দিন" }), { status: 400, headers });
        if (!voterNo && ((!name && !father) || (name && name.length < 3) || (father && father.length < 3))) {
          return new Response(JSON.stringify({ success: false, error: "ভোটার নম্বর অথবা কমপক্ষে ৩ অক্ষরের নাম/পিতার নাম দিন" }), { status: 400, headers });
        }

        let query = "SELECT voter_no, name, father, ward FROM voters WHERE ";
        let params;
        if (voterNo) {
          query += "voter_no = ?";
          params = [voterNo];
        } else if (name) {
          query += "name LIKE ? ESCAPE '\\'";
          params = [`%${name}%`];
        } else {
          query += "father LIKE ? ESCAPE '\\'";
          params = [`%${father}%`];
        }
        query += " LIMIT 5";

        try {
          const { results } = await env.DB.prepare(query).bind(...params).all();
          const voters = (results || []).map(v => ({
            voterNo: v.voter_no || "",
            name: v.name || "",
            father: v.father || "",
            ward: v.ward || ""
          }));
          return new Response(JSON.stringify({ success: true, voters }), { headers });
        } catch (err) {
          return new Response(JSON.stringify({ success: false, error: "ভোটার ডেটাবেস অনুসন্ধান সম্পন্ন করা যায়নি।", voters: [] }), { status: 500, headers });
        }
      }

      // 7. User Vault: Save / List items (USER AUTHENTICATED)
      if (url.pathname === "/api/user/saved-items") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth) {
          return new Response(JSON.stringify({ success: false, error: "লগইন আবশ্যক" }), { status: 401, headers });
        }

        const khatians = await env.DB.prepare("SELECT * FROM saved_khatians WHERE user_id = ? ORDER BY saved_at DESC").bind(auth.sub).all();
        const voters = await env.DB.prepare("SELECT * FROM saved_voters WHERE user_id = ? ORDER BY saved_at DESC").bind(auth.sub).all();

        return new Response(JSON.stringify({
          success: true,
          savedKhatians: khatians.results || [],
          savedVoters: voters.results || []
        }), { headers });
      }

      if (url.pathname === "/api/user/save-khatian" && request.method === "POST") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth) {
          return new Response(JSON.stringify({ success: false, error: "লগইন আবশ্যক" }), { status: 401, headers });
        }

        const body = await request.json();
        const { mouza, survey, khatian_no, dag_summary, owners_summary, notes } = body;
        const id = "sk_" + crypto.randomUUID().replace(/-/g, "").substring(0, 12);

        await env.DB.prepare(
          "INSERT INTO saved_khatians (id, user_id, mouza, survey, khatian_no, dag_summary, owners_summary, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(id, auth.sub, mouza, survey, khatian_no, dag_summary || "", owners_summary || "", notes || "").run();

        return new Response(JSON.stringify({ success: true, id }), { headers });
      }

      if (url.pathname === "/api/user/save-voter" && request.method === "POST") {
        const auth = await authenticateActiveUser(request, env, tokenSecret);
        if (!auth) {
          return new Response(JSON.stringify({ success: false, error: "লগইন আবশ্যক" }), { status: 401, headers });
        }

        const body = await request.json();
        const { voter_no, name, father, mother, ward, address, notes } = body;
        const id = "sv_" + crypto.randomUUID().replace(/-/g, "").substring(0, 12);

        await env.DB.prepare(
          "INSERT INTO saved_voters (id, user_id, voter_no, name, father, mother, ward, address, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(id, auth.sub, voter_no, name, father || "", mother || "", ward || "", address || "", notes || "").run();

        return new Response(JSON.stringify({ success: true, id }), { headers });
      }

      // Default 404
      return new Response(JSON.stringify({ error: "Endpoint not found" }), { status: 404, headers });

    } catch (e) {
      console.error("Worker runtime error:", e);
      return new Response(JSON.stringify({ success: false, error: "সার্ভারে সাময়িক সমস্যা দেখা দিয়েছে।" }), { status: 500, headers });
    }
  }
};
