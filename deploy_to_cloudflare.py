import os
import sys
import urllib.request
import json
import re

base_dir = os.path.dirname(os.path.abspath(__file__))
deploy_html = os.path.join(base_dir, "raipur_pages_deploy", "public", "index.html")
local_html = os.path.join(base_dir, "01_LIVE_SMART_PORTAL_APP", "Land_Intelligence_Hub.html")
rates_js = os.path.join(base_dir, "01_LIVE_SMART_PORTAL_APP", "raipur_registry_rates.js")
backend_js = os.path.join(base_dir, "raipur_cloudflare_backend", "src", "index.js")
env_file = os.path.join(base_dir, ".env")

print("1. Reading local application files...")
if not os.path.exists(local_html):
    print(f"Error: {local_html} not found!")
    sys.exit(1)

with open(local_html, "r", encoding="utf-8") as f:
    local_content = f.read()

with open(rates_js, "r", encoding="utf-8") as f:
    rates_content = f.read()

with open(backend_js, "r", encoding="utf-8") as f:
    backend_script = f.read()

target_str = '<script src="raipur_registry_rates.js"></script>'
replacement_str = f"<script>\n{rates_content}\n</script>"

if target_str in local_content:
    cloud_content = local_content.replace(target_str, replacement_str)
else:
    cloud_content = local_content.replace("</head>", f"{replacement_str}\n</head>")

# Large citizen/land datasets are local-only assets and are deliberately not
# committed or bundled into the Worker. Production reads from the D1 API.
for asset in ("raipur_full_database.js", "core_7_database.js", "raipur_voters_database.js"):
    pattern = re.compile(r'<script\s+src=["\']' + re.escape(asset) + r'["\']\s*>\s*</script>', re.IGNORECASE)
    cloud_content, removed = pattern.subn("", cloud_content)
    if removed != 1:
        raise SystemExit(f"Expected one {asset} script reference in the portal HTML; found {removed}.")

# Replace the local-global initializer so an API-only Worker never evaluates
# undefined globals after the local data assets have been removed.
database_pattern = re.compile(r"(?ms)^[ \t]*const DATABASE = \{.*?^[ \t]{8}\};")
cloud_content, database_replacements = database_pattern.subn(
    "        const DATABASE = { khatians: [], dagIndex: {}, voters: [] };",
    cloud_content,
    count=1,
)
if database_replacements != 1:
    raise SystemExit("Could not safely replace the local DATABASE initializer for the API-only Worker build.")

# Voter API access is authenticated; use the browser's session token.
voter_fetch_old = "const resp = await fetch('/api/voters?' + p.toString());"
voter_fetch_new = "const resp = await fetch('/api/voters?' + p.toString(), { headers: { 'Authorization': 'Bearer ' + getPortalAuthToken() } });"
if local_content.count(voter_fetch_old) < 1:
    raise SystemExit("Could not identify the online voter lookup call; refusing to deploy.")
cloud_content = cloud_content.replace(voter_fetch_old, voter_fetch_new)
token_helper = """<script>
function getPortalAuthToken() {
  const stores = [localStorage, sessionStorage];
  const knownKeys = ['auth_token', 'raipur_token', 'raipur_auth_token', 'access_token', 'token'];
  for (const store of stores) {
    for (const key of knownKeys) {
      const raw = store.getItem(key);
      if (raw) {
        const value = raw.replace(/^Bearer\\s+/i, '');
        if (value.split('.').length === 3) return value;
        try {
          const parsed = JSON.parse(value);
          const nested = parsed && (parsed.token || parsed.auth_token || parsed.accessToken);
          if (typeof nested === 'string' && nested.split('.').length === 3) return nested;
        } catch (_) {}
      }
    }
    for (const key of Object.keys(store)) {
      const raw = store.getItem(key);
      if (raw && raw.split('.').length === 3) return raw;
      if (raw && raw.startsWith('{')) {
        try {
          const parsed = JSON.parse(raw);
          const nested = parsed && (parsed.token || parsed.auth_token || parsed.accessToken);
          if (typeof nested === 'string' && nested.split('.').length === 3) return nested;
        } catch (_) {}
      }
    }
  }
  return '';
}
</script>"""
if "</head>" not in cloud_content:
    raise SystemExit("Portal HTML has no closing head tag; refusing to inject the auth-token helper.")
cloud_content = cloud_content.replace("</head>", token_helper + "\n</head>", 1)

os.makedirs(os.path.dirname(deploy_html), exist_ok=True)
with open(deploy_html, "w", encoding="utf-8") as f:
    f.write(cloud_content)

print(f"   Compiled standalone cloud index.html ({len(cloud_content)} bytes)")

if "--apply" not in sys.argv:
    print("Dry run only: no Cloudflare API request was made. Pass --apply to deploy the Worker.")
    sys.exit(0)

print("2. Reading credentials from environment or .env...")
creds = {}
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds[k.strip()] = v.strip().strip('"').strip("'")

# Read from OS environment first (for GitHub Actions CI/CD), fallback to .env
acc_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or creds.get("CLOUDFLARE_ACCOUNT_ID")
email = os.environ.get("CLOUDFLARE_EMAIL") or creds.get("CLOUDFLARE_EMAIL")
key = os.environ.get("CLOUDFLARE_GLOBAL_API_KEY") or creds.get("CLOUDFLARE_GLOBAL_API_KEY")
api_token = os.environ.get("CLOUDFLARE_API_TOKEN") or creds.get("CLOUDFLARE_API_TOKEN")
db_id = os.environ.get("CLOUDFLARE_D1_DATABASE_ID") or creds.get("CLOUDFLARE_D1_DATABASE_ID")
worker_name = os.environ.get("CLOUDFLARE_WORKER_NAME") or creds.get("CLOUDFLARE_WORKER_NAME", "raipur-land-portal")
live_url = os.environ.get("LIVE_PORTAL_URL") or creds.get("LIVE_PORTAL_URL", "https://raipur-land-portal.raipur-land.workers.dev")

if not (acc_id and db_id and ((email and key) or api_token)):
    print("Error: Missing Cloudflare credentials! Provide either (CLOUDFLARE_EMAIL + CLOUDFLARE_GLOBAL_API_KEY) or CLOUDFLARE_API_TOKEN.")
    sys.exit(1)

def d1_query(sql):
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/d1/database/{db_id}/query"
    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    else:
        headers["X-Auth-Email"] = email
        headers["X-Auth-Key"] = key
    payload = json.dumps({"sql": sql}).encode("utf-8")
    request = urllib.request.Request(url, data=payload, method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("success"):
        raise RuntimeError("D1 schema preflight query failed")
    return result.get("result", [{}])[0].get("results", [])

def require_migrated_d1_schema():
    # Read-only checks; migrations must be applied separately and reviewed.
    for sql in (
        "SELECT notes FROM saved_khatians LIMIT 0",
        "SELECT notes FROM saved_voters LIMIT 0",
        "SELECT source_pdf FROM voters LIMIT 0",
    ):
        d1_query(sql)
    for table in ("saved_khatians", "saved_voters"):
        rows = d1_query(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        ddl = " ".join(str(row.get("sql") or "") for row in rows).lower()
        if "id text primary key" not in " ".join(ddl.split()):
            raise RuntimeError(f"D1 migration required before Worker deploy: {table}.id must be TEXT PRIMARY KEY")
    expected_counts = {
        "khatians": int(os.environ.get("D1_EXPECTED_KHATIANS") or creds.get("D1_EXPECTED_KHATIANS", "157657")),
        "voters": int(os.environ.get("D1_EXPECTED_VOTERS") or creds.get("D1_EXPECTED_VOTERS", "492074")),
        "dag_khatian_map": int(os.environ.get("D1_EXPECTED_DAG_RELATIONS") or creds.get("D1_EXPECTED_DAG_RELATIONS", "418967")),
    }
    for table, expected in expected_counts.items():
        rows = d1_query(f"SELECT COUNT(*) AS total FROM {table}")
        if not rows or int(rows[0].get("total", -1)) != expected:
            actual = int(rows[0].get("total", -1)) if rows else -1
            raise RuntimeError(f"D1 completeness check failed for {table}: {actual:,} rows; expected exactly {expected:,}")

print(f"   Target Worker: {worker_name} (Account: {acc_id[:8]}...)")

# Build Worker bundle: embed HTML_CONTENT at the top and backend_script logic
escaped_html = cloud_content.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

# Inject HTML fallback into backend_script
if 'return new Response(JSON.stringify({ error: "Endpoint not found" })' in backend_script:
    backend_script = backend_script.replace(
        'return new Response(JSON.stringify({ error: "Endpoint not found" }), { status: 404, headers });',
        """if (url.pathname.startsWith("/api/")) {
        return new Response(JSON.stringify({ error: "Endpoint not found" }), { status: 404, headers });
      }
      return new Response(HTML_CONTENT, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-cache, no-store, must-revalidate"
        }
      });"""
    )

worker_script = f"const HTML_CONTENT = `{escaped_html}`;\n\n" + backend_script

print("3. Packaging and uploading Worker script to Cloudflare Edge...")
boundary = "---------------------------974767299852498929531610575"
body = []

bindings = [
    {
        "type": "d1",
        "name": "DB",
        "id": db_id
    }
]

token_secret = os.environ.get("TOKEN_SECRET") or creds.get("TOKEN_SECRET")
if not token_secret or len(token_secret.encode("utf-8")) < 32:
    print("Error: TOKEN_SECRET must be configured as a random value of at least 32 bytes; refusing insecure deployment.")
    sys.exit(1)
try:
    require_migrated_d1_schema()
except Exception as exc:
    print(f"Error: D1 is not ready for this Worker release: {exc}")
    print("Apply and verify the reviewed migrations in raipur_cloudflare_backend/migrations/ first.")
    sys.exit(1)
bindings.append({
    "type": "secret_text",
    "name": "TOKEN_SECRET",
    "text": token_secret
})

metadata = {
    "main_module": "index.js",
    "bindings": bindings
}

body.append(f"--{boundary}".encode())
body.append(b'Content-Disposition: form-data; name="metadata"; filename="metadata.json"')
body.append(b"Content-Type: application/json")
body.append(b"")
body.append(json.dumps(metadata).encode())

body.append(f"--{boundary}".encode())
body.append(b'Content-Disposition: form-data; name="index.js"; filename="index.js"')
body.append(b"Content-Type: application/javascript+module")
body.append(b"")
body.append(worker_script.encode("utf-8"))

body.append(f"--{boundary}--".encode())
body.append(b"")

payload = b"\r\n".join(body)

upload_url = f"https://api.cloudflare.com/client/v4/accounts/{acc_id}/workers/scripts/{worker_name}"
req_headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}"
}
if api_token:
    req_headers["Authorization"] = f"Bearer {api_token}"
else:
    req_headers["X-Auth-Email"] = email
    req_headers["X-Auth-Key"] = key

req = urllib.request.Request(upload_url, data=payload, method="PUT", headers=req_headers)

try:
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        if res.get("success"):
            print("======================================================================")
            print("   [SUCCESS] ক্লাউড সার্ভারলেস ডিপ্লয়মেন্ট সফল হয়েছে!")
            print(f"   লাইভ ইউআরএল: {live_url}")
            print("======================================================================")
        else:
            print("Upload Error:", res.get("errors"))
except urllib.error.HTTPError as e:
    print("Deployment Error:", e.read().decode("utf-8"))
    sys.exit(1)
