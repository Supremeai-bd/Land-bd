/**
 * Raipur Land & Citizen Intelligence Portal - Cloudflare Worker Backend
 * Includes Cadastral Search, Auth, Role Approval & Saved Vault Endpoints
 */

async function sha256(str) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
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

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const headers = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
      "Content-Type": "application/json; charset=utf-8"
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers });
    }

    try {
      // 1. Cadastral search endpoint
      if (url.pathname === "/api/search") {
        const mouza = url.searchParams.get("mouza") || "ALL";
        const survey = url.searchParams.get("survey") || "ALL";
        const dag = (url.searchParams.get("dag") || "").trim();
        const khatian = (url.searchParams.get("khatian") || "").trim();
        const name = (url.searchParams.get("name") || "").trim();
        const father = (url.searchParams.get("father") || "").trim();

        let sabekRecords = [];
        let haalRecords = [];

        if (dag) {
          let dagQuery = "SELECT k.* FROM dag_khatian_map m JOIN khatians k ON m.mouza = k.mouza AND m.survey = k.survey AND m.khatian_no = k.khatian_no WHERE m.dag_no = ?";
          let params = [dag];
          if (mouza !== "ALL") { dagQuery += " AND m.mouza = ?"; params.push(mouza); }
          if (survey !== "ALL") { dagQuery += " AND m.survey = ?"; params.push(survey); }
          dagQuery += " LIMIT 200";

          const { results } = await env.DB.prepare(dagQuery).bind(...params).all();
          (results || []).forEach(r => {
            const item = {
              mouza: r.mouza,
              survey: r.survey,
              khatianNo: r.khatian_no,
              khatian_no: r.khatian_no,
              owners: parseArrayField(r.owners),
              guardian: r.guardian || "—",
              dags: parseArrayField(r.dags),
              totalLand: r.total_land || "—"
            };
            if (r.survey === "CS" || r.survey === "SA") sabekRecords.push(item);
            else haalRecords.push(item);
          });
        }

        if (khatian) {
          let kQuery = "SELECT * FROM khatians WHERE khatian_no = ?";
          let params = [khatian];
          if (mouza !== "ALL") { kQuery += " AND mouza = ?"; params.push(mouza); }
          if (survey !== "ALL") { kQuery += " AND survey = ?"; params.push(survey); }
          kQuery += " LIMIT 200";

          const { results } = await env.DB.prepare(kQuery).bind(...params).all();
          (results || []).forEach(r => {
            const item = {
              mouza: r.mouza,
              survey: r.survey,
              khatianNo: r.khatian_no,
              khatian_no: r.khatian_no,
              owners: parseArrayField(r.owners),
              guardian: r.guardian || "—",
              dags: parseArrayField(r.dags),
              totalLand: r.total_land || "—"
            };
            if (r.survey === "CS" || r.survey === "SA") sabekRecords.push(item);
            else haalRecords.push(item);
          });
        }

        if (name) {
          let nQuery = "SELECT * FROM khatians WHERE owners LIKE ?";
          let params = [`%${name}%`];
          if (mouza !== "ALL") { nQuery += " AND mouza = ?"; params.push(mouza); }
          if (survey !== "ALL") { nQuery += " AND survey = ?"; params.push(survey); }
          nQuery += " LIMIT 150";

          const { results } = await env.DB.prepare(nQuery).bind(...params).all();
          (results || []).forEach(r => {
            const item = {
              mouza: r.mouza,
              survey: r.survey,
              khatianNo: r.khatian_no,
              khatian_no: r.khatian_no,
              owners: parseArrayField(r.owners),
              guardian: r.guardian || "—",
              dags: parseArrayField(r.dags),
              totalLand: r.total_land || "—"
            };
            if (r.survey === "CS" || r.survey === "SA") sabekRecords.push(item);
            else haalRecords.push(item);
          });
        }

        if (father) {
          let fQuery = "SELECT * FROM khatians WHERE guardian LIKE ?";
          let params = [`%${father}%`];
          if (mouza !== "ALL") { fQuery += " AND mouza = ?"; params.push(mouza); }
          if (survey !== "ALL") { fQuery += " AND survey = ?"; params.push(survey); }
          fQuery += " LIMIT 150";

          const { results } = await env.DB.prepare(fQuery).bind(...params).all();
          (results || []).forEach(r => {
            const item = {
              mouza: r.mouza,
              survey: r.survey,
              khatianNo: r.khatian_no,
              khatian_no: r.khatian_no,
              owners: parseArrayField(r.owners),
              guardian: r.guardian || "—",
              dags: parseArrayField(r.dags),
              totalLand: r.total_land || "—"
            };
            if (r.survey === "CS" || r.survey === "SA") sabekRecords.push(item);
            else haalRecords.push(item);
          });
        }

        return new Response(JSON.stringify({ success: true, sabekRecords, haalRecords }), { headers });
      }

      // 2. Authentication: Register
      if (url.pathname === "/api/auth/register" && request.method === "POST") {
        const body = await request.json();
        const { phone, name, password, role, association_license_no } = body;

        if (!phone || !name || !password) {
          return new Response(JSON.stringify({ success: false, error: "নাম, ফোন ও পাসওয়ার্ড আবশ্যক" }), { status: 400, headers });
        }

        const cleanPhone = phone.trim();
        const pHash = await sha256(password);
        const userId = "u_" + Math.random().toString(36).substr(2, 9);
        const userRole = role === "deed_writer" ? "deed_writer" : "citizen";
        const status = userRole === "deed_writer" ? "pending" : "active";

        const existing = await env.DB.prepare("SELECT id FROM users WHERE phone = ?").bind(cleanPhone).first();
        if (existing) {
          return new Response(JSON.stringify({ success: false, error: "এই মোবাইল নম্বরে ইতিমধ্যে একাউন্ট রয়েছে।" }), { status: 409, headers });
        }

        await env.DB.prepare(
          "INSERT INTO users (id, phone, name, role, status, association_license_no, password_hash) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind(userId, cleanPhone, name.trim(), userRole, status, association_license_no || null, pHash).run();

        return new Response(JSON.stringify({
          success: true,
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
        const body = await request.json();
        const { phone, password } = body;

        if (!phone || !password) {
          return new Response(JSON.stringify({ success: false, error: "মোবাইল নম্বর ও পাসওয়ার্ড প্রদান করুন" }), { status: 400, headers });
        }

        const pHash = await sha256(password);
        const user = await env.DB.prepare(
          "SELECT id, phone, name, role, status, association_license_no FROM users WHERE phone = ? AND password_hash = ?"
        ).bind(phone.trim(), pHash).first();

        if (!user) {
          return new Response(JSON.stringify({ success: false, error: "ভুল মোবাইল নম্বর অথবা পাসওয়ার্ড!" }), { status: 401, headers });
        }

        return new Response(JSON.stringify({
          success: true,
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

      // 4. Admin Management: Pending deed writers
      if (url.pathname === "/api/admin/writers/pending") {
        const { results } = await env.DB.prepare(
          "SELECT id, phone, name, role, status, association_license_no, created_at FROM users WHERE role = 'deed_writer' AND status = 'pending' ORDER BY created_at DESC"
        ).all();
        return new Response(JSON.stringify({ success: true, pendingWriters: results || [] }), { headers });
      }

      // 5. Admin Management: Approve / Reject writer
      if (url.pathname === "/api/admin/writers/action" && request.method === "POST") {
        const body = await request.json();
        const { userId, action, adminId } = body;

        if (!userId || !action) {
          return new Response(JSON.stringify({ success: false, error: "userId ও action আবশ্যক" }), { status: 400, headers });
        }

        const newStatus = action === "approve" ? "active" : "rejected";
        await env.DB.prepare(
          "UPDATE users SET status = ?, approved_by = ?, approved_at = CURRENT_TIMESTAMP WHERE id = ?"
        ).bind(newStatus, adminId || "admin", userId).run();

        return new Response(JSON.stringify({ success: true, newStatus }), { headers });
      }

      // 6. Voter search endpoint (D1)
      if (url.pathname === "/api/voters") {
        const voterNo = (url.searchParams.get("voter_no") || "").trim();
        const name = (url.searchParams.get("name") || "").trim();
        const father = (url.searchParams.get("father") || "").trim();
        const mother = (url.searchParams.get("mother") || "").trim();
        const ward = (url.searchParams.get("ward") || "").trim();
        const address = (url.searchParams.get("address") || "").trim();

        let query = "SELECT voter_no, name, father, mother, gender, ward, address FROM voters WHERE 1=1";
        const params = [];
        if (voterNo) { query += " AND voter_no LIKE ?"; params.push(`%${voterNo}%`); }
        if (name) { query += " AND name LIKE ?"; params.push(`%${name}%`); }
        if (father) { query += " AND father LIKE ?"; params.push(`%${father}%`); }
        if (mother) { query += " AND mother LIKE ?"; params.push(`%${mother}%`); }
        if (ward) { query += " AND (ward LIKE ? OR address LIKE ?)"; params.push(`%${ward}%`, `%${ward}%`); }
        if (address) { query += " AND address LIKE ?"; params.push(`%${address}%`); }
        query += " LIMIT 200";

        try {
          const { results } = await env.DB.prepare(query).bind(...params).all();
          const voters = (results || []).map(v => ({
            voterNo: v.voter_no || "",
            name: v.name || "",
            father: v.father || "",
            mother: v.mother || "",
            gender: v.gender || "",
            ward: v.ward || "",
            address: v.address || ""
          }));
          return new Response(JSON.stringify({ success: true, voters }), { headers });
        } catch (err) {
          return new Response(JSON.stringify({ success: false, error: "voters table unavailable: " + err.message, voters: [] }), { status: 500, headers });
        }
      }

      // 7. User Vault: Save / List items
      if (url.pathname === "/api/user/saved-items") {
        const userId = url.searchParams.get("userId");
        if (!userId) {
          return new Response(JSON.stringify({ success: false, error: "userId আবশ্যক" }), { status: 400, headers });
        }

        const khatians = await env.DB.prepare("SELECT * FROM saved_khatians WHERE user_id = ? ORDER BY saved_at DESC").bind(userId).all();
        const voters = await env.DB.prepare("SELECT * FROM saved_voters WHERE user_id = ? ORDER BY saved_at DESC").bind(userId).all();

        return new Response(JSON.stringify({
          success: true,
          savedKhatians: khatians.results || [],
          savedVoters: voters.results || []
        }), { headers });
      }

      if (url.pathname === "/api/user/save-khatian" && request.method === "POST") {
        const body = await request.json();
        const { userId, mouza, survey, khatian_no, dag_summary, owners_summary, notes } = body;
        if (!userId || !khatian_no) {
          return new Response(JSON.stringify({ success: false, error: "তথ্যাদি অসম্পূর্ণ" }), { status: 400, headers });
        }

        await env.DB.prepare(
          "INSERT INTO saved_khatians (user_id, mouza, survey, khatian_no, dag_summary, owners_summary, notes) VALUES (?, ?, ?, ?, ?, ?, ?)"
        ).bind(userId, mouza, survey, khatian_no, dag_summary || "", owners_summary || "", notes || "").run();

        return new Response(JSON.stringify({ success: true }), { headers });
      }

      if (url.pathname === "/api/user/save-voter" && request.method === "POST") {
        const body = await request.json();
        const { userId, voter_no, name, father, mother, ward, address, relation_tag } = body;
        if (!userId || !voter_no) {
          return new Response(JSON.stringify({ success: false, error: "তথ্যাদি অসম্পূর্ণ" }), { status: 400, headers });
        }

        await env.DB.prepare(
          "INSERT INTO saved_voters (user_id, voter_no, name, father, mother, ward, address, relation_tag) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        ).bind(userId, voter_no, name || "", father || "", mother || "", ward || "", address || "", relation_tag || "").run();

        return new Response(JSON.stringify({ success: true }), { headers });
      }

      return new Response(JSON.stringify({ error: "Endpoint not found" }), { status: 404, headers });

    } catch (err) {
      return new Response(JSON.stringify({ success: false, error: err.message }), { status: 500, headers });
    }
  }
};
