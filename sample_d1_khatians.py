import json, urllib.request

creds = {}
with open('F:/khotiyan book/.env', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            creds[k.strip()] = v.strip().strip('"').strip("'")

acc_id = creds['CLOUDFLARE_ACCOUNT_ID']
email = creds['CLOUDFLARE_EMAIL']
key = creds['CLOUDFLARE_GLOBAL_API_KEY']
db_id = creds['CLOUDFLARE_D1_DATABASE_ID']

query_url = f'https://api.cloudflare.com/client/v4/accounts/{acc_id}/d1/database/{db_id}/query'
headers = {'X-Auth-Email': email, 'X-Auth-Key': key, 'Content-Type': 'application/json'}

req = urllib.request.Request(query_url, data=json.dumps({'sql': 'SELECT * FROM khatians WHERE mouza = "দেবীপুর" LIMIT 2'}).encode(), headers=headers)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode())
    print('Sample দেবীপুর rows in D1:')
    for r in res['result'][0]['results']:
        print(r)

