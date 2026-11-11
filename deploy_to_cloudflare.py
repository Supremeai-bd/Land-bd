import os
import sys
import urllib.request
import json

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

os.makedirs(os.path.dirname(deploy_html), exist_ok=True)
with open(deploy_html, "w", encoding="utf-8") as f:
    f.write(cloud_content)

print(f"   Compiled standalone cloud index.html ({len(cloud_content)} bytes)")

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

metadata = {
    "main_module": "index.js",
    "bindings": [
        {
            "type": "d1",
            "name": "DB",
            "id": db_id
        }
    ]
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
